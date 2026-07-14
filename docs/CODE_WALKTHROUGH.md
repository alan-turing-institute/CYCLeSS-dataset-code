# Code Walkthrough

Covers the three Python translations in this repo. All three expect a
`code/` and `data/` folder pair as siblings under one project root. Each
script derives `project_root` as one level up from its own location and
reads/writes everything under `project_root/data/`, following the R scripts'
`file.path(getwd(), "..")` convention. Drop each `.py` file in `code/`
alongside its `.R` counterpart.

# Turing Sentinel Yield Data Matching

## Setup

```python
base = str(
    Path(__file__).resolve().parents[2]
    / "CYCLESS_anonymisation"
    / "CYCLESS_anonymisation"
) + "/"

if os.path.exists(base + "Intermediate"):
    shutil.rmtree(base + "Intermediate")
if os.path.exists(base + "Output"):
    shutil.rmtree(base + "Output")
os.makedirs(base + "Intermediate")
os.makedirs(base + "Output")
```

`base` is the single root folder everything else hangs off. Before anything
runs, `Intermediate` and `Output` are deleted (if present) and recreated
empty. This matters because of how the script builds up intermediate files
as it goes (see the stacking passes below): if these folders weren't cleared
first, a second run would find `Stacked_*.csv` files left over from a
previous run sitting in `Intermediate` and merge them back in as if they
were new data, silently corrupting the output. Wiping both folders at the
start of every run makes that impossible, since there's nothing left over to
pick up.

## Loading and aggregating the yield data

```python
yield_dat = pd.read_csv(base + "precision_yield_data_example.csv")
yield_dat = yield_dat[yield_dat["sample_year"].isin([2015, 2016, 2017])]
```

Reads the raw per-sample yield readings, then throws away any years with no
satellite coverage.

```python
yield_agg = yield_dat.groupby(["field_id", "sample_year", "type_of_crop"], as_index = False)["yield_t_ha"].mean()
yield_agg.columns = ["ID", "Year", "Crop", "Yield"]
```

Collapses all the individual samples down to one average yield per field,
per year, per crop type, and renames the columns to the short labels used
for the rest of the script.

## Loading field boundaries

```python
fields = gpd.read_file(base + "Example_field.shp")
fields_ll = fields.to_crs("epsg:4326")
```

Reads the shapefile defining each field's boundary polygon, then reprojects
it to lat/long (EPSG:4326) so it lines up with the satellite point data,
which is already in lat/long.

## Matching satellite points to fields

```python
tlist = glob.glob(base + "Satellite data/**/*.csv", recursive = True)
for tfile in tlist:
    tdat = pd.read_csv(tfile)
    tpnts = gpd.GeoDataFrame(tdat, geometry = gpd.points_from_xy(tdat["x"], tdat["y"]), crs = "epsg:4326")
    tisect = gpd.sjoin(tpnts, fields_ll, predicate = "intersects")
```

For every satellite CSV file (searched recursively through subfolders), it
turns the raw `x`/`y` columns into point geometries, then spatially joins
them against the field polygons. `sjoin(..., predicate="intersects")` keeps
only the points that fall inside a field, and tags each one with that
field's attributes (including its ID).

```python
    if len(tisect) > 0:
        tisect = tisect.drop(columns = ["geometry", "index_right"])
        tisect.to_csv(base + "Intermediate/" + os.path.basename(tfile).replace(".csv", "") + "_FieldID.csv", index = False)
```

If any points landed inside a field, it drops the now-unneeded geometry
columns and writes the result out as `<original filename>_FieldID.csv` in
`Intermediate`. Files with no matches are skipped, which is why not every
satellite file produces an output.

## First stacking pass, combining tiles for the same sensor/date-range

```python
inter_files = [x for x in os.listdir(base + "Intermediate") if x.endswith(".csv") and not x.startswith(".")]
uqs = list(set(["_".join(x.split("_")[0:4]) for x in inter_files]))
```

Each satellite file's name follows a `sensor_year_startMonth_endMonth_...`
pattern (e.g. `Ratio_2017_Apr_Jun_tile3_FieldID.csv`). Taking the first 4
underscore-separated tokens gives a group key like `Ratio_2017_Apr_Jun`,
representing all the tiles for this sensor, in this date range, in this
year. `uqs` is the unique set of these keys. The only filter applied to
`inter_files` is skipping hidden files (`.DS_Store` and similar). Since
`Intermediate` is guaranteed empty at the start of the run, there's never
any old `Stacked_*.csv` file around to worry about excluding here.

