#!/bin/sh

HOSTNAME="compressorcam"

rsync -av * $HOSTNAME:/home/pi/slp/ --exclude="storage"
rsync -av S34slp $HOSTNAME:/etc/init.d