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

# curl -v -H "Accept: application/json" -H "Content-type: application/json" -X POST -d @data.json  http://192.168.10.126:8083/putsftp
@app.route('/putsftp', methods=[ 'POST' ])
def putsftp():
    authorization = request.authorization
    # print(authorization)

    auth = {}
    auth['host'] = 'sc-sftp-01'
    auth['port'] = 22
    auth['username'] = 'huongnv'
    auth['password'] = 'Nguyen080!'
    # auth['password'] = './keys/id_rsa_sftp'
    auth['flag'] = 'file'

    files = None
    result = []
    if request.method == 'POST':
        files = request.files.getlist('file')
        if request.json is not None and (files is None or len(files) <= 0):
            files = request.json.get('files')
            auth['flag'] = 'json'

        # print(files)
        if files is None or len(files) <= 0:
            obj = {}
            obj['name'] = None
            obj['data'] = 'ファイルデータは必須です。'
            result.append(obj)
            return jsonify(result), 200

    result = transport_sftp(auth, files)
    return jsonify(result), 200

@app.route('/getsftp', methods=[ 'GET' ])
def getsftp():
    authorization = request.authorization
    # print(authorization)

    auth = {}
    auth['host'] = 'sc-sftp-01'
    auth['port'] = 22
    auth['username'] = 'huongnv'
    auth['password'] = 'Nguyen080!'
    # auth['password'] = './keys/id_rsa_sftp'
    auth['flag'] = 'file'

    files = None
    if request.json is not None:
        auth['flag'] = request.json.get('flag')
        auth['zippw'] = request.json.get('zippw')
        files = request.json.get('files')
    # file = {}
    # file['path'] = '/home/huongnv/20191127040812.761'
    # file['file'] = '001-home.svg'
    # file['flag'] = 'json'

    result = {}
    obj = download_sftp(auth, files)
    if auth['flag'] == 'file':
        filename = obj['filename']
        local = obj['path'] + '/' + filename
        response = make_response()
        response.data = open(local, 'rb').read()
        response.headers['Content-Disposition'] = 'attachment; filename=' + filename
        response.mimetype = 'image/png'

        delete_dir(obj['path'])
        return response
    elif auth['flag'] == 'json':
        delete_dir(obj['path'])
        return jsonify(obj), 200
    else:
        return jsonify(result), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8083)