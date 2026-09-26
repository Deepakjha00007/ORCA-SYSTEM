import duckdb
import pandas as pd
from typing import Dict, Any, Optional

class MarineDuckDBAnalytics:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = duckdb.connect(db_path)
        # Load spatial extension in DuckDB
        try:
            self.conn.execute("INSTALL spatial; LOAD spatial;")
        except Exception:
            pass  # Fallback to standard relational SQL if spatial extension isn't pre-fetched

    def run_spatial_aggregation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Executes fast OLAP analytical queries on spatial observation DataFrames.
        """
        if df.empty:
            return {
                "mean_sst": None,
                "max_current": None,
                "total_pfz_zones": 0,
                "high_pfz_ratio": 0.0
            }

        # Register pandas DataFrame as a DuckDB virtual table
        self.conn.register("marine_data", df)

        query = """
            SELECT 
                ROUND(AVG(sst), 2) AS mean_sst,
                ROUND(MAX(current_speed), 2) AS max_current,
                COUNT(CASE WHEN pfz_score = 'HIGH' THEN 1 END) AS total_pfz_zones,
                ROUND(COUNT(CASE WHEN pfz_score = 'HIGH' THEN 1 END) * 1.0 / COUNT(*), 2) AS high_pfz_ratio
            FROM marine_data
        """
        res = self.conn.execute(query).fetchone()

        return {
            "mean_sst": res[0],
            "max_current": res[1],
            "total_pfz_zones": res[2],
            "high_pfz_ratio": res[3]
        }

    def query_bounding_box(self, df: pd.DataFrame, min_lat: float, max_lat: float, min_lon: float, max_lon: float) -> pd.DataFrame:
        """Filters spatial observations inside a bounding box."""
        if df.empty:
            return df
            
        self.conn.register("marine_data", df)
        query = f"""
            SELECT * FROM marine_data 
            WHERE latitude BETWEEN {min_lat} AND {max_lat}
              AND longitude BETWEEN {min_lon} AND {max_lon}
        """
        return self.conn.execute(query).df()


# Backwards compatibility function wrapper
def run_spatial_aggregation(df: pd.DataFrame) -> Dict[str, Any]:
    analytics = MarineDuckDBAnalytics()
    return analytics.run_spatial_aggregation(df)