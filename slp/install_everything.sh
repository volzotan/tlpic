#!/bin/sh

HOSTNAME="compressorcam"

# remount main partition as RW
ssh $HOSTNAME 'mount -o remount,rw /dev/root /'

# ------------------------------------------

ssh $HOSTNAME 'rm /etc/init.d/S34compressorcam'
ssh $HOSTNAME 'mkdir /home/pi/tmp'

echo "DONE"
