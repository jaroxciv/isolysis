import os

import folium as fl
import streamlit as st
from dotenv import find_dotenv, load_dotenv
from streamlit_folium import st_folium

from api.utils import (
    add_coordinates_to_map,
    call_api,
    format_time_display,
    get_coordinates_center,
    get_map_center,
    get_pos,
    handle_coordinate_upload,
)

# -------------------------
# ENV + CONFIG
# -------------------------
# Keep Docker env vars if present, don't override with .env file
load_dotenv(find_dotenv(usecwd=True), override=False)

MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
ISO4APP_API_KEY = os.getenv("ISO4APP_API_KEY")

# Use Docker's service name in container, localhost in local dev
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
ISOCHRONES_ENDPOINT = f"{API_URL}/isochrones"

# Default color palette for isochrones (darker tones)
DEFAULT_COLORS = [
    "#1a5ccc",
    "#cc4429",
    "#1fcc3d",
    "#cc29c4",
    "#cca300",
    "#0099cc",
    "#7a29cc",
    "#cc5200",
]

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
def build_feature_group():
    """Build feature group with all current elements (fragment for auto-refresh)"""
    fg = create_feature_group()

    # Build coverage data lookup from analysis results if available
    coverage_by_center = {}
    has_analysis = hasattr(st.session_state, "analysis_result")
    if has_analysis:
        for cov in st.session_state.analysis_result.get("coverage_analysis", []):
            center_id = cov.get("centroid_id")
            if cov.get("bands"):
                # Use first band (usually only one)
                band = cov["bands"][0]
                coverage_by_center[center_id] = {
                    "band_label": band.get("band_label", "N/A"),
                    "poi_count": band.get("poi_count", 0),
                    "coverage_percentage": band.get("coverage_percentage", 0),
                    "production_sum": band.get("production_sum", 0) or 0,
                    "viable": band.get("viable"),
                }

    # Add center markers
    for idx, (name, coords) in enumerate(st.session_state.centers.items()):
        # Build tooltip with coverage data if available
        max_prod = coords.get("max_production", 0)

        if name in coverage_by_center:
            cov_data = coverage_by_center[name]
            viable_str = ""
            if cov_data["viable"] is True:
                viable_str = f"<br>Max Prod: {max_prod:,.0f}<br>Viable: Yes"
            elif cov_data["viable"] is False:
                viable_str = f"<br>Max Prod: {max_prod:,.0f}<br>Viable: No"

            tooltip_html = (
                f"<b>{name}</b><br>"
                f"Time Band: {cov_data['band_label']}<br>"
                f"POIs Covered: {cov_data['poi_count']}<br>"
                f"Coverage: {cov_data['coverage_percentage']:.1f}%<br>"
                f"Prod Sum: {cov_data['production_sum']:,.0f}{viable_str}"
            )
            tooltip = fl.Tooltip(tooltip_html)
        else:
            tooltip = name

        # Use popup instead of tooltip for rich content
        if name in coverage_by_center:
            cov_data = coverage_by_center[name]
            viable_str = ""
            if cov_data["viable"] is True:
                viable_str = (
                    f"<br><b>Max Prod:</b> {max_prod:,.0f}<br><b>Viable:</b> ✅ Yes"
                )
            elif cov_data["viable"] is False:
                viable_str = (
                    f"<br><b>Max Prod:</b> {max_prod:,.0f}<br><b>Viable:</b> ❌ No"
                )

            popup_html = f"""
            <div style="font-family: sans-serif; font-size: 12px;">
            <b>{name}</b><br>
            <b>Time Band:</b> {cov_data["band_label"]}<br>
            <b>POIs Covered:</b> {cov_data["poi_count"]}<br>
            <b>Coverage:</b> {cov_data["coverage_percentage"]:.1f}%<br>
            <b>Prod Sum:</b> {cov_data["production_sum"]:,.0f}{viable_str}
            </div>
            """
        else:
            popup_html = f"{name}<br>{coords['lat']:.5f}, {coords['lng']:.5f}"

        marker = fl.Marker(
            location=[coords["lat"], coords["lng"]],
            popup=fl.Popup(popup_html, max_width=300),
            tooltip=tooltip,
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
                <b>Region</b>: {coord.region or "N/A"}<br>
                <b>Municipality</b>: {coord.municipality or "N/A"}
                """,
                tooltip=label,
                color="black",
                weight=1,
                fillColor="grey",
                fillOpacity=0.5,
                opacity=0.8,
            )
            fg.add_child(circle_marker)

    # Add isochrones with per-center colors
    for idx, (center_name, isochrone_data) in enumerate(
        st.session_state.isochrones.items()
    ):
        if "bands" in isochrone_data and isochrone_data["bands"]:
            band_data = isochrone_data["bands"][0]  # single polygon only
            band_hours = band_data["band_hours"]
            geojson_feature = band_data["geojson_feature"]
            time_display = format_time_display(band_hours)

            # Get per-center color or use default from palette
            center_coords = st.session_state.centers.get(center_name, {})
            fill_color = center_coords.get(
                "color", DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
            )
            border_color = fill_color

            def style_func(x, fill=fill_color, border=border_color):
                return {
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
                    control=True,
                    overlay=True,
                    show=True,
                )
                fg.add_child(geojson_layer)

    return fg


def draw_map():
    """Draw the map with all current elements"""
    m = create_base_map()
    fg = build_feature_group()

    map_center = get_map_center()

    return st_folium(
        m,
        center=map_center,
        zoom=9,
        key="main_map",
        feature_group_to_add=fg,
        height=500,
        width=None,
        returned_objects=["last_clicked"],
    )


def handle_coordinate_upload_sidebar():
    """Handle coordinate upload in sidebar"""
    st.subheader("📂 Upload Coordinates")
    uploaded_file = st.file_uploader(
        "Upload coordinates (JSON, CSV, XLSX)",
        type=["json", "csv", "xlsx"],
        help=(
            "Upload a file with coordinates. "
            "CSV/XLSX must include columns: "
            "Categoria, Subcategoria, Nombre, Latitud, Longitud."
        ),
    )

    if uploaded_file is not None:
        coordinates = handle_coordinate_upload(uploaded_file)
        if coordinates:
            st.success(f"✅ Loaded {len(coordinates)} coordinates")
            st.session_state.uploaded_coordinates = coordinates
            if coordinates:
                coord_center = get_coordinates_center(coordinates)
                st.session_state.coord_center = coord_center

    # 🔹 Add remove button if we have uploaded coordinates
    if (
        hasattr(st.session_state, "uploaded_coordinates")
        and st.session_state.uploaded_coordinates
    ):
        if st.button("🗑️ Remove Uploaded Coordinates"):
            del st.session_state.uploaded_coordinates
            if hasattr(st.session_state, "coord_center"):
                del st.session_state.coord_center
            st.success("✅ Uploaded coordinates removed")
            st.rerun()


def render_sidebar():
    """Render complete sidebar"""
    with st.sidebar:
        st.header("⚙️ Isochrone Settings")

        # Provider selection
        provider = st.selectbox(
            "Provider",
            options=["osmnx", "mapbox", "iso4app"],
            index=2,  # default to iso4app since client uses it
            help="Choose routing engine",
        )
        st.session_state.provider = provider

        # Travel time unit selector
        time_unit = st.radio(
            "Time Unit",
            options=["Minutes", "Hours"],
            index=0,
            horizontal=True,
        )

        # Travel time slider - adjusts based on unit
        if time_unit == "Minutes":
            time_value = st.slider(
                "Travel Time",
                min_value=5,
                max_value=120,
                value=30,
                step=5,
                help="Maximum travel time from center (minutes)",
            )
            rho = time_value / 60.0  # Convert to hours for API
            st.session_state.rho_minutes = time_value
        else:
            time_value = st.slider(
                "Travel Time",
                min_value=0.5,
                max_value=6.0,
                value=0.5,
                step=0.5,
                help="Maximum travel time from center (hours)",
            )
            rho = time_value  # Already in hours
            st.session_state.rho_minutes = int(time_value * 60)

        st.session_state.rho = rho

        # Iso4App-specific options
        if provider == "iso4app":
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

            st.session_state.iso4app_type = iso_type
            st.session_state.iso4app_mobility = mobility
            st.session_state.iso4app_speed_type = speed_type
            st.session_state.iso4app_speed_limit = speed_limit

        st.markdown("---")
        handle_coordinate_upload_sidebar()

        st.markdown("---")
        st.write("**Settings:**")
        st.write(f"Provider: {provider}")
        if time_unit == "Minutes":
            st.write(f"Travel time: {time_value} min")
        else:
            st.write(f"Travel time: {time_value}h")

        if provider == "iso4app":
            st.write(f"Type: {iso_type}")
            st.write(f"Mobility: {mobility}")
            st.write(f"Speed: {speed_type}")
            if speed_limit:
                st.write(f"Speed limit: {speed_limit} km/h")

    return provider, rho


def process_isochrone_request(center_name, lat, lng, rho, provider):
    """Process isochrone computation request"""
    payload = {
        "centroids": [{"lat": lat, "lon": lng, "rho": rho, "id": center_name}],
        "options": {
            "provider": provider,
            "travel_speed_kph": 25,
            "num_bands": 1,
        },
    }

    # Iso4App extras
    if provider == "iso4app":
        payload["options"].update(
            {
                "iso4app_type": st.session_state.iso4app_type,
                "iso4app_mobility": st.session_state.iso4app_mobility,
                "iso4app_speed_type": st.session_state.iso4app_speed_type,
                "iso4app_speed_limit": st.session_state.iso4app_speed_limit,
            }
        )

    result = call_api(ISOCHRONES_ENDPOINT, payload)

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
                    {
                        "band_hours": band_hours,
                        "band_label": format_time_display(band_hours),
                        "geojson_feature": feature,
                    }
                )

            if bands_data:
                # Store isochrone with metadata
                speed_kph = payload["options"].get("iso4app_speed_limit") or payload[
                    "options"
                ].get("travel_speed_kph", 25)
                st.session_state.isochrones[center_name] = {
                    "bands": bands_data,
                    "rho": rho,
                    "rho_minutes": int(rho * 60),
                    "speed_kph": speed_kph,
                    "provider": provider,
                }
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


def handle_map_click(map_data, provider, rho):
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

                with st.spinner(f"Computing isochrone for {center_name}..."):
                    success = process_isochrone_request(
                        center_name, lat, lng, rho, provider
                    )

                    if success:
                        # Only persist the marker if the isochrone computed successfully
                        st.session_state.centers[center_name] = {"lat": lat, "lng": lng}
                        st.rerun()

    else:
        st.info(
            "👆 Click anywhere on the map to add a center (you can click on existing isochrones too)"
        )


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

        # Build production sum lookup from analysis results if available
        prod_sum_by_center = {}
        if hasattr(st.session_state, "analysis_result"):
            for cov in st.session_state.analysis_result.get("coverage_analysis", []):
                center_id = cov.get("centroid_id")
                # Sum production from all bands (usually just 1)
                total_prod = sum(
                    band.get("production_sum", 0) or 0 for band in cov.get("bands", [])
                )
                prod_sum_by_center[center_id] = total_prod

        # List all centers with band information, color picker, and max_production input
        for idx, (name, coords) in enumerate(st.session_state.centers.items()):
            bands_info = ""
            if (
                name in st.session_state.isochrones
                and "bands" in st.session_state.isochrones[name]
            ):
                iso_data = st.session_state.isochrones[name]
                num_bands = len(iso_data["bands"])
                rho_min = iso_data.get("rho_minutes", int(iso_data.get("rho", 1) * 60))
                speed = iso_data.get("speed_kph", "N/A")
                bands_info = f" - {num_bands} band(s) | {rho_min}min @ {speed} km/h"

            # Add production sum if available
            prod_sum_info = ""
            if name in prod_sum_by_center:
                prod_sum_info = f" | Prod: {prod_sum_by_center[name]:.1f}"

            col_color, col_info, col_max_prod = st.columns([0.5, 2.5, 1])

            with col_color:
                # Get current color or assign default
                current_color = coords.get(
                    "color", DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
                )
                new_color = st.color_picker(
                    "Color",
                    value=current_color,
                    key=f"color_{name}",
                    label_visibility="collapsed",
                )
                if new_color != coords.get("color"):
                    st.session_state.centers[name]["color"] = new_color

            with col_info:
                st.write(
                    f"**{name}:** {coords['lat']:.5f}, {coords['lng']:.5f}{bands_info}{prod_sum_info}"
                )
            with col_max_prod:
                current_max_prod = coords.get("max_production", 0.0)
                new_max_prod = st.number_input(
                    "Max Prod",
                    min_value=0.0,
                    value=float(current_max_prod),
                    step=100.0,
                    key=f"max_prod_{name}",
                    label_visibility="collapsed",
                    help=f"Max production for {name}",
                )
                if new_max_prod != current_max_prod:
                    st.session_state.centers[name]["max_production"] = new_max_prod


# -------------------------
# SPATIAL ANALYSIS FUNCTIONS
# -------------------------
def send_analysis_request(provider, rho):
    """Send analysis request with all current centers and uploaded coordinates"""
    if not st.session_state.centers:
        return None

    # Prepare centroids from current centers (including per-center max_production)
    centroids = []
    for name, coords in st.session_state.centers.items():
        # Use the stored rho for this center, fallback to current sidebar value
        center_rho = rho
        if name in st.session_state.isochrones:
            center_rho = st.session_state.isochrones[name].get("rho", rho)

        centroid_data = {
            "lat": coords["lat"],
            "lon": coords["lng"],
            "rho": center_rho,
            "id": name,
        }
        # Include max_production if set (> 0)
        max_prod = coords.get("max_production", 0.0)
        if max_prod > 0:
            centroid_data["max_production"] = max_prod
        centroids.append(centroid_data)

    # Prepare POIs from uploaded coordinates
    pois = []
    if hasattr(st.session_state, "uploaded_coordinates"):
        for coord in st.session_state.uploaded_coordinates:
            pois.append(
                {
                    "id": coord.id,
                    "lat": coord.lat,
                    "lon": coord.lon,
                    "name": coord.name,
                    "region": coord.region,
                    "municipality": coord.municipality,
                    "metadata": coord.metadata,
                }
            )

    payload = {
        "centroids": centroids,
        "options": {
            "provider": provider,
            "travel_speed_kph": 25,
            "num_bands": 1,
        },
        "pois": pois if pois else None,
    }

    if provider == "iso4app":
        payload["options"].update(
            {
                "iso4app_type": st.session_state.iso4app_type,
                "iso4app_mobility": st.session_state.iso4app_mobility,
                "iso4app_speed_type": st.session_state.iso4app_speed_type,
                "iso4app_speed_limit": st.session_state.iso4app_speed_limit,
            }
        )

    return call_api(ISOCHRONES_ENDPOINT, payload)


def render_analysis_summary(analysis):
    """Render high-level analysis summary"""
    st.subheader("📊 Analysis Summary")

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            "Total POIs",
            analysis["total_pois"],
            help="Total points of interest analyzed",
        )

    with col2:
        noi = analysis.get("network_optimization_index", None)
        help_msg = f"(X - Y - Z) / total_pois - measures how efficiently the network covers POIs"
        if noi is not None:
            st.metric(
                "Network Optimization Index",
                f"{noi:.3f}",
                help=help_msg,
            )
        else:
            st.metric("Network Optimization Index", "N/A")

    with col3:
        coverage = analysis["global_coverage_percentage"]
        st.metric(
            "Coverage",
            f"{coverage:.1f}%",
            help="Percentage of POIs covered by at least one isochrone",
        )

    with col4:
        intersections = analysis["intersection_analysis"]["total_intersections"]
        st.metric(
            "Intersections",
            intersections,
            help="Number of overlapping areas between different centers",
        )

    with col5:
        total_pois = analysis["total_pois"]
        oob_count = analysis["oob_analysis"]["total_oob_pois"]
        covered_count = total_pois - oob_count
        st.metric(
            "Covered",
            covered_count,
            help="POIs covered by at least one isochrone",
        )

    with col6:
        oob_count = analysis["oob_analysis"]["total_oob_pois"]
        st.metric(
            "Uncovered",
            oob_count,
            delta=f"-{analysis['oob_analysis']['oob_percentage']:.1f}%",
            delta_color="inverse",
            help="POIs outside all coverage areas",
        )


def render_coverage_analysis(coverage_analysis):
    """Render coverage analysis in a single combined table"""
    st.subheader("🎯 Coverage Analysis")

    # Build combined table data from all centers
    table_data = []
    for centroid_coverage in coverage_analysis:
        center_id = centroid_coverage["centroid_id"]
        for band in centroid_coverage["bands"]:
            # Determine viable display value
            viable_value = band.get("viable")
            if viable_value is True:
                viable_display = "✅ Yes"
            elif viable_value is False:
                viable_display = "❌ No"
            else:
                viable_display = "-"

            table_data.append(
                {
                    "Center": center_id,
                    "Time Band": band["band_label"],
                    "POIs Covered": band["poi_count"],
                    "Coverage %": f"{band['coverage_percentage']:.1f}%",
                    "Prod Sum": f"{band.get('production_sum', 0):.1f}",
                    "Viable": viable_display,
                }
            )

    if table_data:
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # Summary stats
        total_centers = len(coverage_analysis)
        viable_count = sum(1 for row in table_data if "Yes" in row["Viable"])
        not_viable_count = sum(1 for row in table_data if "No" in row["Viable"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Centers", total_centers)
        with col2:
            st.metric("Viable", viable_count)
        with col3:
            st.metric("Not Viable", not_viable_count)


def render_intersection_analysis(intersection_analysis):
    """Render intersection analysis"""
    if intersection_analysis["total_intersections"] == 0:
        st.info("ℹ️ No intersections found between centers")
        return

    st.subheader("🔄 Intersection Analysis")

    # Pairwise intersections
    pairwise = intersection_analysis["pairwise_intersections"]
    if pairwise:
        st.write("**2-way Overlaps:**")

        # Sort by POI count for better presentation
        sorted_pairwise = sorted(pairwise, key=lambda x: x["poi_count"], reverse=True)

        for intersection in sorted_pairwise[:5]:  # Show top 5
            label = intersection["intersection_label"]
            poi_count = intersection["poi_count"]

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {label}")
            with col2:
                st.code(f"{poi_count} POIs")

        if len(pairwise) > 5:
            st.caption(f"... and {len(pairwise) - 5} more intersections")

    # Multi-way intersections
    multiway = intersection_analysis["multiway_intersections"]
    if multiway:
        st.write("**Multi-way Overlaps:**")
        for intersection in multiway:
            label = intersection["intersection_label"]
            poi_count = intersection["poi_count"]
            overlap_type = intersection["overlap_type"]

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {label} ({overlap_type})")
            with col2:
                st.code(f"{poi_count} POIs")


def render_out_of_band_analysis(oob_analysis):
    """Render out-of-band analysis"""
    if oob_analysis["total_oob_pois"] == 0:
        st.success("🎉 All POIs are covered by at least one center!")
        return

    st.subheader("🚫 Uncovered Areas")

    oob_count = oob_analysis["total_oob_pois"]
    oob_percentage = oob_analysis["oob_percentage"]

    st.warning(
        f"⚠️ {oob_count} POIs ({oob_percentage:.1f}%) are not covered by any center"
    )

    # Show some uncovered POI IDs
    oob_ids = oob_analysis["oob_poi_ids"]
    if len(oob_ids) <= 10:
        st.write("**Uncovered POIs:**", ", ".join(oob_ids))
    else:
        st.write(
            f"**Uncovered POIs:** {', '.join(oob_ids[:10])}, ... and {len(oob_ids) - 10} more"
        )


def render_spatial_analysis_panel():
    """Render the complete spatial analysis panel"""
    # Only show if we have both centers and uploaded coordinates
    if not st.session_state.centers or not hasattr(
        st.session_state, "uploaded_coordinates"
    ):
        return

    st.markdown("---")
    st.header("🧮 Spatial Analysis")

    # Get current settings
    provider = st.session_state.get("provider", "osmnx")
    rho = st.session_state.get("rho", 1.0)

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("🔍 Analyze Coverage", type="primary", use_container_width=True):
            with st.spinner("Computing spatial analysis..."):
                try:
                    result = send_analysis_request(provider, rho)

                    if (
                        result
                        and "spatial_analysis" in result
                        and result["spatial_analysis"]
                    ):
                        st.session_state.analysis_result = result["spatial_analysis"]
                        st.success("✅ Analysis complete!")
                        st.rerun()  # Refresh to update map tooltips
                    else:
                        st.error("❌ Analysis failed - no POI data in response")

                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")

    with col2:
        st.caption(
            f"Analyze {len(st.session_state.centers)} centers "
            f"against {len(st.session_state.uploaded_coordinates)} POIs"
        )

    # Show analysis results if available
    if hasattr(st.session_state, "analysis_result"):
        analysis = st.session_state.analysis_result

        # Summary metrics
        render_analysis_summary(analysis)

        # Detailed analysis in tabs
        tab1, tab2, tab3 = st.tabs(["🎯 Coverage", "🔄 Intersections", "🚫 Uncovered"])

        with tab1:
            render_coverage_analysis(analysis["coverage_analysis"])

        with tab2:
            render_intersection_analysis(analysis["intersection_analysis"])

        with tab3:
            render_out_of_band_analysis(analysis["oob_analysis"])


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
    provider, rho = render_sidebar()

    # Main content
    st.title("🗺️ Click to Add Isochrone Centers")
    st.markdown("Click anywhere on the map to see coordinates")

    # Draw map (fragment)
    map_data = draw_map()

    # Handle map interactions
    handle_map_click(map_data, provider, rho)

    # Render controls
    render_center_controls()

    # Render spatial analysis panel
    render_spatial_analysis_panel()


if __name__ == "__main__":
    main()
