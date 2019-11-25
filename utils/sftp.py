# -*- coding: utf-8 -*-
import os
import paramiko
# paramiko.util.log_to_file('/tmp/paramiko.log')

def transport(auth, files):
    print('Send File Start !!!')
    transport = paramiko.Transport((auth['host'], int(auth['port'])))
    transport.connect(username = auth['username'], password = auth['password'])
    sftp = paramiko.SFTPClient.from_transport(transport)

    result = []
    dt = datetime.datetime.now()
    dir = dt.strftime('%Y%m%d%H%M%S.%f')[:-3]
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
        obj['name'] = local
        if mkdir_remote(sftp, remote):
            try:
                if os.path.isfile(local):
                    print(os.getcwd())
                    print(file['local'])
                    print(file['remove'])
                    sftp.put(local, filename)
                    obj['msg'] =  local + 'へ' + remote + '/' + filename + 'の送信完了。'
                else:
                    raise IOError('Could not find localFile %s !!' % local)
            except IOError as err:
                obj['msg'] = str(err)
            finally:
                if sftp is not None:
                    sftp.close()
                if transport is not None:
                    transport.close()
        else:
            obj['msg'] = 'Can not create dir to remote !!!'
        
        result.append(obj)

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

    return result

def mkdir_remote(sftp, remote_directory):
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
