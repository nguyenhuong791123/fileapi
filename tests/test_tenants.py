import base64
from contextlib import contextmanager

from conftest import FakeSFTP, make_config, make_token
from app import create_app
from app.tenants import TenantServers

EDU = {'tenant': 'edu', 'file': {'protocol': 'sftp', 'host': 'files.edu', 'port': 2222, 'username': 'edu', 'password': 'pw'}}


def tenant_client(monkeypatch, tmp_path, fetch):
    import os
    os.makedirs(tmp_path / 'home/dev/upload', exist_ok=True)
    used = []

    @contextmanager
    def connect(cfg):
        if not cfg.configured:
            from app.errors import ApiError
            raise ApiError('SFTP server is not configured', 503)
        used.append(cfg)
        yield FakeSFTP(tmp_path)

    monkeypatch.setattr('app.sftp.connect', connect)
    app = create_app(make_config(settings_uri='http://be/internal/file-servers', internal_secret='x' * 20))
    app.config['TENANTS'] = TenantServers(app.config['FILE'], fetch=fetch)
    return app.test_client(), used


def put(client, tenant):
    return client.post('/putsftp', json={'files': [{'filename': 'a.txt', 'data': base64.b64encode(b'x').decode()}]},
                       headers={'Authorization': f'Bearer {make_token(client_id=tenant)}'})


def test_account_of_the_tenant_is_used(monkeypatch, tmp_path):
    calls = []
    client, used = tenant_client(monkeypatch, tmp_path, lambda t: calls.append(t) or EDU)
    assert put(client, 'edu').status_code == 200
    put(client, 'edu')
    s = used[0]
    assert (s.host, s.port, s.username, s.password) == ('files.edu', 2222, 'edu', 'pw')
    assert s.base_dir == 'upload'                     # global setting kept
    assert calls == ['edu']                           # cached


def test_each_tenant_has_its_own_server(monkeypatch, tmp_path):
    servers = {'edu': EDU['file'], 'other': {**EDU['file'], 'host': 'files.other', 'username': 'other'}}
    client, used = tenant_client(monkeypatch, tmp_path, lambda t: {'file': servers.get(t)})
    put(client, 'edu'); put(client, 'other')
    assert [(u.host, u.username) for u in used] == [('files.edu', 'edu'), ('files.other', 'other')]
    assert put(client, 'nofiles').status_code == 503  # no file server set for that company


def test_unsupported_protocol(monkeypatch, tmp_path):
    client, _ = tenant_client(monkeypatch, tmp_path, lambda t: {'file': {**EDU['file'], 'protocol': 'ftp'}})
    assert put(client, 'edu').status_code == 501


def test_environment_account_without_settings_uri():
    cfg = make_config()
    assert TenantServers(cfg, fetch=lambda t: EDU).config_for('edu') is cfg
