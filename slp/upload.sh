#!/bin/sh

rsync -av * pi:/home/pi/slp/ --exclude="storage"