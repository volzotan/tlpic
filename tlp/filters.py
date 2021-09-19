import os
import subprocess

import cv2
import numpy as np

FILTER_RESET            = "RESET"
FILTER_BOOMERANG        = "BOOMERANG"
FILTER_FOCAL_SWITCH     = "FOCAL_SWITCH"

TMP_DIR                 = "/tmp"

def select_filter(payload):
    if payload == filters.FILTER_RESET:
        return FILTER_RESET
    elif payload == filters.FILTER_BOOMERANG:
        return filters.FILTER_BOOMERANG
    elif payload == filters.FILTER_FOCAL_SWITCH:
        return filters.FILTER_FOCAL_SWITCH
    else:
        return None


def apply_boomerang(filename, images):
        
    NUM_INTERPOLATIONS  = 8
    EXTENSIONS          = ["gif"]
    BOUNCE_OFF          = True

    # IMAGES              = ["1.jpg", "2.jpg"]

    PARAMS = {}
    PARAMS["gif"]  = "-vf \"fps=10,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse\" -loop 0"
    PARAMS["webm"] = "-vf \"fps=10,scale=640:-1\" -an -c libvpx-vp9 -b:v 0 -crf 41"
    PARAMS["mp4"]  = "-vf \"fps=10,scale=640:-1,crop=trunc(iw/2)*2:trunc(ih/2)*2\" -an -b:v 0 -crf 25 -f mp4 -vcodec libx264 -pix_fmt yuv420p"

    img_objects = images
    num_total_images = NUM_INTERPOLATIONS + 2

    for i in range(0, num_total_images):
        tmp = cv2.addWeighted(
            img_objects[0], 1-(i/(num_total_images-1)), 
            img_objects[1],   (i/(num_total_images-1)), 
            0.0)
        cv2.imwrite(os.path.join(TMP_DIR, "interpolate_{}.jpg".format(i)), tmp)
        
        if BOUNCE_OFF:
            # cv2.imwrite("interpolate_{}.jpg".format(num_total_images + (num_total_images-2-i)), tmp) # do not double last frame | total number * 2 -1
            cv2.imwrite("interpolate_{}.jpg".format(num_total_images + (num_total_images-1-i)), tmp) # double last frame | total number * 2

    for extension in EXTENSIONS:

        cmd = ["ffmpeg", "-i", os.path.join(TMP_DIR, "interpolate_%d.jpg"), PARAMS[extension], "-y", "{}.{}".format(filename, extension)]

        cmdstr = ""
        for item in cmd:
            cmdstr += item
            cmdstr += " "

        subprocess.run(cmdstr, check=True, shell=True)

        print("finished {}".format(filename))

if __name__ == "__main__":
    pass