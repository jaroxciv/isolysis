import json
import requests
import folium as fl
import streamlit as st
from typing import Dict, Optional, List, Tuple
from isolysis.io import Coordinate


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

    # Default: London
    return [51.5074, -0.1278]


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
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors

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


@st.cache_data
def handle_coordinate_upload(uploaded_file) -> Optional[List[Coordinate]]:
    """
    Process uploaded JSON file and return list of Coordinate objects.

    Args:
        uploaded_file: Streamlit uploaded file object

    Returns:
        List of Coordinate objects or None if error
    """
    try:
        # Read and parse JSON
        content = uploaded_file.read()
        data = json.loads(content)

        # Convert to Coordinate objects
        coordinates = [Coordinate(**item) for item in data]

        return coordinates

    except json.JSONDecodeError:
        st.error("❌ Invalid JSON format")
        return None
    except Exception as e:
        st.error(f"❌ Error processing coordinates: {str(e)}")
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
