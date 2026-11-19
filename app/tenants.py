"""SFTP account of each tenant, from the API server (サーバー情報 > ファイルサーバー of the tenant DB).

be `GET /internal/file-servers/<tenant>` (header X-Internal-Secret) returns the tenant's file server:
`{"file": {protocol, host, port, username, password}}` (null when not set), cached for
`SERVER_SETTINGS_TTL` seconds. Host key checking, the base directory, the private key and the timeout
stay global settings (SFTP_*). Without `SERVER_SETTINGS_URI` the SFTP_* account is used for every tenant.
"""
import dataclasses
import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request

from .config import Config
from .errors import ApiError

log = logging.getLogger(__name__)
TENANT = re.compile(r'^[a-z0-9-]{1,30}$', re.I)


class TenantServers:
    def __init__(self, cfg: Config, fetch=None):
        self.cfg = cfg
        self._fetch = fetch or self._http
        self._cache = {}
        self._lock = threading.Lock()

    def _http(self, tenant: str) -> dict:
        req = urllib.request.Request(f'{self.cfg.settings_uri}/{tenant}',
                                     headers={'X-Internal-Secret': self.cfg.internal_secret})
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return json.loads(res.read().decode('utf-8'))
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return {}
            log.warning('File server of %s: HTTP %s', tenant, err.code)
            raise ApiError('File server settings are not available', 503) from None
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            log.warning('File server of %s: %s', tenant, err)
            raise ApiError('File server settings are not available', 503) from None

    def config_for(self, tenant) -> Config:
        """The configuration with the tenant's SFTP account."""
        if not self.cfg.settings_uri:
            return self.cfg
        if not tenant or not TENANT.match(str(tenant)):
            raise ApiError('The tenant of the access token is unknown', 401)
        now = time.monotonic()
        with self._lock:
            hit = self._cache.get(tenant)
            if hit and hit[0] > now:
                return hit[1]
        f = (self._fetch(str(tenant)) or {}).get('file')
        if not isinstance(f, dict) or not f.get('host'):
            sftp = dataclasses.replace(self.cfg.sftp, host='', username='', password='')   # not configured: 503
        elif str(f.get('protocol') or 'sftp').lower() != 'sftp':
            raise ApiError(f"File server protocol {f.get('protocol')} is not supported (SFTP only)", 501)
        else:
            sftp = dataclasses.replace(self.cfg.sftp, host=str(f['host']), port=int(f.get('port') or 22),
                                       username=str(f.get('username') or ''), password=str(f.get('password') or ''),
                                       private_key_file='', private_key_passphrase='')
        cfg = dataclasses.replace(self.cfg, sftp=sftp)
        with self._lock:
            self._cache[tenant] = (now + max(0, self.cfg.settings_ttl), cfg)
        return cfg
