# fileapi

SFTP サーバーへファイルをアップロード・ダウンロードする API（Flask）。

## 起動

```sh
# リポジトリのルート（hv）で。テスト用 SFTP サーバー（sftp）も起動します
docker compose up -d --build fileapi
curl http://localhost:8083/health        # {"status":"ok"}
```

- 設定は `fileapi/.env`（`.env.example` を参照）。SFTP のアカウントは環境変数だけで設定します。
- テスト用 SFTP サーバーには `sftp -P 2222 dev@localhost` で入れます（パスワードは `fileapi/dev.env`）。

コンテナを使わない場合:

```sh
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt     # pyminizip のビルドに C コンパイラと zlib が必要
set -a && . ./.env && set +a
python wsgi.py                           # http://localhost:8083
python -m pytest -q tests
```

## 認証

`/` と `/health` 以外は、トークンサーバー（wso2）が発行したアクセストークンが必要です（`Authorization: Bearer <access_token>`）。
検証方法は API サーバー（be）と同じです。

## API

| メソッド | パス | 内容 |
|---|---|---|
| GET | `/health` | 稼働確認 |
| POST | `/putsftp` | アップロード |
| POST | `/getsftp` | ダウンロード |

### POST /putsftp

- multipart: `file`（複数可）
- JSON: `{"files": [{"filename": "a.pdf", "data": "<base64>"}]}`

`SFTP_BASE_DIR` の下に新しいフォルダ（`YYYYmmddHHMMSS.fff`）を作って保存します。

```json
[{"filename": "a.pdf", "path": "20261118011026.394", "remote": "/upload/20261118011026.394/a.pdf", "msg": "…転送完了。"}]
```

### POST /getsftp

- JSON: `{"flag": "file", "zip": false, "zippw": "", "files": [{"filename": "a.pdf", "path": "20261118011026.394"}]}`
- form: `flag`, `zip`, `zippw`, `filename`, `path`

`path` は `SFTP_BASE_DIR` からの相対パス（アップロード結果の `path`）。その外（`../` や別の絶対パス）は 403 です。

- `flag: file`（既定）: 1 ファイルならそのまま、複数または `zip: true` なら ZIP（`zippw` でパスワード付き）を返します
- `flag: json`: base64 で返します（1 ファイル: `{filename, remote, data, msg}`、複数: `{filename: null, data: [...]}`、zip: `{filename, data, files}`）

## 主な設定（環境変数）

| 変数 | 既定 | 内容 |
|---|---|---|
| `SFTP_HOST` / `SFTP_PORT` / `SFTP_USER` | – / 22 / – | 未設定なら 503 |
| `SFTP_PASSWORD` または `SFTP_PRIVATE_KEY_FILE`（+ `_PASSPHRASE`） | | 認証 |
| `SFTP_BASE_DIR` | ログインディレクトリ | 保存先・ダウンロードできる範囲 |
| `SFTP_KNOWN_HOSTS` / `SFTP_STRICT_HOST_KEY` | – / true | ホスト鍵の確認。`false` は任意の鍵を受け入れます（ローカルのみ） |
| `CORS_ORIGINS` | なし | ブラウザから呼べるオリジン（カンマ区切り、正規表現可） |
| `FILE_MAX_FILES` / `FILE_MAX_DOWNLOAD_MB` / `MAX_CONTENT_MB` | 50 / 100 / 100 | 上限 |
