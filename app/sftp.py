"""SFTP upload / download. One connection per request; paths are confined to the base directory."""
import datetime as dt
import io
import logging
import posixpath
import stat
from contextlib import contextmanager

import paramiko

from .config import Config, SftpConfig
from .errors import ApiError
from .files import safe_filename

log = logging.getLogger(__name__)


@contextmanager
def connect(cfg: SftpConfig):
    if not cfg.configured:
        raise ApiError('SFTP server is not configured', 503)
    client = paramiko.SSHClient()
    if cfg.known_hosts:
        client.load_host_keys(cfg.known_hosts)
    else:
        client.load_system_host_keys()
    # Unknown host keys are refused unless SFTP_STRICT_HOST_KEY=false (local test servers).
    client.set_missing_host_key_policy(
        paramiko.RejectPolicy() if cfg.strict_host_key else paramiko.AutoAddPolicy())
    pkey = None
    if cfg.private_key_file:
        pkey = paramiko.PKey.from_path(cfg.private_key_file, passphrase=cfg.private_key_passphrase or None)
    try:
        client.connect(cfg.host, cfg.port, username=cfg.username, password=cfg.password or None, pkey=pkey,
                       timeout=cfg.timeout, banner_timeout=cfg.timeout, auth_timeout=cfg.timeout,
                       allow_agent=False, look_for_keys=False)
        sftp = client.open_sftp()
    except paramiko.AuthenticationException:
        client.close()
        log.error('SFTP authentication failed for %s@%s', cfg.username, cfg.host)
        raise ApiError('SFTP authentication failed', 502) from None
    except (paramiko.SSHException, OSError) as err:
        client.close()
        log.error('SFTP connection failed: %s', err)
        raise ApiError('Could not connect to the SFTP server', 502) from None
    try:
        yield sftp
    finally:
        sftp.close()
        client.close()


def base_dir(sftp, cfg: SftpConfig) -> str:
    return posixpath.normpath(sftp.normalize(cfg.base_dir or '.'))


def resolve(base: str, path, filename) -> str:
    """Remote path of `path/filename` (relative to the base directory); refuses anything outside it."""
    name = safe_filename(filename)
    folder = str(path or '')
    full = posixpath.normpath(posixpath.join(base, folder, name))
    if full != base and not full.startswith(base.rstrip('/') + '/'):
        raise ApiError(f'Path is outside the allowed directory: {posixpath.join(folder, name)}', 403)
    return full


def makedirs(sftp, path: str) -> None:
    parts, current = [p for p in path.split('/') if p], '/' if path.startswith('/') else ''
    for part in parts:
        current = posixpath.join(current, part) if current else part
        try:
            if not stat.S_ISDIR(sftp.stat(current).st_mode):
                raise ApiError(f'Not a directory: {current}', 409)
        except FileNotFoundError:
            sftp.mkdir(current)


def _now() -> str:
    return dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def upload(cfg: Config, files: list) -> list:
    """Uploads `[(name, bytes)]` into a new folder `<base>/<YYYYmmddHHMMSS.fff>`."""
    if not files:
        raise ApiError('ファイルデータは必須です。')
    if len(files) > cfg.max_files:
        raise ApiError(f'Too many files (max {cfg.max_files})')
    folder = dt.datetime.now().strftime('%Y%m%d%H%M%S.%f')[:-3]
    results = []
    with connect(cfg.sftp) as sftp:
        base = base_dir(sftp, cfg.sftp)
        remote_dir = posixpath.join(base, folder)
        try:
            makedirs(sftp, remote_dir)
        except OSError as err:
            log.error('Could not create %s: %s', remote_dir, err)
            raise ApiError(f'Could not create the remote directory: {err.strerror or err}', 502) from None
        for name, data in files:
            remote = posixpath.join(remote_dir, name)
            try:
                sftp.putfo(io.BytesIO(data), remote, file_size=len(data), confirm=True)
                results.append({'filename': name, 'remote': remote, 'path': folder,
                                'msg': f'「{_now()}」転送完了。'})
            except (OSError, paramiko.SSHException) as err:
                log.warning('Upload failed %s: %s', remote, err)
                results.append({'filename': name, 'path': folder, 'msg': str(err)})
    return results


def download(cfg: Config, items: list) -> list:
    """`[{filename, remote, data: bytes | None, msg}]` for `[{filename, path}]`."""
    if not isinstance(items, list) or not items:
        raise ApiError('ファイルデータは必須です。')
    if len(items) > cfg.max_files:
        raise ApiError(f'Too many files (max {cfg.max_files})')
    results, total = [], 0
    with connect(cfg.sftp) as sftp:
        base = base_dir(sftp, cfg.sftp)
        targets = []
        for item in items:
            if not isinstance(item, dict):
                raise ApiError('files must be a list of {filename, path}')
            targets.append(resolve(base, item.get('path'), item.get('filename')))  # all checked before reading
        for remote in targets:
            name = posixpath.basename(remote)
            out = {'filename': name, 'remote': posixpath.relpath(remote, base), 'data': None}
            try:
                st = sftp.stat(remote)
                if not stat.S_ISREG(st.st_mode):
                    raise IsADirectoryError(f'Not a file: {out["remote"]}')
                total += st.st_size
                if total > cfg.max_download:
                    raise ApiError(f'Download is too large (max {cfg.max_download // 1024 // 1024} MB)', 413)
                buf = io.BytesIO()
                sftp.getfo(remote, buf)
                out['data'] = buf.getvalue()
                out['msg'] = f'「{_now()}」ダウンロード完了。'
            except FileNotFoundError:
                out['msg'] = f'File not found: {out["remote"]}'
            except (OSError, paramiko.SSHException) as err:
                out['msg'] = str(err)
            results.append(out)
    return results
