import os
from itertools import combinations
from typing import Any, Dict, List

import geopandas as gpd
import pandas as pd
import rasterio
from fastapi import APIRouter, HTTPException
from loguru import logger
from rasterstats import zonal_stats
from shapely import intersection_all
from shapely.geometry import shape

from api.utils import resolve_project_path

router = APIRouter(prefix="/raster-stats", tags=["Raster Analysis"])


# -----------------------------
# Core functions
# -----------------------------
def _compute_stats_for_polygon(geom, raster_path: str) -> Dict[str, float]:
    """Compute min, max, mean, std for a single polygon against a raster"""
    stats_list = ["count", "min", "max", "mean", "median", "sum"]
    try:
        # Detect nodata value automatically from the raster
        with rasterio.open(raster_path) as src:
            nodata_value = src.nodata if src.nodata is not None else -9999

        stats = zonal_stats(
            [geom],
            raster_path,
            stats=stats_list,
            nodata=nodata_value,  # use raster's internal nodata (-9999)
            all_touched=True,  # include partially covered pixels
            geojson_out=False,
        )[0]

        # Replace any None or negative no-data leftovers with 0 for population context
        cleaned = {k: (0 if v is None or v < 0 else v) for k, v in stats.items()}
        return cleaned

    except Exception as e:
        logger.error(f"Failed raster stats for {raster_path}: {e}")
        return {k: None for k in stats_list}


def _compute_area_km2(geom) -> float:
    """
    Compute the area of a geometry in square kilometers, projecting to EPSG:3857.
    Falls back to planar area if projection fails.
    """
    try:
        area_km2 = (
            gpd.GeoSeries([geom], crs="EPSG:4326").to_crs(3857).area.iloc[0] / 1e6
        )
        return float(area_km2)
    except Exception as e:
        logger.warning(f"Area projection failed: {e}")
        try:
            return float(geom.area)
        except Exception:
            return None


def _compute_intersection_stats(iso_gdf: gpd.GeoDataFrame, raster_path: str):
    """
    Compute raster statistics for all valid intersections between isochrones.
    Uses shapely.intersection_all for robust n-way geometric intersections.
    """
    intersections = []
    centroid_ids = list(iso_gdf["centroid_id"])
    raster_name = os.path.basename(raster_path)

    logger.info(
        f"Starting intersection analysis for {len(centroid_ids)} centers "
        f"on raster '{raster_name}'"
    )

    for r in range(2, len(centroid_ids) + 1):
        combos = list(combinations(centroid_ids, r))
        logger.debug(
            f"Computing {r}-way intersections across {len(combos)} combinations"
        )

        for combo in combos:
            geoms = [
                iso_gdf.loc[iso_gdf["centroid_id"] == cid, "geometry"].values[0]
                for cid in combo
            ]

            try:
                inter_geom = intersection_all(geoms)
            except Exception as e:
                logger.error(f"Intersection failed for {combo}: {e}")
                continue

            if inter_geom is None or inter_geom.is_empty:
                logger.debug(f"No intersection geometry for {combo}")
                continue

            # Compute area in km² (project to EPSG:3857)
            area_km2 = _compute_area_km2(inter_geom)
            stats = _compute_stats_for_polygon(inter_geom, raster_path)
            intersections.append(
                {
                    "scope": "intersection",
                    "centroid_id": " & ".join(combo),
                    "type": f"{r}-way",
                    "area_km2": area_km2,
                    **stats,
                }
            )

        logger.info(
            f"Completed {r}-way intersections → "
            f"{len([i for i in intersections if i['type'] == f'{r}-way'])} valid"
        )

    total_area = sum(i.get("area_km2", 0) or 0 for i in intersections)
    logger.info(
        f"Finished intersection analysis → total={len(intersections)} "
        f"({sum(1 for i in intersections if i['type'] == '2-way')} two-way, "
        f"{sum(1 for i in intersections if '3-way' in i['type'])} three-way+), "
        f"aggregate area={total_area:.3f} km²"
    )

    return intersections


