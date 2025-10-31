import os
import json
import rasterio
import tempfile
import streamlit as st
import folium as fl
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from streamlit_folium import st_folium
from dotenv import find_dotenv, load_dotenv

import base64
from PIL import Image
from io import BytesIO

from api.utils import (
    call_api,
    format_time_display,
    get_map_center,
    get_band_color,
    get_pos,
)


# ---------------------------
# TEMP DIR SETUP (shared path for Streamlit + API)
# ---------------------------
import warnings

warnings.filterwarnings("ignore", message=".*GPKG application_id.*")

# Force all temp files into a shared folder within the project
tempfile.tempdir = os.path.join(os.getcwd(), "data", "tmp", "iso_raster_current")
os.makedirs(tempfile.tempdir, exist_ok=True)


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


@st.cache_data
def load_uploaded_file(uploaded_file):
    """
    Cache and return the file bytes in memory.
    Used for quick visualization, not for heavy processing.
    """
    return uploaded_file.getvalue()


def read_raster(uploaded_file):
    """Read raster from memory for map visualization (not for backend)."""
    file_bytes = load_uploaded_file(uploaded_file)
    dataset = rasterio.open(BytesIO(file_bytes))
    return dataset


def read_boundary(uploaded_file):
    """
    Safely read boundary file (GPKG, GeoJSON, or ZIP shapefile).
    Writes GeoPackage to a temporary file because GDAL needs a real path.
    """
    file_bytes = load_uploaded_file(uploaded_file)

    if uploaded_file.name.endswith(".gpkg"):
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        gdf = gpd.read_file(tmp_path)
        return gdf

    if uploaded_file.name.endswith(".geojson"):
        gdf = gpd.read_file(BytesIO(file_bytes))
        return gdf

    if uploaded_file.name.endswith(".zip"):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        gdf = gpd.read_file(f"zip://{tmp_path}")
        return gdf

    st.warning("Unsupported boundary format.")
    return None


def add_raster_to_map(m, uploaded_file, layer_name="Raster Overlay", opacity=0.7):
    """Overlay a raster from uploaded bytes."""
    try:
        dataset = read_raster(uploaded_file)
        data = dataset.read(1)
        bounds = dataset.bounds
        dataset.close()

        # Mask and normalize
        mask = data <= 0
        data = np.where(mask, np.nan, data)
        vmin, vmax = np.nanmin(data), np.nanmax(data)
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
        cmap = plt.get_cmap("viridis")
        rgba_img = cmap(norm(data))
        rgba_img[..., 3] = np.where(np.isnan(data), 0, 1)

        rgb_img = (rgba_img[:, :, :3] * 255).astype(np.uint8)
        alpha = (rgba_img[:, :, 3] * 255).astype(np.uint8)
        rgba_8bit = np.dstack((rgb_img, alpha))

        img = Image.fromarray(rgba_8bit)
        buf = BytesIO()
        img.save(buf, format="PNG")
        b64_img = base64.b64encode(buf.getvalue()).decode("utf-8")

        bounds_sw = [bounds.bottom, bounds.left]
        bounds_ne = [bounds.top, bounds.right]

        fl.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{b64_img}",
            bounds=[bounds_sw, bounds_ne],
            opacity=opacity,
            name=layer_name,
        ).add_to(m)

    except Exception as e:
        st.warning(f"⚠️ Could not render raster overlay: {e}")


