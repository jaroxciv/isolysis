import os
import folium as fl
import streamlit as st
from streamlit_folium import st_folium
from dotenv import load_dotenv, find_dotenv

from api.utils import (
    get_map_center,
    add_coordinates_to_map,
    format_time_display,
    get_band_color,
    get_pos,
    call_api,
    handle_coordinate_upload,
    get_coordinates_center,
)


# -------------------------
# ENV + CONFIG
# -------------------------
load_dotenv(find_dotenv(usecwd=True), override=True)

MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
ISO4APP_API_KEY = os.getenv("ISO4APP_API_KEY")
API_URL = "http://localhost:8000/isochrones"


# Page config
st.set_page_config(page_title="🗺️ Simple Isochrone Map", layout="wide")


# -------------------------
# CACHED FUNCTIONS
# -------------------------
@st.cache_data
def create_base_map():
    """Create the base folium map (cached)"""
    m = fl.Map(
        location=[51.5074, -0.1278],  # Default center
        zoom_start=9,
        tiles="CartoDB positron",
    )
    m.add_child(fl.LatLngPopup())
    return m


@st.cache_data
def create_feature_group():
    """Create empty feature group (cached)"""
    return fl.FeatureGroup(name="Dynamic Elements")


# -------------------------
# FRAGMENT FUNCTIONS
# -------------------------
@st.fragment(run_every=1)
def build_feature_group():
    """Build feature group with all current elements (fragment for auto-refresh)"""
    fg = create_feature_group()

    # Add center markers
    for name, coords in st.session_state.centers.items():
        marker = fl.Marker(
            location=[coords["lat"], coords["lng"]],
            popup=f"{name}<br>{coords['lat']:.5f}, {coords['lng']:.5f}",
            tooltip=name,
            icon=fl.Icon(color="red", icon="plus"),
        )
        fg.add_child(marker)

    # Add uploaded coordinates
    if hasattr(st.session_state, "uploaded_coordinates"):
        for coord in st.session_state.uploaded_coordinates:
            label = coord.name or coord.id or "Unknown"
            circle_marker = fl.CircleMarker(
                location=[coord.lat, coord.lon],
                radius=3,
                popup=f"""
                <b>Lat</b>: {coord.lat:.5f}<br>
                <b>Lon</b>: {coord.lon:.5f}<br>
                <b>Region</b>: {coord.region or 'N/A'}<br>
                <b>Municipality</b>: {coord.municipality or 'N/A'}
                """,
                tooltip=label,
                color="black",
                weight=1,
                fillColor="grey",
                fillOpacity=0.5,
                opacity=0.8,
            )
            fg.add_child(circle_marker)

    # Add isochrones
    for center_name, isochrone_data in st.session_state.isochrones.items():
        if "bands" in isochrone_data:
            total_bands = len(isochrone_data["bands"])
            sorted_bands = sorted(
                isochrone_data["bands"], key=lambda x: x["band_hours"], reverse=True
            )

            for band_index, band_data in enumerate(sorted_bands):
                band_hours = band_data["band_hours"]
                geojson_feature = band_data["geojson_feature"]
                time_display = format_time_display(band_hours)
                tooltip_text = f"{center_name} - {time_display} travel area"
                popup_text = f"{center_name}<br>Travel time: {time_display}<br>Band: {band_hours}h"

                # Get colors - need to access colormap from session state
                colormap = st.session_state.get("colormap", "viridis")
                fill_color, border_color = get_band_color(
                    band_index, total_bands, colormap
                )

                style_func = lambda x, fill=fill_color, border=border_color: {
                    "fillColor": fill,
                    "color": border,
                    "weight": 2,
                    "fillOpacity": 0.4,
                    "opacity": 0.8,
                }

                if geojson_feature["geometry"]["type"] in ["Polygon", "MultiPolygon"]:
                    geojson_layer = fl.GeoJson(
                        geojson_feature,
                        style_function=style_func,
                        popup=popup_text,
                        tooltip=tooltip_text,
                    )
                    fg.add_child(geojson_layer)

    return fg


def draw_map():
    """Draw the map with all current elements"""
    m = create_base_map()
    fg = build_feature_group()  # This is now the fragment

    map_center = get_map_center()

    return st_folium(
        m,
        center=map_center,
        zoom=9,
        key="dynamic_map",
        feature_group_to_add=fg,
        height=500,
        width=None,
        returned_objects=["last_clicked"],
    )


def handle_coordinate_upload_sidebar():
    """Handle coordinate upload in sidebar"""
    st.subheader("📂 Upload Coordinates")
    uploaded_file = st.file_uploader(
        "Upload JSON coordinates",
        type=["json"],
        help="Upload a JSON file with coordinate data",
    )

    if uploaded_file is not None:
        coordinates = handle_coordinate_upload(uploaded_file)
        if coordinates:
            st.success(f"✅ Loaded {len(coordinates)} coordinates")
            st.session_state.uploaded_coordinates = coordinates
            if coordinates:
                coord_center = get_coordinates_center(coordinates)
                st.session_state.coord_center = coord_center


