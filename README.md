# CYCLeSS-dataset-code
R code used to merge and align available UK climate, soil and Sentinel-1 synthetic aperture radard (SAR) data to the 1 kilometre square grid used in the creation of the Crop Yields, Climate, Soils, and Satellites (CYCleSS) dataset, a large-scale crop yield dataset derived from precision yield data for 2,000 fields across England on which a variety of crops are grown.  This dataset and potential use cases are described in full in the following paper:

>Corcoran et al. (2024). CYCleSS: A dataset for developing coarse-grained UK-wide crop yield models with machine learning. Nature Scientific Data, *under review*.

Alignment of the gathered climate and soil metadata to the same spatial scale of 1 km2  grids was performed using R, and can be replicated using the file **‘001_climate_and_soil_data_alignment.R’**.

Sentinel-1 SAR radar band time-series data was extracted via the SEPAL platform in three month chunks, which were then converted to yearly dataframes using the ‘merge’ function of the ‘dplyr’ package in R. Code for performing merging of 3-monthly chunked Sentinel-1 SAR radar data is provided in the **‘002_merge_sentinel1.R’**.
