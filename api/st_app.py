# st_app.py
import os
import json
import requests
import geopandas as gpd
import pandas as pd
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import folium
from streamlit_folium import st_folium

from isolysis.io import IsoRequest, Centroid, Coordinate


# -------------------------
# ENV + CONFIG
# -------------------------
load_dotenv(find_dotenv(usecwd=True), override=True)

MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
ISO4APP_API_KEY = os.getenv("ISO4APP_API_KEY")
API_URL = "http://localhost:8000/isochrones"

st.set_page_config(page_title="Isolysis - Isochrone Explorer", layout="wide")

# -------------------------
# SIDEBAR CONTROLS
# -------------------------
st.sidebar.header("Settings")

provider = st.sidebar.selectbox(
    "Provider", options=["mapbox", "iso4app"], index=0, help="OSMnx disabled for now."
)

rho_hours = st.sidebar.number_input(
    "Max time (hours) per centroid (rho)",
    min_value=0.25,
    max_value=4.0,
    value=1.0,
    step=0.25,
)
interval_hours = st.sidebar.number_input(
    "Band interval (hours)", min_value=0.25, max_value=1.0, value=0.25, step=0.25
)

if provider == "mapbox" and not MAPBOX_API_KEY:
    st.sidebar.error("Missing MAPBOX_API_KEY in environment.")
if provider == "iso4app" and not ISO4APP_API_KEY:
    st.sidebar.error("Missing ISO4APP_API_KEY in environment.")

# -------------------------
# LOAD POINTS
# -------------------------
points_path = "data/coords.json"
if not os.path.exists(points_path):
    st.warning("No data/coords.json found.")
    st.stop()

with open(points_path, encoding="utf-8") as f:
    raw_points = json.load(f)

try:
    coordinates = [Coordinate(**p) for p in raw_points]
except Exception as e:
    st.error(f"Failed to parse coords.json: {e}")
    st.stop()

points_df = pd.DataFrame([c.model_dump() for c in coordinates])
points_gdf = gpd.GeoDataFrame(
    points_df,
    geometry=gpd.points_from_xy(points_df.lon, points_df.lat),
    crs="EPSG:4326",
)

# -------------------------
# SESSION STATE
# -------------------------
if "centroids" not in st.session_state:
    st.session_state.centroids = []
if "last_click" not in st.session_state:
    st.session_state.last_click = None
if "iso_geojson" not in st.session_state:
    st.session_state.iso_geojson = None
if "coverage_json" not in st.session_state:
    st.session_state.coverage_json = None


def add_centroid(lat, lon, rho):
    new_id = f"hub{len(st.session_state.centroids) + 1}"
    st.session_state.centroids.append(
        {"id": new_id, "lat": float(lat), "lon": float(lon), "rho": float(rho)}
    )


def clear_last():
    if st.session_state.centroids:
        st.session_state.centroids.pop()


def clear_all():
    st.session_state.centroids = []


# -------------------------
# COLOR HELPER
# -------------------------
def _color_for_band(band, min_b, max_b):
    span = max(max_b - min_b, 1e-9)
    t = (band - min_b) / span
    palette = ["#440154", "#31688e", "#35b779", "#fde725"]
    idx = min(int(t * (len(palette) - 1)), len(palette) - 1)
    return palette[idx]


# -------------------------
# MAP RENDERER
# -------------------------
def render_map(container, points_df):
    center_lat = float(points_df["lat"].mean()) if len(points_df) else 13.7
    center_lon = float(points_df["lon"].mean()) if len(points_df) else -89.2

    m = folium.Map(
        location=[center_lat, center_lon], zoom_start=9, tiles="CartoDB Positron"
    )

    # health units
    for _, row in points_df.iterrows():
        folium.CircleMarker(
            [row["lat"], row["lon"]],
            radius=2,
            weight=1,
            color="#444",
            fill=True,
            fill_opacity=0.6,
        ).add_to(m)

    # centroids
    for c in st.session_state.centroids:
        folium.Marker(
            [c["lat"], c["lon"]],
            tooltip=f'{c["id"]} (ρ={c["rho"]}h)',
            icon=folium.Icon(color="green", icon="plus"),
        ).add_to(m)

    # polygons
    if st.session_state.iso_geojson:
        fc = st.session_state.iso_geojson
        bands = [
            float(f.get("properties", {}).get("band_hours"))
            for f in fc.get("features", [])
            if f.get("properties", {}).get("band_hours") is not None
        ]
        min_b, max_b = (min(bands), max(bands)) if bands else (0.0, 1.0)

        feats_sorted = sorted(
            fc.get("features", []),
            key=lambda f: float(f.get("properties", {}).get("band_hours", 0.0)),
        )
        for feat in feats_sorted:
            band = float(feat.get("properties", {}).get("band_hours", 0.0))
            color = _color_for_band(band, min_b, max_b)
            label = feat.get("properties", {}).get("label", f"band {band}h")
            gj = folium.GeoJson(
                data=feat,
                style_function=lambda _, c=color: {
                    "fillColor": c,
                    "color": "black",
                    "weight": 1,
                    "fillOpacity": 0.35,
                },
                name=label,
            )
            folium.Tooltip(label).add_to(gj)
            gj.add_to(m)
        folium.LayerControl().add_to(m)

    m.add_child(folium.LatLngPopup())
    return st_folium(m, height=520, width=None, key="main_map")


