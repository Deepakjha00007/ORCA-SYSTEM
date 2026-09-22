import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from agents.state import ORCAMarineState
from services.isro_data_pipeline import load_ocean_data
from agents.sub_agents.fishermen_agent import execute_fishermen_agent
from agents.sub_agents.fishery_agent import execute_fishery_agent
from agents.sub_agents.navigation_agent import execute_navigation_agent

load_dotenv()

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def process_orca_query(user_query: str) -> ORCAMarineState:
    system_prompt = """
    You are Agent 1 & 2 (Language, Intent & Supervisor Orchestrator) for ORCA Marine System.
    Analyze the user prompt and extract intent details.
    
    If latitude and longitude are not explicitly stated, extract or default to lat=15.0, lon=72.0 (Arabian Sea).
    """

    # Enforce strict JSON Schema output
    json_schema = {
        "type": "OBJECT",
        "properties": {
            "persona": {
                "type": "STRING",
                "enum": ["Fishermen", "Navigation", "Policy"]
            },
            "intent": {
                "type": "STRING",
                "enum": ["PFZ_Location", "Safety_Alert", "Route_Optimization"]
            },
            "lat": {"type": "NUMBER"},
            "lon": {"type": "NUMBER"}
        },
        "required": ["persona", "intent", "lat", "lon"]
    }

    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash-lite',
            contents=user_query,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=json_schema,
                temperature=0.0,
            ),
        )
        extracted = json.loads(response.text)
    except Exception:
        extracted = {"persona": "Fishermen", "intent": "PFZ_Location", "lat": 15.0, "lon": 72.0}

    lat = float(extracted.get("lat", 15.0))
    lon = float(extracted.get("lon", 72.0))
    intent = extracted.get("intent", "PFZ_Location")

    # Fetch ocean variables via xarray pipeline
    ocean_data = load_ocean_data(lat=lat, lon=lon)
    metrics = ocean_data["point_metrics"]

    # Route to domain sub-agents
    if intent == "Safety_Alert":
        response_msg = execute_fishermen_agent(lat, lon, metrics)
    elif intent == "Route_Optimization":
        response_msg = execute_navigation_agent(lat, lon, metrics)
    else:
        response_msg = execute_fishery_agent(lat, lon, metrics)

    return ORCAMarineState(
        user_query=user_query,
        persona=extracted.get("persona", "Fishermen"),
        intent=intent,
        lat=lat,
        lon=lon,
        subagent_response=response_msg,
        geospatial_data=ocean_data
    )