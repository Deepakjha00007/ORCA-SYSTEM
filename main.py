import os
import io
import base64
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Imports from core modules and schemas
from tools.schemas import (
    AgentState, 
    LanguageCode, 
    PrimaryIntent, 
    UrgencyLevel, 
    GeoCoordinates
)
from agents.guardrails_agents import guardrails_node, GuardrailsAgent
from agents.multilingual_agent import MultilingualAgent
from agents.nlp_intent_agent import NLPIntentAgent
from services.bhashini_service import BhashiniNLPService
from services.nlp_speech_service import NLPSpeechService

# Imports from local sub-agents
from agents.sub_agents.fishermen_agent import SafetyAdvisoryAgent
from agents.sub_agents.fishery_agent import run_fishery_agent
from agents.sub_agents.navigation_agent import run_navigation_agent
from agents.sub_agents.rag_agent import run_rag_advisory

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [ORCA GATEWAY] - %(levelname)s - %(message)s")
logger = logging.getLogger("ORCA_Gateway")

app = FastAPI(
    title="ORCA Ocean Intelligence Gateway",
    description="Production Gateway for ORCA Multi-Agent Maritime Safety & Advisory Architecture (Local Ollama Engine + Bhashini + ChromaDB)",
    version="2.2.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services & Local Agents
speech_service = NLPSpeechService()
bhashini_service = BhashiniNLPService()
multilingual_agent = MultilingualAgent()
nlp_agent = NLPIntentAgent()
safety_agent = SafetyAdvisoryAgent()


# ==========================================
# 1. REQUEST & RESPONSE SCHEMAS
# ==========================================

class QueryRequest(BaseModel):
    user_id: str = Field(..., example="MH_RATNAGIRI_04")
    query_text: str = Field(..., example="आज रत्नागिरी जवळ मासेमारीसाठी हवामान कसे आहे?")
    latitude: float = Field(..., ge=-90.0, le=90.0, example=18.92)
    longitude: float = Field(..., ge=-180.0, le=180.0, example=72.83)
    language: LanguageCode = Field(default=LanguageCode.MARATHI)
    raw_audio_base64: Optional[str] = Field(None, description="Optional Base64 audio query input")


class AdvisoryResponse(BaseModel):
    status: str
    user_id: str
    intent: PrimaryIntent
    urgency: UrgencyLevel
    is_emergency: bool
    english_advisory: str
    localized_advisory: str
    audio_output_base64: Optional[str] = None
    extracted_coordinates: Optional[Dict[str, float]] = None
    data_context: Dict[str, Any] = Field(default_factory=dict)


# ==========================================
# 2. KEYWORD HEURISTIC INTENT OVERRIDE
# ==========================================

def apply_keyword_intent_fallback(query_text: str, current_intent: PrimaryIntent) -> PrimaryIntent:
    if current_intent not in [PrimaryIntent.UNKNOWN, None]:
        return current_intent

    query_lower = (query_text or "").lower()

    fishing_keywords = ["fish", "fishing", "pfz", "chlorophyll", "catch", "abundance", "hotspot", "species", "tuna"]
    weather_keywords = ["weather", "wind", "wave", "swell", "storm", "rain", "cyclone", "sst", "temperature"]
    safety_keywords = ["sos", "help", "distress", "hazard", "danger", "warning", "rescue", "emergency"]
    navigation_keywords = ["border", "imbl", "boundary", "geofence", "route", "gps", "coordinate"]
    rag_keywords = ["rule", "scheme", "subsidy", "regulation", "law", "government", "policy", "guideline"]

    if any(kw in query_lower for kw in fishing_keywords):
        logger.info(f"Keyword heuristic matched FISHERY_ADVISORY for query: '{query_text}'")
        return PrimaryIntent.FISHERY_ADVISORY
    elif any(kw in query_lower for kw in safety_keywords):
        logger.info(f"Keyword heuristic matched SAFETY_ALERT for query: '{query_text}'")
        return PrimaryIntent.SAFETY_ALERT
    elif any(kw in query_lower for kw in navigation_keywords):
        logger.info(f"Keyword heuristic matched NAVIGATION_BORDER for query: '{query_text}'")
        return PrimaryIntent.NAVIGATION_BORDER
    elif any(kw in query_lower for kw in weather_keywords):
        logger.info(f"Keyword heuristic matched WEATHER for query: '{query_text}'")
        return PrimaryIntent.WEATHER
    elif any(kw in query_lower for kw in rag_keywords):
        logger.info(f"Keyword heuristic matched GENERAL_KNOWLEDGE (RAG) for query: '{query_text}'")
        return PrimaryIntent.GENERAL_KNOWLEDGE

    return PrimaryIntent.UNKNOWN


# ==========================================
# 3. ORCHESTRATION PIPELINE ENGINE (ASYNC)
# ==========================================

async def run_orca_orchestrator_pipeline(state: AgentState) -> AgentState:
    """
    Executes multi-stage local ORCA agent workflow:
    Audio/Text Input -> Translation -> Guardrails -> Intent Parsing -> Sub-Agent & RAG Dispatch -> Localized TTS
    """
    logger.info(f"Processing query: '{state.raw_query}' | Language: {state.user_language}")

    # Stage 1: Multilingual Translation (Indic -> English)
    trans_res = await multilingual_agent.process_incoming_query(state.raw_query, source_lang=state.user_language)
    state.query = trans_res.get("english_query", state.raw_query)

    # Stage 2: Guardrails Verification & Emergency Check
    guardrail_res = guardrails_node({"query": state.query, "data_context": state.data_context or {}})
    
    if guardrail_res.get("status") == "BLOCKED":
        state.status = "BLOCKED"
        state.error = guardrail_res.get("error")
        state.response = guardrail_res.get("response", "Query blocked by security guardrails.")
        state.final_localized_response = state.response
        return state

    if guardrail_res.get("status") == "EMERGENCY_TRIGGERED":
        state.status = "EMERGENCY"
        state.is_emergency = True
        state.urgency = UrgencyLevel.CRITICAL
        state.intent = PrimaryIntent.SAFETY_ALERT
        state.response = guardrail_res.get("response", "EMERGENCY ALERT: Maritime safety forces notified.")
        
        output_res = await multilingual_agent.format_final_advisory(state.response, target_lang=state.user_language, generate_audio=False)
        state.final_localized_response = output_res.get("localized_text", state.response)
        state.audio_payload = output_res.get("audio_base64")
        return state

    # Stage 3: NLP Entity Extraction & Intent Classification
    nlp_res = nlp_agent.process_query_nlp(state.query)
    intent_str = nlp_res.get("parsed_intent", "UNKNOWN")
    
    parsed_intent = PrimaryIntent(intent_str) if intent_str in PrimaryIntent.__members__ else PrimaryIntent.UNKNOWN
    
    # Apply Heuristic Fallback
    state.intent = apply_keyword_intent_fallback(state.query, parsed_intent)
    
    urgency_str = nlp_res.get("urgency_level", "NORMAL")
    state.urgency = UrgencyLevel(urgency_str) if urgency_str in UrgencyLevel.__members__ else UrgencyLevel.NORMAL
    
    lat = state.extracted_coords.latitude if state.extracted_coords else 18.92
    lon = state.extracted_coords.longitude if state.extracted_coords else 72.83

    # Stage 4: Sub-Agent & ChromaDB RAG Routing
    logger.info(f"Routing query to sub-agent / RAG for intent: {state.intent}")
    
    if state.intent == PrimaryIntent.FISHERY_ADVISORY or state.intent == "PFZ":
        state.response = run_fishery_agent(query=state.query, lat=lat, lon=lon)
        
    elif state.intent in [PrimaryIntent.NAVIGATION_BORDER, PrimaryIntent.ROUTING]:
        state.response = run_navigation_agent(query=state.query, lat=lat, lon=lon)
        
    elif state.intent == PrimaryIntent.SAFETY_ALERT:
        state.response = safety_agent.run(lat=lat, lon=lon, user_query=state.query)
        
    elif state.intent in [PrimaryIntent.GENERAL_KNOWLEDGE, PrimaryIntent.UNKNOWN]:
        # Route to ChromaDB RAG Engine
        telemetry_ctx = f"Latitude: {lat}°N, Longitude: {lon}°E"
        state.response = run_rag_advisory(user_query=state.query, telemetry_context=telemetry_ctx)
        
    else:
        # Default Marine Weather Response
        state.response = (
            f"Marine Weather & Sea State Update for ({lat}°N, {lon}°E): "
            f"Sea surface temperature is 28.5°C, wind speed is 12 knots from SW, "
            f"and surface current velocity is 1.4 knots. Navigation conditions are favorable."
        )

    # Populate Data Context
    state.data_context = {
        **(state.data_context or {}),
        "sea_surface_temperature_celsius": 28.5,
        "current_speed_knots": 1.4,
        "rough_sea_alert": state.urgency == UrgencyLevel.HIGH,
        "detected_port": nlp_res.get("detected_port")
    }

    # Stage 5: Output Guardrail Validation
    guard_agent = GuardrailsAgent()
    state.response = guard_agent.validate_output_advisory(state.response, state.data_context)

    # Stage 6: Output Localized Synthesis & Audio Generation via Bhashini
    output_res = await multilingual_agent.format_final_advisory(
        state.response, 
        target_lang=state.user_language, 
        generate_audio=True
    )
    state.final_localized_response = output_res.get("localized_text", state.response)
    state.audio_payload = output_res.get("audio_base64")
    state.status = "SUCCESS"

    return state


# ==========================================
# 4. REST API ENDPOINTS
# ==========================================

@app.get("/")
async def health_check():
    return {
        "system": "ORCA Ocean Intelligence Gateway",
        "status": "ONLINE",
        "llm_engine": "Ollama (Local)",
        "vector_db": "ChromaDB",
        "translation_engine": "Bhashini API",
        "supported_languages": list(LanguageCode.__members__.keys())
    }


@app.post("/query", response_model=AdvisoryResponse)
async def process_text_query(req: QueryRequest):
    try:
        query_text = req.query_text
        
        # Decode base64 audio input if present
        if req.raw_audio_base64:
            audio_bytes = base64.b64decode(req.raw_audio_base64)
            transcribed = await speech_service.transcribe_audio_bytes(audio_bytes, source_lang=req.language.value)
            if transcribed:
                query_text = transcribed

        # Initialize Agent State
        initial_state = AgentState(
            raw_query=query_text,
            user_language=req.language,
            extracted_coords=GeoCoordinates(latitude=req.latitude, longitude=req.longitude)
        )

        # Run async orchestration pipeline
        final_state = await run_orca_orchestrator_pipeline(initial_state)

        return AdvisoryResponse(
            status=final_state.status,
            user_id=req.user_id,
            intent=final_state.intent,
            urgency=final_state.urgency,
            is_emergency=final_state.is_emergency,
            english_advisory=final_state.response or "No advisory generated.",
            localized_advisory=final_state.final_localized_response or "No advisory generated.",
            audio_output_base64=final_state.audio_payload,
            extracted_coordinates={
                "lat": final_state.extracted_coords.latitude,
                "lon": final_state.extracted_coords.longitude
            } if final_state.extracted_coords else None,
            data_context=final_state.data_context or {}
        )

    except Exception as e:
        logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"ORCA Gateway Pipeline Error: {str(e)}")


