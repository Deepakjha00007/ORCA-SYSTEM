import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from agents.tools import query_ocean_telemetry_tool, find_pfz_hotspots_tool

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def run_fishery_agent(query: str, lat: float, lon: float) -> str:
    """
    Evaluates SST thermal fronts, chlorophyll levels, and potential fishing zone (PFZ) hotspots 
    using local Ollama execution.
    """
    telemetry = query_ocean_telemetry_tool(lat, lon)
    pfz_data = find_pfz_hotspots_tool(lat, lon, telemetry.get("chlorophyll_mg_m3", 0.42))

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL,
        temperature=0.2
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are Agent 3B: Potential Fishing Zone (PFZ) & Marine Biology Specialist. Evaluate SST thermal fronts and Chlorophyll-a optical density to provide actionable commercial fishing reports."),
        ("user", """
USER COMMAND: {query}
LOCATION: {lat}°N, {lon}°E
CHLOROPHYLL: {chlorophyll} mg/m³ | SST: {sst} °C
PFZ METRICS: Probability {pfz_prob}, Hotspots {hotspots_count}, Species {species}

Provide a concise, highly actionable commercial fishing dispatch report.
""")
    ])

    chain = prompt | llm
    
    response = chain.invoke({
        "query": query,
        "lat": lat,
        "lon": lon,
        "chlorophyll": telemetry.get("chlorophyll_mg_m3", 0.42),
        "sst": telemetry.get("sst_celsius", 28.5),
        "pfz_prob": pfz_data.get("pfz_probability", "85%"),
        "hotspots_count": pfz_data.get("potential_hotspots_count", 3),
        "species": pfz_data.get("primary_fish_species", ["Pelagic", "Mackerel"])
    })

    return response.content