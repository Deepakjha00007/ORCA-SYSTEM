import json
from shapely.geometry import Point,shape
from pyproj import Geod
from langchain_core.tools import tool

class BoundaryChecker:
    def __init__(self, geojson_path: str = "data/imbl_eez_boundaries.geojson"):
        self.geod = Geod(ellps="WGS84")
        try:
            with open(geojson_path, "r") as f:
                self.boundaries = json.load(f)
        except FileNotFoundError:
            self.boundaries = {"type": "FeatureCollection", "features": []}

    def check_boundary_proximity(self, lat: float, lon: float, threshold_km: float = 5.0):
        current_pt = Point(lon, lat)
        warnings = []
        is_violation = False

        for feature in self.boundaries.get("features", []):
            geom = shape(feature["geometry"])
            boundary_name = feature.get("properties", {}).get("name", "Restricted Area")
            
            if geom.contains(current_pt):
                is_violation = True
                warnings.append(f"CRITICAL: Vessel inside prohibited boundary: {boundary_name}!")
            else:
                nearest_pt, _ = geom.boundary.project(current_pt), geom
                # Calculate distance using pyproj
                _, _, dist_meters = self.geod.inv(lon, lat, nearest_pt.x, nearest_pt.y)
                dist_km = dist_meters / 1000.0
                if dist_km <= threshold_km:
                    warnings.append(f"WARNING: Vessel is {dist_km:.2f} km from boundary: {boundary_name}.")

        return {"is_violation": is_violation, "warnings": warnings}

@tool
def check_vessel_safety_zone(lat: float, lon: float) -> str:
    """Checks if the vessel coordinates violate IMBL/EEZ boundaries or approach danger zones."""
    checker = BoundaryChecker()
    res = checker.check_boundary_proximity(lat, lon)
    return json.dumps(res)