```python
for u in uqs:
    tstack = pd.concat([pd.read_csv(base + "Intermediate/" + x) for x in inter_files if x.startswith(u)])
    tstack.to_csv(base + "Intermediate/Stacked_" + u + ".csv", index = False)
```

For each group key, it grabs every file whose name starts with that key
(all the geographic tiles covering that sensor/date-range/year), stacks them
into one dataframe, and writes it out as `Stacked_<key>.csv`.

## Second stacking pass, joining the four seasons together

```python
stacked_files = [x for x in os.listdir(base + "Intermediate") if x.startswith("Stacked") and x.endswith(".csv")]
uqs2 = list(set(["_".join(x.split("_")[1:3]) for x in stacked_files]))
```

Now it looks at the `Stacked_*` files just created and pulls out just the
`sensor_year` part (dropping the date range), e.g. `Ratio_2017`. `uqs2` is
the unique set of sensor/year combos. Each one has up to four seasonal files
(Jan-Mar, Apr-Jun, Jul-Sep, Oct-Dec) to bring together.

```python
for u2 in uqs2:
    satdat_1 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Jan_Mar.csv")
    satdat_2 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Apr_Jun.csv")
    satdat_3 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Jul_Sep.csv")
    satdat_4 = pd.read_csv(base + "Intermediate/Stacked_" + u2 + "_Oct_Dec.csv")
```

Reads in the four seasonal files for that sensor/year, by name. This is why
the naming convention has to be exact, or you get a `FileNotFoundError`.

```python
    for satdat in [satdat_1, satdat_2, satdat_3, satdat_4]:
        satdat["xy"] = satdat["x"].round(5).astype(str) + " " + satdat["y"].round(5).astype(str)
```

Builds a text key from the rounded `x`/`y` coordinates in each seasonal
dataframe. Rounding to 5 decimal places avoids two dataframes failing to
match on the same point purely because of tiny floating-point differences.

```python
    keep_cols = ["x", "y", "grid_ID", "id"]
    satdat_all = satdat_1
    for i, satdat in enumerate([satdat_2, satdat_3, satdat_4]):
        satdat = satdat[[c for c in satdat.columns if c not in keep_cols]]
        satdat_all = satdat_all.merge(satdat, on = "xy", how = "left", suffixes = ("", "_" + str(i + 2)))
    satdat_all = satdat_all.drop(columns = "xy").copy()
```

Starts from the Jan-Mar data and left-joins in the other three seasons on
that `xy` key, one at a time, dropping the duplicate `x`/`y`/`grid_ID`/`id`
columns from each new season before merging (since they're already present
from `satdat_1`), and adding a numeric suffix (`_2`, `_3`, `_4`) to any
clashing column names so each season's readings stay distinguishable. The
`xy` helper column is dropped once all four are merged, and the `.copy()` at
the end keeps the dataframe defragmented after several rounds of merging.

## Aggregating and joining yield

```python
metcols = [c for c in satdat_all.columns if c.startswith("X2")]
satdat_agg = satdat_all.groupby("id", as_index = False)[metcols].mean()
```

Picks out all the satellite metric columns (anything starting with `X2`,
date-stamped band/index columns) and averages them per field ID, collapsing
individual points down to one row per field.

```python
yield_agg_year = yield_agg[yield_agg["Year"] == int(u2.split("_")[1])]
all_dat_agg = satdat_agg.merge(yield_agg_year, left_on = "id", right_on = "ID", how = "left")
all_dat_agg = all_dat_agg[all_dat_agg["ID"].notna()]
```

Pulls the year (e.g. `2017`) out of `u2` (e.g. `"Ratio_2017"`), filters the
yield table down to that year, and joins it onto the satellite data by field
ID. Any satellite field with no matching yield record (`ID` is `NaN` after
the left join) gets dropped.

## Anonymising and writing output

```python
all_dat_agg_anonymised = pd.concat([all_dat_agg[["Year", "Crop", "Yield"]], all_dat_agg[metcols].round(0)], axis = 1)
```

Builds the final output by keeping only `Year`, `Crop`, `Yield`, and the
satellite metric columns rounded to whole numbers, deliberately dropping
field IDs and coordinates so the output can't be traced back to a specific
location.

```python
assert not any(c in all_dat_agg_anonymised.columns for c in ["x", "y", "grid_ID", "id", "ID"])
```

A sanity check before writing out. Since the entire purpose of this final
step is to strip out anything that could identify a field's location, this
asserts none of the spatial/ID columns (`x`, `y`, `grid_ID`, `id`, `ID`)
made it into the output dataframe. The `pd.concat` above should already
guarantee this, but if a future edit to this script accidentally left one of
those columns in, this makes the script fail loudly instead of quietly
writing out a de-anonymisable file.