def render_sidebar():
    """Render complete sidebar"""
    with st.sidebar:
        st.header("⚙️ Isochrone Settings")

        # Provider selection
        provider = st.selectbox(
            "Provider",
            options=["osmnx", "mapbox", "iso4app"],
            index=1,
            help="Choose routing engine",
        )

        # Travel time (rho)
        rho = st.slider(
            "Travel Time (hours)",
            min_value=0.25,
            max_value=4.0,
            value=1.0,
            step=0.25,
            help="Maximum travel time from center",
        )

        # Time band interval
        time_bands = st.slider(
            "Number of Time Bands",
            min_value=1,
            max_value=5,
            value=1,
            step=1,
            help="1 = single polygon, 2+ = multiple equally-spaced bands",
        )

        # Colormap selection
        colormap = st.selectbox(
            "Color Scheme",
            options=[
                "viridis",
                "plasma",
                "magma",
                "inferno",
                "cividis",
                "Blues",
                "Reds",
                "YlOrRd",
                "RdYlBu_r",
            ],
            index=0,
            help="Color scheme for time bands (shorter time = more intense color)",
        )

        # Store colormap in session state for fragment access
        st.session_state.colormap = colormap

        st.markdown("---")
        handle_coordinate_upload_sidebar()

        st.markdown("---")
        st.write(f"**Settings:**")
        st.write(f"Provider: {provider}")
        st.write(f"Travel time: {rho}h")
        if time_bands == 1:
            st.write(f"Mode: Single polygon")
        else:
            st.write(f"Bands: {time_bands} equally spaced")

    return provider, rho, time_bands, colormap


def process_isochrone_request(center_name, lat, lng, rho, provider, time_bands):
    """Process isochrone computation request"""
    payload = {
        "centroids": [{"lat": lat, "lon": lng, "rho": rho, "id": center_name}],
        "options": {
            "provider": provider,
            "travel_speed_kph": 25,
            "num_bands": time_bands,
        },
    }

    result = call_api(API_URL, payload)

    if result and "results" in result and len(result["results"]) > 0:
        first_result = result["results"][0]
        geojson = first_result.get("geojson")
        cached = first_result.get("cached", False)

        if geojson and "features" in geojson:
            bands_data = []
            for feature in geojson["features"]:
                properties = feature.get("properties", {})
                band_hours = properties.get("band_hours")
                if band_hours is None:
                    st.warning("band_hours not found in feature properties")
                    continue
                bands_data.append(
                    {"band_hours": band_hours, "geojson_feature": feature}
                )

            if bands_data:
                st.session_state.isochrones[center_name] = {"bands": bands_data}
                cache_msg = " (cached)" if cached else ""
                band_count = len(bands_data)
                st.success(
                    f"✅ Added {center_name} with {band_count} band(s){cache_msg}"
                )
                return True
            else:
                st.error(f"❌ No valid band data found for {center_name}")
        else:
            st.error(f"❌ No geojson data returned for {center_name}")
    else:
        st.error(f"❌ Failed to compute isochrone for {center_name}")
    return False


def handle_map_click(map_data, provider, rho, time_bands):
    """Handle map click interactions"""
    data = None
    if map_data.get("last_clicked"):
        data = get_pos(map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])

    if data is not None:
        lat, lng = data
        st.success(f"📍 **Clicked:** {lat:.5f}, {lng:.5f}")

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric("Latitude", f"{lat:.5f}")
        with col2:
            st.metric("Longitude", f"{lng:.5f}")
        with col3:
            if st.button("➕ Add Center", type="primary"):
                center_name = f"Center{len(st.session_state.centers) + 1}"
                st.session_state.centers[center_name] = {"lat": lat, "lng": lng}

                with st.spinner(f"Computing isochrone for {center_name}..."):
                    success = process_isochrone_request(
                        center_name, lat, lng, rho, provider, time_bands
                    )

                    if success:
                        st.rerun()

    else:
        st.info("👆 Click on the map to see coordinates")


def render_center_controls():
    """Render center management controls"""
    if st.session_state.centers:
        st.markdown("---")

        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.subheader(f"📍 Stored Centers ({len(st.session_state.centers)})")
        with col2:
            if st.button("↶ Undo Last"):
                if st.session_state.centers:
                    last_key = list(st.session_state.centers.keys())[-1]
                    del st.session_state.centers[last_key]
                    if last_key in st.session_state.isochrones:
                        del st.session_state.isochrones[last_key]
                    st.success(f"🗑️ Removed {last_key}")
        with col3:
            if st.button("🧹 Clear Polygons"):
                count = len(st.session_state.isochrones)
                st.session_state.isochrones = {}
                st.success(f"🧹 Cleared {count} polygons")
        with col4:
            if st.button("🗑️ Clear All"):
                center_count = len(st.session_state.centers)
                poly_count = len(st.session_state.isochrones)
                st.session_state.centers = {}
                st.session_state.isochrones = {}
                st.success(f"🗑️ Cleared {center_count} centers & {poly_count} polygons")

        # List all centers with band information
        for name, coords in st.session_state.centers.items():
            bands_info = ""
            if (
                name in st.session_state.isochrones
                and "bands" in st.session_state.isochrones[name]
            ):
                sorted_bands = sorted(
                    st.session_state.isochrones[name]["bands"],
                    key=lambda x: x["band_hours"],
                )
                band_times = [
                    format_time_display(b["band_hours"]) for b in sorted_bands
                ]
                bands_info = f" - Bands: {', '.join(band_times)}"

            st.write(
                f"**{name}:** {coords['lat']:.5f}, {coords['lng']:.5f}{bands_info}"
            )


# -------------------------
# MAIN APP
# -------------------------
def main():
    """Main application function"""
    # Initialize session state
    if "centers" not in st.session_state:
        st.session_state.centers = {}
    if "isochrones" not in st.session_state:
        st.session_state.isochrones = {}

    # Render sidebar and get settings
    provider, rho, time_bands, colormap = render_sidebar()

    # Main content
    st.title("🗺️ Click to Add Isochrone Centers")
    st.markdown("Click anywhere on the map to see coordinates")

    # Draw map (fragment)
    map_data = draw_map()

    # Handle map interactions
    handle_map_click(map_data, provider, rho, time_bands)

    # Render controls
    render_center_controls()


if __name__ == "__main__":
    main()
