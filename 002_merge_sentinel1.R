############################################################
# Add 1km grid IDs to extracted Satellite band time series #
# Version: 21/08/24 Author: Evangeline Corcoran            #
############################################################

#install package dependencies

install.packages('raster')
install.packages('maptools')
install.packages('rgdal')
install.packages('dplyr')

library(raster)
library(maptools)
library(rgdal)
library(dplyr)

#install.packages("Rcpp")
#install.packages("ncdf4")

#library(Rcpp)
#library(ncdf4)

##GLOBAL VARIABLES##
# Import 1km grid for metadata
setwd('D:/par-merge-test')
meta_grid <- read.csv('LargeScaleCropData_grid_10km_merge.csv')
drop <- c("east_adj", "north_adj", "gridref_adj")
meta_grid_id <- meta_grid[,!(names(meta_grid) %in% drop)]

#create empty raster and add grid id values to it
e <- extent(meta_grid_id[,1:2])
r <- raster(e, ncol = 3069, nrow = 18)
x <- rasterize(meta_grid_id[, 1:2], r, meta_grid_id[,3], crs = "+proj=longlat +datum=WGS84")
#plot(x)

##LOAD DATA##
#set working directory to folder with tiles of band data 
setwd('D:/Raw Sentinel-1 SAR/2015/VH/VH_2015_Apr_Jun/2/chunk-2015-04-01_2015-06-30')
files = list.files(path = "D:/Raw Sentinel-1 SAR/2015/VH/VH_2015_Apr_Jun/2/chunk-2015-04-01_2015-06-30", 
                   pattern = "*.tif")
#setwd('C:/Users/ecorcoran/OneDrive - The Alan Turing Institute/Documents/Large Scale Model Data/par-merge-test')
#files = list.files(path = "D:/par-merge-test", pattern = "*.tif")

#merge satellite band data with grid I.D. for 1km metadata
add_grid_id = function(input) {
  # Import raw satellite band raster tile
  tile <- stack(input)
  #tile <- stack('test_ts_vv_0_2016-01-01_2016-04-01-0000000000-0000000000.tif')
  # convert to dataframe
  tile_df <- as.data.frame(tile, xy = TRUE)
  
  #retrieve tile name
  tile_name = strsplit(input, "[.]")[[1]][1]
  tile_name
  
  #add 1 km grid ID to satellite band data
  points = cbind(tile_df$x, tile_df$y)
  tile_df$grid_ID <- round(extract(x,SpatialPoints(points)),0)
  
  #remove any satellite band data without a grid ID
  tile_df_clean <- tile_df[!is.na(tile_df$grid_ID),]
  
  #output csv with cleaned band data and 1km grid ID
  write.csv(tile_df_clean, file = paste(tile_name, '_with_grid.csv', sep = ""), row.names = FALSE)
}

for (i in 1:length(files)) {
  add_grid_id(files[i])
}


