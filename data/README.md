# data/

This folder holds the CYCLeSS dataset the scripts read from. The dataset
itself is not included in this repository, it is published separately on
Figshare as the canonical CYCLeSS dataset record. Download it from there and
place the three subfolders here so the layout is:

    data/
    ├── data.yml
    ├── crop_yield_type_and_satellite_data/   *_MeanYieldperField.csv
    ├── soil_data/                            LandUseandSoil_*.csv
    └── climate_data/                         one subfolder per year, one CSV per variable

`data.yml` is the intake catalog config. Its `{{ CATALOG_DIR }}` paths resolve
relative to this folder, so keep it here alongside the three data subfolders.
The scripts in `code/` expect this `data/` folder to sit as a sibling of
`code/` under one project root.

The `.gitkeep` files exist only so the empty subfolders are tracked by git;
they can be removed once the real data is in place.
