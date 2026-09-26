import sys
import os
import io
import base64
import requests
import pandas as pd
import pydeck as pdk
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# Add project root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Load local environment configurations (Ollama & Gateway)
load_dotenv(ROOT_DIR / ".env")

# Import UI Components & Schemas
from UI.components.audio_recorder import render_audio_recorder
from tools.schemas import LanguageCode, PrimaryIntent, UrgencyLevel

# Gateway & Local LLM Endpoint Configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ==========================================
# 1. PAGE CONFIGURATION & LIGHT THEME STYLING
# ==========================================

st.set_page_config(
    page_title="ORCA: Marine Agentic Intelligence Platform",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# High-contrast Light Theme CSS
st.markdown("""
<style>
    /* Main Light Background */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }
    
    /* Light Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f1f5f9 !important;
        border-right: 1px solid #cbd5e1 !important;
    }

    /* Input Fields & Text Areas */
    input, textarea, div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
    }
    
    /* Typography Visibility & High Contrast */
    label, .stTextInput label, .stNumberInput label, .stSelectbox label, h1, h2, h3, h4, p, span, li, div {
        color: #0f172a !important;
    }

    /* High-Contrast Chat Message Containers */
    [data-testid="stChatMessage"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 10px !important;
        color: #0f172a !important;
        margin-bottom: 12px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }

    /* Chat Text Markdown High Visibility Override */
    [data-testid="stChatMessage"] p, 
    [data-testid="stChatMessage"] li, 
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {
        color: #0f172a !important;
        font-weight: 500 !important;
    }

    /* Fixed Bottom Chat Input Bar */
    [data-testid="stChatInput"] {
        background-color: #ffffff !important;
        border: 1px solid #0284c7 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.15) !important;
    }

    [data-testid="stChatInput"] textarea {
        color: #0f172a !important;
        background-color: #ffffff !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #64748b !important;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #ffffff;
        border-radius: 8px;
        padding: 14px;
        border: 1px solid #cbd5e1;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Custom Ocean Blue Primary Buttons */
    .stButton>button {
        background-color: #0284c7 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-radius: 6px !important;
        border: none !important;
        width: 100% !important;
        padding: 10px !important;
    }
    
    .stButton>button:hover {
        background-color: #0369a1 !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. SIDEBAR TELEMETRY & VESSEL PROFILE
# ==========================================

with st.sidebar:
    st.image("https://img.icons8.com/color/96/anchor.png", width=56)
    st.title("ORCA Vessel Gateway")
    st.caption("Offline-First Marine Safety & Intelligence System")
    
    st.divider()
    
    st.subheader("📍 Vessel GPS Telemetry")
    user_id = st.text_input("Vessel Registration / ID", value="MH_MUMBAI_01")
    vessel_lat = st.number_input("Latitude (°N)", value=18.92, format="%.4f")
    vessel_lon = st.number_input("Longitude (°E)", value=72.83, format="%.4f")
    
    st.divider()
    
    st.subheader("🖥️ Local Engine Health")
    
    # Check local Gateway connectivity
    try:
        gw_check = requests.get(f"{GATEWAY_URL}/", timeout=1)
        gateway_online = gw_check.status_code == 200
    except Exception:
        gateway_online = False

    # Check local Ollama connectivity
    try:
        ollama_check = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1)
        ollama_online = ollama_check.status_code == 200
    except Exception:
        ollama_online = False

    col_h1, col_h2 = st.columns(2)
    col_h1.metric("FastAPI Gateway", "Online" if gateway_online else "Offline", delta="Port 8000" if gateway_online else "ERR")
    col_h2.metric("Ollama LLM", "Active" if ollama_online else "Offline", delta="Local 11434" if ollama_online else "ERR")

    st.divider()
    st.info("💡 **Local Ollama Mode Active**: All LLM processing, translation, and agent orchestration run 100% on-device/offline.")


# ==========================================
# 3. DASHBOARD MAIN HEADER & SPATIAL MAP
# ==========================================

st.title("🌊 ORCA Ocean Intelligence Platform")
st.markdown("Real-Time Multilingual Marine Navigation, Weather, and Fishery Intelligence Engine")

# Map Visualization
map_df = pd.DataFrame({
    "lat": [vessel_lat, vessel_lat + 0.03, vessel_lat - 0.04, vessel_lat + 0.08],
    "lon": [vessel_lon, vessel_lon - 0.03, vessel_lon + 0.02, vessel_lon - 0.08],
    "label": [
        "Your Vessel Location", 
        "PFZ Hotspot #1 (High Chlorophyll)", 
        "PFZ Hotspot #2 (Thermal Front)", 
        "Hazard/IMBL Warning Boundary Zone"
    ]
})

deck_layer = pdk.Layer(
    "ScatterplotLayer",
    data=map_df,
    get_position="[lon, lat]",
    get_fill_color="[2, 132, 199, 255]",
    get_radius=150,
    radius_min_pixels=6,
    radius_max_pixels=10,
    pickable=True
)

view_state = pdk.ViewState(
    latitude=vessel_lat,
    longitude=vessel_lon,
    zoom=9.5,
    pitch=0
)

col_map, col_env = st.columns([2.2, 1])

with col_map:
    st.pydeck_chart(
        pdk.Deck(
            layers=[deck_layer],
            initial_view_state=view_state,
            tooltip={"text": "{label}\nLat: {lat}, Lon: {lon}"}
        )
    )

with col_env:
    st.markdown("### 🛰️ Live Ocean Metrics")
    
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Sea Surface Temp (SST)", "28.5 °C", delta="-0.2 °C (Front Detected)")
    st.markdown('</div><br>', unsafe_allow_html=True)
    
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Chlorophyll-a Conc.", "2.14 mg/m³", delta="+0.41 mg/m³ (High Density)")
    st.markdown('</div><br>', unsafe_allow_html=True)
    
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Surface Drift Speed", "1.4 Knots", delta="240° SW Drift Vector")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()


# ==========================================
# 4. MULTILINGUAL VOICE & CHAT INTERFACE
# ==========================================

st.subheader("🎙️ Multilingual Indic Advisory Request")

# Render Voice Recording Widget
audio_bytes, selected_lang = render_audio_recorder()

# Helper Function to Process API Payload
def process_query_payload(text_input, audio_data=None):
    payload = {
        "user_id": user_id,
        "query_text": text_input if text_input else "Voice Query Input",
        "latitude": vessel_lat,
        "longitude": vessel_lon,
        "language": selected_lang.value if hasattr(selected_lang, "value") else str(selected_lang),
        "raw_audio_base64": base64.b64encode(audio_data).decode("utf-8") if audio_data else None
    }
    
    try:
        response = requests.post(f"{GATEWAY_URL}/query", json=payload, timeout=180)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Gateway Error [{response.status_code}]: {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Could not connect to local ORCA Gateway. Ensure `uvicorn main:app --reload` is running on port 8000.")
        return None
    except requests.exceptions.Timeout:
        st.error("⏰ Request timed out waiting for local multi-agent graph execution.")
        return None

# Process Voice Input Button
if st.button("🚀 Process Voice Input"):
    if not audio_bytes:
        st.warning("⚠️ Please record voice audio before clicking this button.")
    else:
        with st.spinner("⚡ Processing audio advisory query..."):
            res_data = process_query_payload("Voice Advisory Query", audio_data=audio_bytes)
            if res_data:
                is_emergency = res_data.get("is_emergency") or res_data.get("urgency") == UrgencyLevel.CRITICAL.value
                localized = res_data.get("localized_advisory", "")
                english = res_data.get("english_advisory", "")
                intent = res_data.get("intent", "ADVISORY")
                
                advisory_text = localized if localized else english
                reply_text = f"🚨 **CRITICAL MARITIME SAFETY ALERT**\n\n{advisory_text}" if is_emergency else f"📢 **Voice Advisory Response ({intent})**\n\n{advisory_text}"

                st.session_state.messages.append({"role": "user", "content": "🎙️ [Voice Input Query Recorded]"})
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": reply_text,
                    "audio_base64": res_data.get("audio_output_base64")
                })

st.divider()
st.subheader("💬 Interactive Advisory Chat")

# Initialize Chat Message History in Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render Chat History ONCE
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("audio_base64"):
            st.audio(base64.b64decode(msg["audio_base64"]), format="audio/wav")

# Single Chat Input Block
if chat_input := st.chat_input("Ask ORCA about weather, fishing zones, or navigation..."):
    # 1. Store user prompt
    st.session_state.messages.append({"role": "user", "content": chat_input})
    
    # 2. Render user prompt immediately
    with st.chat_message("user"):
        st.markdown(chat_input)

    # 3. Request assistant output & render ONCE
    with st.chat_message("assistant"):
        with st.spinner("⚡ Executing local multi-agent workflow..."):
            res_data = process_query_payload(chat_input, audio_data=None)
            
            if res_data:
                is_emergency = res_data.get("is_emergency") or res_data.get("urgency") == UrgencyLevel.CRITICAL.value
                localized = res_data.get("localized_advisory", "")
                english = res_data.get("english_advisory", "")
                intent = res_data.get("intent", "ADVISORY")
                
                # Deduplicate response text if backend concatenated it
                advisory_text = localized if localized else english
                if advisory_text.count("Commercial Fishing Dispatch Report") > 1:
                    advisory_text = advisory_text.split("Commercial Fishing Dispatch Report")[-1]
                    advisory_text = "Commercial Fishing Dispatch Report" + advisory_text

                reply_text = f"🚨 **CRITICAL MARITIME SAFETY ALERT**\n\n{advisory_text}" if is_emergency else f"📢 **Local Advisory Response ({intent})**\n\n{advisory_text}"

                # Render output directly inside assistant block
                st.markdown(reply_text)
                
                if res_data.get("audio_output_base64"):
                    audio_out = base64.b64decode(res_data["audio_output_base64"])
                    st.audio(audio_out, format="audio/wav")

                # Store response in session state without rerun
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply_text,
                    "audio_base64": res_data.get("audio_output_base64")
                })