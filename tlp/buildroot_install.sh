#!/bin/sh

export READTHEDOCS=True # required to install picamera
pip3 install -r /home/pi/tlp/requirements.txt

# add quiet to the cmdline.txt
grep -qF 'quiet' /boot/cmdline.txt || sed -i '$ s/$/ quiet/' /boot/cmdline.txt