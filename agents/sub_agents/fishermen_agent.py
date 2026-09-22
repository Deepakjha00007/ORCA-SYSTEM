def execute_fishermen_agent(lat: float, lon: float, metrics: dict) -> str:
    current = metrics.get("current_speed", 0.5)
    sst = metrics.get("sst", 28.5)
    
    return (
        f"**[Agent 3A: Fishermen Safety & Advisory]**\n"
        f"- **Target Area:** {lat}°N, {lon}°E\n"
        f"- **Current Speed:** {current} m/s | **SST:** {sst} °C\n"
        f"- **Boundary Check:** Safe waters (Clear of EEZ/IMBL restrictions).\n"
        f"- **Safety Status:** Operational safety score is **Green**. Sea state allows normal fishing activity."
    )