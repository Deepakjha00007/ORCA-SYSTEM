import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.tools import query_ocean_telemetry_tool, calculate_hydrodynamic_route_tool

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def run_navigation_agent(query: str, lat: float, lon: float) -> str:
    """
    Analyzes surface velocity vectors, drift rates, and fuel-optimal route vectors 
    using local Ollama execution.
    """
    telemetry = query_ocean_telemetry_tool(lat, lon)
    route_data = calculate_hydrodynamic_route_tool(lat, lon, telemetry.get("surface_velocity_ms", 0.45))

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.1
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are Agent 3C: Route Hydrodynamics & Navigation Specialist for the ORCA System. Analyze ocean current velocity vectors and calculate fuel-optimal paths."),
        ("user", """
USER COMMAND: {query}
TELEMETRY DATA: Latitude {lat}°N, Longitude {lon}°E
SURFACE CURRENT: {surface_current} m/s
ROUTE CALCULATION: Heading {heading}°, Drift {drift} knots, Fuel Savings {fuel_savings}

Synthesize a brief, authoritative navigation advisory.
""")
    ])

    chain = prompt | llm

    response = chain.invoke({
        "query": query,
        "lat": lat,
        "lon": lon,
        "surface_current": telemetry.get("surface_velocity_ms", 0.45),
        "heading": route_data.get("recommended_heading_deg", 240),
        "drift": route_data.get("current_drift_knots", 1.2),
        "fuel_savings": route_data.get("fuel_savings_pct", "14%")
    })

    return response.content