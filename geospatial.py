import os
import dotenv
from arcgis.geometry import project
from arcgis.features import FeatureLayer
from arcgis.gis import GIS
from arcgis.geometry.filters import intersects


class RoadOwnerFinder:
    def __init__(
        self,
        api_key: str | None = None,
        gis_url: str = "https://www.arcgis.com",
        roads_url: str = "https://maps.townofcary.org/arcgis/rest/services/Transportation/Transportation/MapServer/19",
        buffer_meters: float = 10.0,
    ):
        dotenv.load_dotenv()
        key = api_key or os.getenv("ARCGIS_API_KEY")
        self.gis = GIS(gis_url, api_key=key)
        self.roads_layer = FeatureLayer(roads_url, gis=self.gis)
        # approximate degrees per meter at mid-lat (~10 m buffer)
        self._delta_deg = buffer_meters / 111_000

    def get_pothole_owner(self, lat: float, lon: float) -> str:
        """Return 'Town', 'State', 'Private' or 'UNKNOWN' for a given point."""
        road = self._find_nearby_road(lat, lon)
        return self._get_road_owner(road) if road else "UNKNOWN"

    def _find_nearby_road(self, lat: float, lon: float):
        # build a small WGS84 box around the point
        d = self._delta_deg
        extent = {
            "xmin": lon - d,
            "ymin": lat - d,
            "xmax": lon + d,
            "ymax": lat + d,
            "spatialReference": {"wkid": 4326},
        }
        # reproject to layer's SR (hard-coded here)
        projected = project([extent], in_sr=4326, out_sr=102719)[0]
        geom_filter = intersects(projected, sr=102719)
        res = self.roads_layer.query(
            geometry_filter=geom_filter,
            out_fields="OWNERSHP",
            return_geometry=False,
            result_record_count=1,
        )
        return res.features[0] if res.features else None

    def _get_road_owner(self, feature) -> str:
        return feature.attributes.get("OWNERSHP", "UNKNOWN")


def main():
    client = RoadOwnerFinder()
    owner = client.get_pothole_owner(35.795120, -78.786080)
    print(owner)


if __name__ == "__main__":
    main()
