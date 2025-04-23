from arcgis.gis import GIS
from arcgis.geometry import Geometry
from arcgis.geometry.functions import project
from arcgis.geometry import distance as arcgis_distance
from arcgis.features import use_proximity
from arcgis.features import Feature, FeatureLayer, FeatureLayerCollection, FeatureSet
from arcgis.geometry import *
from arcgis import *
import os
from shapely.geometry import Point as ShapelyPoint
from shapely.ops import transform
import pyproj

api_key = os.getenv("ARCGIS_API_KEY")
gis = GIS("https://carync.maps.arcgis.com", api_key=api_key)
print("Connected to ArcGIS Online")

# Load just the road ownership layer
road_ownership_item: FeatureLayerCollection = gis.content.get("e79290fb33664e6d94cb650ea29a6bfa")
roads_layer: FeatureLayer = road_ownership_item.layers[0]


# Pothole location
lat, lon = 35.791836, -78.784555  # Example spot on a state road
pothole = Point({"x" : lon, "y" : lat, 
            "spatialReference" : {"wkid" : 3857}}) 

pothole_set = Feature(geometry=pothole, attributes={})
pothole_featureset = FeatureSet([pothole_set])

# Create a 50-meter buffer around the projected pothole point
# Convert ArcGIS point to shapely
shapely_point = ShapelyPoint(pothole["x"], pothole["y"])
buffered = shapely_point.buffer(50)  # 50m buffer (in meters)

circle = Geometry(buffered.__geo_interface__)
circle["spatialReference"] = {"wkid": 3857}
print(f'{circle._type = }')

results = roads_layer.query(
    geometry=circle,
    geometry_type="esriGeometryPolygon",
    spatial_rel="esriSpatialRelIntersects",
    out_fields="*",
    return_geometry=True
)

print(f'{results = }')