def add_boundary_to_map(m, uploaded_file, layer_name="Boundary", color="#ff7800"):
    """Add boundary polygons from uploaded file (gpkg, geojson, or zipped shapefile)."""
    try:
        gdf = read_boundary(uploaded_file)
        if gdf is None or gdf.empty:
            st.warning("⚠️ Boundary file contains no geometries.")
            return

        fl.GeoJson(
            gdf.to_json(),
            name=layer_name,
            style_function=lambda x: {
                "fillColor": "#00000000",
                "color": color,
                "weight": 2,
                "opacity": 0.8,
            },
            tooltip=layer_name,
        ).add_to(m)

        # Center map
        gdf_proj = gdf.to_crs(3857)
        centroid = gdf_proj.geometry.union_all().centroid
        centroid_wgs84 = gpd.GeoSeries([centroid], crs=3857).to_crs(4326).iloc[0]
        st.session_state.coord_center = (centroid_wgs84.y, centroid_wgs84.x)

    except Exception as e:
        st.warning(f"⚠️ Could not render boundary overlay: {e}")


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

        # Boundary upload
        uploaded_boundary = st.file_uploader(
            "Upload boundary file (.gpkg, .geojson, .zip for shapefile)",
            type=["gpkg", "geojson", "zip"],
        )

        # Store selections
        st.session_state.rho = rho
        st.session_state.colormap = colormap
        st.session_state.uploaded_rasters = uploaded_rasters
        st.session_state.uploaded_boundary = uploaded_boundary
        st.session_state.iso4app_type = iso_type
        st.session_state.iso4app_mobility = mobility
        st.session_state.iso4app_speed_type = speed_type
        st.session_state.iso4app_speed_limit = speed_limit

        # ---------------------------
        # RASTER CENTERING
        # ---------------------------
        if uploaded_rasters:
            st.success(f"✅ Loaded {len(uploaded_rasters)} raster(s)")

            try:
                first_raster = uploaded_rasters[0]
                dataset = read_raster(first_raster)
                bounds = dataset.bounds
                center = (
                    (bounds.top + bounds.bottom) / 2,
                    (bounds.left + bounds.right) / 2,
                )
                dataset.close()

                st.session_state.coord_center = center
                st.info(f"📍 Centered map on raster ({center[0]:.4f}, {center[1]:.4f})")

            except Exception as e:
                st.warning(f"⚠️ Could not compute raster center: {e}")

        # ---------------------------
        # BOUNDARY CENTERING
        # ---------------------------
        if uploaded_boundary:
            file_names = (
                [f.name for f in uploaded_boundary]
                if isinstance(uploaded_boundary, list)
                else [uploaded_boundary.name]
            )
            st.success(f"✅ Loaded boundary file(s): {', '.join(file_names)}")

            try:
                gdf = read_boundary(uploaded_boundary)
                if gdf is not None and not gdf.empty:
                    gdf_proj = gdf.to_crs(3857)
                    centroid = gdf_proj.geometry.union_all().centroid
                    centroid_wgs84 = (
                        gpd.GeoSeries([centroid], crs=3857).to_crs(4326).iloc[0]
                    )
                    st.session_state.coord_center = (centroid_wgs84.y, centroid_wgs84.x)
            except Exception as e:
                st.warning(f"⚠️ Could not auto-center on boundary: {e}")

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
    """Draw the folium map and update dynamically using st_folium's new parameters."""
    m = create_base_map()
    fg = fl.FeatureGroup(name="Isochrones")

    # --- Add isochrones dynamically ---
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

    # --- Overlay first raster if available ---
    if st.session_state.uploaded_rasters:
        first_raster = st.session_state.uploaded_rasters[0]
        add_raster_to_map(m, first_raster, layer_name=first_raster.name, opacity=0.6)

    if st.session_state.get("uploaded_boundary"):
        boundary_data = st.session_state.uploaded_boundary
        add_boundary_to_map(m, boundary_data, layer_name="Boundary", color="#ff6600")

    # --- Compute map center and zoom ---
    if hasattr(st.session_state, "coord_center"):
        center = st.session_state.coord_center
    else:
        center = get_map_center()

    zoom = 9

    # --- Use new dynamic update arguments ---
    return st_folium(
        m,
        center=center,
        zoom=zoom,
        feature_group_to_add=fg,
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
    """Send rasters + polygon source (isochrone or boundary) to backend."""
    if not st.session_state.uploaded_rasters:
        st.warning("Upload at least one raster file.")
        return

    boundary = st.session_state.get("uploaded_boundary")
    isochrones_exist = bool(st.session_state.isochrones)

    # --- Validate polygon source ---
    if not boundary and not isochrones_exist:
        st.warning("Upload a boundary file or add isochrones first.")
        return
    if boundary and isochrones_exist:
        st.error("❌ Please use either boundary or isochrones, not both.")
        return

    # --- Save rasters temporarily (shared, stable folder) ---
    tmpdir = os.path.join("data", "tmp", "iso_raster_current")
    os.makedirs(tmpdir, exist_ok=True)

    raster_paths = []
    for f in st.session_state.uploaded_rasters:
        path = os.path.join(tmpdir, f.name)
        with open(path, "wb") as out:
            out.write(f.getvalue())
        raster_paths.append(path)

    payload = {
        "rasters": [{"name": os.path.basename(p), "path": p} for p in raster_paths]
    }

    # --- Choose polygon source ---
    if boundary:
        path = os.path.join(tmpdir, boundary.name)
        with open(path, "wb") as out:
            out.write(boundary.getvalue())
        payload["boundary_path"] = path
    else:
        payload["isochrones"] = [
            {
                "centroid_id": cid,
                "geometry": data["bands"][0]["geojson_feature"]["geometry"],
            }
            for cid, data in st.session_state.isochrones.items()
        ]

    # --- Call API ---
    with st.spinner("Computing raster statistics..."):
        # st.write("Payload:", payload)
        result = call_api(RASTER_STATS_ENDPOINT, payload)
        if not result:
            st.error("❌ Raster stats request failed.")
            return
        if "results" not in result:
            st.error("❌ Unexpected API response format.")
            st.json(result)
            return

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

    # --- Manage loaded isochrones ---
    if st.session_state.isochrones:
        st.subheader("🗺️ Loaded Isochrones")
        for cname in list(st.session_state.isochrones.keys()):
            cols = st.columns([4, 1])
            cols[0].write(
                f"**{cname}** - {len(st.session_state.isochrones[cname]['bands'])} band(s)"
            )
            if cols[1].button("❌ Remove", key=f"remove_{cname}"):
                del st.session_state.isochrones[cname]
                st.toast(f"Isochrone '{cname}' removed.")
                st.rerun()

    if st.button("📊 Compute Raster Stats", type="primary"):
        compute_raster_stats()

    render_results()


if __name__ == "__main__":
    main()
