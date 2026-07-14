# R to Python Equivalence

This repo contains the R scripts (the original) and their Python
translations. This document tracks which translations have been verified to
produce the same output as the R version, and how that was checked, so
nobody has to re-verify from scratch.

## Verified

### `Turing_Sentinel_Yield_Data_Matching_Dummy.R` to `sentinel_yield_data_matching.py`

Verified equivalent. Both were run against the same dummy dataset
(`CYCLESS_anonymisation.zip`, the fake yield/field/satellite data included
in this repo), and the three anonymised output CSVs
(`Anonymised_VV_2017_MeanYieldperField.csv`,
`Anonymised_VH_2017_MeanYieldperField.csv`,
`Anonymised_Ratio_2017_MeanYieldperField.csv`) were byte-for-byte identical
between the two runs (`diff` clean, no changes).

How it was checked:
1. Ran the original R script on the dummy data, kept its `Output/` folder.
2. Ran the Python translation on a fresh copy of the same dummy data.
3. `diff`'d each output CSV between the two runs.

This was re-checked twice: once for the initial translation, and again after
the Python version was restructured (path handling, comments, a fix for a
stale-file bug on reruns). The logic changes didn't change any output,
confirmed by the same diff check.

Known limitation of this check: the dummy dataset only has one field and one
year (2017). It exercises the full code path (matching, stacking, joining
seasons, aggregating, anonymising) but not edge cases like multiple fields
sharing a grid square, or years with missing seasonal data. Treat "verified"
here as "verified on the dummy data provided", not "verified against every
possible input shape".

### `002_merge_sentinel1.R` to `002_merge_sentinel1.py`

Verified equivalent. Built a small dummy input set (a fake 10km merge grid
CSV, two small synthetic Sentinel-1 band tiles, see
`make_dummy_002_inputs.py`) and ran both R and Python end-to-end. The two
`_with_grid.csv` outputs (one per tile) were byte-for-byte identical between
the two runs (`diff` clean, no changes), including the tile deliberately
positioned to poke past the grid's edge, so the no-grid-ID-drop path got
exercised too.

How it was checked:
1. Ran the modernised R script on the dummy tiles, stashed its output.
2. Ran the Python translation on the same tiles (R doesn't overwrite its
   inputs here, so no need to regenerate between runs).
3. `diff`'d each tile's `_with_grid.csv` between the two runs.

Unlike 001, this script never leaves the tiles' native CRS. There's no
coordinate transform step, so the R-vs-pyproj discrepancy documented under
001 doesn't apply here.

Known limitation of this check: only two small (6x5 pixel) synthetic tiles
were tested, both from the same band/date-range. Real Sentinel-1 tiles will
be much larger, and this hasn't been checked against tiles with missing/NaN
pixel data within the grid extent (as opposed to outside it).

## Not yet verified

*(nothing outstanding right now)*

## Partially verified

### `001_climate_and_soil_data_alignment.R` to `001_climate_and_soil_data_alignment.py`

Logic verified, coordinate transform step not verified. Built a small dummy
input set (12 fake CHESS `peti` NetCDFs, a fake grid points CSV, see
`make_dummy_001_inputs.py`) and ran both R and Python end-to-end.

What's confirmed working and matching between R and Python: reading and
merging the twelve monthly NetCDFs on (x, y), the `signif(7)` rounding
logic, the grid merge, `na.omit`, and the output CSV format/columns. This
was confirmed by capturing R's own transformed coordinates and feeding them
back in as the grid points CSV (sidestepping the issue below). R's own run
produced the expected 28 output rows (30 dummy cells minus 2 all-NaN ones),
matching row-for-row what the merge logic should produce.

What's not confirmed: the BNG (EPSG:27700) to WGS84 (EPSG:4326) coordinate
transform itself. On this dev machine, R (via `sp`/`sf`, using GDAL 3.13.1 /
PROJ 9.8.1) and Python (via `pyproj`) produce different results for the same
input coordinate, about a 1.5m real-world offset, e.g. one point transformed
to `x = -1.263331` in R vs `x = -1.263346` in Python. That's far outside the
`signif(7)` rounding tolerance (sub-millimetre), so at full scale this could
cause systematic mismatches between which grid cells the Python version
matches against vs. the R version.

Ruled out as the cause: a missing correction grid file on the Python side
(forcing `pyproj.Transformer.from_crs(..., only_best=True)` neither errored
nor changed the result, which it should have if a grid file were the issue).
Most likely explanation: R's PROJ and Python's PROJ are each picking a
different (but individually valid) named coordinate operation for OSGB36 to
WGS84 by default, since more than one exists in the EPSG registry. Not
pinned down further. Would need inspecting the specific operation each
library selects (`pyproj.transformer.TransformerGroup` /
`projinfo -s EPSG:27700 -t EPSG:4326`) and forcing both to use the same one
explicitly.

Before relying on this script's output for real analysis, either confirm R
and Python agree on the transform in whatever environment will actually run
it, or pin both to an identical named transform operation. This may or may
not reproduce on a different machine, since PROJ's default operation choice
can depend on what's installed/cached locally.

## If you pick 001's transform mismatch up

The fastest path is inspecting what named coordinate operation each side is
actually using. `pyproj.transformer.TransformerGroup('epsg:27700',
'epsg:4326')` on the Python side lists candidates with their names and
accuracies; `projinfo -s EPSG:27700 -t EPSG:4326 -o PROJ` on the command
line shows what GDAL/PROJ considers available. Once you know which operation
each picked by default, force both to use the same one explicitly (rather
than each library's own best guess) and re-run the same dummy-data diff
check used for 001's other logic.
