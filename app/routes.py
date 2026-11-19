"""HTTP endpoints. Request formats are the original ones; the SFTP account is never taken from them."""
import base64
import datetime as dt
import io
import mimetypes

from flask import Blueprint, current_app, g, jsonify, render_template, request, send_file

from .errors import ApiError
from .files import decode_base64, make_zip, safe_filename
from .sftp import download, upload

bp = Blueprint('file', __name__)


def _truthy(v) -> bool:
    return v is True or str(v).lower() in ('true', '1', 'yes', 'on')


def _config():
    """SFTP account of the user's tenant (サーバー情報 > ファイルサーバー), or of the environment."""
    user = getattr(g, 'user', None) or {}
    return current_app.config['TENANTS'].config_for(user.get('tenant'))


def _json() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@bp.get('/')
def index():
    return render_template('index.html')


@bp.get('/health')
def health():
    return jsonify({'status': 'ok'})


@bp.post('/putsftp')
def putsftp():
    """multipart `file` (several allowed) or JSON `{"files": [{filename, data(base64)}]}`."""
    cfg = _config()
    uploads = request.files.getlist('file')
    if uploads:
        files = [(safe_filename(f.filename), f.read()) for f in uploads]
    else:
        items = _json().get('files') or []
        if not isinstance(items, list):
            raise ApiError('files must be a list of {filename, data}')
        files = []
        for f in items:
            if not isinstance(f, dict):
                raise ApiError('files must be a list of {filename, data}')
            name = safe_filename(f.get('filename'))
            files.append((name, decode_base64(f.get('data'), name)))
    return jsonify(upload(cfg, files))


@bp.post('/getsftp')
def getsftp():
    """JSON `{flag: file|json, zip, zippw, files: [{filename, path}]}` or form fields `flag, zip, zippw, filename, path`.

    `path` is relative to the base directory (an upload's `path`). flag=file returns the file
    (several files or zip=true: one ZIP); flag=json returns the contents in base64.
    """
    cfg = _config()
    data = _json()
    if data:
        items = data.get('files')
    else:
        data = request.form
        if not data.get('filename') or not data.get('path'):
            raise ApiError('「ファイル名又はパス」を指定してください。')
        items = [{'filename': data.get('filename'), 'path': data.get('path')}]
    flag = str(data.get('flag') or 'file').lower()
    if flag not in ('file', 'json'):
        raise ApiError('flag must be file or json')
    zipped, password = _truthy(data.get('zip')), str(data.get('zippw') or '')

    results = download(cfg, items)
    found = [(r['filename'], r['data']) for r in results if r['data'] is not None]
    stamp = dt.datetime.now().strftime('%Y%m%d%H%M%S')

    if flag == 'file':
        if not found:
            raise ApiError('; '.join(r['msg'] for r in results), 404)
        if len(found) == 1 and not zipped:
            name, content = found[0]
            return send_file(io.BytesIO(content), as_attachment=True, download_name=name,
                             mimetype=mimetypes.guess_type(name)[0] or 'application/octet-stream')
        return send_file(io.BytesIO(make_zip(found, password)), as_attachment=True,
                         download_name=f'{stamp}_zip.zip', mimetype='application/zip')

    for r in results:
        r['data'] = base64.b64encode(r['data']).decode() if r['data'] is not None else None
    done = f'「{dt.datetime.now():%Y-%m-%d %H:%M:%S}」ダウンロード完了。'
    if zipped:
        content = base64.b64encode(make_zip(found, password)).decode() if found else None
        files = [{k: v for k, v in r.items() if k != 'data'} for r in results]
        return jsonify({'filename': f'{stamp}_zip.zip', 'data': content, 'files': files, 'msg': done})
    if len(results) == 1:
        return jsonify(results[0])
    return jsonify({'filename': None, 'data': results, 'msg': done})
