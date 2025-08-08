# leaf_app.py
import os
import json
import requests
import pandas as pd
import geopandas as gpd
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import leafmap.foliumap as leafmap
from streamlit_folium import st_folium

# -------------------------
# Load environment
# -------------------------
load_dotenv(find_dotenv(usecwd=True), override=True)

API_URL = "http://localhost:8000/isochrones"  # FastAPI backend

# -------------------------
# Streamlit page setup
# -------------------------
st.set_page_config(page_title="Isolysis - Leafmap Demo", layout="wide")
st.title("Isolysis – Isochrone Explorer (Leafmap Demo)")

# -------------------------
# Sidebar: settings
# -------------------------
st.sidebar.header("Settings")
provider = st.sidebar.selectbox("Provider", ["mapbox", "iso4app"], index=0)
rho_hours = st.sidebar.number_input(
    "Max time (hours) per centroid", 0.25, 4.0, 1.0, step=0.25
)
interval_hours = st.sidebar.number_input(
    "Band interval (hours)", 0.25, 1.0, 0.25, step=0.25
)

# API key warnings
if provider == "mapbox" and not os.getenv("MAPBOX_API_KEY"):
    st.sidebar.error("Missing MAPBOX_API_KEY in environment.")
if provider == "iso4app" and not os.getenv("ISO4APP_API_KEY"):
    st.sidebar.error("Missing ISO4APP_API_KEY in environment.")

# -------------------------
# Optional upload of coords
# -------------------------
uploaded_file = st.sidebar.file_uploader("Upload coords.json (optional)", type="json")
if uploaded_file:
    raw_points = json.load(uploaded_file)
elif os.path.exists("data/coords.json"):
    with open("data/coords.json", encoding="utf-8") as f:
        raw_points = json.load(f)
else:
    raw_points = []
    st.warning("No points loaded. You can still add centroids.")

points_df = (
    pd.DataFrame(raw_points) if raw_points else pd.DataFrame(columns=["lat", "lon"])
)
if not points_df.empty:
    points_gdf = gpd.GeoDataFrame(
        points_df,
        geometry=gpd.points_from_xy(points_df.lon, points_df.lat),
        crs="EPSG:4326",
    )

# -------------------------
# Session state
# -------------------------
if "centroids" not in st.session_state:
    st.session_state.centroids = []
if "iso_polygons" not in st.session_state:
    st.session_state.iso_polygons = []


def add_centroid(lat, lon, rho):
    cid = f"hub{len(st.session_state.centroids) + 1}"
    st.session_state.centroids.append(
        {"id": cid, "lat": float(lat), "lon": float(lon), "rho": float(rho)}
    )


def clear_last():
    if st.session_state.centroids:
        st.session_state.centroids.pop()


def clear_all():
    st.session_state.centroids = []
    st.session_state.iso_polygons = []


st.sidebar.subheader("Centroids")
st.sidebar.write(f"Selected: {len(st.session_state.centroids)}")
colA, colB = st.sidebar.columns(2)
colA.button("Undo last", on_click=clear_last, use_container_width=True)
colB.button("Clear all", on_click=clear_all, use_container_width=True)

# -------------------------
# Leafmap
# -------------------------
center_lat = float(points_df["lat"].mean()) if not points_df.empty else 13.7
center_lon = float(points_df["lon"].mean()) if not points_df.empty else -89.2
m = leafmap.Map(center=[center_lat, center_lon], zoom=9)

# Plot health unit points (dots, no popup overload)
if not points_df.empty:
    m.add_points_from_xy(
        points_df,
        x="lon",
        y="lat",
        color_column=None,
        layer_name="Health Units",
        icon_names=None,
        spin=False,
        add_legend=False,
    )

# Plot existing centroids
for c in st.session_state.centroids:
    m.add_marker(location=[c["lat"], c["lon"]], popup=f'{c["id"]} (ρ={c["rho"]}h)')

# Plot isochrone polygons if available
if st.session_state.iso_polygons:
    for poly in st.session_state.iso_polygons:
        m.add_geojson(poly, layer_name=f"{poly['properties'].get('id', 'iso')}")

# Render map and capture click
map_state = st_folium(m, height=600, width=None)
if map_state and map_state.get("last_clicked"):
    lat = map_state["last_clicked"]["lat"]
    lon = map_state["last_clicked"]["lng"]
    if st.button(f"Add centroid at ({lat:.5f}, {lon:.5f}) with ρ={rho_hours}h"):
        add_centroid(lat, lon, rho_hours)

# -------------------------
# Compute button
# -------------------------
if st.button("Compute Isochrones", type="primary", use_container_width=True):
    if not st.session_state.centroids:
        st.error("Add at least one centroid first.")
    else:
        payload = {
            "coordinates": raw_points,
            "centroids": st.session_state.centroids,
            "provider": provider,
            "interval": interval_hours,
            "travel_speed_kph": 30,
        }
        with st.spinner("Requesting API..."):
            resp = requests.post(f"{API_URL}", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.iso_polygons = data.get("isochrones", [])
            st.success("Results ready. Polygons will appear on the map above.")
        else:
            st.error(f"API error: {resp.text}")

# -------------------------
# Download buttons
# -------------------------
if st.session_state.iso_polygons:
    st.download_button(
        "Download isochrones JSON",
        data=json.dumps(st.session_state.iso_polygons, indent=2),
        file_name=f"{provider}_isochrones.json",
        mime="application/json",
        use_container_width=True,
    )
