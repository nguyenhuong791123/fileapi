# -*- coding: UTF-8 -*-
import os
import datetime
import shutil
from flask import Flask, jsonify, request, render_template, make_response
from flask_cors import CORS
from utils.sftp import *

app = Flask(__name__)
CORS(app, supports_credentials=True)

# @app.before_request
# def before_request():
#     current_user = get_jwt_identity()
#     print(current_user)
#     if current_user is None:
#         return jsonify({"error": "JWT authentication is required !!!"}), 401

@app.route('/', methods=[ 'GET', 'POST' ])
def index():
    auth = request.authorization
    print(auth)

    return render_template('index.html')

@app.route('/putsftp', methods=[ 'POST' ])
def putsftp():
    authorization = request.authorization
    # print(authorization)

    files = None
    result = []
    if request.method == 'POST':
        files = request.files.getlist('file')
        # print(files)
        if files is None or len(files) <= 0:
            obj = {}
            obj['name'] = None
            obj['data'] = 'ファイルデータは必須です。'
            result.append(obj)
            return jsonify(result), 200

    auth = {}
    auth['host'] = 'sc-sftp-01'
    auth['port'] = 22
    auth['username'] = 'sftp01'
    auth['password'] = 'sftp01'
    # auth['password'] = './keys/id_rsa_sftp'

    result = transport_sftp(auth, files)
    return jsonify(result), 200

@app.route('/getsftp', methods=[ 'GET' ])
def getsftp():
    authorization = request.authorization
    # print(authorization)

    auth = {}
    auth['host'] = 'sc-sftp-01'
    auth['port'] = 22
    auth['username'] = 'sftp01'
    auth['password'] = 'sftp01'

    file = {}
    file['path'] = '/home/sftp01/20191125142219.644'
    file['filename'] = 'img.png'
    file['flag'] = 'json'

    result = {}
    obj = download_sftp(auth, file)
    filename = obj['filename']
    local = obj['path'] + '/' + filename
    if file['flag'] == 'file':
        response = make_response()
        response.data = open(local, 'rb').read()
        response.headers['Content-Disposition'] = 'attachment; filename=' + filename
        response.mimetype = 'image/png'
        return response
    elif file['flag'] == 'json':
        if os.path.isfile(local):
            result['filename'] = filename
            result['msg'] = obj['msg']
            result['data'] = str(convert_file_to_b64_string(local))
            return jsonify(result), 200
        return jsonify(result), 200
    else:
        return jsonify(result), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8083)