import streamlit as st

def render_audio_recorder():
    """
    Renders an audio input interface component.
    """
    audio_val = st.audio_input("🎤 Record Indic Voice Query")
    return audio_val