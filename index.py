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
        print(files)
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

    outpath = None
    # outfile = None
    updir =  os.getcwd() + '/upload/'
    try:
        dt = datetime.datetime.now()
        dir = dt.strftime('%Y%m%d%H%M%S.%f')[:-3]
        outpath = updir + dir
        if os.path.isdir(outpath) == False:
            os.mkdir(outpath)

        for file in files:
            if file is None:
                continue

            filename = file.filename
            # outfile = outpath + '/' + filename
            file.save(outpath + '/' + filename)
            auth['filename'] =  filename
            auth['local'] =  outpath
            auth['remove'] = '/home/' + auth['username']
            # auth['remove'] = '/home/' + auth['username'] + '/' + dir

            result.append(transport(auth))
    except Exception as e:
        obj = {}
        obj['name'] = 'ファイル転送エラー発生しました。'
        obj['msg'] = str(e)
        result.append(obj)
    # finally:
        # if outpath is not None and os.path.isdir(outpath):
        #     shutil.rmtree(outpath)

    return jsonify(result), 200

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8083)