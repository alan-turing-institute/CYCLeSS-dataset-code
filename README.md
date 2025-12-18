# CYCLeSS-dataset-code
R code used to merge and align available UK climate, soil and Sentinel-1 synthetic aperture radard (SAR) data to the 1 kilometre square grid used in the creation of the Crop Yields, Climate, Soils, and Satellites (CYCleSS) dataset, a large-scale crop yield dataset derived from precision yield data for 2,000 fields across England on which a variety of crops are grown.  This dataset and potential use cases are described in full in the following paper:

>Corcoran et al. (2024). CYCleSS: A dataset for developing coarse-grained UK-wide crop yield models with machine learning. Nature Scientific Data, *under review*.

Alignment of the gathered climate and soil metadata to the same spatial scale of 1 km2  grids was performed using R, and can be replicated using the file **‘001_climate_and_soil_data_alignment.R’**.

Sentinel-1 SAR radar band time-series data was extracted via the SEPAL platform in three month chunks, which were then converted to yearly dataframes using the ‘merge’ function of the ‘dplyr’ package in R. Code for performing merging of 3-monthly chunked Sentinel-1 SAR radar data is provided in the **‘002_merge_sentinel1.R’**.

**Replicating the Anonymisation Process**
All code and dummy data needed to replicate the final data merging and anonymisation process used on the CYCLeSS Dataset are contained in the zipped **'CLYCLESS_anonymisation'** folder.

Once all files and subfolders have been extracted, running the ‘Turing_Sentinel_Yield_Data_Matching_Dummy.R’ file in R will:
1) Pull in the dummy data (‘precision_yield_data_example.csv’) to calculate average yields per field and use the field boundaries contained in the ‘example_field.shp’ file to identify intersecting intersecting satellite data
2) Draw in satellite data from the ‘Satellite Data’ folder and filters by fields with yield data. This output combines yield and satellite data for 3-month periods to the ‘Intermediate’ folder
3) Combine all the satellite from 3-month chunks for the same location into a single file per year
4) Remove data related to Field IDs with no matching field data in the precision yield dummy data
5) Strip out location data and identifiers, average satellite measurements per field and round these measurements to prevent reverse engineering of field locations
6) Output final merged and anonymised to the ‘Output’ folder in .csv format

