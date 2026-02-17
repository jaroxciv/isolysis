import os
import tempfile

# ---------------------------
# TEMP DIR SETUP (shared path for Streamlit + API)
# ---------------------------
import warnings
from io import BytesIO

import folium as fl
import geopandas as gpd
import matplotlib.colors
import matplotlib.pyplot as plt
import numpy as np
import rasterio
import streamlit as st
from dotenv import find_dotenv, load_dotenv
from folium.raster_layers import ImageOverlay
from PIL import Image
from streamlit_folium import st_folium

from st_utils import (
    call_api,
    format_time_display,
    get_band_color,
    get_map_center,
)
from translations import get_selectbox_options, t

warnings.filterwarnings("ignore", message=".*GPKG application_id.*")

# Force all temp files into a shared folder within the project
tempfile.tempdir = os.path.join(os.getcwd(), "data", "tmp", "iso_raster_current")
os.makedirs(tempfile.tempdir, exist_ok=True)


# ---------------------------
# ENV + CONFIG
# ---------------------------
load_dotenv(find_dotenv(usecwd=True), override=False)

API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
ISOCHRONES_ENDPOINT = f"{API_URL}/isochrones"
RASTER_STATS_ENDPOINT = f"{API_URL}/raster-stats"

# Initialize language before set_page_config
if "lang" not in st.session_state:
    st.session_state.lang = "es"

st.set_page_config(page_title=t("page.raster_title"), layout="wide")


# ---------------------------
# CACHED HELPERS
# ---------------------------
@st.cache_data
def create_base_map():
    m = fl.Map(location=[13.7942, -88.8965], zoom_start=9, tiles="CartoDB positron")
    m.add_child(fl.LatLngPopup())
    return m


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

    st.warning(t("raster.unsupported_boundary"))
    return None


@st.cache_data(show_spinner=False)
def raster_to_png_path(_file_bytes: bytes, _name: str, colormap="viridis"):
    """
    Convert raster bytes to a temporary PNG file and cache the resulting path.
    Reuses the same PNG if the same raster bytes are passed again.
    `_name` is included only to give Streamlit a unique cache key per file.
    """
    with rasterio.open(BytesIO(_file_bytes)) as dataset:
        data = dataset.read(1)
        bounds = dataset.bounds

    # Normalize data
    mask = data <= 0
    data = np.where(mask, np.nan, data)
    vmin, vmax = np.nanmin(data), np.nanmax(data)
    norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap(colormap)
    rgba_img = cmap(norm(data))
    rgba_img[..., 3] = np.where(np.isnan(data), 0, 1)

    # Save PNG
    img = Image.fromarray((rgba_img * 255).astype(np.uint8))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img.save(tmp, format="PNG")
        temp_path = tmp.name

    return temp_path, bounds


def add_raster_to_feature_group(
    fg, uploaded_file, layer_name="Raster Overlay", opacity=0.7
):
    """
    Overlay a raster from uploaded bytes, wrapped in a FeatureGroup for smoother behavior.
    Uses caching to avoid re-encoding the same raster on reruns.
    """
    try:
        # --- Cache setup ---
        if "raster_overlays" not in st.session_state:
            st.session_state.raster_overlays = {}

        # --- Load bytes and check cache (include colormap in key) ---
        file_bytes = uploaded_file.getvalue()
        colormap = st.session_state.get("colormap", "viridis")
        cache_key = f"{uploaded_file.name}_{colormap}"
        if cache_key in st.session_state.raster_overlays:
            temp_path, bounds = st.session_state.raster_overlays[cache_key]
        else:
            temp_path, bounds = raster_to_png_path(
                file_bytes,
                uploaded_file.name,
                colormap,
            )
            st.session_state.raster_overlays[cache_key] = (temp_path, bounds)

        # --- Wrap overlay in a FeatureGroup (for smoother handling) ---
        ImageOverlay(
            image=temp_path,
            bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
            opacity=opacity,
            name=layer_name,
            interactive=False,
            cross_origin=False,
            zindex=1,
        ).add_to(fg)

    except Exception as e:
        st.warning(t("raster.overlay_error", error=str(e)))