@app.post("/upload_audio")
async def upload_audio_file(
    file: UploadFile = File(...),
    language: LanguageCode = Form(LanguageCode.MARATHI),
    lat: float = Form(18.92),
    lon: float = Form(72.83)
):
    audio_content = await file.read()
    transcription = await speech_service.transcribe_audio_bytes(audio_content, source_lang=language.value)
    
    initial_state = AgentState(
        raw_query=transcription or "Voice Query",
        user_language=language,
        extracted_coords=GeoCoordinates(latitude=lat, longitude=lon)
    )
    
    final_state = await run_orca_orchestrator_pipeline(initial_state)
    
    return {
        "transcription": transcription,
        "localized_advisory": final_state.final_localized_response,
        "audio_payload": final_state.audio_payload,
        "status": final_state.status
    }


# ==========================================
# 5. WEBSOCKET REAL-TIME TELEMETRY STREAM
# ==========================================

@app.websocket("/ws/vessel_telemetry")
async def websocket_vessel_telemetry(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket telemetry connection opened.")
    
    try:
        while True:
            data = await websocket.receive_json()
            lon = data.get("longitude", 72.83)

            is_near_border = lon > 73.5
            
            telemetry_payload = {
                "vessel_id": data.get("vessel_id", "vessel_unknown"),
                "status": "ALERT" if is_near_border else "SAFE",
                "geofence_warning": is_near_border,
                "distance_to_imbl_km": 14.2 if not is_near_border else 2.1,
                "message": "⚠️ APPROACHING MARITIME BORDER LINE!" if is_near_border else "Vessel in safe fishing waters."
            }
            
            await websocket.send_json(telemetry_payload)

    except WebSocketDisconnect:
        logger.info("WebSocket telemetry connection closed.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()