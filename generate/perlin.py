import math
import argparse
import textwrap

from PIL import Image, ImageOps, ImageFilter
import numpy as np
import matplotlib.pyplot as plt
from stl import mesh

import colormap

PERLIN_PER_UNIT = 0.2
SAMPLING_RATE   = 10 # per unit
Z_HEIGHT        = 10

OUTPUT_FILENAME = "out.png"

def perlin(x, y, seed=0):

    # permutation table
    np.random.seed(seed)
    p = np.arange(256, dtype=int)
    np.random.shuffle(p)
    p = np.stack([p, p]).flatten()

    # coordinates of the top-left
    xi = x.astype(int)
    yi = y.astype(int)

    # internal coordinates
    xf = x - xi
    yf = y - yi

    # fade factors
    u = fade(xf)
    v = fade(yf)

    # noise components
    g00 = p[p[xi]+yi]
    g01 = p[p[xi]+yi+1]
    g11 = p[p[xi+1]+yi+1]
    g10 = p[p[xi+1]+yi]
    n00 = gradient(g00, xf, yf)
    n01 = gradient(g01, xf, yf-1)
    n11 = gradient(g11, xf-1, yf-1)
    n10 = gradient(g10, xf-1, yf)

    # combine noises
    x1 = lerp(n00,n10,u)
    x2 = lerp(n01,n11,u)
    return lerp(x1,x2,v)

def lerp(a,b,x):
    # linear interpolation
    return a + x * (b-a)

def fade(t):
    # 6t^5 - 15t^4 + 10t^3
    return 6 * t**5 - 15 * t**4 + 10 * t**3

def gradient(h,x,y):
    # grad converts h to the right gradient vector and return the dot product with (x,y)
    
    # vectors = np.array([
    #     [0, 1],
    #     [0, -1],
    #     [1, 0],
    #     [-1, 0]]
    # )

    vectors = np.array([
        [1, 1],
        [-1, 1],
        [1, -1],
        [-1, -1]]
    )

    g = vectors[h%4]
    return g[:, :, 0] * x + g[:, :, 1] * y


def coord_to_ind(x, y, dim, sampling):
    return y * dim[0]*sampling + x


ap = argparse.ArgumentParser(description="Generate Perlin Noise")
ap.add_argument("-x",    type=int, default=100, help="width")
ap.add_argument("-y",    type=int, default=100, help="depth")
ap.add_argument("-z",    type=float, default=Z_HEIGHT, help="height")
ap.add_argument("-ppu",  type=float, default=PERLIN_PER_UNIT, help="perlin per unit")
ap.add_argument("-s", "--sampling-rate", type=int, default=SAMPLING_RATE, help="number of points per unit (width/height) [int]")
ap.add_argument("--output-image", default=None, help="output image filename")
ap.add_argument("--output-xyz", default=None, help="output pointcloud filename")
ap.add_argument("--output-stl", default=None, help="output STL filename")
ap.add_argument("--output-ply", default=None, help="output PLY filename")
ap.add_argument("--cutoff", action="store_true", default=False, help="cut off positive values")
ap.add_argument("--surface-only", action="store_true", default=False, help="for point cloud coordinates do not extrude the volume")
    
args = vars(ap.parse_args())

DIMENSIONS      = [args["x"], args["y"]]
BLOCK_HEIGHT    = args["z"]*2

linx = np.linspace(0, DIMENSIONS[0]*args["ppu"], DIMENSIONS[0]*args["sampling_rate"], endpoint=False)
liny = np.linspace(0, DIMENSIONS[1]*args["ppu"], DIMENSIONS[1]*args["sampling_rate"], endpoint=False)
x, y = np.meshgrid(linx, liny)

res = perlin(x, y, seed=2)
res_min = np.min(res)
res_max = np.max(res)
res = np.multiply(res, args["z"])

# cut off the hills, keep the valleys
if args["cutoff"]:
    res[res[:,:] > 0] = 0 

if args["output_image"]:
    plt.imsave(
        args["output_image"], 
        res, 
        vmin=-1, #-math.sqrt(2), 
        vmax=1, #+math.sqrt(2), 
        origin="upper"
    )

if args["output_ply"]:

    s = args["sampling_rate"]
    num_vertices = (DIMENSIONS[0]*s) * (DIMENSIONS[1]*s)
    num_faces = (DIMENSIONS[0]*s-1) * (DIMENSIONS[1]*s-1) * 2

    with open(args["output_ply"], "w") as f:
        data =  """
                ply
                format ascii 1.0
                element vertex {}
                property float x
                property float y
                property float z
                property uchar red
                property uchar green
                property uchar blue
                element face {}
                property list uchar int vertex_indices
                end_header
                """

        data = textwrap.dedent(data[1:]) # remove first newline (for dedent to work)        
        data = data.format(num_vertices, num_faces)

        vertices = []
        faces = []

        f.write(data)

        for y in range(0, DIMENSIONS[1]*s):
            for x in range(0, DIMENSIONS[0]*s):

                pos = (res[y, x]/args["z"] - res_min)/(res_max-res_min)
                c = colormap._viridis_data[int(pos*(len(colormap._viridis_data)-1))]
                c = [int(x*255) for x in c]

                f.write("{:.3f} {:.3f} {:.3f} {:d} {:d} {:d}\n".format(x/s, y/s, res[y,x], *c))

        for y in range(0, DIMENSIONS[1]*s-1):
            for x in range(0, DIMENSIONS[0]*s-1):

                f.write("3 {} {} {}\n".format(
                    coord_to_ind(x,     y,      DIMENSIONS, s),
                    coord_to_ind(x+1,   y,      DIMENSIONS, s),
                    coord_to_ind(x,     y+1,    DIMENSIONS, s),
                ))
                
                f.write("3 {} {} {}\n".format(
                    coord_to_ind(x+1,   y,      DIMENSIONS, s),
                    coord_to_ind(x+1,   y+1,    DIMENSIONS, s),
                    coord_to_ind(x,     y+1,    DIMENSIONS, s),
                ))

        f.write("\n")
        

