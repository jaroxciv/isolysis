import json
import uuid
from typing import Dict, List, Optional, Tuple

import folium as fl
import pandas as pd
import rasterio
import requests
import streamlit as st
from loguru import logger

from isolysis.io import Coordinate

REQUIRED_COLUMNS = {"Categoria", "Subcategoria", "Nombre", "Latitud", "Longitud"}


def get_pos(lat, lng):
    return lat, lng


def call_api(url: str, payload: Dict) -> Optional[Dict]:
    """Call the isochrones API endpoint"""
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


def get_map_center():
    """Get map center based on uploaded coordinates or last added centroid"""
    # Priority 1: Use uploaded coordinates center
    if hasattr(st.session_state, "coord_center"):
        return list(st.session_state.coord_center)

    # Priority 2: Use last centroid
    if st.session_state.centers:
        last_center_name = list(st.session_state.centers.keys())[-1]
        last_coords = st.session_state.centers[last_center_name]
        return [last_coords["lat"], last_coords["lng"]]

    # Default: El Salvador 🇸🇻
    return [13.7942, -88.8965]


def format_time_display(hours: float) -> str:
    """Convert hours to a readable time format"""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes}min"
    elif hours == int(hours):
        return f"{int(hours)}h"
    else:
        return f"{hours}h"


def get_band_color(
    band_index: int, total_bands: int, colormap: str = "viridis"
) -> tuple:
    """Get a color for the band based on its index using matplotlib colormaps"""
    import matplotlib.colors as mcolors
    import matplotlib.pyplot as plt

    # Get the colormap
    try:
        cmap = plt.get_cmap(colormap)
    except ValueError:
        # Fallback to viridis if colormap not found
        cmap = plt.get_cmap("viridis")

    if total_bands == 1:
        # Single band gets middle of the colormap
        color_value = 0.5
    else:
        # For multiple bands, map band_index to colormap
        # Reverse the mapping so smaller time = darker/more intense color
        color_value = (total_bands - band_index - 1) / (total_bands - 1)

    # Get RGBA color from colormap
    rgba = cmap(color_value)

    # Convert to hex for fill color
    hex_color = mcolors.rgb2hex(rgba[:3])

    # Create darker border color by reducing brightness
    border_rgba = tuple(max(0, c * 0.7) for c in rgba[:3]) + (rgba[3],)
    border_hex = mcolors.rgb2hex(border_rgba[:3])

    return hex_color, border_hex


# -----------------------------
# Shared utilities
# -----------------------------
def _to_float(x):
    """Convert '13,45' or '13.45' safely to float."""
    if pd.isna(x):
        return None
    if isinstance(x, str):
        x = x.strip().replace(",", ".")
    try:
        return float(x)
    except Exception:
        return None


# -----------------------------
# JSON parser
# -----------------------------
def _parse_json_coordinates(uploaded_file) -> Optional[List[Coordinate]]:
    """
    Parse JSON coordinate file (like localization.json).
    Expected: list of dicts with 'lat' and 'lon' keys.
    """
    try:
        # Read and parse JSON
        content = uploaded_file.read()
        data = json.loads(content)

        if not isinstance(data, list):
            logger.error("❌ JSON must be a list of coordinate objects.")
            return None

        normalized = []
        for item in data:
            # Normalize coordinates
            if "lat" in item:
                item["lat"] = float(item["lat"])
            if "lon" in item:
                item["lon"] = float(item["lon"])
            if "lng" in item and "lon" not in item:
                item["lon"] = float(item.pop("lng"))

            # Ensure id
            if "id" not in item:
                item["id"] = str(uuid.uuid4())

            # Optional: fold extra fields into metadata
            metadata = {
                k: v
                for k, v in item.items()
                if k not in ["id", "lat", "lon", "name", "region", "municipality"]
            }
            if metadata:
                item["metadata"] = metadata

            normalized.append(item)

        coordinates = [Coordinate(**item) for item in normalized]
        logger.success(f"✅ Loaded {len(coordinates)} coordinates from JSON")
        return coordinates

    except json.JSONDecodeError:
        logger.error("❌ Invalid JSON format")
        return None
    except Exception as e:
        logger.error(f"❌ Error parsing JSON coordinates: {e}")
        return None


