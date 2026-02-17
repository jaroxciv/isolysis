import os

import folium as fl
import streamlit as st
from dotenv import find_dotenv, load_dotenv
from streamlit_folium import st_folium

from api.utils import (
    call_api,
    format_time_display,
    get_coordinates_center,
    get_map_center,
    get_pos,
    handle_coordinate_upload,
)
from translations import get_selectbox_options, t

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

# Initialize language before set_page_config
if "lang" not in st.session_state:
    st.session_state.lang = "es"

# Page config
st.set_page_config(page_title=t("page.isochrone_title"), layout="wide")


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
                viable_str = (
                    f"<br>{t('tooltip.max_prod')}: {max_prod:,.0f}"
                    f"<br>{t('tooltip.viable_yes')}"
                )
            elif cov_data["viable"] is False:
                viable_str = (
                    f"<br>{t('tooltip.max_prod')}: {max_prod:,.0f}"
                    f"<br>{t('tooltip.viable_no')}"
                )

            tooltip_html = (
                f"<b>{name}</b><br>"
                f"{t('tooltip.time_band')}: {cov_data['band_label']}<br>"
                f"{t('tooltip.pois_covered')}: {cov_data['poi_count']}<br>"
                f"{t('tooltip.coverage')}: {cov_data['coverage_percentage']:.1f}%<br>"
                f"{t('tooltip.prod_sum')}: {cov_data['production_sum']:,.0f}{viable_str}"
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
                    f"<br><b>{t('tooltip.max_prod')}:</b> {max_prod:,.0f}"
                    f"<br><b>{t('viable.yes')}:</b> ✅"
                )
            elif cov_data["viable"] is False:
                viable_str = (
                    f"<br><b>{t('tooltip.max_prod')}:</b> {max_prod:,.0f}"
                    f"<br><b>{t('viable.no')}:</b> ❌"
                )

            popup_html = f"""
            <div style="font-family: sans-serif; font-size: 12px;">
            <b>{name}</b><br>
            <b>{t("tooltip.time_band")}:</b> {cov_data["band_label"]}<br>
            <b>{t("tooltip.pois_covered")}:</b> {cov_data["poi_count"]}<br>
            <b>{t("tooltip.coverage")}:</b> {cov_data["coverage_percentage"]:.1f}%<br>
            <b>{t("tooltip.prod_sum")}:</b> {cov_data["production_sum"]:,.0f}{viable_str}
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
                <b>{t("tooltip.lat")}</b>: {coord.lat:.5f}<br>
                <b>{t("tooltip.lon")}</b>: {coord.lon:.5f}<br>
                <b>{t("tooltip.region")}</b>: {coord.region or t("tooltip.na")}<br>
                <b>{t("tooltip.municipality")}</b>: {coord.municipality or t("tooltip.na")}
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
            geojson_feature = band_data["geojson_feature"]

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
        height=700,
        width=None,
        returned_objects=["last_clicked"],
    )


def handle_coordinate_upload_sidebar():
    """Handle coordinate upload in sidebar"""
    st.subheader(t("upload.header"))
    uploaded_file = st.file_uploader(
        t("upload.label"),
        type=["json", "csv", "xlsx"],
        help=t("upload.help"),
    )

    if uploaded_file is not None:
        coordinates = handle_coordinate_upload(uploaded_file)
        if coordinates:
            st.success(t("upload.success", count=len(coordinates)))
            st.session_state.uploaded_coordinates = coordinates
            if coordinates:
                coord_center = get_coordinates_center(coordinates)
                st.session_state.coord_center = coord_center

    # Add remove button if we have uploaded coordinates
    if (
        hasattr(st.session_state, "uploaded_coordinates")
        and st.session_state.uploaded_coordinates
    ):
        if st.button(t("upload.remove_btn")):
            del st.session_state.uploaded_coordinates
            if hasattr(st.session_state, "coord_center"):
                del st.session_state.coord_center
            st.success(t("upload.removed"))
            st.rerun()


def render_sidebar():
    """Render complete sidebar"""
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

        st.header(t("sidebar.header"))

        # Provider selection
        provider = st.selectbox(
            t("sidebar.provider"),
            options=["osmnx", "mapbox", "iso4app"],
            index=2,  # default to iso4app since client uses it
            help=t("sidebar.provider_help"),
        )
        st.session_state.provider = provider

        # Travel time unit selector
        time_unit_labels = [t("sidebar.minutes"), t("sidebar.hours")]
        time_unit = st.radio(
            t("sidebar.time_unit"),
            options=time_unit_labels,
            index=0,
            horizontal=True,
        )

        # Travel time slider - adjusts based on unit
        if time_unit == t("sidebar.minutes"):
            time_value = st.slider(
                t("sidebar.travel_time"),
                min_value=5,
                max_value=120,
                value=30,
                step=5,
                help=t("sidebar.travel_time_help_min"),
            )
            rho = time_value / 60.0  # Convert to hours for API
            st.session_state.rho_minutes = time_value
        else:
            time_value = st.slider(
                t("sidebar.travel_time"),
                min_value=0.5,
                max_value=6.0,
                value=0.5,
                step=0.5,
                help=t("sidebar.travel_time_help_hrs"),
            )
            rho = time_value  # Already in hours
            st.session_state.rho_minutes = int(time_value * 60)

        st.session_state.rho = rho

        # Iso4App-specific options
        if provider == "iso4app":
            # Isoline type
            iso_labels, iso_values = get_selectbox_options("isoline_type")
            selected_iso = st.selectbox(
                t("sidebar.isoline_type"),
                iso_labels,
                index=0,
                help=t("sidebar.isoline_type_help"),
            )
            iso_type = iso_values[iso_labels.index(selected_iso)]

            # Travel mode
            mode_labels, mode_values = get_selectbox_options("travel_mode")
            selected_mode = st.selectbox(
                t("sidebar.travel_mode"),
                mode_labels,
                index=0,
            )
            mobility = mode_values[mode_labels.index(selected_mode)]

            # Speed profile
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

            st.session_state.iso4app_type = iso_type
            st.session_state.iso4app_mobility = mobility
            st.session_state.iso4app_speed_type = speed_type
            st.session_state.iso4app_speed_limit = speed_limit

        st.markdown("---")
        handle_coordinate_upload_sidebar()

        st.markdown("---")
        st.write(t("sidebar.settings_label"))
        st.write(t("sidebar.settings_provider", provider=provider))
        if time_unit == t("sidebar.minutes"):
            st.write(t("sidebar.settings_time_min", value=time_value))
        else:
            st.write(t("sidebar.settings_time_hrs", value=time_value))

        if provider == "iso4app":
            st.write(t("sidebar.settings_type", type=st.session_state.iso4app_type))
            st.write(
                t(
                    "sidebar.settings_mobility",
                    mobility=st.session_state.iso4app_mobility,
                )
            )
            st.write(
                t("sidebar.settings_speed", speed=st.session_state.iso4app_speed_type)
            )
            if st.session_state.get("iso4app_speed_limit"):
                st.write(
                    t(
                        "sidebar.settings_speed_limit",
                        limit=st.session_state.iso4app_speed_limit,
                    )
                )

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
                    st.warning(t("iso.band_missing"))
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
                    t("iso.added", name=center_name, count=band_count, cache=cache_msg)
                )
                return True
            else:
                st.error(t("iso.no_band_data", name=center_name))
        else:
            st.error(t("iso.no_geojson", name=center_name))
    else:
        st.error(t("iso.failed", name=center_name))
    return False


def handle_map_click(map_data, provider, rho):
    """Handle map click interactions"""
    data = None
    if map_data.get("last_clicked"):
        data = get_pos(map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])

    if data is not None:
        lat, lng = data
        st.success(t("map.clicked", lat=f"{lat:.5f}", lng=f"{lng:.5f}"))

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.metric(t("map.latitude"), f"{lat:.5f}")
        with col2:
            st.metric(t("map.longitude"), f"{lng:.5f}")
        with col3:
            if st.button(t("map.add_center"), type="primary"):
                center_name = f"Center{len(st.session_state.centers) + 1}"

                with st.spinner(t("map.computing", name=center_name)):
                    success = process_isochrone_request(
                        center_name, lat, lng, rho, provider
                    )

                    if success:
                        # Only persist the marker if the isochrone computed successfully
                        st.session_state.centers[center_name] = {"lat": lat, "lng": lng}
                        st.rerun()

    else:
        st.info(t("map.click_hint"))


def render_center_controls():
    """Render center management controls"""
    if st.session_state.centers:
        st.markdown("---")

        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.subheader(t("centers.header", count=len(st.session_state.centers)))
        with col2:
            if st.button(t("centers.undo")):
                if st.session_state.centers:
                    last_key = list(st.session_state.centers.keys())[-1]
                    del st.session_state.centers[last_key]
                    if last_key in st.session_state.isochrones:
                        del st.session_state.isochrones[last_key]
                    st.success(t("centers.removed", name=last_key))
        with col3:
            if st.button(t("centers.clear_polygons")):
                count = len(st.session_state.isochrones)
                st.session_state.isochrones = {}
                st.success(t("centers.cleared_polygons", count=count))
        with col4:
            if st.button(t("centers.clear_all")):
                center_count = len(st.session_state.centers)
                poly_count = len(st.session_state.isochrones)
                st.session_state.centers = {}
                st.session_state.isochrones = {}
                st.success(
                    t("centers.cleared_all", centers=center_count, polygons=poly_count)
                )

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
                bands_info = t(
                    "centers.bands_info", bands=num_bands, minutes=rho_min, speed=speed
                )

            # Add production sum and viability if available
            prod_sum_info = ""
            if name in prod_sum_by_center:
                prod_sum = prod_sum_by_center[name]
                max_prod = coords.get("max_production", 0.0)
                viable_tag = ""
                if max_prod > 0:
                    if prod_sum <= max_prod:
                        viable_tag = (
                            f' | <span style="color: #4CAF50;">{t("viable.yes")}</span>'
                        )
                    else:
                        viable_tag = (
                            f' | <span style="color: #F44336;">{t("viable.no")}</span>'
                        )
                prod_sum_info = f" | <u>Agg Prod: {prod_sum:,.0f}</u>{viable_tag}"

            col_color, col_info, col_lbl, col_input = st.columns([0.3, 2.5, 0.5, 0.7])

            with col_color:
                # Get current color or assign default
                current_color = coords.get(
                    "color", DEFAULT_COLORS[idx % len(DEFAULT_COLORS)]
                )
                new_color = st.color_picker(
                    t("centers.color_label"),
                    value=current_color,
                    key=f"color_{name}",
                    label_visibility="collapsed",
                )
                if new_color != coords.get("color"):
                    st.session_state.centers[name]["color"] = new_color

            with col_info:
                st.markdown(
                    f'<div style="padding-top: 0.5em; font-size: 1.1em;"><b>{name}:</b> {coords["lat"]:.5f}, {coords["lng"]:.5f}{bands_info}{prod_sum_info}</div>',
                    unsafe_allow_html=True,
                )
            with col_lbl:
                st.markdown(
                    f'<div style="padding-top: 0.5em; font-size: 1.1em; text-align: right;">{t("centers.max_prod_label")}</div>',
                    unsafe_allow_html=True,
                )
            with col_input:
                current_max_prod = coords.get("max_production", 0.0)
                new_max_prod = st.number_input(
                    t("centers.max_prod_label"),
                    min_value=0.0,
                    value=float(current_max_prod),
                    step=100.0,
                    key=f"max_prod_{name}",
                    label_visibility="collapsed",
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
    st.subheader(t("summary.header"))

    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.metric(
            t("summary.total_pois"),
            analysis["total_pois"],
            help=t("summary.total_pois_help"),
        )

    with col2:
        noi = analysis.get("network_optimization_index", None)
        if noi is not None:
            st.metric(
                t("summary.noi"),
                f"{noi:.3f}",
                help=t("summary.noi_help"),
            )
        else:
            st.metric(t("summary.noi"), "N/A")

    with col3:
        coverage = analysis["global_coverage_percentage"]
        st.metric(
            t("summary.coverage"),
            f"{coverage:.1f}%",
            help=t("summary.coverage_help"),
        )

    with col4:
        intersections = analysis["intersection_analysis"]["total_intersections"]
        st.metric(
            t("summary.intersections"),
            intersections,
            help=t("summary.intersections_help"),
        )

    with col5:
        total_pois = analysis["total_pois"]
        oob_count = analysis["oob_analysis"]["total_oob_pois"]
        covered_count = total_pois - oob_count
        st.metric(
            t("summary.covered"),
            covered_count,
            help=t("summary.covered_help"),
        )

    with col6:
        oob_count = analysis["oob_analysis"]["total_oob_pois"]
        st.metric(
            t("summary.uncovered"),
            oob_count,
            delta=f"-{analysis['oob_analysis']['oob_percentage']:.1f}%",
            delta_color="inverse",
            help=t("summary.uncovered_help"),
        )


def render_coverage_analysis(coverage_analysis):
    """Render coverage analysis in a single combined table"""
    st.subheader(t("coverage.header"))

    # Build combined table data from all centers
    table_data = []
    for centroid_coverage in coverage_analysis:
        center_id = centroid_coverage["centroid_id"]
        for band in centroid_coverage["bands"]:
            # Determine viable display value
            viable_value = band.get("viable")
            if viable_value is True:
                viable_display = t("coverage.viable_yes")
            elif viable_value is False:
                viable_display = t("coverage.viable_no")
            else:
                viable_display = t("coverage.viable_na")

            table_data.append(
                {
                    t("coverage.col_center"): center_id,
                    t("coverage.col_time_band"): band["band_label"],
                    t("coverage.col_pois_covered"): band["poi_count"],
                    t(
                        "coverage.col_coverage_pct"
                    ): f"{band['coverage_percentage']:.1f}%",
                    t("coverage.col_prod_sum"): f"{band.get('production_sum', 0):.1f}",
                    t("coverage.col_viable"): viable_display,
                }
            )

    if table_data:
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # Summary stats
        total_centers = len(coverage_analysis)
        viable_key = t("coverage.col_viable")
        viable_count = sum(
            1 for row in table_data if row.get(viable_key) == t("coverage.viable_yes")
        )
        not_viable_count = sum(
            1 for row in table_data if row.get(viable_key) == t("coverage.viable_no")
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t("coverage.total_centers"), total_centers)
        with col2:
            st.metric(t("coverage.viable_count"), viable_count)
        with col3:
            st.metric(t("coverage.not_viable_count"), not_viable_count)


def render_intersection_analysis(intersection_analysis):
    """Render intersection analysis"""
    if intersection_analysis["total_intersections"] == 0:
        st.info(t("intersection.no_intersections"))
        return

    st.subheader(t("intersection.header"))

    # Pairwise intersections
    pairwise = intersection_analysis["pairwise_intersections"]
    if pairwise:
        st.write(t("intersection.pairwise"))

        # Sort by POI count for better presentation
        sorted_pairwise = sorted(pairwise, key=lambda x: x["poi_count"], reverse=True)

        for intersection in sorted_pairwise[:5]:  # Show top 5
            label = intersection["intersection_label"]
            poi_count = intersection["poi_count"]

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {label}")
            with col2:
                st.code(t("intersection.pois_label", count=poi_count))

        if len(pairwise) > 5:
            st.caption(t("intersection.more", count=len(pairwise) - 5))

    # Multi-way intersections
    multiway = intersection_analysis["multiway_intersections"]
    if multiway:
        st.write(t("intersection.multiway"))
        for intersection in multiway:
            label = intersection["intersection_label"]
            poi_count = intersection["poi_count"]
            overlap_type = intersection["overlap_type"]

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {label} ({overlap_type})")
            with col2:
                st.code(t("intersection.pois_label", count=poi_count))


def render_out_of_band_analysis(oob_analysis):
    """Render out-of-band analysis"""
    if oob_analysis["total_oob_pois"] == 0:
        st.success(t("oob.all_covered"))
        return

    st.subheader(t("oob.header"))

    oob_count = oob_analysis["total_oob_pois"]
    oob_percentage = oob_analysis["oob_percentage"]

    st.warning(t("oob.warning", count=oob_count, pct=f"{oob_percentage:.1f}"))

    # Show some uncovered POI IDs
    oob_ids = oob_analysis["oob_poi_ids"]
    if len(oob_ids) <= 10:
        st.write(t("oob.uncovered_pois"), ", ".join(oob_ids))
    else:
        st.write(
            f"{t('oob.uncovered_pois')} {', '.join(oob_ids[:10])}, {t('oob.and_more', count=len(oob_ids) - 10)}"
        )


def render_export_button(analysis):
    """Render export button to download coordinates with center coverage columns"""
    from datetime import datetime

    import pandas as pd

    # Generate filename with date suffix (YYMMDD)
    date_suffix = datetime.now().strftime("%y%m%d")
    filename = f"coverage_export_{date_suffix}.csv"

    # Build POI coverage lookup from analysis
    poi_in_center = {}  # {center_id: set of poi_ids}
    for cov in analysis.get("coverage_analysis", []):
        center_id = cov.get("centroid_id")
        poi_ids = set()
        for band in cov.get("bands", []):
            poi_ids.update(band.get("poi_ids", []))
        poi_in_center[center_id] = poi_ids

    # Build DataFrame from uploaded coordinates
    coords = st.session_state.uploaded_coordinates

    # Check if any coordinate has region/municipality data
    has_region = any(c.region is not None for c in coords)
    has_municipality = any(c.municipality is not None for c in coords)

    data = []
    for coord in coords:
        row = {
            "id": coord.id,
            "Nombre": coord.name,
            "Latitud": coord.lat,
            "Longitud": coord.lon,
        }
        # Add Region/Municipality only if they exist in the data
        if has_region:
            row["Region"] = coord.region
        if has_municipality:
            row["Municipality"] = coord.municipality

        # Add metadata fields if available
        if coord.metadata:
            row["Categoria"] = coord.metadata.get("Categoria", "")
            row["Subcategoria"] = coord.metadata.get("Subcategoria", "")
            row["Prod"] = coord.metadata.get("Prod", 0)

        # Add binary columns for each center
        for center_id in st.session_state.centers.keys():
            row[center_id] = 1 if coord.id in poi_in_center.get(center_id, set()) else 0

        data.append(row)

    df = pd.DataFrame(data)

    # Convert to CSV
    csv_data = df.to_csv(index=False)

    st.download_button(
        label=t("export.btn"),
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )


def render_spatial_analysis_panel():
    """Render the complete spatial analysis panel"""
    # Only show if we have both centers and uploaded coordinates
    if not st.session_state.centers or not hasattr(
        st.session_state, "uploaded_coordinates"
    ):
        return

    st.markdown("---")
    st.header(t("analysis.header"))

    # Get current settings
    provider = st.session_state.get("provider", "osmnx")
    rho = st.session_state.get("rho", 1.0)

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button(
            t("analysis.analyze_btn"), type="primary", use_container_width=True
        ):
            with st.spinner(t("analysis.computing")):
                try:
                    result = send_analysis_request(provider, rho)

                    if (
                        result
                        and "spatial_analysis" in result
                        and result["spatial_analysis"]
                    ):
                        st.session_state.analysis_result = result["spatial_analysis"]
                        st.success(t("analysis.complete"))
                        st.rerun()  # Refresh to update map tooltips
                    else:
                        st.error(t("analysis.failed_no_data"))

                except Exception as e:
                    st.error(t("analysis.failed", error=str(e)))

    with col2:
        st.caption(
            t(
                "analysis.caption",
                centers=len(st.session_state.centers),
                pois=len(st.session_state.uploaded_coordinates),
            )
        )

    # Show analysis results if available
    if hasattr(st.session_state, "analysis_result"):
        analysis = st.session_state.analysis_result

        # Summary metrics
        render_analysis_summary(analysis)

        # Export button
        render_export_button(analysis)

        # Detailed analysis in tabs
        tab1, tab2, tab3 = st.tabs(
            [t("tab.coverage"), t("tab.intersections"), t("tab.uncovered")]
        )

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
    st.title(t("main.title"))

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
