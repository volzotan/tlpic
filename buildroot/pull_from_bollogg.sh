#!/bin/sh

DIR="bollogg:/home/volzotan/buildroot_extree_tlp/buildroot"

# rsync -av $DIR/configs/raspberrypi0w_defconfig .
# rsync -av $DIR/configs/raspberrypi0_defconfig .
# rsync -av $DIR/userfile .
# rsync -av $DIR/.config .
rsync -av $DIR/output/images/sdcard.img .