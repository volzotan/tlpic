import os
import subprocess

import cv2
import numpy as np
import matplotlib.pyplot as plt

NUM_INTERPOLATIONS  = 20-2
EXTENSIONS          = ["mp4"]
BOOMERANG           = True

IMAGES              = ["focal_2.jpg", "focal_1.jpg"]
IMAGES              = ["focal_4.jpg", "focal_3.jpg"]
TMP_DIR             = "tmp"

MIN_MATCH_COUNT = 6

PARAMS = {}
PARAMS["gif"]  = "-vf \"fps=25,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse\" -loop 0"
PARAMS["webm"] = "-vf \"fps=25,scale=640:-1\" -an -c libvpx-vp9 -b:v 0 -crf 41"
PARAMS["mp4"]  = "-vf \"fps=25,scale=640:-1,crop=trunc(iw/2)*2:trunc(ih/2)*2\" -an -b:v 0 -crf 25 -f mp4 -vcodec libx264 -pix_fmt yuv420p"

img1 = cv2.imread(IMAGES[0])
img2 = cv2.imread(IMAGES[1])

img1_bw = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
img2_bw = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

# scale_percent = 50 # percent of original size
# width = int(img1.shape[1] * scale_percent / 100)
# height = int(img1.shape[0] * scale_percent / 100)
# dim = (width, height)
  
# img1 = cv2.resize(img1, dim, interpolation = cv2.INTER_AREA)
# img2 = cv2.resize(img2, dim, interpolation = cv2.INTER_AREA)

# Initiate ORB detector
# orb = cv2.ORB_create(nfeatures=1000) #scoreType=cv2.ORB_FAST_SCORE)
# kp1, des1 = orb.detectAndCompute(img1_bw,None)
# kp2, des2 = orb.detectAndCompute(img2_bw,None)

surf = cv2.xfeatures2d.SURF_create(400)
kp1, des1 = surf.detectAndCompute(img1_bw,None)
kp2, des2 = surf.detectAndCompute(img2_bw,None)

print("found keypoints: {} | {}".format(len(kp1), len(kp2)))

# FLANN_INDEX_LSH = 6
# index_params= dict(algorithm = FLANN_INDEX_LSH,
#                    table_number = 6, # 12
#                    key_size = 12,     # 20
#                    multi_probe_level = 1) #2
# search_params = {}


FLANN_INDEX_KDTREE = 1
index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
search_params = dict(checks=50)   # or pass empty dictionary

flann = cv2.FlannBasedMatcher(index_params, search_params)
matches = flann.knnMatch(des1,des2,k=2)

matchesMask = [[0,0] for i in range(len(matches))]
good = []

for i in range(0, len(matches)):
    if len(matches[i]) == 2:
        m, n = matches[i]
        if m.distance < 0.7*n.distance:
            matchesMask[i]=[1,0]
            good.append(m)

print("found {} good matches".format(len(good)))

if len(good) < MIN_MATCH_COUNT:

    print( "Not enough matches are found - {}/{}".format(len(good), MIN_MATCH_COUNT) )
    matchesMask = None
    exit()

src_pts = np.float32([ kp1[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
dst_pts = np.float32([ kp2[m.trainIdx].pt for m in good ]).reshape(-1,1,2)

M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)

# TODO: check if images are correctly ordered.
# img1 needs to have the higher focal length (more zoomed in)

h,w,d = img1.shape
pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)
dst = cv2.perspectiveTransform(pts,M)

# draw outlines of warped image
# img2 = cv2.polylines(img2,[np.int32(dst)],True,255,3, cv2.LINE_AA)

# avg_x1 =  (dst[0][0][0] + dst[1][0][0])/2
# avg_x2 =  (dst[2][0][0] + dst[3][0][0])/2
# avg_y1 =  (dst[0][0][1] + dst[3][0][1])/2
# avg_y2 =  (dst[1][0][1] + dst[2][0][1])/2

# dst[0][0][0] = avg_x1
# dst[1][0][0] = avg_x1
# dst[2][0][0] = avg_x2
# dst[3][0][0] = avg_x2

# dst[0][0][1] = avg_y1
# dst[3][0][1] = avg_y1
# dst[1][0][1] = avg_y2
# dst[2][0][1] = avg_y2

# img2 = cv2.polylines(img2,[np.int32(dst)],True,255,3, cv2.LINE_AA)

# draw_params = dict(matchColor = (0,255,0),
#                    singlePointColor = (255,0,0),
#                    matchesMask = matchesMask,
#                    flags = cv2.DrawMatchesFlags_DEFAULT)
# img3 = cv2.drawMatchesKnn(img1,kp1,img2,kp2,matches,None,**draw_params)
# plt.imshow(img3,),plt.show()
# exit()


num_total_images = NUM_INTERPOLATIONS + 2

for i in range(0, num_total_images):

    height, width, channels = img1.shape
    img1_warp = cv2.warpPerspective(img1, M, (width, height))

    # img2[img1_warp > 0] = 0

    tmp = img2.copy().astype(np.float64)
    tmp[img1_warp > 0] *= 1-(i/(num_total_images-1))
    tmp = np.add(tmp, img1_warp * (i/(num_total_images-1))).astype(np.uint8)

    # tmp = cv2.addWeighted(
    #     img2, 1.0, #1-(i/(num_total_images-1)), 
    #     img1_warp, (i/(num_total_images-1)), 
    #     0.0)

    M_inverse = np.linalg.inv(M)
    diff = np.identity(3) - M_inverse 

    M_intermediate = np.identity(3) - (i/(num_total_images-1)) * diff

    height, width, channels = tmp.shape
    tmp_warp = cv2.warpPerspective(tmp, M_intermediate, (width, height))

    cv2.imwrite(os.path.join(TMP_DIR, "focal_{}.jpg".format(i)), tmp_warp)

    if BOOMERANG:
        cv2.imwrite(os.path.join(TMP_DIR, "focal_{}.jpg".format(num_total_images + (num_total_images-1-i))), tmp_warp) # double last frame | total number * 2

for extension in EXTENSIONS:

    cmd = ["ffmpeg", "-i", os.path.join(TMP_DIR, "focal_%d.jpg"), PARAMS[extension], "-y", "{}.{}".format("focal2", extension)]

    cmdstr = ""
    for item in cmd:
        cmdstr += item
        cmdstr += " "

    subprocess.run(cmdstr, check=True, shell=True)

    print("finished {}".format("foo", extension))