from arcgis.gis import GIS
from arcgis.geometry import Point
from arcgis.features import FeatureLayer

# Connect to GIS
gis = GIS("https://your-org.maps.arcgis.com", api_key="YOUR_API_KEY")

# Define your point (latitude, longitude)
lat = 35.7915
lon = -78.7811
point = {"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}

# Load your roads layer
roads_layer = FeatureLayer("https://services.arcgis.com/<your-org-id>/arcgis/rest/services/Roads/FeatureServer/0")

# Find nearest road
result = roads_layer.query_nearest(geometries=[point], search_distance=100, return_attributes=True)

# Get the closest feature and its attributes
nearest_road = result['features'][0]['attributes']

# Extract relevant info
road_name = nearest_road.get("ROAD_NAME")
owner = nearest_road.get("OWNER")  # Field names depend on your layer!
maintainer = nearest_road.get("MAINT_RESPONSIBILITY")

print(f"Closest road: {road_name}")
print(f"Maintained by: {maintainer or owner}")