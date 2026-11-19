#!/bin/sh
# Local test SFTP server (docker compose service "sftp"): the upload volume belongs to the user.
chown 1001:100 /home/dev/upload
