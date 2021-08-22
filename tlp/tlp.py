#!/usr/bin/env python3

import time
import datetime
import os
import sys
import subprocess
from fractions import Fraction
import logging
import traceback

import RPi.GPIO as GPIO
import picamera

from devices import CompressorCameraController

# import numpy as np

BUTTON_SHUTTER          = 23 # BCM numbering
OUTPUT_DIR              = "/media/storage"
OUTPUT_DIR_TMP          = "/home/pi/tmp"

SERIAL_PORT             = "/dev/ttyAMA0"

IMAGE_FORMAT            = "jpeg"
CAPTURE_RAW             = False
SENSOR_MODE             = 0
EXPOSURE_COMPENSATION   = 0

# all units in seconds
RECORDING_TIME_MAX      = 10
MOUNTING_TIME_MAX       = 10
IDLE_TIME_MAX           = 60

# consts
MODE_IDLE   = 0
MODE_REC    = 30

# camera settings: PREVIEW / STILL / VIDEO

# sensor modes:
# MODE  : SETTING           : CAMERA 
# 0     : automatic         : all
# 2     : 1    <  fps <= 15 : v1
# 3     : 1/6  <= fps <= 1  : v1   
# 2     : 1/10 <= fps <= 15 : v2
# 3     : 1/10 <= fps <= 15 : v2
# 2     : 0.1-50fps         : HQ (2x2 binned = half resolution)
# 3     : 0.005-10fps       : HQ

CAMERA_SETTINGS = {
    "HQ": [
        {"resolution": [640, 480]},     # preview
        {"resolution": [4056, 3040]},   # still 
        {"resolution": [1920, 1080]}    # video
    ],
    "V2": [
        {"resolution": [640, 480]},
        {"resolution": [3280, 2464]},
        {"resolution": [1920, 1080]}
    ],
    "V1": [
        {"resolution": [640, 480]},
        {"resolution": [2592, 1944]}, #, "framerate": Fraction(1, 15)},
        {"resolution": [1296, 972]}
    ]
}


def global_except_hook(exctype, value, tb):
    
    if cam is not None:
        cam.close()

    log = logging.getLogger()

    log.error("global error: {} | {}".format(exctype, value))

    logging.shutdown()

    # subprocess.call(["sync"])
    # sleep(1.0)

    # print("sync called. traceback:")
    if type(exctype) is not KeyboardInterrupt:
        print("traceback:")
        traceback.print_tb(tb)

    exit()

    # sys.__excepthook__(exctype, value, traceback)


def check_for_mount():

    pass


def mount():

    pass


def unmount():

    pass


