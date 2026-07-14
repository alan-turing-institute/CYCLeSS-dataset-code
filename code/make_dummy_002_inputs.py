#######################################################################
# Make dummy inputs for 002_merge_sentinel1
#######################################################################

# builds fake versions of the raw inputs 002 needs (the 10km merge grid csv
# plus a folder of sentinel-1 band tiles) so runs can be diffed on identical
# inputs. deterministic - rerun to reset

# pip install pandas numpy rasterio

import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_bounds, from_origin

############################
# Project paths
############################

# run this from inside code/ so "one level up" lands on the same project
# root 002 uses
code_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(code_dir)
base = project_root + "/data/par-merge-test/"
tiles = project_root + "/data/Raw Sentinel-1 SAR/2015/VH/VH_2015_Apr_Jun/2/chunk-2015-04-01_2015-06-30/"
os.makedirs(base, exist_ok = True)
os.makedirs(tiles, exist_ok = True)

# clear outputs from any previous run - the _with_grid csvs land right next
# to the tifs, so a failed run would otherwise leave stale files behind
for f in os.listdir(tiles):
    if f.endswith("_with_grid.csv"):
        os.remove(tiles + f)

############################
# Grid extent and tiles
############################

# all coordinates and pixel sizes here are dyadic (exact in floating point,
# e.g. 1/1024) - a value that isn't exact would diff dirty on formatting
# alone even when the numbers are identical
res = 1.0 / 1024.0

# extent of the fake 1km grid - the two corner points below pin min/max so
# both runs build the same raster over ncol = 3069, nrow = 18
minx, miny = -1.25, 51.5
maxx, maxy = -1.0, 51.75
ncol, nrow = 3069, 18
transform = from_bounds(minx, miny, maxx, maxy, ncol, nrow)

# two small tiles - the first fully inside the grid extent, the second
# poking past the east edge so some pixels get no grid id and the drop path
# gets exercised. 6 x 5 pixels, 3 bands each (a mini 12-day time series)
tile_specs = [
    ("dummy_ts_vh_0_2015-04-01_2015-06-30-0000000000-0000000000.tif", -1.1875, 51.703125),
    ("dummy_ts_vh_0_2015-04-01_2015-06-30-0000000000-0000000256.tif", -1.00390625, 51.6015625),
]
band_dates = ("2015-04-01", "2015-04-13", "2015-04-25")
nx, ny = 6, 5

rng = np.random.default_rng(42)

############################
# Grid points csv
############################

# for every tile pixel centre that falls inside the extent, work out which
# grid cell it lands in and put a grid point (with a made-up id) at that
# cell's centre - guarantees rasterize burns the id into exactly the cell
# the lookup later hits, on both sides
cells = {}
next_id = 101
for name, ox, oy in tile_specs:
    for j in range(ny):
        for i in range(nx):
            px = ox + (i + 0.5) * res
            py = oy - (j + 0.5) * res
            col, row = ~transform * (px, py)
            if 0 <= col < ncol and 0 <= row < nrow:
                cell = (int(np.floor(row)), int(np.floor(col)))
                if cell not in cells:
                    cells[cell] = next_id
                    next_id += 1

# corner points first (ids 1 and 2, they only exist to pin the extent), then
# one point per touched cell. east_adj / north_adj / gridref_adj are junk
# columns that 002 drops - after the drop the first three columns have to be
# x, y, grid id, which is what the positional indexing relies on
rows = [(minx, miny, 1), (maxx, maxy, 2)]
for (r, c), gid in sorted(cells.items()):
    gx, gy = transform * (c + 0.5, r + 0.5)
    rows.append((gx, gy, gid))
grid = pd.DataFrame(rows, columns = ["x", "y", "grid_ID"])
grid["east_adj"] = 0
grid["north_adj"] = 0
grid["gridref_adj"] = "AA000000"
grid.to_csv(base + "LargeScaleCropData_grid_10km_merge.csv", index = False)

############################
# Tile geotiffs
############################

for name, ox, oy in tile_specs:
    # odd / 128 so no band value is ever a whole number - a whole-number
    # double prints differently across the two runs
    vals = (rng.integers(0, 200, size = (3, ny, nx)) * 2 + 1) / 128.0

    tile_transform = from_origin(ox, oy, res, res)
    with rasterio.open(tiles + name, "w", driver = "GTiff", width = nx, height = ny,
                       count = 3, dtype = "float64", crs = "EPSG:4326", transform = tile_transform) as dst:
        dst.write(vals)
        # date-stamped band descriptions - these become the X2015.04.01...
        # column names
        dst.descriptions = band_dates

print("dummy inputs written")
print(str(len(grid)) + " grid points in " + base)
print("2 tiles in " + tiles + " - tile 2 has pixels past the east edge that should get dropped")
