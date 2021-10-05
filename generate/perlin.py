from PIL import Image, ImageOps, ImageFilter
import numpy as np
import matplotlib.pyplot as plt
import pyvista as pv

DIMENSIONS      = [60, 110]
PERLIN_PER_UNIT = 0.09
SAMPLING_RATE   = 10 # per unit
Z_HEIGHT        = 10

BLOCK_HEIGHT    = Z_HEIGHT*2

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

linx = np.linspace(0, DIMENSIONS[0]*PERLIN_PER_UNIT, DIMENSIONS[0]*SAMPLING_RATE, endpoint=False)
liny = np.linspace(0, DIMENSIONS[1]*PERLIN_PER_UNIT, DIMENSIONS[1]*SAMPLING_RATE, endpoint=False)
x, y = np.meshgrid(linx, liny)

res = perlin(x, y, seed=2)

res[res[:,:] > 0] = 0 

# res = res + np.sqrt(2)
# res = np.add(res, np.abs(np.min(res)))

with open("p.xyz", "w") as f:
    grid = pv.StructuredGrid(x, y, res)
    for p in grid.points:
        f.write("{} {} {}\n".format(p[0]/PERLIN_PER_UNIT, p[1]/PERLIN_PER_UNIT, p[2]*Z_HEIGHT))

    # add additional points
    # for px in linx:
    #     for py in liny:
    #         f.write("{} {} {}\n".format(px/PERLIN_PER_UNIT, py/PERLIN_PER_UNIT, Z_HEIGHT*3))

    # for e in res[,:]
    # lin = np.linspace(0, DIMENSIONS[1]*PERLIN_PER_UNIT, DIMENSIONS[1]*SAMPLING_RATE, endpoint=False)

    # for i in range(0, 10):
    #     for p in grid.points:
    #         f.write("{} {} {}\n".format(p[0]/PERLIN_PER_UNIT, p[1]/PERLIN_PER_UNIT, p[2]-1.0*i))

    for i in range(0, DIMENSIONS[1]*SAMPLING_RATE):
        for j in [0, DIMENSIONS[0]*SAMPLING_RATE-1]:
            zs = np.linspace(-BLOCK_HEIGHT, res[i, j]*Z_HEIGHT, BLOCK_HEIGHT*SAMPLING_RATE, endpoint=False)
            for z in zs:
                f.write("{} {} {}\n".format(j/SAMPLING_RATE, i/SAMPLING_RATE, z))

    for i in [0, DIMENSIONS[1]*SAMPLING_RATE-1]:
        for j in range(0, DIMENSIONS[0]*SAMPLING_RATE):
            zs = np.linspace(-BLOCK_HEIGHT, res[i, j]*Z_HEIGHT, BLOCK_HEIGHT*SAMPLING_RATE, endpoint=False)
            for z in zs:
                f.write("{} {} {}\n".format(j/SAMPLING_RATE, i/SAMPLING_RATE, z))

    for j in linx[1:]:
        for i in liny[1:]:
            f.write("{} {} {}\n".format(j/PERLIN_PER_UNIT, i/PERLIN_PER_UNIT, -BLOCK_HEIGHT))

exit()

plt.imsave("test.png", res, origin='upper')

with Image.open("overlay.png") as im:
    im = im.resize([res.shape[1], res.shape[0]])
    im = ImageOps.grayscale(im)
    blurred_image = im.filter(ImageFilter.GaussianBlur(radius=2))
    base = np.array(blurred_image)/255

    base = np.multiply(res, base)

    result = Image.fromarray((base * 255).astype(np.uint8))
    result.save("out.png")

exit()

grid = pv.StructuredGrid(x, y, res)
# grid.plot(show_edges=True)

top = grid.points.copy()
bottom = grid.points.copy()
bottom[:,-1] = -1.0 

vol = pv.StructuredGrid()
vol.points = np.vstack((top, bottom))
vol.dimensions = [*grid.dimensions[0:2], 2]
vol.plot() #show_edges=True)

# surf = pv.wrap(vol.points).reconstruct_surface()

# pl = pv.Plotter(shape=(1,2))
# pl.add_mesh(vol.points)
# pl.add_title('Point Cloud of 3D Surface')
# pl.subplot(0,1)
# pl.add_mesh(surf, color=True, show_edges=True)
# pl.add_title('Reconstructed Surface')
# pl.show()

# vol.save("mesh.vtk")
# vol.save("mesh.stl")

# contours = vol.contour()

# p = pv.Plotter()
# p.add_mesh(vol, opacity=0.85)
# p.add_mesh(contours, color="white", line_width=5)
# p.show()