class Cam(object):

    def __init__(self):

        try:
            os.mkdir(OUTPUT_DIR)
        except Exception as e:
            pass

        self.mode               = MODE_IDLE
        self.camera_type        = None
        self.camera             = None
        self.timer_start        = None
        self.last_interaction   = datetime.datetime.now()

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BUTTON_SHUTTER, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        self.camera = picamera.PiCamera(sensor_mode=SENSOR_MODE) 

        self.camera.meter_mode = "average"
        self.camera.exposure_compensation = EXPOSURE_COMPENSATION
        # camera.iso = 400

        for key in CAMERA_SETTINGS.keys():
            try:
                for setting in CAMERA_SETTINGS[key][0]:

                    # set to STILL settings to check if it fails
                    setattr(self.camera, setting, CAMERA_SETTINGS[key][1][setting])

                    # set to PREVIEW settings if the correct model is known
                    setattr(self.camera, setting, CAMERA_SETTINGS[key][0][setting])

                log.debug("camera settings applied: {}".format(key))
                self.camera_type = key
                break
            except picamera.exc.PiCameraValueError as e:
                log.debug("failing setting camera resolution for {}, attempting fallback".format(key))

        self.camera.start_preview()

        log.info("camera ready")

        try:
            self.controller = CompressorCameraController.find_by_portname(SERIAL_PORT)

            if self.controller is not None:
                log.info("controller found")
            else:
                log.warning("no controller found")
        except Exception as e:
            log.error("no controller found: {}".format(e))


    def change_camera_settings(self, mode):

        #self.camera.stop_preview()

        settings = CAMERA_SETTINGS[self.camera_type][mode]

        for key in settings:
            setattr(self.camera, key, settings[key])

        #self.camera.start_preview()


    def trigger(self):

        self.change_camera_settings(1)

        filename = self.get_filename(IMAGE_FORMAT)
        self.camera.capture(os.path.join(*filename), format=IMAGE_FORMAT, bayer=CAPTURE_RAW)
        log.info("TRIGGER: {}".format(filename[1]))
        
        self.change_camera_settings(0)


    def start_recording(self):

        log.info("REC start")

        self.mode = MODE_REC

        self.change_camera_settings(2)

        filename = self.get_filename("h264")
        log.debug("recording file: {}".format(filename))
        self.camera.start_recording(os.path.join(*filename))

        self.timer_start = datetime.datetime.now()


    def stop_recording(self):

        log.info("REC stop")

        self.mode = MODE_IDLE
        self.camera.stop_recording()

        self.change_camera_settings(0)

        self.convert_last_video_to_gif()


    def convert_last_video_to_gif(self):
        # ffmpeg package for buildroot?
        pass


    def loop(self):

        if self.mode == MODE_IDLE:

            if GPIO.input(BUTTON_SHUTTER) == 0:
                time.sleep(0.5)

                self.last_interaction = datetime.datetime.now()

                # single press: photo
                if GPIO.input(BUTTON_SHUTTER) == 1:
                    self.trigger()
                
                # long press: video
                if GPIO.input(BUTTON_SHUTTER) == 0:
                    self.start_recording()

            if (datetime.datetime.now() - self.last_interaction).total_seconds() > MOUNTING_TIME_MAX:
                unmount()

            if (datetime.datetime.now() - self.last_interaction).total_seconds() > IDLE_TIME_MAX:
                    
                if self.controller is not None:
                    try:
                        self.controller.shutdown(delay=15000)

                    except Exception as e:
                        log.error("poweroff failed: {}".format(e))
                else:
                    log.error("poweroff failed: {}".format("no controller found"))

                log.debug("logging shutdown")
                logging.shutdown()

                subprocess.call(["sync"])
                    
                # important, damage to filesystem: 
                # wait a few sec before poweroff!
                time.sleep(5)

                subprocess.call(["poweroff"])
 
        elif self.mode == MODE_REC:

            if (datetime.datetime.now() - self.timer_start).total_seconds() > RECORDING_TIME_MAX:
                log.debug("recording time max exceeded")
                self.stop_recording()
                self.mode = MODE_IDLE

            if GPIO.input(BUTTON_SHUTTER) == 1:
                self.stop_recording()
                self.mode = MODE_IDLE

        # sleep loop

        if self.mode == MODE_REC:
            self.camera.wait_recording(0.1)
        else:
            time.sleep(0.1)


    # all extensions are checked for duplicate filenames, first extension 
    # is returned as file name candidate
    def get_filename(self, extensions, prefix=None): # returns(path, filename.ext)

        if not type(extensions) is list:
            extensions = [extensions]

        for i in range(0, len(extensions)):
            if extensions[i] == "jpeg":
                extensions[i] = "jpg"

        for i in range(0, 100000):

            filename_base = "{:06d}.".format(i)
            if not prefix is None:
                filename_base = prefix + filename_base
            duplicate_found = False

            for extension in extensions:
                filename = filename_base + extension
                if os.path.exists(os.path.join(OUTPUT_DIR, filename)):
                    duplicate_found = True
                    break

            if not duplicate_found:
                return (OUTPUT_DIR, filename_base + extensions[0])

        raise Exception("no filenames left!")


    def close(self):

        log.info("CLOSE")

        if self.camera is not None:
            self.camera.stop_preview()
            self.camera.close()


if __name__ == "__main__":

    global cam

    print("init")

    # create logger
    log = logging.getLogger()
    log.handlers = [] # remove externally inserted handlers (systemd?)
    log.setLevel(logging.DEBUG)

    # subloggers
    exifread_logger = logging.getLogger("exifread").setLevel(logging.INFO)
    pil_logger = logging.getLogger("PIL").setLevel(logging.INFO) # PIL.TiffImagePlugin
    devices_logger = logging.getLogger("devices").setLevel(logging.INFO)

    # create formatter
    formatter = logging.Formatter("%(asctime)s | %(name)-7s | %(levelname)-7s | %(message)s")
    # formatter = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")

    # console handler and set level to debug
    consoleHandler = logging.StreamHandler()
    consoleHandler.setLevel(logging.DEBUG)
    consoleHandler.setFormatter(formatter)
    log.addHandler(consoleHandler)

    # fileHandlerDebug = logging.FileHandler(LOG_FILE, mode="a", encoding="UTF-8")
    # fileHandlerDebug.setLevel(logging.DEBUG)
    # fileHandlerDebug.setFormatter(formatter)
    # log.addHandler(fileHandlerDebug)

    sys.excepthook = global_except_hook

    # subprocess.run("mount -t tmpfs -o size=100m tmpfs {}".format(OUTPUT_DIR_TMP), shell=True, check=True)

    cam = None
    cam = Cam()
    
    while True:
        cam.loop()
