#######################################################################
# Evangeline Corcoran,  Version: 21/08/2024
# Retrieve climate data matching land use and soil data grid points
#######################################################################
install.packages("raster")
install.packages("rgdal")
install.packages("dplyr")
install.packages("Rcpp")
install.packages("ncdf4")
install.packages('maptools')

#load packages
library(Rcpp)
library(raster)
library(rgdal)
library(maptools)
library(dplyr)
library(ncdf4)

setwd('~/Large Scale Model Data')
#read in grid points
grid <- read.csv('LargeScaleCropData_grid_points.csv')

#read in met data by variable
setwd('~/Large Scale Model Data/met/2017/peti')
stack_1 <- stack("chess-pe_peti_gb_1km_daily_20170101-20170131.nc")
stack_2 <- stack("chess-pe_peti_gb_1km_daily_20170201-20170228.nc")
stack_3 <- stack("chess-pe_peti_gb_1km_daily_20170301-20170331.nc")
stack_4 <- stack("chess-pe_peti_gb_1km_daily_20170401-20170430.nc")
stack_5 <- stack("chess-pe_peti_gb_1km_daily_20170501-20170531.nc")
stack_6 <- stack("chess-pe_peti_gb_1km_daily_20170601-20170630.nc")
stack_7 <- stack("chess-pe_peti_gb_1km_daily_20170701-20170731.nc")
stack_8 <- stack("chess-pe_peti_gb_1km_daily_20170801-20170831.nc")
stack_9 <- stack("chess-pe_peti_gb_1km_daily_20170901-20170930.nc")
stack_10 <- stack("chess-pe_peti_gb_1km_daily_20171001-20171031.nc")
stack_11 <- stack("chess-pe_peti_gb_1km_daily_20171101-20171130.nc")
stack_12 <- stack("chess-pe_peti_gb_1km_daily_20171201-20171231.nc")

#convert to dataframes
df_1 <- as.data.frame(stack_1, xy= TRUE)
df_2 <- as.data.frame(stack_2, xy= TRUE)
df_3 <- as.data.frame(stack_3, xy= TRUE)
df_4 <- as.data.frame(stack_4, xy= TRUE)
df_5 <- as.data.frame(stack_5, xy= TRUE)
df_6 <- as.data.frame(stack_6, xy= TRUE)
df_7 <- as.data.frame(stack_7, xy= TRUE)
df_8 <- as.data.frame(stack_8, xy= TRUE)
df_9 <- as.data.frame(stack_9, xy= TRUE)
df_10 <- as.data.frame(stack_10, xy= TRUE)
df_11 <- as.data.frame(stack_11, xy= TRUE)
df_12 <- as.data.frame(stack_12, xy= TRUE)

#merge all variable data for year
merge_df <- merge(df_1, df_2, by = c("x","y"))
merge_df <- merge(merge_df, df_3, by = c("x","y"))
merge_df <- merge(merge_df, df_4, by = c("x","y"))
merge_df <- merge(merge_df, df_5, by = c("x","y"))
merge_df <- merge(merge_df, df_6, by = c("x","y"))
merge_df <- merge(merge_df, df_7, by = c("x","y"))
merge_df <- merge(merge_df, df_8, by = c("x","y"))
merge_df <- merge(merge_df, df_9, by = c("x","y"))
merge_df <- merge(merge_df, df_10, by = c("x","y"))
merge_df <- merge(merge_df, df_11, by = c("x","y"))
merge_df <- merge(merge_df, df_12, by = c("x","y"))

# FROM (BNG) TO (WGS84)
bng <- "+init=epsg:27700"
wgs84 <- "+init=epsg:4326"

# Create spatial object where eastings is x-axis and northings is y-axis
coordinates(merge_df) <- c("x", "y")
# Set projection of data
proj4string(merge_df) <- CRS(bng)

# BNG to WGS84 conversion
merge_wgs84 = spTransform(merge_df, CRS(wgs84))

# Convert SpatialPoints back into a data-frame
merge_wgs84 <- as.data.frame(merge_wgs84)

#round coordinates in grid and met data to 7 significant figures
merge_wgs84$x <- signif(merge_wgs84$x, digits = 7)
merge_wgs84$y <- signif(merge_wgs84$y, digits = 7)
grid$x <- signif(grid$x, digits = 7)
grid$y <- signif(grid$y, digits = 7)

#filter met data for grid points matching land use and soil
merge_grid <- merge(merge_wgs84, grid, by = c("x","y"))

#remove missing data
merge_grid <- na.omit(merge_grid)

#save data
write.csv(merge_grid, 'LargeScaleCropData_met_peti_2017.csv')

#retrieve and save updated grid points
setwd('~/Large Scale Model Data')
grids <- as.data.frame(cbind(merge_grid$x, merge_grid$y))
grids <- grids %>% rename(x = V1,
                          y = V2)
write.csv(grids, 'LargeScaleCropData_grid_points.csv')
