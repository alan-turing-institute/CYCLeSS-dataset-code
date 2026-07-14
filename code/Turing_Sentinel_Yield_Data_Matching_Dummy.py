import os
import glob
import shutil
import pandas as pd
import geopandas as gpd
from pathlib import Path

############################
# Load and pre-process required precision yield datasets
############################

# base folder - change this if the project folder moves
base = str(
    Path(__file__).resolve().parents[2]
    / "CYCLESS_anonymisation"
    / "CYCLESS_anonymisation"
) + "/"

# clear out Intermediate/Output from any previous run - if these aren't
# cleared, old Stacked_ files get picked back up below and mixed into the
# next run's data
if os.path.exists(base + "Intermediate"):
    shutil.rmtree(base + "Intermediate")
if os.path.exists(base + "Output"):
    shutil.rmtree(base + "Output")
os.makedirs(base + "Intermediate")
os.makedirs(base + "Output")

# read csv file of all cleaned yield data
yield_dat = pd.read_csv(base + "precision_yield_data_example.csv")

# drop data from years outside of range of satellite data
yield_dat = yield_dat[yield_dat["sample_year"].isin([2015, 2016, 2017])]

# get average yield and crop type per field ID per year
yield_agg = yield_dat.groupby(["field_id", "sample_year", "type_of_crop"], as_index = False)["yield_t_ha"].mean()
yield_agg = yield_agg.sort_values(["field_id", "sample_year"])
yield_agg.columns = ["ID", "Year", "Crop", "Yield"]

# read field boundaries for yield data
fields = gpd.read_file(base + "Example_field.shp")

# project to lat/long coordinate system
fields_ll = fields.to_crs("epsg:4326")

############################
# Identify satellite data intersecting yield data
############################

# iterate through all satellite files
tlist = glob.glob(base + "Satellite data/**/*.csv", recursive = True)
for tfile in tlist:
    # read as spatial points
    tdat = pd.read_csv(tfile)
    tpnts = gpd.GeoDataFrame(tdat, geometry = gpd.points_from_xy(tdat["x"], tdat["y"]), crs = "epsg:4326")

    # check for intersection with fields
    tisect = gpd.sjoin(tpnts, fields_ll, predicate = "intersects")

    # if any fields intersect, write intersecting points to new csv file
    if len(tisect) > 0:
        tisect = tisect.drop(columns = ["geometry", "index_right"])
        tisect.to_csv(base + "Intermediate/" + os.path.basename(tfile).replace(".csv", "") + "_FieldID.csv", index = False)

############################
# Stack files referring to same sensor/year combination
############################

# read back new files, concat for same sensor in same date range in year.
# only take real csv files - ignore .DS_Store and other hidden files
inter_files = [x for x in os.listdir(base + "Intermediate") if x.endswith(".csv") and not x.startswith(".")]

# list unique sensor, year, date range combinations. filenames are
# sensor_year_startMonth_endMonth_... so first 4 tokens = the group key
uqs = list(set(["_".join(x.split("_")[0:4]) for x in inter_files]))

for u in uqs:
    # stack all files
    tstack = pd.concat([pd.read_csv(base + "Intermediate/" + x) for x in inter_files if x.startswith(u)])

    # rewrite stacked output
    tstack.to_csv(base + "Intermediate/Stacked_" + u + ".csv", index = False)

############################
# Append columns for same sensor, different date ranges within the same year
# Aggregate per field and strip out spatial data
############################

# read back, join new files for different date ranges in same year.
# list unique sensor/year combinations
stacked_files = [x for x in os.listdir(base + "Intermediate") if x.startswith("Stacked") and x.endswith(".csv")]
uqs2 = list(set(["_".join(x.split("_")[1:3]) for x in stacked_files]))

for u2 in uqs2:
    # read in for four seasonal date ranges
    satdat_1 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Jan_Mar.csv")
    satdat_2 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Apr_Jun.csv")
    satdat_3 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Jul_Sep.csv")
    satdat_4 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Oct_Dec.csv")

    # match and join by spatial location (x,y), rounded to 5dp to avoid float mismatches
    for satdat in [satdat_1, satdat_2, satdat_3, satdat_4]:
        satdat["xy"] = satdat["x"].round(5).astype(str) + " " + satdat["y"].round(5).astype(str)

    # left-join the other 3 seasons onto Jan-Mar on xy - drop x/y/grid_ID/id
    # from each before merging since satdat_1 already has them, suffix
    # clashing cols with _2/_3/_4 so each season stays distinguishable
    keep_cols = ["x", "y", "grid_ID", "id"]
    satdat_all = satdat_1
    for i, satdat in enumerate([satdat_2, satdat_3, satdat_4]):
        satdat = satdat[[c for c in satdat.columns if c not in keep_cols]]
        satdat_all = satdat_all.merge(satdat, on = "xy", how = "left", suffixes = ("", "_" + str(i + 2)))
    satdat_all = satdat_all.drop(columns = "xy").copy()  # copy to defrag after all the merges

    # aggregate satellite data per field - metcols = the date-stamped band columns (X2...)
    metcols = [c for c in satdat_all.columns if c.startswith("X2")]
    satdat_agg = satdat_all.groupby("id", as_index = False)[metcols].mean()

    # join summary yield data by field ID
    yield_agg_year = yield_agg[yield_agg["Year"] == int(u2.split("_")[1])]
    all_dat_agg = satdat_agg.merge(yield_agg_year, left_on = "id", right_on = "ID", how = "left")

    # strip out ids that do not match yield data
    all_dat_agg = all_dat_agg[all_dat_agg["ID"].notna()]

    # strip out spatial data and IDs, round satellite metrics to prevent reverse engineering of location
    all_dat_agg_anonymised = pd.concat([all_dat_agg[["Year", "Crop", "Yield"]], all_dat_agg[metcols].round(0)], axis = 1)

    # sanity check - none of the spatial/ID columns should have made it into
    # the anonymised output, want a loud failure instead of a silent leak if
    # that ever changes
    assert not any(c in all_dat_agg_anonymised.columns for c in ["x", "y", "grid_ID", "id", "ID"])

    # write csv
    all_dat_agg_anonymised.to_csv(base + "Output/Anonymised_" + u2 + "_MeanYieldperField.csv", index = False)