# -------------------------
# SIDEBAR BUTTONS
# -------------------------
st.sidebar.markdown("### Centroids")
st.sidebar.write(f"Selected: {len(st.session_state.centroids)}")
colA, colB = st.sidebar.columns(2)
colA.button("Undo last", on_click=clear_last, use_container_width=True)
colB.button("Clear all", on_click=clear_all, use_container_width=True)

# -------------------------
# MAIN UI
# -------------------------
st.markdown("### Click on map to add centroids")

map_container = st.container()
map_state = render_map(map_container, points_df)

# Map click capture
if map_state and map_state.get("last_clicked"):
    st.session_state.last_click = (
        map_state["last_clicked"]["lat"],
        map_state["last_clicked"]["lng"],
    )

if st.session_state.last_click:
    lat, lon = st.session_state.last_click
    if st.button(
        f"Add centroid ({lat:.5f}, {lon:.5f}) @ ρ={rho_hours}h",
        use_container_width=True,
    ):
        add_centroid(lat, lon, rho_hours)
        # map_container.empty()
        render_map(map_container, points_df)

# Show table of centroids
if st.session_state.centroids:
    st.write("Current centroids:")
    st.table(pd.DataFrame(st.session_state.centroids))

st.markdown("---")


# -------------------------
# API CALL
# -------------------------
def api_compute(payload):
    r = requests.post(API_URL, json=payload)
    r.raise_for_status()
    return r.json()


if st.button("Compute Isochrones", type="primary", use_container_width=True):
    if not st.session_state.centroids:
        st.error("Add at least one centroid.")
    else:
        req = IsoRequest(
            coordinates=[Coordinate(**r) for r in points_df.to_dict(orient="records")],
            centroids=[Centroid(**c) for c in st.session_state.centroids],
        )
        options = {
            "provider": provider,
            "interval": interval_hours,
            "travel_speed_kph": 30,
        }
        payload = {"isorequest": req.model_dump(), "options": options}

        with st.spinner("Calling API…"):
            try:
                resp = api_compute(payload)
            except Exception as e:
                st.error(f"API error: {e}")
                resp = None

        if resp:
            st.session_state.coverage_json = resp.get("coverage", {})
            st.session_state.iso_geojson = resp.get("polygons_geojson")

            # redraw instantly
            map_container.empty()
            render_map(map_container, points_df)

            st.success("Results ready. Polygons have been added to the map.")

# -------------------------
# REPORT + DOWNLOADS
# -------------------------
st.markdown("### Report")
if st.session_state.coverage_json:
    with st.expander("Coverage summary (JSON)"):
        st.json(st.session_state.coverage_json)

    st.download_button(
        "Download coverage JSON",
        data=json.dumps(st.session_state.coverage_json, indent=2),
        file_name=f"{provider}_isochrone_coverage.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.session_state.iso_geojson:
        st.download_button(
            "Download isochrones as GeoJSON",
            data=json.dumps(st.session_state.iso_geojson),
            file_name=f"{provider}_isochrones.geojson",
            mime="application/geo+json",
            use_container_width=True,
        )

# -------------------------
# CLEAR RESULTS
# -------------------------
if st.button("Clear results", type="secondary"):
    st.session_state.iso_geojson = None
    st.session_state.coverage_json = None
    map_container.empty()
    render_map(map_container, points_df)
