import os
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from tools.geofence import check_vessel_safety_zone
from tools.marine_data import get_ocean_conditions

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


class SafetyAdvisoryAgent:
    def __init__(self):
        # Local Ollama LLM initialization
        self.llm = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
            temperature=0.1
        )
        # Bind local tool functions for safety and geofence checks
        self.llm_with_tools = self.llm.bind_tools([check_vessel_safety_zone, get_ocean_conditions])

    def run(self, lat: float, lon: float, user_query: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are ORCA's Marine Safety Agent. Generate clear, actionable safety advisories based on boundary checks and ocean metrics."),
            ("user", "Coordinates: Lat {lat}, Lon {lon}. Query: {query}")
        ])
        
        chain = prompt | self.llm_with_tools
        res = chain.invoke({"lat": lat, "lon": lon, "query": user_query})
        
        return res.content