import os
import json
import rasterio
import tempfile
import streamlit as st
import folium as fl
from streamlit_folium import st_folium
from dotenv import find_dotenv, load_dotenv

from api.utils import (
    call_api,
    format_time_display,
    get_map_center,
    get_band_color,
    get_pos,
)

# ---------------------------
# ENV + CONFIG
# ---------------------------
load_dotenv(find_dotenv(usecwd=True), override=False)

MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
ISO4APP_API_KEY = os.getenv("ISO4APP_API_KEY")

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
ISOCHRONES_ENDPOINT = f"{API_URL}/isochrones"
RASTER_STATS_ENDPOINT = f"{API_URL}/raster-stats"

st.set_page_config(page_title="📈 Iso-Raster Analysis", layout="wide")


# ---------------------------
# CACHED HELPERS
# ---------------------------
@st.cache_data
def create_base_map():
    m = fl.Map(location=[13.7942, -88.8965], zoom_start=9, tiles="CartoDB positron")
    m.add_child(fl.LatLngPopup())
    return m


@st.cache_data
def save_uploaded_file(uploaded_file):
    """Save raster to a temp file and return its path"""
    suffix = os.path.splitext(uploaded_file.name)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name


@st.cache_data
def get_raster_center(raster_path: str):
    """Return (lat, lon) center coordinates of a raster file."""
    try:
        with rasterio.open(raster_path) as src:
            bounds = src.bounds
            lon_center = (bounds.left + bounds.right) / 2
            lat_center = (bounds.top + bounds.bottom) / 2
            return lat_center, lon_center
    except Exception as e:
        st.warning(f"⚠️ Could not read raster center: {e}")
        return None


def add_raster_to_map(m, raster_path, layer_name="Raster Overlay", opacity=0.7):
    """Overlay a raster on the folium map with transparency for nodata / zeros."""
    import rasterio
    import numpy as np
    import matplotlib.pyplot as plt
    from PIL import Image
    import base64
    from io import BytesIO
    import folium

    try:
        with rasterio.open(raster_path) as src:
            data = src.read(1)
            bounds = src.bounds

            # Mask out no-data and zeros
            if src.nodata is not None:
                mask = data == src.nodata
            else:
                mask = data <= 0  # treat 0 and negatives as empty

            data = np.where(mask, np.nan, data)

            # Normalize only non-NaN values
            vmin, vmax = np.nanmin(data), np.nanmax(data)
            norm = plt.Normalize(vmin=vmin, vmax=vmax)

            cmap = plt.get_cmap("viridis")
            rgba_img = cmap(norm(data))

            # Make masked/NaN values fully transparent
            rgba_img[..., 3] = np.where(np.isnan(data), 0, 1)

            rgb_img = (rgba_img[:, :, :3] * 255).astype(np.uint8)
            alpha = (rgba_img[:, :, 3] * 255).astype(np.uint8)
            rgba_8bit = np.dstack((rgb_img, alpha))

            # Convert to PNG
            img = Image.fromarray(rgba_8bit)
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

            # Map bounds
            bounds_sw = [bounds.bottom, bounds.left]
            bounds_ne = [bounds.top, bounds.right]

            folium.raster_layers.ImageOverlay(
                image=f"data:image/png;base64,{b64_img}",
                bounds=[bounds_sw, bounds_ne],
                opacity=opacity,
                name=layer_name,
                interactive=True,
                cross_origin=False,
                zindex=1,
            ).add_to(m)

    except Exception as e:
        st.warning(f"⚠️ Could not render raster overlay: {e}")


# ---------------------------
# SIDEBAR
# ---------------------------
def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Iso-Raster Settings")

        # Travel time (rho)
        rho = st.slider(
            "Travel Time (hours)",
            min_value=0.5,
            max_value=10.0,
            value=1.0,
            step=0.5,
            help="Maximum travel time for each centroid.",
        )

        # Iso4App-specific options
        iso_type = st.selectbox(
            "Isoline Type",
            ["isochrone", "isodistance"],
            index=0,
            help="Compute by travel time (isochrone) or distance (isodistance)",
        )
        mobility = st.selectbox(
            "Travel Mode",
            ["motor_vehicle", "bicycle", "pedestrian"],
            index=0,
        )
        speed_type = st.selectbox(
            "Speed Profile",
            ["very_low", "low", "normal", "fast"],
            index=2,
        )
        speed_limit = st.number_input(
            "Maximum Speed (km/h)",
            min_value=10.0,
            max_value=200.0,
            value=50.0,
            step=5.0,
            help="Optional: maximum speed used for Iso4App isochrones",
        )

        # Colormap
        colormap = st.selectbox(
            "Color Scheme",
            ["viridis", "plasma", "magma", "inferno", "cividis", "Reds", "Blues"],
            index=0,
        )

        # Raster upload
        uploaded_rasters = st.file_uploader(
            "📂 Upload Raster(s) (.tif)",
            type=["tif", "tiff"],
            accept_multiple_files=True,
        )

        # Store selections
        st.session_state.rho = rho
        st.session_state.colormap = colormap
        st.session_state.uploaded_rasters = uploaded_rasters
        st.session_state.iso4app_type = iso_type
        st.session_state.iso4app_mobility = mobility
        st.session_state.iso4app_speed_type = speed_type
        st.session_state.iso4app_speed_limit = speed_limit

        if uploaded_rasters:
            st.success(f"✅ Loaded {len(uploaded_rasters)} raster(s)")

            # Zoom map to center of first uploaded raster
            first_raster = uploaded_rasters[0]
            temp_path = save_uploaded_file(first_raster)
            center = get_raster_center(temp_path)

            if center:
                st.session_state.coord_center = center
                st.info(f"📍 Centered map on raster ({center[0]:.4f}, {center[1]:.4f})")

    return rho, colormap


