"""FastAPI router for raster statistics endpoints."""

import os

import geopandas as gpd
from fastapi import APIRouter, HTTPException
from loguru import logger
from shapely.geometry import shape

from api.path_utils import resolve_project_path
from isolysis.models import RasterStatsRequest
from isolysis.raster import (
    compute_intersection_stats,
    compute_stats_for_geometries,
    log_summary,
)

router = APIRouter(prefix="/raster-stats", tags=["Raster Analysis"])


@router.post("")
def raster_stats_endpoint(payload: RasterStatsRequest):
    """
    Compute raster statistics for:
      - Isochrone geometries (and their intersections)
      - or uploaded boundary polygons from a file.

    Returns flattened results suitable for display.
    """
    try:
        rasters = [r.model_dump() for r in payload.rasters]
        raw_boundary = payload.boundary_path
        boundary_path = resolve_project_path(raw_boundary) if raw_boundary else None
        isochrones = payload.isochrones

        if not rasters:
            raise HTTPException(status_code=400, detail="Missing raster files.")

        for r in rasters:
            r["path"] = resolve_project_path(r["path"])

        logger.debug(f"Working dir: {os.getcwd()}")
        for r in rasters:
            logger.debug(f"Exists({r['path']}): {os.path.exists(r['path'])}")
        logger.debug(f"Boundary provided: {bool(boundary_path)}")

        # CASE 1: Boundary
        if boundary_path and os.path.exists(boundary_path):
            logger.info(f"Running BOUNDARY mode with file: {boundary_path}")
            gdf = gpd.read_file(boundary_path).to_crs(4326)
            results = compute_stats_for_geometries(gdf, rasters, scope="boundary")
            log_summary(results, label="Boundary stats")
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
            results = compute_stats_for_geometries(iso_gdf, rasters, scope="isochrone")

            # Add intersection stats
            for raster in rasters:
                inter_stats = compute_intersection_stats(iso_gdf, raster["path"])
                results.extend(inter_stats)

            log_summary(results, label="Isochrone stats")
            return {"results": results}

        else:
            raise HTTPException(
                status_code=400,
                detail="No valid geometry source found (isochrones or boundary).",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Raster analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Internal raster analysis error")