def _compute_stats_for_geometries(
    gdf: gpd.GeoDataFrame, rasters: List[Dict[str, str]], scope: str
) -> List[Dict[str, Any]]:
    """Generic helper to compute zonal stats for a GeoDataFrame across rasters."""
    results = []
    for raster in rasters:
        raster_path = raster["path"]
        if not os.path.exists(raster_path):
            logger.error(f"Raster not found: {raster_path}")
            continue

        logger.info(f"Processing raster: {os.path.basename(raster_path)}")
        logger.debug(f"Boundary GDF columns: {gdf.columns.tolist()}")
        for idx, row in gdf.iterrows():
            geom = row.geometry
            stats = _compute_stats_for_polygon(geom, raster_path)
            area_km2 = _compute_area_km2(geom)
            name = (
                row.get("centroid_id")
                or row.get("name")
                or row.get("NAME_3")
                or row.get("NAME_2")
                or row.get("NAME_1")
                or f"Feature_{idx}"
            )
            results.append(
                {
                    "scope": scope,
                    "centroid_id": name,
                    "type": "polygon" if scope == "boundary" else "1-way",
                    "area_km2": area_km2,
                    **stats,
                }
            )
    return results


def _log_summary(results: List[Dict[str, Any]], label: str = "Results"):
    """Log descriptive stats summary similar to df.describe()."""
    if not results:
        logger.warning(f"{label}: no results to summarize.")
        return

    df = pd.DataFrame(results)
    numeric_cols = df.select_dtypes(include="number")
    if numeric_cols.empty:
        logger.info(f"{label}: no numeric columns to summarize.")
        return

    summary = numeric_cols.describe().T
    logger.info(f"📊 {label} summary (n={len(df)})")
    logger.info("\n" + summary.round(3).to_string())


# -----------------------------
# Main route
# -----------------------------
@router.post("")
def raster_stats_endpoint(payload: Dict[str, Any]):
    """
    Compute raster statistics for:
      - Isochrone geometries (and their intersections)
      - or uploaded boundary polygons from a file.

    Returns flattened results suitable for display.
    """
    try:
        rasters = payload.get("rasters")
        boundary_path = resolve_project_path(payload.get("boundary_path"))
        isochrones = payload.get("isochrones")

        if not rasters:
            raise HTTPException(status_code=400, detail="Missing raster files.")

        for r in rasters:
            r["path"] = resolve_project_path(r.get("path"))

        logger.debug(f"Working dir: {os.getcwd()}")
        for r in rasters:
            logger.debug(f"Exists({r['path']}): {os.path.exists(r['path'])}")
        logger.debug(f"Boundary provided: {bool(boundary_path)}")

        # CASE 1: Boundary
        if boundary_path and os.path.exists(boundary_path):
            logger.info(f"Running BOUNDARY mode with file: {boundary_path}")
            gdf = gpd.read_file(boundary_path).to_crs(4326)
            results = _compute_stats_for_geometries(gdf, rasters, scope="boundary")
            _log_summary(results, label="Boundary stats")
            return {"results": results}

        # CASE 2: Isochrones
        elif isochrones:
            logger.info(f"Running ISOCHRONE mode for {len(isochrones)} centroids")
            iso_gdf = gpd.GeoDataFrame(
                [
                    {"centroid_id": i["centroid_id"], "geometry": shape(i["geometry"])}
                    for i in isochrones
                ],
                crs="EPSG:4326",
            )
            results = _compute_stats_for_geometries(iso_gdf, rasters, scope="isochrone")

            # Add intersection stats
            for raster in rasters:
                inter_stats = _compute_intersection_stats(iso_gdf, raster["path"])
                results.extend(inter_stats)

            _log_summary(results, label="Isochrone stats")
            return {"results": results}

        else:
            raise HTTPException(
                status_code=400,
                detail="No valid geometry source found (isochrones or boundary).",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Raster analysis failed.")
        raise HTTPException(status_code=500, detail=str(e))