def add_boundary_to_feature_group(
    fg, uploaded_file, layer_name="Boundary", color="#ff7800", center=False
):
    """Add boundary polygons to FeatureGroup (modern approach, no flicker)."""
    try:
        gdf = read_boundary(uploaded_file)
        if gdf is None or gdf.empty:
            st.warning(t("raster.no_geometries"))
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
        ).add_to(fg)  # Add to FeatureGroup instead of map

        # Center map
        if center:
            gdf_proj = gdf.to_crs(3857)
            centroid = gdf_proj.geometry.union_all().centroid
            centroid_wgs84 = gpd.GeoSeries([centroid], crs=3857).to_crs(4326).iloc[0]
            st.session_state.coord_center = (centroid_wgs84.y, centroid_wgs84.x)

    except Exception as e:
        st.warning(t("raster.boundary_error", error=str(e)))


# ---------------------------
# SIDEBAR
# ---------------------------
def render_sidebar():
    with st.sidebar:
        # Language selector at top of sidebar
        lang_options = ["Español", "English"]
        lang_values = ["es", "en"]
        current_idx = lang_values.index(st.session_state.lang)
        selected_lang = st.selectbox(
            t("lang.label"),
            options=lang_options,
            index=current_idx,
            key="lang_selector",
        )
        new_lang = lang_values[lang_options.index(selected_lang)]
        if new_lang != st.session_state.lang:
            st.session_state.lang = new_lang
            st.rerun()

        st.header(t("sidebar.raster_header"))

        # Travel time (rho) - in minutes for UI, converted to hours for API
        rho_minutes = st.slider(
            t("sidebar.travel_time_minutes"),
            min_value=5,
            max_value=60,
            value=30,
            step=5,
            help=t("sidebar.travel_time_centroid_help"),
        )
        rho = rho_minutes / 60.0  # Convert to hours for API

        # Iso4App-specific options
        iso_labels, iso_values = get_selectbox_options("isoline_type")
        selected_iso = st.selectbox(
            t("sidebar.isoline_type"),
            iso_labels,
            index=0,
            help=t("sidebar.isoline_type_help"),
        )
        iso_type = iso_values[iso_labels.index(selected_iso)]

        mode_labels, mode_values = get_selectbox_options("travel_mode")
        selected_mode = st.selectbox(
            t("sidebar.travel_mode"),
            mode_labels,
            index=0,
        )
        mobility = mode_values[mode_labels.index(selected_mode)]

        speed_labels, speed_values = get_selectbox_options("speed_profile")
        selected_speed = st.selectbox(
            t("sidebar.speed_profile"),
            speed_labels,
            index=2,
        )
        speed_type = speed_values[speed_labels.index(selected_speed)]

        speed_limit = st.number_input(
            t("sidebar.max_speed"),
            min_value=10.0,
            max_value=200.0,
            value=50.0,
            step=5.0,
            help=t("sidebar.max_speed_help"),
        )

        # Colormap
        colormap = st.selectbox(
            t("sidebar.color_scheme"),
            ["viridis", "plasma", "magma", "inferno", "cividis", "Reds", "Blues"],
            index=0,
        )

        # Raster upload
        uploaded_rasters = st.file_uploader(
            t("sidebar.upload_rasters"),
            type=["tif", "tiff"],
            accept_multiple_files=True,
            key=f"raster_uploader_{st.session_state.raster_uploader_key}",
        )

        # Boundary upload
        # Use a key to allow resetting the uploader
        if "boundary_uploader_key" not in st.session_state:
            st.session_state.boundary_uploader_key = 0

        uploaded_boundary = st.file_uploader(
            t("sidebar.upload_boundary"),
            type=["gpkg", "geojson", "zip"],
            key=f"boundary_uploader_{st.session_state.boundary_uploader_key}",
        )

        # Store selections
        st.session_state.rho = rho
        st.session_state.rho_minutes = rho_minutes
        st.session_state.colormap = colormap
        if uploaded_rasters:
            st.session_state.uploaded_rasters = uploaded_rasters
        if uploaded_boundary:
            st.session_state.uploaded_boundary = uploaded_boundary
        st.session_state.iso4app_type = iso_type
        st.session_state.iso4app_mobility = mobility
        st.session_state.iso4app_speed_type = speed_type
        st.session_state.iso4app_speed_limit = speed_limit

        # ---------------------------
        # RASTER CENTERING
        # ---------------------------
        if uploaded_rasters:
            st.success(t("raster.loaded_rasters", count=len(uploaded_rasters)))

        # ---------------------------
        # BOUNDARY CENTERING
        # ---------------------------
        if uploaded_boundary is not None:
            st.success(t("raster.loaded_boundary", names=uploaded_boundary.name))

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
        st.error(t("iso.request_failed"))
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
    st.success(t("iso.created", name=center_name))
    return bands


