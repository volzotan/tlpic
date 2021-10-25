import os
import subprocess
from datetime import datetime
import numpy as np

cmd = "python3 perlin.py -x {x} -y {y} -ppu {ppu} -s {s} --output-filename {filename}"

count = 0

for i in np.linspace(1, 0.0005, num=200):
    count += 1

    values = {
        "x":    255,
        "y":    255,
        "ppu":  i,
        "s":    4,
        "filename": "animation/{:04}.png".format(count)
    }

    timer = datetime.now()
    subprocess.call(cmd.format(**values), shell=True)

    print("calculting step {:04} | took: {:5.2f}s".format(count, (datetime.now()-timer).total_seconds()))