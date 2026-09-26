import os
import logging
from typing import Dict, Any, Optional
from services.bhashini_service import BhashiniNLPService

# Configure Logging
logger = logging.getLogger("ORCA_MultilingualAgent")

class MultilingualAgent:
    """
    Multilingual Interface Agent for ORCA system architecture.
    Handles Indic speech processing (ASR), English cross-translation (NMT), 
    and localized voice output synthesis (TTS).
    """
    def __init__(self):
        self.bhashini = BhashiniNLPService()
        # ISO-639-1 / Bhashini language code mappings
        self.supported_languages = {
            "hi": "Hindi",
            "mr": "Marathi",
            "gu": "Gujarati",
            "ta": "Tamil",
            "te": "Telugu",
            "kn": "Kannada",
            "bn": "Bengali",
            "ml": "Malayalam",
            "or": "Odia",
            "en": "English"
        }

    def _normalize_language_code(self, lang_input: Any) -> str:
        """Helper to extract raw string code from string or enum instance."""
        if hasattr(lang_input, "value"):
            lang_str = str(lang_input.value)
        else:
            lang_str = str(lang_input)
            
        lang_clean = lang_str.lower().strip()
        if lang_clean not in self.supported_languages:
            return "mr"  # Default to Marathi for Maharashtra coastal belt
        return lang_clean

    async def process_incoming_query(self, user_input: str, source_lang: Any = "mr") -> Dict[str, str]:
        """
        Translates user input (text or audio transcription) from regional Indic language to English
        for processing by ORCA Router & Sub-Agents.
        """
        clean_lang = self._normalize_language_code(source_lang)

        if not user_input:
            return {
                "original_query": "",
                "english_query": "",
                "detected_language": clean_lang
            }

        if clean_lang == "en":
            return {
                "original_query": user_input,
                "english_query": user_input,
                "detected_language": "en"
            }

        logger.info(f"Translating query from {self.supported_languages.get(clean_lang)} to English...")
        
        # Support both async and sync Bhashini service implementations
        if hasattr(self.bhashini, "translate_indic_to_english"):
            if callable(getattr(self.bhashini, "translate_indic_to_english")):
                import inspect
                if inspect.iscoroutinefunction(self.bhashini.translate_indic_to_english):
                    english_text = await self.bhashini.translate_indic_to_english(user_input, source_lang=clean_lang)
                else:
                    english_text = self.bhashini.translate_indic_to_english(user_input, source_lang=clean_lang)
        elif hasattr(self.bhashini, "translate_text"):
            english_text = await self.bhashini.translate_text(text=user_input, source_lang=clean_lang, target_lang="en")
        else:
            english_text = user_input

        return {
            "original_query": user_input,
            "english_query": english_text or user_input,
            "detected_language": clean_lang
        }

    async def format_final_advisory(self, english_advisory: str, target_lang: Any = "mr", generate_audio: bool = True) -> Dict[str, Any]:
        """
        Translates generated English agent advisory into the fisherman's native Indic language 
        and synthesizes Base64 WAV audio for voice playback.
        """
        clean_lang = self._normalize_language_code(target_lang)

        if not english_advisory:
            return {
                "target_language": clean_lang,
                "language_name": self.supported_languages.get(clean_lang, "Marathi"),
                "localized_text": "",
                "audio_base64": None
            }

        if clean_lang == "en":
            localized_text = english_advisory
        else:
            logger.info(f"Translating response to {self.supported_languages.get(clean_lang)}...")
            
            if hasattr(self.bhashini, "translate_english_to_indic"):
                import inspect
                if inspect.iscoroutinefunction(self.bhashini.translate_english_to_indic):
                    localized_text = await self.bhashini.translate_english_to_indic(english_advisory, target_lang=clean_lang)
                else:
                    localized_text = self.bhashini.translate_english_to_indic(english_advisory, target_lang=clean_lang)
            elif hasattr(self.bhashini, "translate_text"):
                localized_text = await self.bhashini.translate_text(text=english_advisory, source_lang="en", target_lang=clean_lang)
            else:
                localized_text = english_advisory

        audio_payload = None
        if generate_audio and localized_text:
            logger.info(f"Generating Audio TTS in {self.supported_languages.get(clean_lang)}...")
            
            if hasattr(self.bhashini, "text_to_speech"):
                import inspect
                if inspect.iscoroutinefunction(self.bhashini.text_to_speech):
                    audio_payload = await self.bhashini.text_to_speech(localized_text, target_lang=clean_lang)
                else:
                    audio_payload = self.bhashini.text_to_speech(localized_text, target_lang=clean_lang)
            elif hasattr(self.bhashini, "generate_speech"):
                audio_payload = await self.bhashini.generate_speech(text=localized_text, target_lang=clean_lang)

        return {
            "target_language": clean_lang,
            "language_name": self.supported_languages.get(clean_lang, "Marathi"),
            "localized_text": localized_text or english_advisory,
            "audio_base64": audio_payload
        }


# ==========================================
# ASYNC GRAPH NODE INTEGRATION HELPERS
# ==========================================

async def multilingual_input_node(state: Dict[str, Any]) -> Dict[str, Any]:
    agent = MultilingualAgent()
    raw_query = state.get("raw_query", "")
    user_lang = state.get("user_language", "mr")

    processed = await agent.process_incoming_query(raw_query, source_lang=user_lang)

    return {
        **state,
        "query": processed["english_query"],
        "user_language": processed["detected_language"]
    }


async def multilingual_output_node(state: Dict[str, Any]) -> Dict[str, Any]:
    agent = MultilingualAgent()
    english_response = state.get("response", "")
    user_lang = state.get("user_language", "mr")

    output = await agent.format_final_advisory(english_response, target_lang=user_lang, generate_audio=True)

    return {
        **state,
        "final_localized_response": output["localized_text"],
        "audio_payload": output["audio_base64"]
    }