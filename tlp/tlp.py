#!/usr/bin/env python3

import math
import time
import datetime
import os
import sys
import subprocess
from fractions import Fraction
import logging
import traceback

from concurrent.futures import ThreadPoolExecutor

import RPi.GPIO as GPIO
import picamera
import numpy as np
import cv2
from PIL import Image

# from pyzbar.pyzbar import decode, ZBarSymbol

from devices import CompressorCameraController
import filters

# revA/B | BCM numbering
PIN_BUTTON_SHUTTER      = 22 
PIN_BUTTON_FOCUS        = 27
PIN_BUTTON_CAM0         = 17 
PIN_BUTTON_CAM1         =  4
PIN_LED1                =  6
PIN_LED2                = 13

OUTPUT_DIR              = "/media/storage"
OUTPUT_DIR_TMP          = "/home/pi/tmp"
ASSET_DIR               = "assets"

SERIAL_PORT             = "/dev/ttyAMA0"

IMAGE_FORMAT            = "jpeg"
CAPTURE_RAW             = False
SENSOR_MODE             = 0 #3 #0
EXPOSURE_COMPENSATION   = 0

SCAN_QR_CODES           = False
QR_CODE_PREFIX          = "TLP::"
DEFAULT_ACTIVE_FILTER   = filters.FILTER_BOOMERANG

# all units in seconds
RECORDING_TIME_MAX      = 10
IDLE_TIME_MAX           = 300 
TRIGGER_TIMEOUT         = 10

# consts
MODE_IDLE   = 0
MODE_REC    = 30

# FOR DEBUG:
IDLE_TIME_MAX           = 600

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
    "IMX477": [
        {"resolution": [320, 240]},     # 0 : preview
        {"resolution": [4056, 3040]},   # 1 : still 
        {"resolution": [1920, 1080]}    # 2 : video
    ],
    "IMX219": [
        {"resolution": [320, 240]},
        {"resolution": [3280, 2464]},
        {"resolution": [1920, 1080]}
    ],
    "OV5647": [
        {"resolution": [320, 240]},
        {"resolution": [2592, 1944]}, #, "framerate": Fraction(1, 15)},
        {"resolution": [1296, 972]}
    ]
}

MODE_PREVIEW    = 0
MODE_STILL      = 1
MODE_VIDEO      = 2


def global_except_hook(exctype, value, tb):
    
    if tlcam is not None:
        tlcam.close()

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


def _change_camera_settings(cam, mode):

    camera_type = None

    log.debug("change mode: {}".format(mode))

    try:
        key = str(cam.revision).upper()
        for setting in CAMERA_SETTINGS[key][mode]:
            setattr(cam, setting, CAMERA_SETTINGS[key][mode][setting])

        camera_type = key
        log.debug("cam {} | camera settings applied: {}".format(cam, key))
    except picamera.exc.PiCameraValueError as e:
        log.debug("cam {} | failing setting camera resolution for {}, attempting fallback".format(cam, key))

        for key in CAMERA_SETTINGS.keys():
            try:
                # set to STILL resolution to check if it fails
                cam.resolution = CAMERA_SETTINGS[key][MODE_STILL]["resolution"]
     
                for setting in CAMERA_SETTINGS[key][mode]:
                    setattr(cam, setting, CAMERA_SETTINGS[key][mode][setting])

                camera_type = key
                log.debug("cam {} | camera settings applied: {}".format(cam, key))

                break
            except picamera.exc.PiCameraValueError as e:
                log.debug("cam {} | failing setting camera resolution for {}, attempting fallback".format(cam, key))
         
    return camera_type