# -----------------------------
# CSV / XLSX parser
# -----------------------------
def _parse_tabular_coordinates(uploaded_file) -> Optional[List[Coordinate]]:
    """
    Parse coordinates from CSV or XLSX files.
    Requires columns: Categoria, Subcategoria, Nombre, Latitude, Longitud.
    Optional column: Prod (production value for viability checking).
    """
    try:
        file_name = uploaded_file.name.lower()
        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            logger.error("❌ Unsupported tabular file type.")
            return None

        # Normalize headers
        df.columns = [str(c).strip() for c in df.columns]

        # Validate required columns
        missing = REQUIRED_COLUMNS.difference(df.columns)
        if missing:
            logger.error(f"❌ Missing required columns: {', '.join(sorted(missing))}")
            return None

        # Clean data
        df["Latitud"] = df["Latitud"].apply(_to_float)
        df["Longitud"] = df["Longitud"].apply(_to_float)
        df["Nombre"] = df["Nombre"].astype(str).str.strip()
        df["Categoria"] = df["Categoria"].astype(str).str.strip()
        df["Subcategoria"] = df["Subcategoria"].astype(str).str.strip()

        # Handle optional Prod column
        has_prod = "Prod" in df.columns
        if has_prod:
            df["Prod"] = df["Prod"].apply(_to_float)
            logger.info("📊 Found 'Prod' column - production values will be included")

        df = df.dropna(subset=["Latitud", "Longitud"])
        df = df[(df["Latitud"].between(-90, 90)) & (df["Longitud"].between(-180, 180))]

        coordinates = []
        for i, row in df.iterrows():
            prod_value = float(row.get("Prod", 0) or 0) if has_prod else 0.0
            coordinates.append(
                Coordinate(
                    id=f"poi_{i + 1}",
                    name=row["Nombre"],
                    lat=row["Latitud"],
                    lon=row["Longitud"],
                    region=None,
                    municipality=None,
                    metadata={
                        "Categoria": row["Categoria"],
                        "Subcategoria": row["Subcategoria"],
                        "Prod": prod_value,
                    },
                )
            )

        logger.success(f"✅ Loaded {len(coordinates)} coordinates from {file_name}")
        return coordinates

    except Exception as e:
        logger.error(f"❌ Error parsing tabular coordinates: {e}")
        return None


# -----------------------------
# Generic dispatcher
# -----------------------------
@st.cache_data
def handle_coordinate_upload(uploaded_file) -> Optional[List[Coordinate]]:
    """
    Detect file type and delegate parsing.
    Supports: JSON, CSV, XLSX.
    Returns a list[Coordinate] or None.
    """
    try:
        file_name = uploaded_file.name.lower()

        if file_name.endswith(".json"):
            return _parse_json_coordinates(uploaded_file)

        elif file_name.endswith((".csv", ".xlsx", ".xls")):
            return _parse_tabular_coordinates(uploaded_file)

        else:
            logger.error("❌ Unsupported file type. Use JSON, CSV, or XLSX.")
            return None

    except Exception as e:
        logger.error(f"❌ Error processing coordinate upload: {e}")
        return None


def get_coordinates_center(coordinates: List[Coordinate]) -> Tuple[float, float]:
    """Calculate average lat/lon from list of coordinates"""
    avg_lat = sum(coord.lat for coord in coordinates) / len(coordinates)
    avg_lon = sum(coord.lon for coord in coordinates) / len(coordinates)
    return avg_lat, avg_lon


def add_coordinates_to_map(folium_map, coordinates: List[Coordinate]):
    """Add coordinate markers to folium map"""
    for coord in coordinates:
        # Use name or id for marker label
        label = coord.name or coord.id or "Unknown"

        fl.CircleMarker(
            location=[coord.lat, coord.lon],
            radius=3,
            popup=f"<b>{label}</b><br>"
            f"<b>Lat</b>: {coord.lat:.5f}<br>"
            f"<b>Lon</b>: {coord.lon:.5f}<br>"
            f"<b>Region</b>: {coord.region or 'N/A'}<br>"
            f"<b>Municipality</b>: {coord.municipality or 'N/A'}",
            tooltip=label,
            color="black",
            weight=1,
            fillColor="grey",
            fillOpacity=0.5,
            opacity=0.8,
        ).add_to(folium_map)


def resolve_project_path(path: str, must_exist: bool = True) -> str:
    """
    Normalize and resolve a file path (absolute or relative) within the project.

    Ensures consistent behavior between Streamlit (frontend) and FastAPI (backend)
    when working with uploaded files stored under `data/tmp`.

    Args:
        path (str): The input file path (absolute or relative).
        must_exist (bool): If True, logs a warning when the resolved path does not exist.

    Returns:
        str: The absolute, normalized path.
    """
    import os

    if not path:
        return None

    try:
        # Normalize slashes and collapse redundant parts
        p = os.path.normpath(path)

        # Convert to absolute if relative
        if not os.path.isabs(p):
            p = os.path.join(os.getcwd(), p)

        # Warn if missing
        if must_exist and not os.path.exists(p):
            logger.warning(f"⚠️ File not found or inaccessible: {p}")

        return p
    except Exception as e:
        logger.error(f"❌ Failed to resolve path '{path}': {e}")
        return path