# ---------------------------
# ISOCHRONE LOGIC
# ---------------------------
def process_isochrone(center_name, lat, lon, rho):
    payload = {
        "centroids": [{"lat": lat, "lon": lon, "rho": rho, "id": center_name}],
        "options": {
            "provider": "iso4app",
            "travel_speed_kph": 25,
            "num_bands": 1,
            "iso4app_type": st.session_state.get("iso4app_type", "isochrone"),
            "iso4app_mobility": st.session_state.get(
                "iso4app_mobility", "motor_vehicle"
            ),
            "iso4app_speed_type": st.session_state.get("iso4app_speed_type", "normal"),
            "iso4app_speed_limit": st.session_state.get("iso4app_speed_limit", 50.0),
        },
    }

    result = call_api(ISOCHRONES_ENDPOINT, payload)
    if not result or "results" not in result:
        st.error("❌ Isochrone request failed.")
        return None

    first = result["results"][0]
    geojson = first["geojson"]
    bands = []
    for feat in geojson.get("features", []):
        props = feat.get("properties", {})
        band_hours = props.get("band_hours", rho)
        bands.append(
            {
                "band_hours": band_hours,
                "band_label": format_time_display(band_hours),
                "geojson_feature": feat,
            }
        )
    st.success(f"✅ Isochrone created for {center_name}")
    return bands


# ---------------------------
# MAP + INTERACTION
# ---------------------------
def draw_map():
    m = create_base_map()
    fg = fl.FeatureGroup(name="Isochrones")

    # Add all existing polygons
    for cname, data in st.session_state.isochrones.items():
        for band in data["bands"]:
            geo = band["geojson_feature"]
            fill, border = get_band_color(0, 1, st.session_state.colormap)
            fl.GeoJson(
                geo,
                style_function=lambda x, fill=fill, border=border: {
                    "fillColor": fill,
                    "color": border,
                    "weight": 2,
                    "fillOpacity": 0.4,
                    "opacity": 0.8,
                },
                tooltip=f"{cname} - {band['band_label']}",
            ).add_to(fg)

    m.add_child(fg)
    map_center = get_map_center()

    # Overlay raster if available
    if st.session_state.uploaded_rasters:
        first_raster = st.session_state.uploaded_rasters[0]
        temp_path = save_uploaded_file(first_raster)
        add_raster_to_map(m, temp_path, layer_name=first_raster.name, opacity=0.6)

    zoom_level = 9 if hasattr(st.session_state, "coord_center") else 9
    return st_folium(
        m,
        center=map_center,
        zoom=zoom_level,
        key="raster_map",
        height=500,
        width=None,
        use_container_width=True,
    )


def handle_map_click(map_data):
    if not map_data.get("last_clicked"):
        return
    lat, lon = get_pos(map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
    st.success(f"📍 Clicked: {lat:.5f}, {lon:.5f}")
    if st.button("➕ Add Isochrone Here"):
        cname = f"Center{len(st.session_state.isochrones)+1}"
        with st.spinner(f"Computing isochrone for {cname}..."):
            bands = process_isochrone(cname, lat, lon, st.session_state.rho)
            if bands:
                st.session_state.isochrones[cname] = {"bands": bands}
                st.rerun()


# ---------------------------
# RASTER STATS
# ---------------------------
def compute_raster_stats():
    if not st.session_state.isochrones:
        st.warning("Add at least one isochrone first.")
        return
    if not st.session_state.uploaded_rasters:
        st.warning("Upload at least one raster file.")
        return

    raster_paths = [save_uploaded_file(f) for f in st.session_state.uploaded_rasters]
    isochrones = []
    for cid, data in st.session_state.isochrones.items():
        geo = data["bands"][0]["geojson_feature"]["geometry"]
        isochrones.append({"centroid_id": cid, "geometry": geo})

    payload = {
        "isochrones": isochrones,
        "rasters": [{"name": os.path.basename(p), "path": p} for p in raster_paths],
    }
    with st.spinner("Computing raster statistics..."):
        result = call_api(RASTER_STATS_ENDPOINT, payload)
        if result and "results" in result:
            st.session_state.raster_results = result["results"]
            st.success("✅ Raster stats computed!")


# ---------------------------
# DISPLAY RESULTS
# ---------------------------
def render_results():
    if not st.session_state.get("raster_results"):
        return
    st.subheader("📊 Raster Statistics")
    st.dataframe(st.session_state.raster_results, use_container_width=True)


# ---------------------------
# MAIN
# ---------------------------
def main():
    # --- Initialize session state ---
    if "centers" not in st.session_state:
        st.session_state.centers = {}
    if "isochrones" not in st.session_state:
        st.session_state.isochrones = {}
    if "uploaded_rasters" not in st.session_state:
        st.session_state.uploaded_rasters = []
    if "raster_results" not in st.session_state:
        st.session_state.raster_results = None
    render_sidebar()
    st.title("📈 Iso-Raster Analysis")
    st.caption("Compute raster statistics inside isochrones and their intersections.")
    map_data = draw_map()
    handle_map_click(map_data)

    if st.button("📊 Compute Raster Stats", type="primary"):
        compute_raster_stats()

    render_results()


if __name__ == "__main__":
    main()