if args["output_stl"]:

    s = args["sampling_rate"]

    num_faces = ((DIMENSIONS[0]*s-1) *
                (DIMENSIONS[1]*s-1) * 4 +
                (DIMENSIONS[0]*s) * 4 +
                (DIMENSIONS[1]*s) * 4)

    obj = mesh.Mesh(np.zeros(num_faces, dtype=mesh.Mesh.dtype))
    count = 0

    for x in range(0, DIMENSIONS[0]*s-1):
        for y in range(0, DIMENSIONS[1]*s-1):
            
            obj.vectors[count][0] = [x/s, y/s, res[y,x]]
            obj.vectors[count][1] = [(x+1)/s, y/s, res[y,x+1]]
            obj.vectors[count][2] = [x/s, (y+1)/s, res[y+1,x]]

            count += 1

            obj.vectors[count][0] = [(x+1)/s, y/s, res[y,x+1]]
            obj.vectors[count][1] = [(x+1)/s, (y+1)/s, res[y+1,x+1]]
            obj.vectors[count][2] = [x/s, (y+1)/s, res[y+1,x]]

            count += 1

    if not args["surface_only"]:

        # side T/B

        for y in [0, DIMENSIONS[1]*s-1]:
            for x in range(0, DIMENSIONS[0]*s-1):
                    
                obj.vectors[count][0] = [x/s, y/s, -BLOCK_HEIGHT]
                obj.vectors[count][1] = [(x+1)/s, y/s, -BLOCK_HEIGHT]
                obj.vectors[count][2] = [x/s, y/s, res[y,x]]

                count += 1

                obj.vectors[count][0] = [(x+1)/s, y/s, -BLOCK_HEIGHT]
                obj.vectors[count][1] = [(x+1)/s, y/s, res[y,x+1]]
                obj.vectors[count][2] = [x/s, y/s, res[y,x]]

                count += 1

        # side L/R

        for x in [0, DIMENSIONS[0]*s-1]:
            for y in range(0, DIMENSIONS[0]*s-1):

                obj.vectors[count][0] = [x/s, y/s, -BLOCK_HEIGHT]
                obj.vectors[count][1] = [x/s, (y+1)/s, -BLOCK_HEIGHT]
                obj.vectors[count][2] = [x/s, y/s, res[y,x]]

                count += 1

                obj.vectors[count][0] = [x/s, (y+1)/s, -BLOCK_HEIGHT]
                obj.vectors[count][1] = [x/s, (y+1)/s, res[y+1,x]]
                obj.vectors[count][2] = [x/s, y/s, res[y,x]]

                count += 1

        # bottom

        for x in range(0, DIMENSIONS[0]*s-1):
            for y in range(0, DIMENSIONS[1]*s-1):
                
                obj.vectors[count][0] = [x/s, y/s, -BLOCK_HEIGHT]
                obj.vectors[count][1] = [(x+1)/s, y/s, -BLOCK_HEIGHT]
                obj.vectors[count][2] = [x/s, (y+1)/s, -BLOCK_HEIGHT]

                count += 1

                obj.vectors[count][0] = [(x+1)/s, y/s, -BLOCK_HEIGHT]
                obj.vectors[count][1] = [(x+1)/s, (y+1)/s, -BLOCK_HEIGHT]
                obj.vectors[count][2] = [x/s, (y+1)/s, -BLOCK_HEIGHT]

                count += 1

    obj.save(args["output_stl"])


if args["output_xyz"]:

    with open(args["output_xyz"], "w") as f:

        for i in range(0, DIMENSIONS[1]*args["sampling_rate"]):
            for j in range(0, DIMENSIONS[0]*args["sampling_rate"]):
                f.write("{} {} {}\n".format(j/args["sampling_rate"], i/args["sampling_rate"], res[i, j]))

        if not args["surface_only"]:

            ## additional points
            # side L/R

            for i in range(0, DIMENSIONS[1]*args["sampling_rate"]):
                for j in [0, DIMENSIONS[0]*args["sampling_rate"]-1]:
                    zs = np.linspace(-BLOCK_HEIGHT, res[i, j]*args["z"], int(BLOCK_HEIGHT*args["sampling_rate"]), endpoint=False)
                    for z in zs:
                        f.write("{} {} {}\n".format(j/args["sampling_rate"], i/args["sampling_rate"], z))

            # side T/B

            for i in [0, DIMENSIONS[1]*args["sampling_rate"]-1]:
                for j in range(0, DIMENSIONS[0]*args["sampling_rate"]):
                    zs = np.linspace(-BLOCK_HEIGHT, res[i, j]*args["z"], int(BLOCK_HEIGHT*args["sampling_rate"]), endpoint=False)
                    for z in zs:
                        f.write("{} {} {}\n".format(j/args["sampling_rate"], i/args["sampling_rate"], z))

            # bottom plane

            for j in linx[1:]:
                for i in liny[1:]:
                    f.write("{} {} {}\n".format(j/args["ppu"], i/args["ppu"], -BLOCK_HEIGHT))
