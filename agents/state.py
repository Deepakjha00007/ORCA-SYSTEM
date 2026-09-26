from typing import Annotated, Sequence, TypedDict, Optional, Dict, Any
from langchain_core.messages import BaseMessage
import operator

class ORCAMarineState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_id: str
    user_language: str            # e.g., "hi", "mr", "ta", "en"
    raw_audio_base64: Optional[str]
    input_text_english: str
    latitude: Optional[float]
    longitude: Optional[float]
    intent: str                   # "SAFETY", "FISHERY", "NAVIGATION"
    active_agent: str
    tool_results: Dict[str, Any]
    safety_violation: bool
    safety_warnings: list[str]
    final_advisory_english: str
    final_advisory_localized: str
    audio_output_base64: Optional[str]
    geojson_payload: Optional[Dict[str, Any]]