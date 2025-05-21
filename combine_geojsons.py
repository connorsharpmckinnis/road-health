import os
import pandas as pd
import geopandas as gpd

"""
Aggregates GeoJSON files containing AI analysis results into a single overview.
Pulls from 'road_geojsons' folder and writes to 'all_files.geojson'.
"""


# 1) Gather all .geojson file paths
folder = 'road_geojsons'
files = [os.path.join(folder, f) 
         for f in os.listdir(folder) 
         if f.lower().endswith('.geojson')]

# 2) Read each one into a GeoDataFrame
gdfs = [gpd.read_file(fp) for fp in files]

# 3) Concatenate them (ignoring the old index)
combined = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

# 4) (Optional) ensure a consistent CRS
# combined = combined.to_crs(epsg=4326)

# 5) Write out
combined.to_file('all_files.geojson', driver='GeoJSON')