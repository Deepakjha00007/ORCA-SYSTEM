import pandas as pd

def run_spatial_aggregation(df: pd.DataFrame):
    """
    In-memory spatial data summaries.
    """
    return {
        "mean_sst": df['sst'].mean(),
        "max_current": df['current_speed'].max(),
        "total_pfz_zones": len(df[df['pfz_score'] == 'HIGH'])
    }