```python
all_dat_agg_anonymised.to_csv(base + "Output/Anonymised_" + u2 + "_MeanYieldperField.csv", index = False)
```

Writes one CSV per sensor/year combo to `Output`.

# 001: Climate and Soil Data Alignment

Status: logic verified against the R original on dummy data; the coordinate
transform step specifically is not. See the equivalence notes for details
before relying on this script's output.

## Setup

```python
code_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(code_dir)
data_dir = project_root + "/data/"
met = data_dir + "met/2017/peti/"
```

Derives `project_root` from the script's own location rather than the
current working directory, since Python doesn't inherit R's launch-directory
convention the same way. `data_dir` and `met` follow the R's
`file.path(getwd(), "..")` to `data_dir` to `met_dir` chain.

```python
def signif(x, digits):
    x = np.asarray(x, dtype = float)
    out = np.zeros_like(x)
    nz = x != 0
    mags = np.floor(np.log10(np.abs(x[nz])))
    factor = 10 ** (digits - 1 - mags)
    out[nz] = np.round(x[nz] * factor) / factor
    return out
```

R's `signif()` rounds to N significant figures, not decimal places, and
there's no direct numpy/pandas equivalent, so this reimplements it: find
each value's order of magnitude, then round at the position that gives the
requested number of significant digits.

## Reading and merging the climate data

```python
grid = pd.read_csv(data_dir + "LargeScaleCropData_grid_points.csv")
```

Reads the master list of grid points to match climate data against. This
same file gets overwritten later with a filtered-down version.

```python
dfs = []
for f in file_names:
    ds = xr.open_dataset(met + f)
    tdf = ds["peti"].to_dataframe().reset_index()
    wide = tdf.pivot(index = ["x", "y"], columns = "time", values = "peti")
    wide.columns = ["X" + pd.Timestamp(c).strftime("%Y.%m.%d") for c in wide.columns]
    dfs.append(wide.reset_index())
    ds.close()
```

For each of the twelve monthly NetCDFs, reshapes it to one row per (x, y)
grid cell with one column per day, the same shape
`as.data.frame(stack(...), xy = TRUE)` produces in R. Column names are built
to match `raster::stack`'s own naming convention (`X2017.01.01` style) since
the anonymisation script downstream matches on that `X` prefix. `pivot` (not
`pivot_table`) is used deliberately: it raises on any duplicate (x, y, time)
triple instead of silently averaging one away.

```python
merge_df = dfs[0]
for tdf in dfs[1:]:
    merge_df = merge_df.merge(tdf, on = ["x", "y"])
```

Joins all twelve months together on (x, y), giving one row per grid cell
with 365 daily columns.

## Coordinate transform

```python
transformer = Transformer.from_crs("epsg:27700", "epsg:4326", always_xy = True)
lon, lat = transformer.transform(merge_df["x"].to_numpy(), merge_df["y"].to_numpy())
```

Converts from British National Grid (BNG, EPSG:27700) to WGS84 (EPSG:4326)
lat/long, matching the R's `spTransform`. This is the step with unresolved
R/Python numerical disagreement. See the equivalence notes.

```python
merge_wgs84["x"] = signif(merge_wgs84["x"], digits = 7)
merge_wgs84["y"] = signif(merge_wgs84["y"], digits = 7)
grid["x"] = signif(grid["x"], digits = 7)
grid["y"] = signif(grid["y"], digits = 7)
```

Rounds both the transformed climate coordinates and the grid points to 7
significant figures, so tiny floating-point differences don't stop
otherwise-matching points from joining.

## Joining to the grid and writing output

```python
merge_grid = merge_wgs84.merge(grid, on = ["x", "y"])
merge_grid = merge_grid.sort_values(["x", "y"])
```

Keeps only climate data that lands on a known grid point. The explicit sort
matches R's `merge()`, which sorts its result by the join columns by
default. pandas doesn't, so this is needed for the outputs to line up
row-for-row.

```python
merge_grid = merge_grid.dropna()

merge_grid.to_csv(data_dir + "LargeScaleCropData_met_peti_2017.csv", index = False)

grids = merge_grid[["x", "y"]].copy()
grids.to_csv(data_dir + "LargeScaleCropData_grid_points.csv", index = False)
```

Drops any row with missing data, writes the merged climate/grid data out,
then overwrites the grid points file with just the (x, y) pairs that
actually had matching climate data, trimming the master list down for
whatever reads it next. Both writes use `index = False` since the R writes
with `row.names = FALSE`.

