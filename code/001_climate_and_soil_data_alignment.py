#######################################################################
# Evangeline Corcoran
# Version: 21/08/2024
#
# Retrieve climate data matching land use and soil data grid points
# Modernised: July 2026
#######################################################################

# pip install pandas numpy xarray netCDF4 pyproj

import os
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer

############################
# Project paths
############################

# project root is one level up from this script's folder (code/), data
# lives in project_root/data
code_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(code_dir)
data_dir = project_root + "/data/"
met = data_dir + "met/2017/peti/"

############################
# Helpers
############################

# round to n significant figures
def signif(x, digits):
    x = np.asarray(x, dtype = float)
    out = np.zeros_like(x)
    nz = x != 0
    mags = np.floor(np.log10(np.abs(x[nz])))
    factor = 10 ** (digits - 1 - mags)
    out[nz] = np.round(x[nz] * factor) / factor
    return out

############################
# Read grid points
############################

grid = pd.read_csv(data_dir + "LargeScaleCropData_grid_points.csv")

############################
# Read NetCDF files
############################

file_names = [
    "chess-pe_peti_gb_1km_daily_20170101-20170131.nc",
    "chess-pe_peti_gb_1km_daily_20170201-20170228.nc",
    "chess-pe_peti_gb_1km_daily_20170301-20170331.nc",
    "chess-pe_peti_gb_1km_daily_20170401-20170430.nc",
    "chess-pe_peti_gb_1km_daily_20170501-20170531.nc",
    "chess-pe_peti_gb_1km_daily_20170601-20170630.nc",
    "chess-pe_peti_gb_1km_daily_20170701-20170731.nc",
    "chess-pe_peti_gb_1km_daily_20170801-20170831.nc",
    "chess-pe_peti_gb_1km_daily_20170901-20170930.nc",
    "chess-pe_peti_gb_1km_daily_20171001-20171031.nc",
    "chess-pe_peti_gb_1km_daily_20171101-20171130.nc",
    "chess-pe_peti_gb_1km_daily_20171201-20171231.nc",
]

############################
# Convert to data frames
############################

# one row per (x, y) cell, one column per day. day columns named
# X2017.01.01 style so downstream matching on the X-prefix works
dfs = []
for f in file_names:
    ds = xr.open_dataset(met + f)
    tdf = ds["peti"].to_dataframe().reset_index()
    wide = tdf.pivot(index = ["x", "y"], columns = "time", values = "peti")
    wide.columns = ["X" + pd.Timestamp(c).strftime("%Y.%m.%d") for c in wide.columns]
    dfs.append(wide.reset_index())
    ds.close()

############################
# Merge monthly data
############################

merge_df = dfs[0]
for tdf in dfs[1:]:
    merge_df = merge_df.merge(tdf, on = ["x", "y"])

############################
# Convert BNG to WGS84
############################

transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy = True)
lon, lat = transformer.transform(merge_df["x"].to_numpy(), merge_df["y"].to_numpy())
merge_wgs84 = merge_df.copy()
merge_wgs84["x"] = lon
merge_wgs84["y"] = lat

############################
# Round coordinates
############################

merge_wgs84["x"] = signif(merge_wgs84["x"], digits = 7)
merge_wgs84["y"] = signif(merge_wgs84["y"], digits = 7)
grid["x"] = signif(grid["x"], digits = 7)
grid["y"] = signif(grid["y"], digits = 7)

############################
# Merge climate and grid data
############################

merge_grid = merge_wgs84.merge(grid, on = ["x", "y"])

# sort by the join columns so the ordering is deterministic
merge_grid = merge_grid.sort_values(["x", "y"])

# remove missing data
merge_grid = merge_grid.dropna()

############################
# Save outputs
############################

merge_grid.to_csv(data_dir + "LargeScaleCropData_met_peti_2017.csv", index = False)

# overwrites the input grid file with the surviving grid points
grids = merge_grid[["x", "y"]].copy()
grids.to_csv(data_dir + "LargeScaleCropData_grid_points.csv", index = False)
