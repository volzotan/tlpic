#!/bin/sh

DIR="bollogg:/home/volzotan/buildroot_extree_tlpic/external_tree/"

rsync -av config_raspberrypi4/ $DIR --delete --exclude=".DS_Store"

rsync -av ../tlc $DIR"overlay/home/pi"              \
    --delete                                        \
    --exclude=".DS_Store"                           \
    --exclude="README.md"                           \
    --exclude="*.pyc"                               \
    --exclude="*__pycache__*"                           