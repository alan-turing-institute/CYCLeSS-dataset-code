# CYCLeSS dataset code

Scripts used to build the CYCLeSS dataset (Crop Yields, Climate, Soils and
Satellites) published on Figshare. This covers what each script does, how
the three data sources get linked together, and a few non-obvious quirks in
the data worth knowing before writing anything new against it.

## Pipeline

| Step | Script | Input | Output |
|---|---|---|---|
| 1 | `001_climate_and_soil_data_alignment` (R / Python) | CHESS climate NetCDF files, soil rasters, 1km grid points | Climate/soil data merged onto a shared 1km grid |
| 2 | `002_merge_sentinel1` (R / Python) | Sentinel-1 raster tiles (VV/VH/Ratio), 1km grid reference | Per-pixel satellite readings tagged with a `grid_ID` (`*_with_grid.csv`) |
| 3 | `Turing_Sentinel_Yield_Data_Matching_Dummy.R` / `sentinel_yield_data_matching.py` | `*_with_grid.csv` files, field boundary shapefile, precision yield data | Anonymised satellite + yield summary per field, per year |

Step 3 is the anonymisation handoff step. It is what lets satellite data
(known to one team) get matched to yield data tied to real field locations
(known to a different team) without either side seeing both at once. The
published dataset only contains the output of step 3, aggregated per field
per year, spatial columns stripped.

Steps 1 and 2 (R and Python, both) expect a `code/` and `data/` folder pair
as siblings under one project root. Each script derives its own paths as
one level up from wherever it lives, then down into `data/`. Step 3 works
differently: it uses a `base` variable set at the top of the script instead,
pointing at wherever the unzipped dummy folder ended up. Don't mix the two
conventions up when moving files around.

See `R_Translated_To_Python_Equivalence.md` for which Python translations
have been confirmed to match their R originals, and how.

## Running the anonymisation step on dummy data

`CYCLESS_anonymisation.zip` in this repo is a self-contained dummy version
of step 3, with fake yield data and a single fake field, but the same file
structure and matching logic as the real run. To try it:

1. Unzip it. It should already contain `precision_yield_data_example.csv`,
   `Example_field.shp` (plus sidecar files), a `Satellite data/` folder, and
   empty `Intermediate/` and `Output/` folders.
2. Point `base` (top of the script) at that folder.
3. Run it. Anonymised output lands in `Output/`, one CSV per sensor/year
   (`Anonymised_VV_2017_MeanYieldperField.csv` and so on).

Re-running it is safe, as the script clears `Intermediate/` and `Output/` at
the start of each run. (Earlier versions didn't do this, which meant a
second run would pick up `Stacked_*.csv` files left over from the first run
and silently merge them into the new output. Worth knowing if you're working
from an older copy of the script.)

## Running steps 1 and 2 on dummy data

Steps 1 and 2 need real CHESS climate NetCDFs and raw Sentinel-1 raster
tiles respectively, large files not included in this repo.
`make_dummy_001_inputs.py` and `make_dummy_002_inputs.py` build small fake
versions of each instead (a handful of grid cells, a couple of
NetCDFs/tiles), so both the R and Python versions can be run and their
outputs `diff`'d without needing the real data on hand. Drop each generator
in `code/` alongside the script it feeds and run it before running the R or
Python version. Both are deterministic, so re-running a generator resets its
script's inputs back to a known state (needed since both 001 scripts
overwrite their own grid points file on each run).

## How the three published data folders link together

The Figshare dataset has three subfolders, joined by two different keys
depending on which pair you're joining:

| Folder | Key | Notes |
|---|---|---|
| `crop_yield_type_and_satellite_data` | `ID` (field-level) | One file per band/year, e.g. `VV_2015_MeanYieldperField.csv` |
| `soil_data` | `ID` (field-level) | `LandUseandSoil_2015_2016.csv`, `LandUseandSoil_2017.csv`, static per field |
| `climate_data` | `grid_ID` (1km grid square, coarser than field) | One CSV per variable per year, e.g. `precip_2016.csv`, daily columns |

`ID` joins yield/satellite data straight to soil data. `climate_data` only
has `grid_ID`, and the yield/satellite files also carry a `grid_ID` column,
so that's what you join climate data on, not `ID`.

Coverage: 201 grid squares in 2015, 292 in 2016, 443 in 2017. Mostly winter
wheat, then oilseed rape and spring barley, with smaller numbers of winter
barley and beans.

## Quirks to know about before using this data

Climate CSVs have duplicate rows per `grid_ID`. There's no `ID` column in
`climate_data` files, so every field sharing a grid square gets an identical
row. If you join straight onto yield data without deduplicating first, you'll
get a many-to-many join and inflated/wrong numbers. Deduplicate on `grid_ID`
(plus year) before merging.

Climate CSVs are wide, not long. Each day is its own column (`X2015.01.01`,
`X2015.01.02`, and so on), not a single value column, so reduce to a summary
stat (mean, sum, etc.) per grid square before using it in anything like a
correlation matrix.

The soil `text` column isn't what it looks like. It reads like it should be
a USDA soil texture class, but in the actual data it's a continuous numeric
value (mostly non-repeating, weak correlation with `clay`/`sand`/`silt`),
which looks like an averaged code rather than a category. If you need an
actual soil texture class, derive it yourself from the `clay`/`sand`/`silt`
percentage columns using the standard USDA texture triangle rules rather
than using `text` directly.

Satellite filenames encode their own metadata. The format is
`<sensor>_<year>_<seasonStart>_<seasonEnd>_...`, e.g. `VV_2017_Jan_Mar_...`.
The matching/stacking scripts parse this by position (first four
underscore-separated tokens), so keep this naming convention if you add new
satellite files, or the join step will silently group things wrong.
