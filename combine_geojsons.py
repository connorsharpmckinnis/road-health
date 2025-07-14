import os
import pandas as pd
import geopandas as gpd
import numpy as np

"""
Aggregates GeoJSON files containing AI analysis results into a single overview.
Pulls from 'road_geojsons' folder and writes to 'all_files.geojson'.
"""


# 1) Gather all .geojson file paths
folder = "road_geojsons"
files = [
    os.path.join(folder, f)
    for f in os.listdir(folder)
    if f.lower().endswith(".geojson")
]

# 2) Read each one into a GeoDataFrame
gdfs = [gpd.read_file(fp) for fp in files]

# 3) Concatenate them (ignoring the old index)
combined = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

# 4) Convert road_health_index to int, keep nulls as-is
if "estimated_pcr" in combined.columns:
    combined["estimated_pcr"] = combined["estimated_pcr"].apply(
        lambda x: int(round(x)) if pd.notnull(x) else 0
    )
# combined = combined.to_crs(epsg=4326)

# 5) Write out
combined.to_file("all_files.geojson", driver="GeoJSON")