# ---------------------------
# MAP + INTERACTION
# ---------------------------
def draw_map():
    """Draw the folium map and update dynamically using st_folium's new parameters."""
    m = create_base_map()
    fg = fl.FeatureGroup(name="Isochrones and Boundary")

    # --- Add isochrones dynamically ---
    for cname, data in st.session_state.isochrones.items():
        for band in data["bands"]:
            geo = band["geojson_feature"]
            fill, border = get_band_color(0, 1, st.session_state.colormap)
            # Remove popup to avoid blocking clicks, keep tooltip for hover info
            geojson_layer = fl.GeoJson(
                geo,
                style_function=lambda x, fill=fill, border=border: {
                    "fillColor": fill,
                    "color": border,
                    "weight": 2,
                    "fillOpacity": 0.4,
                    "opacity": 0.8,
                },
                control=True,
                overlay=True,
                show=True,
            )
            geojson_layer.add_to(fg)

    # --- Add boundary to the same FeatureGroup (modern approach, no flicker) ---
    if st.session_state.get("uploaded_boundary"):
        boundary_data = st.session_state.uploaded_boundary
        add_boundary_to_feature_group(
            fg, boundary_data, layer_name="Boundary", color="#ff6600"
        )

    # --- Overlay first raster if available ---
    if st.session_state.uploaded_rasters:
        first_raster = st.session_state.uploaded_rasters[0]
        add_raster_to_feature_group(
            fg, first_raster, layer_name=first_raster.name, opacity=0.6
        )

    # --- Compute map center and zoom ---
    if "coord_center" in st.session_state:
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
    lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    st.success(t("map.clicked", lat=f"{lat:.5f}", lng=f"{lon:.5f}"))
    if st.button(t("map.add_isochrone")):
        cname = f"Center{len(st.session_state.isochrones) + 1}"
        with st.spinner(t("map.computing", name=cname)):
            bands = process_isochrone(cname, lat, lon, st.session_state.rho)
            if bands:
                # Store isochrone with metadata
                speed_kph = st.session_state.get("iso4app_speed_limit", 50.0)
                st.session_state.isochrones[cname] = {
                    "bands": bands,
                    "rho": st.session_state.rho,
                    "rho_minutes": st.session_state.rho_minutes,
                    "speed_kph": speed_kph,
                }
                st.rerun()


