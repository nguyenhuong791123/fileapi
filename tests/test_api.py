import base64
import io
import os
import zipfile

from conftest import make_config
from app import create_app


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def put(client, auth, files):
    return client.post('/putsftp', json={'files': [{'filename': n, 'data': b64(d)} for n, d in files]}, headers=auth)


def test_public_pages(client):
    assert client.get('/health').json == {'status': 'ok'}
    assert client.get('/').status_code == 200


def test_token_required(client, sftp):
    assert client.post('/putsftp', json={'files': []}).status_code == 401
    assert client.post('/getsftp', json={}).status_code == 401


def test_upload_json_and_download_file(client, sftp, auth):
    res = put(client, auth, [('報告書.txt', b'hello')])
    assert res.status_code == 200
    (r,) = res.json
    assert r['filename'] == '報告書.txt' and '転送完了' in r['msg']
    assert r['remote'] == f"/home/dev/upload/{r['path']}/報告書.txt"
    got = client.post('/getsftp', json={'files': [{'filename': '報告書.txt', 'path': r['path']}]}, headers=auth)
    assert got.status_code == 200 and got.data == b'hello'
    assert 'attachment' in got.headers['Content-Disposition']


def test_upload_multipart_several_files(client, sftp, auth):
    data = {'file': [(io.BytesIO(b'a'), 'a.txt'), (io.BytesIO(b'b'), '../../b.txt')]}
    res = client.post('/putsftp', data=data, content_type='multipart/form-data', headers=auth)
    assert [r['filename'] for r in res.json] == ['a.txt', 'b.txt']     # path parts are dropped
    folder = res.json[0]['path']
    assert sorted(os.listdir(sftp.root + f'/home/dev/upload/{folder}')) == ['a.txt', 'b.txt']


def test_download_zip_with_password(client, sftp, auth):
    folder = put(client, auth, [('a.txt', b'A'), ('b.txt', b'B')]).json[0]['path']
    body = {'zip': True, 'zippw': '1234', 'files': [{'filename': 'a.txt', 'path': folder},
                                                   {'filename': 'b.txt', 'path': folder}]}
    got = client.post('/getsftp', json=body, headers=auth)
    assert got.mimetype == 'application/zip'
    with zipfile.ZipFile(io.BytesIO(got.data)) as zf:
        assert zf.read('b.txt', pwd=b'1234') == b'B'


def test_download_json(client, sftp, auth):
    folder = put(client, auth, [('a.txt', b'A'), ('b.txt', b'B')]).json[0]['path']
    one = client.post('/getsftp', json={'flag': 'json', 'files': [{'filename': 'a.txt', 'path': folder}]},
                      headers=auth).json
    assert one['data'] == b64(b'A') and one['remote'] == f'{folder}/a.txt'
    many = client.post('/getsftp', json={'flag': 'json', 'files': [{'filename': 'a.txt', 'path': folder},
                                                                    {'filename': 'x.txt', 'path': folder}]},
                       headers=auth).json
    assert [d['data'] for d in many['data']] == [b64(b'A'), None]
    zipped = client.post('/getsftp', json={'flag': 'json', 'zip': True,
                                           'files': [{'filename': 'a.txt', 'path': folder}]}, headers=auth).json
    assert zipfile.ZipFile(io.BytesIO(base64.b64decode(zipped['data']))).read('a.txt') == b'A'


def test_form_request(client, sftp, auth):
    folder = put(client, auth, [('a.txt', b'A')]).json[0]['path']
    got = client.post('/getsftp', data={'filename': 'a.txt', 'path': folder}, headers=auth)
    assert got.data == b'A'
    assert client.post('/getsftp', data={'filename': 'a.txt'}, headers=auth).status_code == 400


def test_paths_outside_the_base_dir_are_refused(client, sftp, auth):
    os.makedirs(sftp.root + '/etc')
    with open(sftp.root + '/etc/passwd', 'w') as f:
        f.write('root')
    for path in ['../../../../etc', '/etc', '..']:
        res = client.post('/getsftp', json={'files': [{'filename': 'passwd', 'path': path}]}, headers=auth)
        assert res.status_code == 403, path


def test_missing_file(client, sftp, auth):
    res = client.post('/getsftp', json={'files': [{'filename': 'none.txt', 'path': 'x'}]}, headers=auth)
    assert res.status_code == 404


def test_validation(client, sftp, auth):
    assert client.post('/putsftp', json={'files': []}, headers=auth).status_code == 400
    assert put(client, auth, [('a', b'x')] * 6).status_code == 400
    assert client.post('/getsftp', json={'flag': 'xml', 'files': [{'filename': 'a', 'path': 'b'}]},
                       headers=auth).status_code == 400


def test_unconfigured(sftp, auth):
    from app.config import SftpConfig
    app = create_app(make_config(sftp=SftpConfig('', 22, '', '', '', '', '', '', True, 5)))
    assert app.test_client().post('/putsftp', json={'files': [{'filename': 'a', 'data': b64(b'x')}]},
                                  headers=auth).status_code == 503


def test_remote_permission_error_is_reported(client, sftp, auth, monkeypatch):
    def denied(p):
        raise PermissionError(13, 'Permission denied')
    monkeypatch.setattr(sftp, 'mkdir', denied)
    res = put(client, auth, [('a.txt', b'x')])
    assert res.status_code == 502 and 'Permission denied' in res.json['message']


def test_zip_japanese_names(client, sftp, auth):
    folder = put(client, auth, [('成績表.csv', b'A')]).json[0]['path']
    got = client.post('/getsftp', json={'zip': True, 'zippw': 'pw', 'files': [{'filename': '成績表.csv', 'path': folder}]},
                      headers=auth)
    with zipfile.ZipFile(io.BytesIO(got.data)) as zf:
        assert zf.read('成績表.csv', pwd=b'pw') == b'A'
