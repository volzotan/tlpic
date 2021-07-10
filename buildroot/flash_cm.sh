sudo diskutil umountDisk /dev/disk2

sudo gdd if=sdcard.img of=/dev/disk2 bs=4M status=progress
# sudo dd if=sdcard.img of=/dev/disk2 bs=4m
