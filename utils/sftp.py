# -*- coding: utf-8 -*-
import os
import shutil
import datetime
import base64
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

        filename = file.filename
        local = outpath + '/' + filename
        file.save(outpath + '/' + filename)
        remote = '/home/' + auth['username'] + '/' + dir

        obj = {}
        obj['local'] = local
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
                if outpath is not None and os.path.isdir(outpath):
                    shutil.rmtree(outpath)
        else:
            obj['msg'] = 'Can not create dir to remote !!!'
        
        result.append(obj)
    return result

def download_sftp(auth, file):
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

    filename = file['filename']
    local = outpath + '/' + filename
    remote = file['path'] + '/' + filename
    obj = {}
    obj['remote'] = remote
    try:
        sftp.get(remote, local)
        obj['path'] = outpath
        obj['filename'] = filename
        obj['msg'] =  '「' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '」ダウンロード完了。'
    except IOError as err:
        obj['msg'] = str(err)
    finally:
        if sftp is not None:
            sftp.close()
        if transport is not None:
            transport.close()
            print('Download File End !!!' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    return obj

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
