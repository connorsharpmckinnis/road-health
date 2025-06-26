from arcgis.geometry import project
from arcgis.features import FeatureLayer
from arcgis.gis import GIS
from arcgis.geometry.filters import intersects
import os
import dotenv

dotenv.load_dotenv()
gis = GIS("https://www.arcgis.com", api_key=os.getenv("ARCGIS_API_KEY"))

roads_url = "https://maps.townofcary.org/arcgis/rest/services/Transportation/Transportation/MapServer/19"
roads_layer = FeatureLayer(roads_url, gis=gis)


def find_nearby_road(lat, lon):
    # Create extent buffer manually in WGS84
    delta_deg = 0.0001  # ~10 meters
    extent = {
        "xmin": lon - delta_deg,
        "ymin": lat - delta_deg,
        "xmax": lon + delta_deg,
        "ymax": lat + delta_deg,
        "spatialReference": {"wkid": 4326},
    }

    # Project the extent to match layer SR
    projected_extent = project([extent], in_sr=4326, out_sr=102719)[0]

    query_filter = intersects(projected_extent, sr=102719)

    result = roads_layer.query(
        geometry_filter=query_filter,
        out_fields="OWNERSHP",
        return_geometry=True,
        result_record_count=1,
    )

    return result.features[0] if result.features else []


def find_nearby_road_owner(lat, lon):
    road = find_nearby_road(lat, lon)
    owner = road.attributes.get("OWNERSHP", "UNKNOWN")
    return owner


def main():
    latitude = 35.791766
    longitude = -78.776689
    owner = find_nearby_road_owner(latitude, longitude)
    print(owner)


if __name__ == "__main__":
    main()
