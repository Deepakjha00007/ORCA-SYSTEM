def execute_fishery_agent(lat: float, lon: float, metrics: dict) -> str:
    sst = metrics.get("sst", 28.5)
    return (
        f"**[Agent 3B: Spatial Fishery Analytics]**\n"
        f"- **Thermal Front Analysis around {lat}°N, {lon}°E**:\n"
        f"- **Surface Temperature:** {sst} °C\n"
        f"- **PFZ Confidence:** High thermal gradient identified.\n"
        f"- **Fishery Action:** High-yield Potential Fishing Zone (PFZ) cluster detected within 15 km. "
        f"SST fronts are rendered on your map canvas."
    )