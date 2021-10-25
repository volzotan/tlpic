Generate Perlin Noise patterns to modify STL files for 3d printing.

## Usage

See
```
python3 perlin.py --help
```

Important variables:

*ppu* Zoom factor. The smaller the ppu value, the larger the hills and valleys
*s* sample rate: number of evaluation points per x/y unit

## Examples

```
python3 perlin.py -x 100 -y 100 -z 10 -s 3 --output-image image.png --output-xyz pointcloud.xyz --output-stl mesh.stl
```