# -*- coding: UTF-8 -*-
import os
import datetime
import shutil
from flask import Flask, jsonify, request, render_template
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

@app.route('/send', methods=[ 'POST' ])
def send():
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
    auth['host'] = '192.168.10.126'
    auth['port'] = 2222
    auth['username'] = 'huongnv'
    auth['password'] = 'Nguyen080!'
    # auth['password'] = './keys/id_rsa_sftp'

    result = transport(auth, files)
    return jsonify(result), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8083)