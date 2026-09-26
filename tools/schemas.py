from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ==========================================
# 1. ENUMS & CORE DOMAIN TYPES
# ==========================================

class LanguageCode(str, Enum):
    MARATHI = "mr"
    HINDI = "hi"
    GUJARATI = "gu"
    TAMIL = "ta"
    TELUGU = "te"
    KANNADA = "kn"
    BENGALI = "bn"
    MALAYALAM = "ml"
    ENGLISH = "en"


class PrimaryIntent(str, Enum):
    WEATHER = "WEATHER"
    FISHING = "FISHING"
    NAVIGATION = "NAVIGATION"
    ROUTING = "ROUTING"
    SAFETY = "SAFETY"
    GENERAL = "GENERAL"
    UNKNOWN = "UNKNOWN"
    
    # Aliases mapping back to primary intents
    FISHERY_ADVISORY = "FISHING"
    SAFETY_ALERT = "SAFETY"
    NAVIGATION_BORDER = "NAVIGATION"
    GENERAL_WEATHER = "WEATHER"


class UrgencyLevel(str, Enum):
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PFZConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ==========================================
# 2. SPATIAL & OCEANOGRAPHIC SCHEMAS
# ==========================================

class GeoCoordinates(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees WGS84")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees WGS84")


class BoundingBox(BaseModel):
    min_latitude: float = Field(..., ge=-90.0, le=90.0)
    max_latitude: float = Field(..., ge=-90.0, le=90.0)
    min_longitude: float = Field(..., ge=-180.0, le=180.0)
    max_longitude: float = Field(..., ge=-180.0, le=180.0)


class OceanConditionsInput(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0, description="Target latitude for satellite NetCDF extraction")
    lon: float = Field(..., ge=-180.0, le=180.0, description="Target longitude for satellite NetCDF extraction")


class OceanConditionsOutput(BaseModel):
    latitude: float
    longitude: float
    sea_surface_temperature_celsius: float = Field(..., description="SST from OISST / Oceansat-3 (.nc)")
    chlorophyll_mg_m3: float = Field(..., description="Chlorophyll-a concentration from Oceansat-3")
    potential_fishing_zone: bool = Field(..., description="True if ocean thermal/chlorophyll front is detected")
    pfz_confidence: PFZConfidence
    advisory: str


class SurfaceCurrentsOutput(BaseModel):
    latitude: float
    longitude: float
    u_velocity_ms: float = Field(..., description="Zonal current velocity component (m/s)")
    v_velocity_ms: float = Field(..., description="Meridional current velocity component (m/s)")
    current_speed_knots: float = Field(..., description="Calculated drift speed in knots")
    drift_warning: bool = Field(..., description="Warning active if surface drift > 2.5 knots")


class MarineWeatherForecast(BaseModel):
    latitude: float
    longitude: float
    wave_height_meters: float
    wind_speed_knots: float
    rough_sea_alert: bool
    cyclonic_warning: bool
    source: str = Field(default="IMD / ECMWF Model Cache")


class GeofenceCheckInput(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)


class GeofenceCheckOutput(BaseModel):
    latitude: float
    longitude: float
    inside_prohibited_zone: bool
    zone_name: Optional[str] = None
    distance_to_border_km: float
    boundary_warning: bool
    advisory_action: str


# ==========================================
# 3. MULTILINGUAL & SPEECH SCHEMAS
# ==========================================

class SpeechToTextRequest(BaseModel):
    audio_base64: str = Field(..., description="Base64 encoded audio string from micro UI input")
    source_language: LanguageCode = Field(default=LanguageCode.MARATHI)


class SpeechToTextResponse(BaseModel):
    transcribed_text: str
    detected_language: LanguageCode


class TranslationRequest(BaseModel):
    text: str
    source_lang: LanguageCode
    target_lang: LanguageCode


class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_lang: LanguageCode
    target_lang: LanguageCode


class TextToSpeechResponse(BaseModel):
    target_language: LanguageCode
    localized_text: str
    audio_base64: Optional[str] = Field(None, description="Synthesized Base64 WAV audio for voice playback")


# ==========================================
# 4. GUARDRAILS & INTENT PARSER SCHEMAS
# ==========================================

class GuardrailValidationResult(BaseModel):
    is_safe: bool
    is_distress: bool
    flagged_reason: Optional[str] = None
    action: str = Field(..., description="Action directive: PROCEED, BLOCK_REQUEST, or TRIGGER_EMERGENCY_PROTOCOL")
    clean_query: Optional[str] = None


class NLPMetadata(BaseModel):
    processed_text: str
    parsed_intent: PrimaryIntent
    urgency_level: UrgencyLevel
    extracted_coordinates: Optional[GeoCoordinates] = None
    detected_port: Optional[str] = None
    target_species: List[str] = Field(default_factory=list)


# ==========================================
# 5. FASTAPI / GATEWAY PAYLOAD SCHEMAS
# ==========================================

class UserQueryRequest(BaseModel):
    user_id: str = Field(..., description="Unique vessel or registration ID")
    query_text: Optional[str] = Field(default="Voice Query Input", description="User typed or default voice query text")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    language: LanguageCode = Field(default=LanguageCode.MARATHI)
    raw_audio_base64: Optional[str] = Field(default=None, description="Optional raw base64 encoded voice recording")


class AgentQueryResponse(BaseModel):
    status: str = Field(default="SUCCESS")
    intent: PrimaryIntent
    urgency: UrgencyLevel
    is_emergency: bool = False
    english_advisory: str
    localized_advisory: str
    data_context: Dict[str, Any] = Field(default_factory=dict)
    audio_output_base64: Optional[str] = Field(default=None, description="Base64 encoded localized audio advisory")


class EmergencyAlertResponse(BaseModel):
    status: str = Field(default="EMERGENCY_TRIGGERED")
    urgency: UrgencyLevel = UrgencyLevel.CRITICAL
    alert_message: str
    localized_alert: str
    coast_guard_notified: bool = True
    audio_output_base64: Optional[str] = None


# ==========================================
# 6. LANGGRAPH AGENT STATE SCHEMAS
# ==========================================

class AgentState(BaseModel):
    """
    Typed State schema passed across all LangGraph orchestration nodes.
    """
    raw_query: str = Field(..., description="Original input query from voice or text")
    user_language: LanguageCode = Field(default=LanguageCode.MARATHI)
    query: str = Field(default="", description="English normalized query for internal sub-agents")
    
    intent: PrimaryIntent = Field(default=PrimaryIntent.UNKNOWN)
    urgency: UrgencyLevel = Field(default=UrgencyLevel.NORMAL)
    extracted_coords: Optional[GeoCoordinates] = None
    
    is_emergency: bool = Field(default=False)
    status: str = Field(default="INIT")
    error: Optional[str] = None
    
    # Sub-agent response outputs
    data_context: Dict[str, Any] = Field(default_factory=dict)
    retrieved_documents: List[Dict[str, Any]] = Field(default_factory=list)
    response: str = Field(default="", description="Generated English response")
    
    # Localized final outputs
    final_localized_response: str = Field(default="")
    audio_payload: Optional[str] = Field(None, description="Base64 Audio payload for UI player")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))