# 002: Merge Sentinel-1

Status: verified against the R original on dummy data, byte-for-byte
identical output, including the case of a tile that partially falls outside
the grid extent.

## Setup

```python
code_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(code_dir)
data_dir = project_root + "/data/"
merge_dir = data_dir + "par-merge-test/"
tile_dir = data_dir + "Raw Sentinel-1 SAR/2015/VH/VH_2015_Apr_Jun/2/chunk-2015-04-01_2015-06-30/"
```

Same `project_root`-relative pattern as 001. `merge_dir` holds the 10km grid
metadata CSV; `tile_dir` holds the raw Sentinel-1 band tiles for one
sensor/date-range/year. A real run would point this at each date-range
folder in turn.

## Building the grid ID raster

```python
minx, miny = meta_grid_id.iloc[:, 0].min(), meta_grid_id.iloc[:, 1].min()
maxx, maxy = meta_grid_id.iloc[:, 0].max(), meta_grid_id.iloc[:, 1].max()
ncol, nrow = 3069, 18
transform = from_bounds(minx, miny, maxx, maxy, ncol, nrow)
shapes = ((Point(xy), value) for xy, value in zip(meta_grid_id.iloc[:, 0:2].values, meta_grid_id.iloc[:, 2]))
grid_id_raster = rasterize(shapes = shapes, out_shape = (nrow, ncol), transform = transform, fill = np.nan, dtype = "float64")
```

Builds an empty raster spanning the grid metadata's extent, then burns each
grid point's ID into whichever raster cell it falls in, equivalent to R's
`raster(extent(...))` plus `rasterize()`. This raster becomes a lookup
table: given a raster cell, you get back the 1km grid ID for that location.

## Per-tile processing

```python
with rasterio.open(tile_dir + input_file) as src:
    tile = src.read()
    tile_transform = src.transform
    width = src.width
    height = src.height
    descs = src.descriptions
```

Opens one raw satellite band tile and reads its pixel data plus
georeferencing info.

```python
cols, rows = np.meshgrid(np.arange(width), np.arange(height))
xs, ys = rasterio.transform.xy(tile_transform, rows.flatten(), cols.flatten())
tile_df = pd.DataFrame({"x": np.asarray(xs), "y": np.asarray(ys)})
```

Converts the raster to a dataframe with one row per pixel and its (x, y)
centre coordinate, the same layout as
`as.data.frame(stack(...), xy = TRUE)` in R.

```python
for i in range(tile.shape[0]):
    name = descs[i] if descs[i] else "band_" + str(i + 1)
    name = "".join(c if c.isalnum() or c == "_" else "." for c in name)
    if name[0].isdigit():
        name = "X" + name
    tile_df[name] = tile[i].flatten()
```

Names each band column from the tile's own band descriptions (SEPAL exports
carry date-stamped descriptions), cleaned the way R's `make.names` cleans
column names: symbols become dots, a leading digit gets an `X` prefixed.
This matters because the anonymisation script downstream matches its metric
columns on an `X2` prefix. `band_N` is only a fallback for tiles with no
descriptions.

```python
col, row = ~transform * (tile_df["x"].to_numpy(), tile_df["y"].to_numpy())
col = np.floor(col).astype(int)
row = np.floor(row).astype(int)
valid = (row >= 0) & (row < nrow) & (col >= 0) & (col < ncol)
grid_ids = np.full(len(tile_df), np.nan)
grid_ids[valid] = grid_id_raster[row[valid], col[valid]]
tile_df["grid_ID"] = np.round(grid_ids, 0)
```

For each pixel, works out which cell of the grid ID raster it falls into and
looks up that cell's ID, equivalent to R's
`extract(x, SpatialPoints(points))`. Pixels that fall outside the grid
raster's extent entirely (`valid` is False) get `NaN` rather than an
out-of-bounds lookup.

```python
tile_df_clean = tile_df[tile_df["grid_ID"].notna()].copy()
tile_df_clean["grid_ID"] = tile_df_clean["grid_ID"].astype(int)
tile_df_clean.to_csv(tile_dir + tile_name + "_with_grid.csv", index = False, quoting = csv.QUOTE_NONNUMERIC)
```

Drops pixels with no grid ID, casts `grid_ID` to a plain integer (R prints
whole-number doubles without a trailing `.0`, pandas doesn't unless cast),
and writes one `_with_grid.csv` per tile. `quoting = csv.QUOTE_NONNUMERIC`
matches `write.csv`'s default of quoting the header row.
