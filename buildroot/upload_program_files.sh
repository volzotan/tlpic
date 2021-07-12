#/bin/sh

HOSTNAME="tlp"

# remount main partition as RW
# ssh $HOSTNAME 'mount -o remount,rw /dev/root /'

rsync -av                           \
--delete                            \
--exclude=".DS_Store"               \
--exclude="*.pyc"                   \
--exclude="README.md"               \
~/GIT/tlpic/tlp $HOSTNAME:/home/pi

# remount main partition as RO
# ssh $HOSTNAME 'mount -o remount,ro /dev/root /'