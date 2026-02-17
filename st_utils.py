"""Shared Streamlit/Folium utilities used by both st_app.py and st_raster_app.py."""

import json
import uuid
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st
from loguru import logger

from isolysis.analysis import format_time_display  # noqa: F401 — re-export
from isolysis.constants import DEFAULT_MAP_CENTER
from isolysis.models import Coordinate
from translations import t

REQUIRED_COLUMNS = {"Categoria", "Subcategoria", "Nombre", "Latitud", "Longitud"}


def call_api(url: str, payload: Dict) -> Optional[Dict]:
    """Call the isochrones API endpoint"""
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.HTTPError as e:
        # Extract detail from FastAPI JSON error response
        detail = str(e)
        try:
            body = e.response.json()  # type: ignore[union-attr]
            if "detail" in body:
                detail = body["detail"]
        except Exception:
            pass
        st.error(t("api.error", error=detail))
        return None
    except Exception as e:
        st.error(t("api.error", error=str(e)))
        return None


def get_map_center():
    """Get map center based on uploaded coordinates or last added centroid"""
    # Priority 1: Use uploaded coordinates center
    if "coord_center" in st.session_state:
        c = st.session_state.coord_center
        return (float(c[0]), float(c[1]))

    # Priority 2: Use last centroid
    if st.session_state.centers:
        last_center_name = list(st.session_state.centers.keys())[-1]
        last_coords = st.session_state.centers[last_center_name]
        return (float(last_coords["lat"]), float(last_coords["lng"]))

    # Default: El Salvador
    return DEFAULT_MAP_CENTER


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
    r, g, b = rgba[0], rgba[1], rgba[2]
    border_hex = mcolors.rgb2hex(
        (max(0.0, r * 0.7), max(0.0, g * 0.7), max(0.0, b * 0.7))
    )

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
            logger.error("JSON must be a list of coordinate objects.")
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
        logger.success(f"Loaded {len(coordinates)} coordinates from JSON")
        return coordinates

    except json.JSONDecodeError:
        logger.error("Invalid JSON format")
        return None
    except Exception as e:
        logger.error(f"Error parsing JSON coordinates: {e}")
        return None


# -----------------------------
# CSV / XLSX parser
# -----------------------------
def _parse_tabular_coordinates(uploaded_file) -> Optional[List[Coordinate]]:
    """
    Parse coordinates from CSV or XLSX files.
    Requires columns: Categoria, Subcategoria, Nombre, Latitude, Longitud.
    Optional columns: Prod (production value), Region, Municipality.
    """
    try:
        file_name = uploaded_file.name.lower()
        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            logger.error("Unsupported tabular file type.")
            return None

        # Normalize headers
        df.columns = [str(c).strip() for c in df.columns]

        # Validate required columns
        missing = REQUIRED_COLUMNS.difference(df.columns)
        if missing:
            logger.error(f"Missing required columns: {', '.join(sorted(missing))}")
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
            logger.info("Found 'Prod' column - production values will be included")

        # Handle optional Region column
        has_region = "Region" in df.columns
        if has_region:
            df["Region"] = df["Region"].astype(str).str.strip()
            logger.info("Found 'Region' column")

        # Handle optional Municipality column
        has_municipality = "Municipality" in df.columns
        if has_municipality:
            df["Municipality"] = df["Municipality"].astype(str).str.strip()
            logger.info("Found 'Municipality' column")

        df = df.dropna(subset=["Latitud", "Longitud"])
        df = df[(df["Latitud"].between(-90, 90)) & (df["Longitud"].between(-180, 180))]

        coordinates = []
        for i, (_, row) in enumerate(df.iterrows()):
            prod_value = float(row.get("Prod", 0) or 0) if has_prod else 0.0
            region_value = row.get("Region") if has_region else None
            municipality_value = row.get("Municipality") if has_municipality else None

            # Handle NaN values
            if bool(pd.isna(region_value)):
                region_value = None

            if bool(pd.isna(municipality_value)):
                municipality_value = None

            coordinates.append(
                Coordinate(
                    id=f"poi_{i + 1}",
                    name=str(row["Nombre"]),
                    lat=float(row["Latitud"]),
                    lon=float(row["Longitud"]),
                    region=region_value,
                    department=None,
                    municipality=municipality_value,
                    unit_sis=None,
                    metadata={
                        "Categoria": row["Categoria"],
                        "Subcategoria": row["Subcategoria"],
                        "Prod": prod_value,
                    },
                )
            )

        logger.success(f"Loaded {len(coordinates)} coordinates from {file_name}")
        return coordinates

    except Exception as e:
        logger.error(f"Error parsing tabular coordinates: {e}")
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
            logger.error("Unsupported file type. Use JSON, CSV, or XLSX.")
            return None

    except Exception as e:
        logger.error(f"Error processing coordinate upload: {e}")
        return None


def get_coordinates_center(coordinates: List[Coordinate]) -> Tuple[float, float]:
    """Calculate average lat/lon from list of coordinates"""
    avg_lat = sum(coord.lat for coord in coordinates) / len(coordinates)
    avg_lon = sum(coord.lon for coord in coordinates) / len(coordinates)
    return avg_lat, avg_lon


def build_iso4app_payload_options() -> dict:
    """Build iso4app-specific options from session state."""
    return {
        "iso4app_type": st.session_state.get("iso4app_type", "isochrone"),
        "iso4app_mobility": st.session_state.get("iso4app_mobility", "motor_vehicle"),
        "iso4app_speed_type": st.session_state.get("iso4app_speed_type", "normal"),
        "iso4app_speed_limit": st.session_state.get("iso4app_speed_limit"),
    }
