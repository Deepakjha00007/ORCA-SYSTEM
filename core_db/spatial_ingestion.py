import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from typing import Optional, Any
from sqlalchemy import create_engine

def ingest_spatial_dataframe(df: pd.DataFrame, db_connection_url: Optional[str] = None) -> bool:
    """
    Transforms lat/lon spatial coordinates into GeoPandas GeoDataFrames (EPSG:4326)
    and ingests them into PostGIS or local spatial caches.
    """
    if df.empty:
        print("[Spatial Ingestion] Warning: No spatial data provided for ingestion.")
        return False

    print(f"[Spatial Ingestion] Ingesting {len(df)} spatial records...")

    # Ensure required spatial columns exist
    if "latitude" not in df.columns or "longitude" not in df.columns:
        raise ValueError("DataFrame must contain 'latitude' and 'longitude' columns.")

    # 1. Convert Pandas DataFrame -> GeoPandas GeoDataFrame with Point geometry
    geometry = [Point(xy) for xy in zip(df["longitude"], df["latitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    # Clean missing values
    gdf["sst"] = gdf.get("sst", 28.0).fillna(28.0)
    gdf["current_speed"] = gdf.get("current_speed", 0.0).fillna(0.0)
    gdf["pfz_score"] = gdf.get("pfz_score", "MODERATE").fillna("MODERATE")

    # 2. Ingest into PostGIS if database URL is provided
    if db_connection_url:
        try:
            engine = create_engine(db_connection_url)
            # PostGIS ingestion using GeoPandas to_postgis
            gdf.to_postgis(
                name="marine_observations",
                con=engine,
                if_exists="append",
                index=False
            )
            print("[Spatial Ingestion] Successfully ingested GeoDataFrame into PostGIS.")
            return True
        except Exception as e:
            print(f"[Spatial Ingestion] PostGIS ingestion failed ({e}). Saving to local spatial cache.")

    # Local fallback cache if DB connection is offline
    cache_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "spatial_cache.parquet")
    
    gdf.to_parquet(cache_path)
    print(f"[Spatial Ingestion] Successfully cached {len(gdf)} records to {cache_path}")
    return True


if __name__ == "__main__":
    sample_df = pd.DataFrame([
        {"latitude": 18.92, "longitude": 72.83, "sst": 28.5, "current_speed": 1.2, "pfz_score": "HIGH"},
        {"latitude": 18.95, "longitude": 72.88, "sst": 27.8, "current_speed": 0.8, "pfz_score": "MEDIUM"}
    ])
    ingest_spatial_dataframe(sample_df)