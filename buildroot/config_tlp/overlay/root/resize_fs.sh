#!/bin/sh

echo "RESIZING CCSTORAGE"

umount "/media/storage"

# ROOT_PART=mmcblk0p2
PART_NUM=3

# Get the starting offset of the root partition
PART_START=$(parted /dev/mmcblk0 -ms unit s p | grep "^${PART_NUM}" | cut -f 2 -d: | sed 's/[^0-9]//g')
[ "$PART_START" ] || return 1

# Return value will likely be error for fdisk as it fails to reload the
# partition table because the root fs is mounted
fdisk -u /dev/mmcblk0 <<EOF
p
d
3
p
n
p
3


p
t
3
c
w
EOF

sleep 5

mkdir /media/storage

# in case it may already be mounted
umount /media/storage

# problem: old partition table still loaded so the new file system won't
# be created at full size

mkfs.vfat -F 32 -n CCSTORAGE /dev/mmcblk0p3

echo "\n\n"
echo "REBOOT!"

sleep 5

reboot