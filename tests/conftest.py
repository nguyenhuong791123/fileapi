import datetime as dt
import os
import posixpath
import sys
from contextlib import contextmanager
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app  # noqa: E402
from app.config import AuthConfig, Config, SftpConfig  # noqa: E402

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PUBLIC_PEM = KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def make_token(**claims):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {'uid': 1, 'cid': 3, 'client_id': 'edu', 'exp': now + dt.timedelta(minutes=5), **claims}
    return jwt.encode(payload, KEY, algorithm='RS256')


def make_config(**overrides) -> Config:
    base = dict(
        sftp=SftpConfig('sftp.test', 22, 'dev', 'secret', '', '', 'upload', '', False, 5),
        max_files=5, max_download=1024 * 1024, max_content_length=5 * 1024 * 1024, cors_origins=[],
        auth=AuthConfig(True, '', PUBLIC_PEM, '', ['RS256'], '', ''),
    )
    base.update(overrides)
    return Config(**base)


class FakeSFTP:
    """Stands in for paramiko's SFTPClient on a local directory; the login directory is /home/dev."""

    def __init__(self, root):
        self.root = str(root)

    def _local(self, p):
        return self.root + p

    def normalize(self, p):
        return p if p.startswith('/') else posixpath.normpath(posixpath.join('/home/dev', p))

    def stat(self, p):
        return os.stat(self._local(p))

    def mkdir(self, p):
        os.mkdir(self._local(p))

    def putfo(self, fl, remote, file_size=0, confirm=True):
        with open(self._local(remote), 'wb') as f:
            f.write(fl.read())

    def getfo(self, remote, buf):
        with open(self._local(remote), 'rb') as f:
            buf.write(f.read())


@pytest.fixture
def sftp(monkeypatch, tmp_path):
    os.makedirs(tmp_path / 'home/dev/upload')
    fake = FakeSFTP(tmp_path)

    @contextmanager
    def connect(cfg):
        if not cfg.configured:
            from app.errors import ApiError
            raise ApiError('SFTP server is not configured', 503)
        yield fake

    monkeypatch.setattr('app.sftp.connect', connect)
    return fake


@pytest.fixture
def client():
    return create_app(make_config()).test_client()


@pytest.fixture
def auth():
    return {'Authorization': f'Bearer {make_token()}'}
