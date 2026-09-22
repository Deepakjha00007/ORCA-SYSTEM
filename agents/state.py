from typing import TypedDict, Optional, Dict, Any

class ORCAMarineState(TypedDict):
    user_query: str
    persona: str          # "Fishermen", "Navigation", "Policy"
    intent: str           # "PFZ_Location", "Safety_Alert", "Route_Optimization"
    lat: float
    lon: float
    subagent_response: Optional[str]
    geospatial_data: Optional[Dict[str, Any]]