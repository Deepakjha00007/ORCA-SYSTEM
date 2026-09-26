import re
import logging
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from tools.schemas import (
    GeoCoordinates,
    PrimaryIntent,
    UrgencyLevel,
    NLPMetadata,
    AgentState,
)

logger = logging.getLogger("ORCA_Gateway")


class CustomNLPMetadata(NLPMetadata):
    """
    Subclass/Wrapper of NLPMetadata ensuring compatibility with dictionary 
    operations like .get() across legacy and newer pipeline nodes.
    """
    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        # Check model fields/data context
        data = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        return data.get(key, default)


class NLPIntentAgent:
    """
    Extracts Maritime Entities (Coordinates, Port names, Fish species)
    and classifies user intent for LangGraph agent routing.
    """

    def __init__(self, llm=None):
        self.llm = llm

    def extract_maritime_entities(self, text: str) -> Dict[str, Any]:
        """
        Regex + Named Entity Recognition (NER) pipeline for coastal locations & coordinates.
        """
        entities = {
            "coordinates": None,
            "port_name": None,
            "intent": PrimaryIntent.UNKNOWN,
            "urgency": UrgencyLevel.NORMAL,
            "target_species": [],
        }

        # 1. Coordinate Extraction Regex (Supports Decimal Degrees & Basic DM/DMS Formats)
        coord_pattern = r"(\d{1,2}(?:\.\d+)?)\s*°?\s*([NS])?[\s,]+(\d{1,3}(?:\.\d+)?)\s*°?\s*([EW])?"
        match = re.search(coord_pattern, text, re.IGNORECASE)
        if match:
            try:
                lat = float(match.group(1))
                if match.group(2) and match.group(2).upper() == "S":
                    lat = -lat

                lon = float(match.group(3))
                if match.group(4) and match.group(4).upper() == "W":
                    lon = -lon

                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    entities["coordinates"] = GeoCoordinates(latitude=lat, longitude=lon)
            except ValueError as e:
                logger.warning(f"Failed to parse extracted coordinates: {e}")

        # 2. Key Port & Location Keyword Matching
        ports = [
            "Mumbai",
            "Veraval",
            "Ratnagiri",
            "Malvan",
            "Alibaug",
            "Mormugao",
            "Mangalore",
            "Kochi",
            "Chennai",
            "Visakhapatnam",
            "Paradip",
        ]
        text_lower = text.lower()
        for port in ports:
            if port.lower() in text_lower:
                entities["port_name"] = port
                break

        # 3. Urgency & Intent Rules
        if any(w in text_lower for w in ["sos", "mayday", "sinking", "man overboard", "fire on board"]):
            entities["intent"] = PrimaryIntent.SAFETY
            entities["urgency"] = UrgencyLevel.CRITICAL
        elif any(w in text_lower for w in ["help", "storm", "cyclone", "rough sea", "warning", "danger", "engine failure"]):
            entities["intent"] = PrimaryIntent.SAFETY
            entities["urgency"] = UrgencyLevel.HIGH
        elif any(w in text_lower for w in ["fish", "pfz", "catch", "sardine", "mackerel", "tuna", "chlorophyll", "density", "zone", "fishinz"]):
            entities["intent"] = PrimaryIntent.FISHING
            entities["urgency"] = UrgencyLevel.NORMAL
        elif any(w in text_lower for w in ["border", "imbl", "eez", "pakistan", "sri lanka", "geofence", "restricted", "boundary"]):
            entities["intent"] = PrimaryIntent.NAVIGATION
            entities["urgency"] = UrgencyLevel.NORMAL
        elif any(w in text_lower for w in ["weather", "wind", "wave", "rain", "forecast", "temperature"]):
            entities["intent"] = PrimaryIntent.WEATHER
            entities["urgency"] = UrgencyLevel.NORMAL
        else:
            entities["intent"] = PrimaryIntent.GENERAL
            entities["urgency"] = UrgencyLevel.NORMAL

        return entities

    def process_query_nlp(self, text: str) -> CustomNLPMetadata:
        """
        Full NLP Pipeline execution combining Entity Extraction & LLM Intent Verification.
        Returns CustomNLPMetadata which supports both attribute access and .get().
        """
        extracted = self.extract_maritime_entities(text)

        target_species: List[str] = extracted["target_species"]
        parsed_intent: PrimaryIntent = extracted["intent"]
        urgency_level: UrgencyLevel = extracted["urgency"]

        # Enhance with LLM structured parsing if an LLM is provided
        if self.llm:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "You are the ORCA Maritime NLP Processor. Analyze the query and extract JSON with keys:\n"
                        '- "primary_intent": "SAFETY", "FISHING", "NAVIGATION", "WEATHER", or "GENERAL"\n'
                        '- "urgency_level": "NORMAL", "HIGH", or "CRITICAL"\n'
                        '- "target_species": list of target fish species mentioned, if any.',
                    ),
                    ("user", "Analyze this fisherman query: '{query}'"),
                ]
            )
            try:
                chain = prompt | self.llm | JsonOutputParser()
                llm_res = chain.invoke({"query": text})

                if llm_res.get("primary_intent"):
                    try:
                        parsed_intent = PrimaryIntent(llm_res["primary_intent"].upper())
                    except ValueError:
                        pass

                if llm_res.get("urgency_level"):
                    try:
                        urgency_level = UrgencyLevel(llm_res["urgency_level"].upper())
                    except ValueError:
                        pass

                if isinstance(llm_res.get("target_species"), list):
                    target_species = llm_res["target_species"]

            except Exception as e:
                logger.warning(f"LLM Intent extraction failed, falling back to rule-based parsing: {e}")

        return CustomNLPMetadata(
            processed_text=text,
            parsed_intent=parsed_intent,
            urgency_level=urgency_level,
            extracted_coordinates=extracted["coordinates"],
            detected_port=extracted["port_name"],
            target_species=target_species,
        )


def nlp_intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph orchestration node for NLP intent extraction.
    Accepts state dictionary or AgentState payload.
    """
    llm_instance = state.get("llm", None) if isinstance(state, dict) else getattr(state, "llm", None)
    agent = NLPIntentAgent(llm=llm_instance)

    # Fallback to raw query if internal normalized query is not set
    if isinstance(state, dict):
        user_query = state.get("query") or state.get("raw_query", "")
        existing_context = state.get("data_context", {})
    else:
        user_query = getattr(state, "query", None) or getattr(state, "raw_query", "")
        existing_context = getattr(state, "data_context", {}) or {}

    nlp_metadata = agent.process_query_nlp(user_query)

    is_emergency = (
        nlp_metadata.urgency_level == UrgencyLevel.CRITICAL
        or nlp_metadata.parsed_intent == PrimaryIntent.SAFETY
    )

    metadata_dict = (
        nlp_metadata.model_dump() 
        if hasattr(nlp_metadata, "model_dump") 
        else nlp_metadata.dict()
    )

    return {
        "intent": nlp_metadata.parsed_intent,
        "urgency": nlp_metadata.urgency_level,
        "extracted_coords": nlp_metadata.extracted_coordinates,
        "is_emergency": is_emergency,
        "status": "INTENT_PROCESSED",
        "data_context": {
            **(existing_context or {}),
            "nlp_metadata": metadata_dict,
        },
    }