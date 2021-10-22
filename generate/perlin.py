from PIL import Image, ImageOps, ImageFilter
import numpy as np
import matplotlib.pyplot as plt
import pyvista as pv
import argparse

PERLIN_PER_UNIT = 0.2
SAMPLING_RATE   = 10 # per unit
Z_HEIGHT        = 10

BLOCK_HEIGHT    = Z_HEIGHT*2
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
    
    vectors = np.array([
        [0, 1],
        [0, -1],
        [1, 0],
        [-1, 0]]
    )

    # vectors = np.array([
    #     [1, 1],
    #     [-1, 1],
    #     [1, -1],
    #     [-1, -1]]
    # )

    g = vectors[h%4]
    return g[:, :, 0] * x + g[:, :, 1] * y


ap = argparse.ArgumentParser(description="Generate Perlin Noise")
ap.add_argument("-x",    type=int, default=100, help="width")
ap.add_argument("-y",    type=int, default=100, help="depth")
ap.add_argument("-z",    type=float, default=Z_HEIGHT, help="height")
ap.add_argument("-ppu",  type=float, default=PERLIN_PER_UNIT, help="perlin per unit")
ap.add_argument("-s", "--sampling-rate", type=int, default=SAMPLING_RATE, help="number of points per unit (width/height) [int]")
ap.add_argument("-o", "--output-filename", default=OUTPUT_FILENAME, help="output filename")
ap.add_argument("--cutoff", action="store_true", default=False, help="cut off positive values")
    
args = vars(ap.parse_args())

DIMENSIONS = [args["x"], args["y"]]

linx = np.linspace(0, DIMENSIONS[0]*args["ppu"], DIMENSIONS[0]*args["sampling_rate"], endpoint=False)
liny = np.linspace(0, DIMENSIONS[1]*args["ppu"], DIMENSIONS[1]*args["sampling_rate"], endpoint=False)
x, y = np.meshgrid(linx, liny)

res = perlin(x, y, seed=2)

# cut off the hills, keep the valleys
if args["cutoff"]:
    res[res[:,:] > 0] = 0 

plt.imsave(args["output_filename"], res, origin="upper")

exit()

with open("p.xyz", "w") as f:
    grid = pv.StructuredGrid(x, y, res)
    for p in grid.points:
        f.write("{} {} {}\n".format(p[0]/args["ppu"], p[1]/args["ppu"], p[2]*Z_HEIGHT))

    ## additional points
    # side L/R

    for i in range(0, DIMENSIONS[1]*args["sampling_rate"]):
        for j in [0, DIMENSIONS[0]*args["sampling_rate"]-1]:
            zs = np.linspace(-BLOCK_HEIGHT, res[i, j]*Z_HEIGHT, BLOCK_HEIGHT*args["sampling_rate"], endpoint=False)
            for z in zs:
                f.write("{} {} {}\n".format(j/args["sampling_rate"], i/args["sampling_rate"], z))

    # side T/B

    for i in [0, DIMENSIONS[1]*args["sampling_rate"]-1]:
        for j in range(0, DIMENSIONS[0]*args["sampling_rate"]):
            zs = np.linspace(-BLOCK_HEIGHT, res[i, j]*Z_HEIGHT, BLOCK_HEIGHT*args["sampling_rate"], endpoint=False)
            for z in zs:
                f.write("{} {} {}\n".format(j/args["sampling_rate"], i/args["sampling_rate"], z))

    # bottom plane

    for j in linx[1:]:
        for i in liny[1:]:
            f.write("{} {} {}\n".format(j/args["ppu"], i/args["ppu"], -BLOCK_HEIGHT))

exit()

with Image.open("overlay.png") as im:
    im = im.resize([res.shape[1], res.shape[0]])
    im = ImageOps.grayscale(im)
    blurred_image = im.filter(ImageFilter.GaussianBlur(radius=2))
    base = np.array(blurred_image)/255

    base = np.multiply(res, base)

    result = Image.fromarray((base * 255).astype(np.uint8))
    result.save("out.png")


# grid = pv.StructuredGrid(x, y, res)
# # grid.plot(show_edges=True)

# top = grid.points.copy()
# bottom = grid.points.copy()
# bottom[:,-1] = -1.0 

# vol = pv.StructuredGrid()
# vol.points = np.vstack((top, bottom))
# vol.dimensions = [*grid.dimensions[0:2], 2]
# vol.plot() #show_edges=True)

