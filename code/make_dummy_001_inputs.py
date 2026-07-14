#######################################################################
# Make dummy inputs for 001_climate_and_soil_data_alignment
#######################################################################

# builds a small fake version of the raw inputs 001 needs - the grid points
# csv plus the twelve chess-pe peti netcdfs - so runs can be diffed on
# identical inputs. deterministic: rerun to reset the inputs, since 001
# overwrites the grid points csv

# pip install pandas numpy xarray netCDF4 pyproj

import os
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer

############################
# Project paths
############################

# run this from inside code/ so "one level up" lands on the same project
# root 001 uses
code_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(code_dir)
data_dir = project_root + "/data/"
met = data_dir + "met/2017/peti/"
os.makedirs(met, exist_ok = True)

# clear the met output from any previous run so a failed run can't leave a
# stale file behind (the grid points csv gets rewritten below anyway)
if os.path.exists(met + "LargeScaleCropData_met_peti_2017.csv"):
    os.remove(met + "LargeScaleCropData_met_peti_2017.csv")

############################
# Helpers
############################

# round to n significant figures - so the grid csv holds the exact doubles
# both runs produce after their own signif(7)
def signif(x, digits):
    x = np.asarray(x, dtype = float)
    out = np.zeros_like(x)
    nz = x != 0
    mags = np.floor(np.log10(np.abs(x[nz])))
    factor = 10 ** (digits - 1 - mags)
    out[nz] = np.round(x[nz] * factor) / factor
    return out

############################
# Fake 1km BNG grid
############################

# 6 x 5 cells of the 1km BNG grid, cell centres on the chess convention
# (multiples of 1000 + 500), roughly the east midlands
xs = np.arange(450500.0, 456500.0, 1000.0)
ys = np.arange(250500.0, 255500.0, 1000.0)

# two "sea" cells that stay NaN across every day - the one at (row 0, col 0)
# also goes into the grid points csv below so the na drop has something to
# take out
nan_cells = [(0, 0), (4, 3)]

############################
# Twelve monthly netcdfs
############################

rng = np.random.default_rng(42)

for m in range(1, 13):
    mm = str(m).zfill(2)
    ndays = pd.Timestamp("2017-" + mm + "-01").days_in_month
    days = pd.date_range("2017-" + mm + "-01", periods = ndays)

    # odd / 200 so no value is ever a whole number - a whole-number double
    # prints differently across the two runs and would pollute the diff for
    # no real reason
    vals = (rng.integers(0, 600, size = (ndays, len(ys), len(xs))) * 2 + 1) / 200.0
    for (iy, ix) in nan_cells:
        vals[:, iy, ix] = np.nan

    ds = xr.Dataset({"peti": (("time", "y", "x"), vals)}, coords = {"time": days, "y": ys, "x": xs})
    ds["peti"].attrs = {"units": "mm", "long_name": "potential evapotranspiration with interception correction"}
    ds["x"].attrs = {"units": "m", "standard_name": "projection_x_coordinate"}
    ds["y"].attrs = {"units": "m", "standard_name": "projection_y_coordinate"}

    fname = "chess-pe_peti_gb_1km_daily_2017" + mm + "01-2017" + mm + str(ndays) + ".nc"
    ds.to_netcdf(met + fname, encoding = {"time": {"units": "days since 1961-01-01", "calendar": "standard"}, "peti": {"_FillValue": -99999.0}})

############################
# Grid points csv
############################

# a subset of the netcdf cells in lat/long with the same signif(7) rounding
# 001 applies, plus one point matching nothing (the merge should silently
# drop it). both runs do the BNG -> WGS84 transform themselves, so if the
# two transform libraries disagree at the 7th significant figure some cells
# will fail to match in one run but not the other - that shows up in the
# diff as missing rows and is a real finding, not a bug in this script
transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy = True)
cell_x, cell_y = np.meshgrid(xs, ys)
lon, lat = transformer.transform(cell_x.flatten(), cell_y.flatten())

# 11 of the 30 cells - flat index 0 is the (450500, 250500) all-NaN sea cell
keep = [0, 2, 5, 7, 11, 14, 16, 19, 22, 25, 28]
grid = pd.DataFrame({"x": signif(lon[keep], 7), "y": signif(lat[keep], 7)})
grid = pd.concat([grid, pd.DataFrame({"x": [-0.5], "y": [53.5]})], ignore_index = True)
grid.to_csv(data_dir + "LargeScaleCropData_grid_points.csv", index = False)

print("dummy inputs written to " + data_dir)
print("12 netcdfs in " + met + " and " + str(len(grid)) + " grid points - 11 should match, 10 should survive the na drop")