def _trigger(cam, filename):

    camera_type = _change_camera_settings(cam, MODE_STILL)

    # capture to file
    # self.camera.capture(os.path.join(*filename), format=IMAGE_FORMAT, bayer=CAPTURE_RAW)

    # capture to numpy datastructure
    res = CAMERA_SETTINGS[camera_type][MODE_STILL]["resolution"]

    # beware, from the picamera docs:
    # It is also important to note that when outputting to unencoded formats, the camera rounds the 
    # requested resolution. The horizontal resolution is rounded up to the nearest multiple of 32 pixels, 
    # while the vertical resolution is rounded up to the nearest multiple of 16 pixels. For example, 
    # if the requested resolution is 100x100, the capture will actually contain 128x112 pixels worth of data, 
    # but pixels beyond 100x100 will be uninitialized.
    
    res_rounded = [res[0], res[1]]
    res_rounded[0] = math.ceil(res_rounded[0] / 32)*32 
    res_rounded[1] = math.ceil(res_rounded[1] / 16)*16 

    img = np.empty((res_rounded[1] * res_rounded[0] * 3), dtype=np.uint8)
    cam.capture(img, "bgr") #"rgb")

    # cut off padding from rounding
    img = img.reshape([res_rounded[1], res_rounded[0], 3])
    img = img[:res[0], :res[1], :]

    # TODO: somewhere I am mixing up rows and cols, making the image square. Where?

    # scan for QR codes always on the out-of-camera image
    if SCAN_QR_CODES:
        qrcode = decode(img, symbols=[ZBarSymbol.QRCODE])

        try:
            filter_type = self.configure_filter(qrcode.data)
        except Exception as e:
            log.debug("filter not applied")
            # TODO: show message on display

    # self.save_image(filename, img)
    # print(img.shape)

    # write to file
    cv2.imwrite(os.path.join(*filename), img)

    log.info("TRIGGER: {}".format(filename[1]))

    _change_camera_settings(cam, MODE_PREVIEW)

    return (filename, img)


# captures data: [[filename0, img0], [filename1, img1]]
def _apply_filter(filter_type, captures_data):
    try:
        if filter_type == filters.FILTER_BOOMERANG:
            filename = os.path.join(captures_data[0][0][0], "filter_" + captures_data[0][0][1])
            filters.apply_boomerang(
                filename, 
                [x[1] for x in captures_data]
            )
        else:
            log.error("cannot apply filter, unknown filter type: {}".format(filter_type))
    except Exception as e:
        log.error("applying filter {} failed: {}".format(filter_type, e))


