#!/bin/sh

HOSTNAME="tlp"

# remount main partition as RW
ssh $HOSTNAME 'mount -o remount,rw /dev/root /'

# create /boot dir so fstab can mount the boot partition
ssh $HOSTNAME 'mkdir /boot'
# ssh $HOSTNAME 'mkdir /media/storage'
# ssh $HOSTNAME 'mkdir /media/external_storage'

# ------------------------------------------

ssh $HOSTNAME 'sh /root/resize_fs.sh'

echo "sleep 20s"
sleep 20

# re-run resize_fs.sh to actually create the filesystem at the full size
ssh $HOSTNAME 'sh /root/resize_fs.sh'

echo "sleep 20s"
sleep 20

# ------------------------------------------

echo "\n---"
echo "setting current time and date on the pi"
sh set_date.sh

echo "\n---"
echo "uploading device tree files"
rsync -av ../devicetree/CM4_dt_blob $HOSTNAME:/home/pi/
ssh $HOSTNAME "dtc -I dts -O dtb -o /boot/dt-blob.bin /home/pi/CM4_dt_blob/dt-blob-disp0-double_cam.dts"

# upload script takes care of RW-remount
echo "\n---"
echo "uploading tlp program files"
sh upload_program_files.sh

# echo "\n---"
# echo "deleting files"
# sh buildroot_clean.sh

# install script need to access /boot/config.txt and cmdline.txt 
# so boot partition needs to be mounted for this

echo "\n---"
echo "download pip packages"
ssh $HOSTNAME 'sh /home/pi/tlp/buildroot_install.sh'

echo "DONE! reboot..."
ssh $HOSTNAME 'reboot'