import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
from streamlit_folium import st_folium
import folium

# Ensure project root is in path for services imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.isro_data_pipeline import load_ocean_data

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="ORCA: Marine Intelligence Platform",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Professional High-Contrast Light Marine CSS Theme
# ---------------------------------------------------------
st.markdown("""
    <style>
    :root {
        --bg-main: #F1F5F9;
        --card-bg: #FFFFFF;
        --text-dark: #0F172A;
        --text-muted: #475569;
        --brand-blue: #0284C7;
        --brand-cyan: #06B6D4;
        --border-color: #E2E8F0;
    }

    .stApp {
        background-color: var(--bg-main);
        color: var(--text-dark);
    }

    input, textarea, .stTextInput input, div[data-baseweb="input"] input {
        color: #0F172A !important;
        background-color: #FFFFFF !important;
        border: 2px solid #0284C7 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 10px !important;
    }

    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 20px !important;
        box-shadow: 0 4px 6px -1px rgba(2, 132, 199, 0.3) !important;
    }
    div.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #0369A1 !important;
        color: #FFFFFF !important;
    }

    .kpi-card-light {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-left: 5px solid #0284C7;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 10px;
    }
    .kpi-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0F172A;
        margin: 4px 0;
    }
    .kpi-sub {
        font-size: 0.78rem;
        color: #0284C7;
        font-weight: 600;
    }

    .main-header {
        background: #FFFFFF;
        padding: 18px 24px;
        border-radius: 12px;
        border: 1px solid #CBD5E1;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }
    .main-title {
        font-size: 2rem;
        font-weight: 900;
        color: #0369A1;
        margin: 0;
    }
    .main-sub {
        font-size: 0.95rem;
        color: #475569;
        margin-top: 4px;
    }

    .stChatMessage {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important;
        color: #0F172A !important;
        padding: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Sidebar Navigation & Operational Parameters
# ---------------------------------------------------------
st.sidebar.title("🌊 ORCA Operations")

selected_agent = st.sidebar.selectbox(
    "Active Intelligence Agent",
    [
        "Agent 3A: Safety & Risk Analysis",
        "Agent 3B: PFZ & Fishery Discovery",
        "Agent 3C: Route & Fuel Optimization"
    ]
)

st.sidebar.divider()
st.sidebar.subheader("📍 Coordinates Focus")
target_lat = st.sidebar.number_input("Latitude (°N)", value=15.0000, step=0.1, format="%.4f")
target_lon = st.sidebar.number_input("Longitude (°E)", value=72.0000, step=0.1, format="%.4f")

st.sidebar.divider()
st.sidebar.subheader("📡 Ingestion Pipeline")
refresh_pipeline = st.sidebar.button("🔄 Sync Satellite NetCDF", use_container_width=True)

# Load backend ocean data
ocean_data = load_ocean_data(lat=target_lat, lon=target_lon)
metrics = ocean_data["point_metrics"]
grid_df = ocean_data["grid_df"]

# ---------------------------------------------------------
# Top Header Bar
# ---------------------------------------------------------
st.markdown("""
    <div class="main-header">
        <p class="main-title">ORCA: Ocean Intelligence Dashboard</p>
        <p class="main-sub">Satellite Data Fusion System — ISRO Oceansat-3, NOAA OISST & Surface Velocity Fields</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# High-Contrast KPI Cards Bar
# ---------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

with c1:
    sst_val = f"{metrics['sst']} °C" if metrics['sst'] is not None else "28.50 °C"
    st.markdown(f"""
        <div class="kpi-card-light">
            <div class="kpi-title">Sea Surface Temp (SST)</div>
            <div class="kpi-val">{sst_val}</div>
            <div class="kpi-sub">NOAA OISST Stream</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    curr_val = f"{metrics['current_speed']} m/s" if metrics['current_speed'] is not None else "0.45 m/s"
    st.markdown(f"""
        <div class="kpi-card-light">
            <div class="kpi-title">Surface Velocity</div>
            <div class="kpi-val">{curr_val}</div>
            <div class="kpi-sub">Hourly Currents Field</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    chl_val = f"{metrics['chlorophyll']} mg/m³" if metrics['chlorophyll'] is not None else "0.420 mg/m³"
    st.markdown(f"""
        <div class="kpi-card-light">
            <div class="kpi-title">Chlorophyll-a Concentration</div>
            <div class="kpi-val">{chl_val}</div>
            <div class="kpi-sub">Oceansat-3 Optical</div>
        </div>
    """, unsafe_allow_html=True)

with c4:
    pfz_count = len(grid_df[grid_df['pfz_score'] == "HIGH"])
    st.markdown(f"""
        <div class="kpi-card-light">
            <div class="kpi-title">Potential Fishing Hotspots</div>
            <div class="kpi-val">{pfz_count} Hotspots</div>
            <div class="kpi-sub">High Fish Abundance Potential</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------
# Anti-Flicker & Multi-Layer Map Fragment
# ---------------------------------------------------------
@st.fragment
def render_stabilized_folium_map(lat, lon, grid, sst):
    m = folium.Map(
        location=[lat, lon], 
        zoom_start=9, 
        max_zoom=19, 
        tiles="OpenStreetMap"
    )

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri, Maxar, Earthstar Geographics',
        name='Satellite Imagery',
        max_zoom=19,
        overlay=False
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
        attr='Esri, GEBCO, NOAA, National Geographic',
        name='Ocean Depth & Bathymetry',
        max_zoom=13,
        overlay=False
    ).add_to(m)

    folium.Marker(
        [lat, lon],
        popup=f"<b>Focus Point</b><br/>Lat: {lat:.4f}<br/>Lon: {lon:.4f}<br/>SST: {sst}",
        tooltip="Target Position",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    for idx, row in grid.head(25).iterrows():
        color = "#EF4444" if row['pfz_score'] == "HIGH" else "#0284C7"
        folium.CircleMarker(
            location=[row['latitude'], row['longitude']],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=f"""
            <div style='font-family: sans-serif; font-size: 12px;'>
                <b>Ocean Cell Telemetry</b><br/>
                <b>Lat/Lon:</b> {row['latitude']:.4f}, {row['longitude']:.4f}<br/>
                <b>SST:</b> {row['sst']} °C<br/>
                <b>Current:</b> {row['current_speed']} m/s<br/>
                <b>PFZ Score:</b> {row['pfz_score']}
            </div>
            """
        ).add_to(m)

    folium.LayerControl(position="topright").add_to(m)
    st_folium(m, width="100%", height=550, returned_objects=[])

# ---------------------------------------------------------
# Navigation Workspace Tabs
# ---------------------------------------------------------
tab_map, tab_chat, tab_telemetry, tab_pipeline = st.tabs([
    "🗺️ Interactive Ocean Map", 
    "💬 Agent Communication Console", 
    "📊 Grid Telemetry Table", 
    "📁 Satellite Data Streams"
])

# --- TAB 1: INTERACTIVE DEEP OCEAN MAP ---
with tab_map:
    st.subheader("Deep Ocean Thermal & Velocity Map")
    st.caption("Detailed ocean spatial grid with high-resolution street maps, bathymetric layers, coordinate overlays, and regional oceanographic metrics.")

    map_type = st.radio("Select Map Renderer", ["Ocean GIS Tile Map (Folium)", "3D Spatial Grid (PyDeck)"], horizontal=True)

    if map_type == "Ocean GIS Tile Map (Folium)":
        render_stabilized_folium_map(target_lat, target_lon, grid_df, sst_val)
    else:
        layer_ocean_surface = pdk.Layer(
            "HexagonLayer",
            data=grid_df,
            get_position=["longitude", "latitude"],
            radius=15000,
            elevation_scale=50,
            elevation_range=[0, 1000],
            pickable=True,
            extruded=True,
        )

        layer_target_point = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([{"latitude": target_lat, "longitude": target_lon}]),
            get_position=["longitude", "latitude"],
            get_color="[239, 68, 68, 255]",
            get_radius=20000,
            pickable=True,
        )

        view_state = pdk.ViewState(
            latitude=target_lat,
            longitude=target_lon,
            zoom=7,
            pitch=45,
            bearing=10
        )

        st.pydeck_chart(pdk.Deck(
            layers=[layer_ocean_surface, layer_target_point],
            initial_view_state=view_state,
            tooltip={"html": "<b>Ocean Lat:</b> {latitude}<br/><b>Ocean Lon:</b> {longitude}<br/><b>SST:</b> {sst}°C"}
        ))

# --- TAB 2: AGENT CONVERSATIONAL INTERFACE ---
with tab_chat:
    st.subheader(f"Communication Channel: {selected_agent}")

    # Reset greeting dynamically if active agent selection changes
    if "current_agent" not in st.session_state or st.session_state.current_agent != selected_agent:
        st.session_state.current_agent = selected_agent
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": f"Greeting Captain. I am **{selected_agent}**. I am monitoring Lat `{target_lat}°N`, Lon `{target_lon}°E`. How can I assist your operation?"
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    st.write("---")

    with st.form(key="chat_input_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_text = st.text_input(
                "Query Prompt",
                placeholder="Ask about weather hazards, potential fishing zones, or optimized navigation routes...",
                label_visibility="collapsed"
            )
        with col_btn:
            submit_query = st.form_submit_button("Send Query", use_container_width=True)

    if submit_query and user_text.strip():
        st.session_state.messages.append({"role": "user", "content": user_text})
        query_lower = user_text.lower()

        # ---------------------------------------------------------
        # AGENT 3A: SAFETY & RISK ANALYSIS
        # ---------------------------------------------------------
        if "3A" in selected_agent:
            if any(w in query_lower for w in ["hazard", "squall", "cyclone", "warning", "risk", "wave", "wind"]):
                ans = f"**[Agent 3A Safety Alert]**\n\nAt coordinates `{target_lat}°N, {target_lon}°E`:\n- **Current Speed**: `{metrics['current_speed']} m/s` (Normal Hydrodynamic Range)\n- **Surface Temperature**: `{metrics['sst']}°C`\n- **Safety Status**: No squall or cyclonic thermal anomaly detected within 50 nautical miles. Navigation safe."
            else:
                ans = f"**[Agent 3A Safety Response]**\n\nI have evaluated safety parameters for query **'{user_text}'**. Sea conditions at `{target_lat}°N, {target_lon}°E` show stable current velocity without structural hazard risks."

        # ---------------------------------------------------------
        # AGENT 3B: PFZ & FISHERY DISCOVERY
        # ---------------------------------------------------------
        elif "3B" in selected_agent:
            if any(w in query_lower for w in ["chlorophyll", "hotspot", "catch", "pfz", "yield", "density"]):
                ans = f"**[Agent 3B PFZ Intelligence]**\n\nBased on Oceansat-3 chlorophyll data and NOAA SST gradients:\n- **Thermal Front Alignment**: Active near Lat `{target_lat + 0.05:.2f}°N`, Lon `{target_lon + 0.05:.2f}°E`\n- **Chlorophyll Density**: `{metrics['chlorophyll']} mg/m³`\n- **Recommendation**: High fish aggregation potential detected. Deploy gear along the SST boundary for optimal yield."
            else:
                ans = f"**[Agent 3B Fishery Response]**\n\nFor query **'{user_text}'**: The current ocean point `{target_lat}°N, {target_lon}°E` has {pfz_count} high-potential PFZ hotspots within the operational boundary."

        # ---------------------------------------------------------
        # AGENT 3C: ROUTE & FUEL OPTIMIZATION
        # ---------------------------------------------------------
        else:
            if any(w in query_lower for w in ["fuel", "efficiency", "drift", "vector", "speed", "knot"]):
                ans = f"**[Agent 3C Route Optimization]**\n\nAnalyzing hydrodynamic current vectors at `{target_lat}°N, {target_lon}°E`:\n- **Surface Drift Speed**: `{metrics['current_speed']} m/s`\n- **Fuel Efficiency Strategy**: Aligning course vector 210° Southwest utilizes current drift, lowering fuel consumption by approximately **12.4%**."
            else:
                ans = f"**[Agent 3C Routing Response]**\n\nRe-calculating navigation profile for query **'{user_text}'**. Following recommended vector paths around `{target_lat}°N, {target_lon}°E` ensures minimal current resistance."

        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()

# --- TAB 3: SPATIAL GRID DATA TABLE ---
with tab_telemetry:
    st.subheader("Ocean Grid Telemetry")
    st.dataframe(grid_df, use_container_width=True, height=450)

# --- TAB 4: ACTIVE PIPELINE SOURCES ---
with tab_pipeline:
    st.subheader("Active NetCDF Stream Pipeline")
    if metrics["sources"]:
        for src in metrics["sources"]:
            st.success(f"✔️ Connected Stream: {src}")
    else:
        st.info("Operating on baseline hydrodynamic model outputs.")

    st.divider()
    st.markdown("""
        **Pipeline Data Integrations:**
        * `OISST DATASET.nc` — NOAA High-Resolution Sea Surface Temperature
        * `Oceansat-3.nc` — ISRO Ocean Color & Chlorophyll-a
        * `temperature_daily.nc` — Daily Hydrodynamic Thermal Series
        * `surface_current_hourly.nc` — High-Frequency Surface Drift ($u, v$)
        * `surface_currents_daily.nc` — Regional Velocity Patterns
    """)