import io
import hashlib
import streamlit as st
from typing import Dict, Any, Optional, Tuple

# Supported Indic languages for ORCA speech recognition pipeline
LANGUAGE_OPTIONS = {
    "mr": "मराठी (Marathi)",
    "hi": "हिन्दी (Hindi)",
    "gu": "ગુજરાતી (Gujarati)",
    "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "bn": "বাংলা (Bengali)",
    "ml": "മലയാളം (Malayalam)",
    "en": "English"
}


def render_audio_recorder() -> Tuple[Optional[bytes], str]:
    """
    Renders an advanced voice recording interface for the ORCA Streamlit UI.
    Returns a tuple of (raw_audio_bytes, selected_language_code).
    """
    st.markdown("### 🎙️ ORCA Voice Advisory Interface")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_lang = st.selectbox(
            "Select Native Language",
            options=list(LANGUAGE_OPTIONS.keys()),
            format_func=lambda code: LANGUAGE_OPTIONS[code],
            index=0,
            help="Select language for ASR Speech Recognition & Bhashini Voice Advisory."
        )

    with col2:
        st.caption("Click the microphone icon to record your query (e.g. Weather, Fishing Zones, Coastal Borders).")
        # Native Streamlit audio input recorder
        recorded_audio = st.audio_input("Record Indic Voice Query")

    if recorded_audio is not None:
        # Read byte content from UploadedFile / BytesIO stream
        audio_bytes = recorded_audio.read()
        
        # Generate hash to prevent duplicated pipeline execution on Streamlit rerenders
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        
        # Store metadata in Streamlit Session State
        if st.session_state.get("last_processed_audio_hash") != audio_hash:
            st.session_state["audio_processed"] = False
            st.session_state["current_audio_bytes"] = audio_bytes
            st.session_state["last_processed_audio_hash"] = audio_hash

        st.success("✅ Voice recording captured successfully.")
        
        # Playback Preview & Reset option
        with st.expander("🔊 Audio Preview & Controls", expanded=True):
            st.audio(audio_bytes, format="audio/wav")
            if st.button("🗑️ Clear Recording", key="btn_clear_audio"):
                st.session_state["last_processed_audio_hash"] = None
                st.session_state["current_audio_bytes"] = None
                st.session_state["audio_processed"] = True
                st.rerun()

        return audio_bytes, selected_lang

    return None, selected_lang


def get_audio_recorder_state() -> Dict[str, Any]:
    """
    Utility function to retrieve current voice state across Streamlit pages.
    """
    return {
        "has_audio": st.session_state.get("current_audio_bytes") is not None,
        "audio_bytes": st.session_state.get("current_audio_bytes"),
        "is_processed": st.session_state.get("audio_processed", False)
    }