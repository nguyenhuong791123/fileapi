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

# curl -v -H "Content-type: application/json" -X GET -d @get.json  http://192.168.10.126:8083/getsftp | jq
# curl -v -X POST -F "zip=True" -F "zippw='1234'" -F "filename=001-home.svg" -F "path=/home/huongnv/20191127040812.761"  http://192.168.10.126:8083/getsftp | jq
@app.route('/getsftp', methods=[ 'POST' ])
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
    if request.method == 'POST':
        if request.json is not None and (files is None or len(files) <= 0):
            auth['flag'] = request.json.get('flag')
            auth['zip'] = request.json.get('zip')
            auth['zippw'] = request.json.get('zippw')
            files = request.json.get('files')
        else:
            if is_none(request.form.get('flag')) == False:
                auth['flag'] = request.form.get('flag')
            auth['zip'] = request.form.get('zip')
            auth['zippw'] = request.form.get('zippw')
            if is_none(request.form.get('filename')) == False and is_none(request.form.get('path')) == False:
                files = [{ 'filename': request.form.get('filename'), 'path': request.form.get('path') }]
            else:
                obj = {}
                obj['name'] = None
                obj['data'] = '「ファイル名又はパス」を指定してください。'
                return jsonify(obj), 200

        if files is None or len(files) <= 0:
            obj = {}
            obj['name'] = None
            obj['data'] = 'ファイルデータは必須です。'
            return jsonify(obj), 200

    print(auth)
    result = {}
    obj = download_sftp(auth, files)
    print(obj)
    if auth['flag'] == 'file':
        filename = obj['filename']
        local = obj['path'] + '/' + filename
        response = make_response()
        response.data = open(local, 'rb').read()
        response.headers['Content-Disposition'] = 'attachment; filename=' + filename
        response.mimetype = 'application/zip'

        delete_dir(obj['path'])
        return response
    elif auth['flag'] == 'json':
        delete_dir(obj['path'])
        return jsonify(obj), 200
    else:
        return jsonify(result), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8083)