class TLCam(object):

    def __init__(self):

        try:
            os.mkdir(OUTPUT_DIR)
        except Exception as e:
            pass

        self.mode               = MODE_IDLE
        self.camera_type        = []
        self.camera             = [None, None]
        self.active_filter      = DEFAULT_ACTIVE_FILTER
        self.timer_start        = None
        self.last_interaction   = datetime.datetime.now()
        self.controller         = None

        self.pool = ThreadPoolExecutor(3)

        self.init_pins()

        picamera_args = [
            {},
            {"led_pin": 30}
        ]

        for i in range(0, 2):
            try:
                self.camera[i] = (picamera.PiCamera(sensor_mode=SENSOR_MODE, camera_num=i, **picamera_args[i]))
                self.camera[i].exif_tags["IFD0.Make"] = "TLP"
                self.camera[i].exif_tags["IFD0.Model"] += "_TLP_{}".format(i)

                log.debug("init camera {} // sensor: {}".format(i, self.camera[i].revision))
            except Exception as e:
                log.debug("init camera {} failed: {}".format(i, e))

        for cam in self.camera:
            if cam is None:
                continue
            
            cam.meter_mode = "average"
            cam.exposure_compensation = EXPOSURE_COMPENSATION
            # camera.iso = 400

            _change_camera_settings(cam, MODE_PREVIEW)

        self.camera[0].start_preview()

        log.info("camera(s) ready")

        try:
            self.controller = CompressorCameraController.find_by_portname(SERIAL_PORT)

            if self.controller is not None:
                log.info("controller found")
            else:
                log.warning("no controller found")
        except Exception as e:
            log.error("no controller found: {}".format(e))


    def init_pins(self):

        GPIO.setmode(GPIO.BCM)
        
        GPIO.setup(PIN_BUTTON_SHUTTER,  GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PIN_BUTTON_FOCUS,    GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PIN_BUTTON_CAM0,     GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PIN_BUTTON_CAM1,     GPIO.IN, pull_up_down=GPIO.PUD_UP)

        GPIO.setup(PIN_LED1,            GPIO.OUT)
        GPIO.setup(PIN_LED2,            GPIO.OUT)


    def trigger(self):

        future_triggers = []
        filename = self.get_filename(IMAGE_FORMAT)

        for i in range(0, len(self.camera)):
            cam = self.camera[i]
            if cam is None:
                continue

            filename_split = os.path.splitext(filename[1])
            filename_new = [filename[0], "{}_{}{}".format(filename_split[0], i, filename_split[1])]

            future_triggers.append(self.pool.submit(_trigger, cam, filename_new))

        # wait till all trigger threads are done
        captures_data = []
        for f in future_triggers:
            captures_data.append(f.result(timeout=TRIGGER_TIMEOUT))

        # apply filters?
        future_filters = []
        if self.active_filter is not None:
            log.info("applying filter: {}".format(self.active_filter))
            future_filters.append(self.pool.submit(_apply_filter, self.active_filter, captures_data))

        log.debug("trigger done")

        # TODO:

        img = Image.open(os.path.join(ASSET_DIR, "overlay_filter.png"))
        b = img.tobytes()
        o = self.camera[0].add_overlay(b, layer=3, alpha=128)        
        # o = camera.add_overlay(pad.tostring(), size=img.size)
        # o = camera.add_overlay(np.getbuffer(a), layer=3, alpha=64)

        time.sleep(1)


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


    def configure_filter(self, payload):

        if not payload.startswith(QR_CODE_PREFIX):
            log.warning("incompatible QR code recognized. Payload: {}".format(str))
            raise Exception("incompatible QR")

        ret = filters.configure_filter(payload[len(QR_CODE_PREFIX):])

        if ret is not None:
            log.info("configured filter {}".format(ret))
            self.filter_type = ret
        else:
            log.warning("compatible but unknown QR code recognized. Payload: {}".format(str))
            raise


    # def save_image(self, filename, img):
        
    #     if self.filter_type is None:
    #         cv2.imwrite(os.path.join(*filename), img)
    #         log.debug("write image [filter: None] to: {}".format(filename[-1]))
    #     if self.filter_type == filters.FILTER_BOOMERANG:
    #         filters.apply_boomerang(img)
    #     else:
    #         log.error("undefined filter type: {}".format(self.filter_type))


    def convert_last_video_to_gif(self):
        # ffmpeg package for buildroot?
        pass


    def loop(self):

        if self.mode == MODE_IDLE:

            time.sleep(1.0)
            self.trigger()
            time.sleep(1.0)
            self.close()
            exit()

            if GPIO.input(PIN_BUTTON_SHUTTER) == 0:
                time.sleep(0.5)

                self.last_interaction = datetime.datetime.now()

                # single press: photo
                if GPIO.input(PIN_BUTTON_SHUTTER) == 1:
                    self.trigger()
                
                # long press: video
                if GPIO.input(PIN_BUTTON_SHUTTER) == 0:
                    self.start_recording()


            if GPIO.input(PIN_BUTTON_CAM0) == 0:
                self.last_interaction = datetime.datetime.now()


            if GPIO.input(PIN_BUTTON_CAM1) == 0:
                self.last_interaction = datetime.datetime.now()


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

            if GPIO.input(PIN_BUTTON_SHUTTER) == 1:
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

                filename = filename_base + "_0" + extension
                if os.path.exists(os.path.join(OUTPUT_DIR, filename)):
                    duplicate_found = True
                    break

            if not duplicate_found:
                return [OUTPUT_DIR, filename_base + extensions[0]]

        raise Exception("no filenames left!")


    def close(self):

        log.info("CLOSE")

        for cam in self.camera:

            if cam is None:
                continue

            cam.stop_preview()
            cam.close()

        GPIO.cleanup()


if __name__ == "__main__":

    global tlcam

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

    tlcam = None
    tlcam = TLCam()
    
    while True:
        tlcam.loop()
