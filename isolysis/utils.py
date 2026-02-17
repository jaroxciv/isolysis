# isolysis/utils.py

import time
from functools import wraps
from typing import Any, Dict, List

import geopandas as gpd
from loguru import logger

from isolysis.constants import CRS_WGS84


def format_time(seconds: float) -> str:
    """
    Format seconds into 'xh ym zs' as appropriate.
    Show only nonzero components.
    """
    seconds_int = int(seconds)
    ms = int((seconds - seconds_int) * 1000)
    h, rem = divmod(seconds_int, 3600)
    m, s = divmod(rem, 60)
    out = []
    if h > 0:
        out.append(f"{h}h")
    if m > 0:
        out.append(f"{m}m")
    if s > 0 or (h == 0 and m == 0):
        if ms > 0 and seconds < 60:
            out.append(f"{s}.{ms:02d}s")
        else:
            out.append(f"{s}s")
    return " ".join(out)


def log_timing(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info("Elapsed time: {}", format_time(elapsed))
        return result

    return wrapper


def harmonize_isochrones_columns(records: List[Dict[str, Any]]) -> gpd.GeoDataFrame:
    """
    Convert a list of isochrone dicts from any provider to a GeoDataFrame
    with a standardized 'band_hours' column (float) and 'geometry'.
    """
    # Make DataFrame
    gdf = gpd.GeoDataFrame(records, crs=CRS_WGS84)

    # Try to handle various possible band columns
    if "band_hours" not in gdf.columns:
        if "band_minutes" in gdf.columns:
            gdf["band_hours"] = gdf["band_minutes"] / 60.0
        elif "time_min" in gdf.columns:
            gdf["band_hours"] = gdf["time_min"] / 60.0
        elif "band_secs" in gdf.columns:
            gdf["band_hours"] = gdf["band_secs"] / 3600.0
        else:
            raise ValueError(
                "No known band column found (band_hours, band_minutes, time_min, etc.)"
            )
    # Ensure geometry column is properly set as geometry
    if "geometry" in gdf.columns:
        gdf.set_geometry("geometry", inplace=True)
    return gdf