# ---------------------------
# RASTER STATS
# ---------------------------
def compute_raster_stats():
    """Send rasters + polygon source (isochrone or boundary) to backend."""
    if not st.session_state.uploaded_rasters:
        st.warning(t("raster.upload_raster_warning"))
        return

    boundary = st.session_state.get("uploaded_boundary")
    isochrones_exist = bool(st.session_state.isochrones)

    # --- Validate polygon source ---
    if not boundary and not isochrones_exist:
        st.warning(t("raster.upload_boundary_warning"))
        return
    if boundary and isochrones_exist:
        st.error(t("raster.both_error"))
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

    payload: dict[str, object] = {
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
    with st.spinner(t("raster.computing_stats")):
        result = call_api(RASTER_STATS_ENDPOINT, payload)
        if not result:
            st.error(t("raster.stats_failed"))
            return
        if "results" not in result:
            st.error(t("raster.stats_unexpected"))
            st.json(result)
            return

        st.session_state.raster_results = result["results"]
        st.success(t("raster.stats_done"))


# ---------------------------
# DISPLAY RESULTS
# ---------------------------
def render_results():
    if not st.session_state.get("raster_results"):
        return
    st.subheader(t("raster.stats_header"))
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
    if "raster_uploader_key" not in st.session_state:
        st.session_state.raster_uploader_key = 0
    render_sidebar()
    st.title(t("raster.title"))
    st.caption(t("raster.caption"))
    map_data = draw_map()
    handle_map_click(map_data)

    # --- Manage loaded isochrones ---
    if st.session_state.isochrones:
        st.subheader(t("raster.loaded_isochrones"))
        for cname in list(st.session_state.isochrones.keys()):
            cols = st.columns([4, 1])
            iso_data = st.session_state.isochrones[cname]
            num_bands = len(iso_data["bands"])
            rho_min = iso_data.get("rho_minutes", int(iso_data.get("rho", 1) * 60))
            speed = iso_data.get("speed_kph", "N/A")
            cols[0].write(
                f"**{cname}**"
                + t("centers.bands_info", bands=num_bands, minutes=rho_min, speed=speed)
            )
            if cols[1].button(t("raster.remove_btn"), key=f"remove_{cname}"):
                del st.session_state.isochrones[cname]
                st.toast(t("raster.isochrone_removed", name=cname))
                st.rerun()

    # --- Clear All button ---
    if (
        st.session_state.isochrones
        or st.session_state.get("uploaded_boundary")
        or st.session_state.get("uploaded_rasters")
    ):
        st.markdown("---")
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            if st.session_state.isochrones and st.button(t("raster.clear_isochrones")):
                count = len(st.session_state.isochrones)
                st.session_state.isochrones = {}
                st.toast(t("raster.cleared_isochrones", count=count))
                st.rerun()

        with col2:
            if st.session_state.get("uploaded_boundary") and st.button(
                t("raster.clear_boundary")
            ):
                st.session_state.uploaded_boundary = None
                st.session_state.boundary_uploader_key += 1  # Reset the uploader
                if "coord_center" in st.session_state:
                    del st.session_state.coord_center
                st.toast(t("raster.boundary_cleared"))
                st.rerun()

        with col3:
            if st.session_state.get("uploaded_rasters") and st.button(
                t("raster.clear_rasters")
            ):
                raster_count = len(st.session_state.uploaded_rasters)
                st.session_state.uploaded_rasters = []
                st.session_state.raster_overlays = {}
                st.session_state.raster_uploader_key += 1  # Reset the uploader
                st.toast(t("raster.cleared_rasters", count=raster_count))
                st.rerun()

        with col4:
            if (
                st.session_state.isochrones
                or st.session_state.get("uploaded_boundary")
                or st.session_state.get("uploaded_rasters")
            ) and st.button(t("raster.clear_all"), type="secondary"):
                iso_count = len(st.session_state.isochrones)
                st.session_state.isochrones = {}
                st.session_state.uploaded_boundary = None
                st.session_state.boundary_uploader_key += 1  # Reset the uploader
                st.session_state.uploaded_rasters = []
                st.session_state.raster_overlays = {}
                st.session_state.raster_uploader_key += 1  # Reset the uploader
                st.toast(t("raster.cleared_all", count=iso_count))
                st.rerun()

    if st.button(t("raster.compute_btn"), type="primary"):
        compute_raster_stats()

    render_results()


if __name__ == "__main__":
    main()
