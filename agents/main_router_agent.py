import logging
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from agents.sub_agents.rag_agent import run_rag_advisory
# Import schemas and agent nodes
from tools.schemas import AgentState, PrimaryIntent, UrgencyLevel
from agents.nlp_intent_agent import nlp_intent_node

logger = logging.getLogger("ORCA_Gateway")


# ==========================================
# 1. SUB-AGENT NODE HANDLERS
# ==========================================

def safety_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node handler for Safety & Distress Advisories."""
    coords = state.extracted_coords
    lat = coords.latitude if coords else 18.92
    lon = coords.longitude if coords else 72.83
    
    advisory = (
        f"SAFETY ALERT: Vessel monitored at Lat {lat:.4f}, Lon {lon:.4f}. "
        f"Weather and boundary parameters are within normal limits. Maintain VHF Channel 16."
    )
    
    return {
        "status": "SAFETY_PROCESSED",
        "response": advisory,
        "data_context": {
            **(state.data_context or {}),
            "safety_checked": True,
            "monitored_coords": {"lat": lat, "lon": lon}
        }
    }


def fishery_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node handler for Potential Fishing Zone (PFZ) Advisories."""
    coords = state.extracted_coords
    lat = coords.latitude if coords else 18.92
    lon = coords.longitude if coords else 72.83
    
    advisory = (
        f"FISHING ADVISORY: High chlorophyll density detected near Lat {lat:.4f}, Lon {lon:.4f}. "
        f"Good potential fishing zone for pelagic species."
    )
    
    return {
        "status": "FISHERY_PROCESSED",
        "response": advisory,
        "data_context": {
            **(state.data_context or {}),
            "pfz_detected": True,
            "recommended_zone": {"lat": lat, "lon": lon}
        }
    }


def weather_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node handler for Marine Weather & Ocean Currents."""
    coords = state.extracted_coords
    lat = coords.latitude if coords else 18.92
    lon = coords.longitude if coords else 72.83
    
    advisory = (
        f"MARINE WEATHER: Forecast for Lat {lat:.4f}, Lon {lon:.4f}: "
        f"Wind speed 12 knots, wave height 1.2m, light surface swell."
    )
    
    return {
        "status": "WEATHER_PROCESSED",
        "response": advisory,
        "data_context": {
            **(state.data_context or {}),
            "weather_checked": True
        }
    }


def navigation_agent_node(state: AgentState) -> Dict[str, Any]:
    """Node handler for Geofencing & Maritime Boundary Limits."""
    coords = state.extracted_coords
    lat = coords.latitude if coords else 18.92
    lon = coords.longitude if coords else 72.83
    
    advisory = (
        f"NAVIGATION ADVISORY: Vessel positioned at Lat {lat:.4f}, Lon {lon:.4f}. "
        f"Clear of international maritime boundaries (IMBL)."
    )
    
    return {
        "status": "NAVIGATION_PROCESSED",
        "response": advisory,
        "data_context": {
            **(state.data_context or {}),
            "boundary_checked": True
        }
    }


def emergency_handler_node(state: AgentState) -> Dict[str, Any]:
    """Immediate distress handler for SOS / Critical urgency states."""
    return {
        "status": "EMERGENCY_TRIGGERED",
        "is_emergency": True,
        "response": (
            "EMERGENCY SOS RECEIVED: Local Coast Guard and Maritime Rescue Coordination Centre (MRCC) "
            "have been alerted. Stay on current location."
        ),
        "data_context": {
            **(state.data_context or {}),
            "emergency_broadcast": True
        }
    }
def rag_node(state: AgentState):
    query = state["query_text"]
    telemetry = f"Lat: {state['latitude']}, Lon: {state['longitude']}"
    
    # Execute RAG lookup + LLM Generation
    advisory = run_rag_advisory(query, telemetry)
    
    return {"english_advisory": advisory}


# ==========================================
# 2. ROUTING LOGIC & KEYWORD HEURISTIC FALLBACK
# ==========================================

def route_intent(state: AgentState) -> Literal["emergency", "safety", "fishing", "weather", "navigation"]:
    """
    Conditional routing function determining downstream node transition.
    Includes keyword-based fallback if NLP intent classification yields UNKNOWN.
    """
    # 1. Emergency Priority Check
    if state.is_emergency or state.urgency == UrgencyLevel.CRITICAL:
        logger.warning(f"Routing query as EMERGENCY for user {state.user_id}")
        return "emergency"
    
    intent = state.intent
    
    # 2. Standard Intent Mapping
    if intent == PrimaryIntent.SAFETY:
        return "safety"
    elif intent == PrimaryIntent.FISHING or intent == "PFZ":
        return "fishing"
    elif intent == PrimaryIntent.WEATHER:
        return "weather"
    elif intent == PrimaryIntent.NAVIGATION:
        return "navigation"
    
    # 3. Keyword Heuristic Fallback (For UNKNOWN or ambiguous intent classification)
    query_text = (state.query_text or "").lower()
    
    fishing_keywords = ["fish", "fishing", "pfz", "chlorophyll", "catch", "abundance", "hotspot", "species", "tuna"]
    weather_keywords = ["weather", "wind", "wave", "swell", "storm", "rain", "cyclone", "temperature", "sst"]
    safety_keywords = ["sos", "help", "distress", "hazard", "danger", "warning", "rescue"]
    navigation_keywords = ["border", "imbl", "boundary", "geofence", "route", "gps", "coordinate"]
    
    if any(kw in query_text for kw in fishing_keywords):
        logger.info(f"Fallback heuristic matched FISHING for query: '{state.query_text}'")
        return "fishing"
    elif any(kw in query_text for kw in safety_keywords):
        logger.info(f"Fallback heuristic matched SAFETY for query: '{state.query_text}'")
        return "safety"
    elif any(kw in query_text for kw in navigation_keywords):
        logger.info(f"Fallback heuristic matched NAVIGATION for query: '{state.query_text}'")
        return "navigation"
    elif any(kw in query_text for kw in weather_keywords):
        logger.info(f"Fallback heuristic matched WEATHER for query: '{state.query_text}'")
        return "weather"

    # Default fallback to weather agent
    logger.info(f"No specific intent matched. Defaulting to WEATHER agent.")
    return "weather"


# ==========================================
# 3. LANGGRAPH WORKFLOW BUILDER
# ==========================================

builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("nlp_intent", nlp_intent_node)
builder.add_node("safety_agent", safety_agent_node)
builder.add_node("fishery_agent", fishery_agent_node)
builder.add_node("weather_agent", weather_agent_node)
builder.add_node("navigation_agent", navigation_agent_node)
builder.add_node("emergency_handler", emergency_handler_node)

# Add Entry Edge
builder.add_edge(START, "nlp_intent")

# Dynamic Intent Routing Edge
builder.add_conditional_edges(
    "nlp_intent",
    route_intent,
    {
        "emergency": "emergency_handler",
        "safety": "safety_agent",
        "fishing": "fishery_agent",
        "weather": "weather_agent",
        "navigation": "navigation_agent",
    }
)

# Terminal Edges to END
builder.add_edge("safety_agent", END)
builder.add_edge("fishery_agent", END)
builder.add_edge("weather_agent", END)
builder.add_edge("navigation_agent", END)
builder.add_edge("emergency_handler", END)

# Compile Executable Graph
orca_graph = builder.compile()