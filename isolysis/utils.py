# isolysis/utils.py

import time
import geopandas as gpd
from loguru import logger
from functools import wraps


def save_polygons_gpkg(
    polygons, centroids, filename="isochrones.gpkg", layer="isochrones"
):
    gdf = gpd.GeoDataFrame(
        {
            "id": [c["id"] for c in centroids],
            "geometry": polygons,
            "rho": [c["rho"] for c in centroids],
            "lat": [c["lat"] for c in centroids],
            "lon": [c["lon"] for c in centroids],
        },
        crs="EPSG:4326",
    )
    gdf.to_file(filename, driver="GPKG", layer=layer)
    logger.success(f"Isochrone polygons saved to {filename} (layer={layer})")


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
