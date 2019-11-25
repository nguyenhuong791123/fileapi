# -*- coding: utf-8 -*-
import os
import paramiko
# paramiko.util.log_to_file('/tmp/paramiko.log')

def transport(file):
    print('Send File Start !!!')
    transport = paramiko.Transport((file['host'], int(file['port'])))
    transport.connect(username = file['username'], password = file['password'])
    sftp = paramiko.SFTPClient.from_transport(transport)

    obj = {}
    obj['name'] = file['local']
    try:
        if os.path.isfile('/home/coder/project/fileapi/img.png'):
            print(os.getcwd())
            print(file['local'])
            print(file['remove'])
            sftp.put('img.png', '/' + file['filename'])
            # sftp.put(file['local'], file['remove'])
            obj['msg'] =  file['host'] + 'への送信完了。'
        else:
            raise IOError('Could not find localFile %s !!' % localFile)
    except IOError as err:
        obj['msg'] = str(err)
    finally:
        if sftp is not None:
            sftp.close()
        if transport is not None:
            transport.close()

    # client = None
    # sftp_connection = None
    # try:
    #     client = paramiko.SSHClient()
    #     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #     client.connect(file['host'], int(file['port']), file['username'], file['password'])
    #     sftp_connection = client.open_sftp()
    #     # ホームディレクトリのファイル一覧をprint
    #     files = sftp_connection.listdir()
    #     for remote_file in files:
    #         print(remote_file)
    #     # ファイルを取得
    #     # sftp_connection.get('/path/to/remotefile', '/path/to/local')
    #     # ファイルを転送
    #     sftp.put('img.png', '/home/sftp01/' + file['filename'])
    #     # sftp_connection.put(file['local'], file['remove'])
    # except IOError as err:
    #     obj['msg'] = str(err)
    # finally:
    #     if client:
    #         client.close()
    #     if sftp_connection:
    #         sftp_connection.close()

    print(obj)
    return obj

def mkdir_p(sftp, remote_directory):
    """Change to this directory, recursively making new folders if needed.
    Returns True if any folders were created."""
    if remote_directory == '/':
        # absolute path so change directory to root
        sftp.chdir('/')
        return
    if remote_directory == '':
        # top-level relative directory must exist
        return
    try:
        sftp.chdir(remote_directory) # sub-directory exists
    except IOError:
        dirname, basename = os.path.split(remote_directory.rstrip('/'))
        mkdir_p(sftp, dirname) # make parent directories
        sftp.mkdir(basename) # sub-directory missing, so created it
        sftp.chdir(basename)
        return True
