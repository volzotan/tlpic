Generate Perlin Noise patterns to modify STL files for 3d printing.

#### Usage

For detailed usage information see
```
python3 perlin.py --help
```

Important variables:

*ppu* Zoom factor. The smaller the ppu value, the larger the hills and valleys  
*s* sample rate: number of evaluation points per x/y unit

#### Examples

```
python3 perlin.py -x 100 -y 100 -z 10 -s 3 --output-image image.png --output-xyz pointcloud.xyz --output-stl mesh.stl
```

Calculate a block of Perlin noise (100 by 100 units and a height of 10 units) with a precision of 3 values per unit. Output the values as an image, a pointcloud and a mesh. Units can be interpreted as millimeter, meter or inch, depending on your application.

```
python3 perlin.py -x 100 -y 100 -z 10 -s 3 --output-stl mesh.stl --surface-only
```
Same as above, but just the noise (no block) as an STL.