# -*- coding: utf-8 -*-
import os
import shutil
import datetime
import base64
import zipfile
import pyminizip
import paramiko
# paramiko.util.log_to_file('/tmp/paramiko.log')

def transport_sftp(auth, files):
    print('Transport File Start !!!' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    transport = paramiko.Transport((auth['host'], int(auth['port'])))
    transport.connect(username = auth['username'], password = auth['password'])
    sftp = paramiko.SFTPClient.from_transport(transport)

    result = []
    dt = datetime.datetime.now()
    dir = dt.strftime('%Y%m%d%H%M%S.%f')[:-3]
    updir = 'upload/'
    outpath = updir + dir
    if os.path.isdir(outpath) == False:
        os.mkdir(outpath)

    for file in files:
        if file is None:
            continue

        filename = None
        local = None
        if auth['flag'] == 'json':
            filename = file['filename']
            local = outpath + '/' + filename
            convert_b64_string_to_file(file['data'], local)
        else:
            filename = file.filename
            local = outpath + '/' + filename
            file.save(local)

        if filename is None or local is None:
            continue
        remote = '/home/' + auth['username'] + '/' + dir

        obj = {}
        # obj['local'] = local
        if mkdir_remote(sftp, remote):
            try:
                # sftp.chmod(remote, mode=777)
                if os.path.isfile(local):
                    sftp.put(local, filename)
                    obj['remote'] = remote + '/' + filename
                else:
                    raise IOError('Could not find localFile %s !!' % local)
            except IOError as err:
                obj['msg'] = str(err)
            finally:
                if sftp is not None:
                    sftp.close()
                if transport is not None:
                    transport.close()
                    obj['msg'] =  '「' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '」転送完了。'
                    print('Transport File End !!!' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        else:
            obj['msg'] = 'Can not create dir to remote !!!'
        
        result.append(obj)

    delete_dir(outpath)
    return result

def download_sftp(auth, files):
    print('Download File Start !!!' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    transport = paramiko.Transport((auth['host'], int(auth['port'])))
    transport.connect(username = auth['username'], password = auth['password'])
    sftp = paramiko.SFTPClient.from_transport(transport)

    dt = datetime.datetime.now()
    dir = dt.strftime('%Y%m%d%H%M%S.%f')[:-3]
    downdir = 'download/'
    outpath = downdir + dir
    if os.path.isdir(outpath) == False:
        os.mkdir(outpath)

    list = []
    for file in files:
        if file is None:
            continue

        print(file)
        filename = file['filename']
        # local = None
        # if auth['flag'] == 'json':
        #     filename = file['filename']
        # else:
        #     filename = file.filename

        # if filename is None or local is None:
        #     continue

        local = outpath + '/' + filename
        remote = file['path'] + '/' + filename
        obj = {}
        obj['remote'] = remote
        try:
            sftp.get(remote, local)
            # obj['path'] = outpath
            obj['filename'] = filename
            # obj['msg'] =  '「' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '」ダウンロード完了。'
        except IOError as err:
            obj['msg'] = str(err)
        finally:
            if auth['flag'] == 'json' and os.path.isfile(local):
                b64 = str(convert_file_to_b64_string(local))
                if b64 is not None:
                    obj['data'] = b64[2:(len(b64)-1)]

        list.append(obj)

    if sftp is not None:
        sftp.close()
    if transport is not None:
        transport.close()
        print('Download File End !!!' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    zipname = None
    zip = auth['zip']
    zippw = auth['zippw']
    ziphome = './'
    result = {}
    print(zip)
    if zip is not None and zip == True:
        os.chdir(outpath)
        zipname = dir + '_zip.zip'
        if zippw is None or len(zippw) <= 0:
            with zipfile.ZipFile(zipname,'w', compression=zipfile.ZIP_STORED)as n_zip:
                for file in os.listdir(ziphome):
                    n_zip.write(os.path.join(ziphome, file))
        else:
            src = []
            level = 4
            for file in os.listdir(ziphome):
                src.append(os.path.join(ziphome, file))
            pyminizip.compress_multiple(src, [], zipname, zippw, level)

        os.chdir('../../')
        result['filename'] = zipname
        result['data'] = None
    else:
        if len(list) == 1:
            result['filename'] = list[0]['filename']
            result = list[0]
        else:
            result['filename'] = zipname
            result['data'] = list

    result['path'] = outpath
    result['msg'] =  '「' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '」ダウンロード完了。'
    return result

def mkdir_remote(sftp, remote_directory):
    if remote_directory == '/':
        sftp.chdir('/')
        return
    if remote_directory == '':
        return
    try:
        sftp.chdir(remote_directory)
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdir_remote(sftp, dirname)
        sftp.mkdir(basename)
        sftp.chdir(basename)
        return True

def convert_file_to_b64_string(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read())


def convert_b64_string_to_file(s, outfile_path):
    with open(outfile_path, "wb") as f:
        f.write(base64.b64decode(s))

def delete_dir(path):
    if path is not None and os.path.isdir(path):
        shutil.rmtree(path)

def is_none(obj):
    if obj is None:
        return True
    return False