#!/bin/sh

HOSTNAME="compressorcam"

rsync -av * $HOSTNAME:/home/pi/slp/ --exclude="storage" --exclude=".DS_Store"
rsync -av S34slp $HOSTNAME:/etc/init.d
rsync -av S35fbcp $HOSTNAME:/etc/init.d