############################################################
# Add 1km grid IDs to extracted Satellite band time series #
# Version: 21/08/24 Author: Evangeline Corcoran            #
# Modernised: July 2026                                    #
############################################################

# pip install pandas numpy rasterio shapely

import csv
import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_bounds
from shapely.geometry import Point

############################
# Project paths
############################

# project root is one level up from this script's folder (code/), data
# lives in project_root/data
code_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(code_dir)
data_dir = project_root + "/data/"
merge_dir = data_dir + "par-merge-test/"
tile_dir = data_dir + "Raw Sentinel-1 SAR/2015/VH/VH_2015_Apr_Jun/2/chunk-2015-04-01_2015-06-30/"

############################
# Global variables
############################

# import 1km grid for metadata
meta_grid = pd.read_csv(merge_dir + "LargeScaleCropData_grid_10km_merge.csv")
drop = ["east_adj", "north_adj", "gridref_adj"]
meta_grid_id = meta_grid.drop(columns = drop)

# create empty raster and burn the grid id (3rd column) into whichever cell
# each point falls in
minx, miny = meta_grid_id.iloc[:, 0].min(), meta_grid_id.iloc[:, 1].min()
maxx, maxy = meta_grid_id.iloc[:, 0].max(), meta_grid_id.iloc[:, 1].max()
ncol, nrow = 3069, 18
transform = from_bounds(minx, miny, maxx, maxy, ncol, nrow)
shapes = ((Point(xy), value) for xy, value in zip(meta_grid_id.iloc[:, 0:2].values, meta_grid_id.iloc[:, 2]))
grid_id_raster = rasterize(shapes = shapes, out_shape = (nrow, ncol), transform = transform, fill = np.nan, dtype = "float64")

############################
# Load data
############################

files = [f for f in os.listdir(tile_dir) if f.endswith(".tif")]

# merge satellite band data with grid I.D. for 1km metadata
def add_grid_id(input_file):
    # import raw satellite band raster tile
    with rasterio.open(tile_dir + input_file) as src:
        tile = src.read()
        tile_transform = src.transform
        width = src.width
        height = src.height
        descs = src.descriptions

    # convert to dataframe - x, y first then one column per band. coords are
    # pixel centres
    cols, rows = np.meshgrid(np.arange(width), np.arange(height))
    xs, ys = rasterio.transform.xy(tile_transform, rows.flatten(), cols.flatten())
    tile_df = pd.DataFrame({"x": np.asarray(xs), "y": np.asarray(ys)})

    # band columns take their names from the tif band descriptions, tidied so
    # symbols become dots and a leading digit gets an X in front, giving
    # date-stamped bands like X2015.04.01. the anonymisation script downstream
    # matches on that X2 prefix. band_N is only a fallback for tifs with no
    # descriptions
    for i in range(tile.shape[0]):
        name = descs[i] if descs[i] else "band_" + str(i + 1)
        name = "".join(c if c.isalnum() or c == "_" else "." for c in name)
        if name[0].isdigit():
            name = "X" + name
        tile_df[name] = tile[i].flatten()

    # retrieve tile name
    tile_name = os.path.splitext(input_file)[0]

    # add 1 km grid ID to satellite band data - find which grid raster cell
    # each pixel centre falls in
    col, row = ~transform * (tile_df["x"].to_numpy(), tile_df["y"].to_numpy())
    col = np.floor(col).astype(int)
    row = np.floor(row).astype(int)
    valid = (row >= 0) & (row < nrow) & (col >= 0) & (col < ncol)
    grid_ids = np.full(len(tile_df), np.nan)
    grid_ids[valid] = grid_id_raster[row[valid], col[valid]]
    tile_df["grid_ID"] = np.round(grid_ids, 0)

    # remove any satellite band data without a grid ID
    tile_df_clean = tile_df[tile_df["grid_ID"].notna()].copy()

    # cast so whole-number grid IDs print without a trailing .0
    tile_df_clean["grid_ID"] = tile_df_clean["grid_ID"].astype(int)

    # output csv with cleaned band data and 1km grid ID
    tile_df_clean.to_csv(tile_dir + tile_name + "_with_grid.csv", index = False, quoting = csv.QUOTE_NONNUMERIC)

for file in files:
    add_grid_id(file)
