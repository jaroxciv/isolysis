import os
import itertools
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException
from loguru import logger

import rasterio
import geopandas as gpd
from shapely.geometry import shape
from rasterstats import zonal_stats


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


def _compute_intersection_stats(iso_gdf: gpd.GeoDataFrame, raster_path: str):
    """
    Compute stats for all valid intersections between isochrones:
    - Pairwise (2-way)
    - Multi-way (3+, up to all)
    Only returns intersections with non-empty geometry.
    """
    intersections = []

    centroid_ids = list(iso_gdf["centroid_id"])

    # Generate all unique combinations of 2 or more isochrones
    for r in range(2, len(centroid_ids) + 1):
        for combo in itertools.combinations(centroid_ids, r):
            subset = iso_gdf[iso_gdf["centroid_id"].isin(combo)]

            # Compute intersection of all geometries in this combination
            inter_geom = subset.geometry.unary_union
            for geom in subset.geometry[1:]:
                inter_geom = inter_geom.intersection(geom)

            if inter_geom.is_empty:
                continue

            # Compute raster stats for this multi-intersection
            stats = _compute_stats_for_polygon(inter_geom, raster_path)

            intersections.append(
                {
                    "type": f"{r}-way",
                    "intersection": " & ".join(combo),
                    "raster": os.path.basename(raster_path),
                    **stats,  # Flattened stats
                }
            )

    return intersections


# -----------------------------
# Main route
# -----------------------------
@router.post("")
def raster_stats_endpoint(payload: Dict[str, Any]):
    """
    Compute raster statistics for each isochrone and all valid intersections (2-way to N-way).
    Returns flattened results suitable for DataFrame display.
    """
    try:
        isochrones = payload.get("isochrones")
        rasters = payload.get("rasters")

        if not isochrones or not rasters:
            raise HTTPException(
                status_code=400, detail="Missing isochrones or rasters."
            )

        # Convert to GeoDataFrame
        iso_gdf = gpd.GeoDataFrame(
            [
                {"centroid_id": i["centroid_id"], "geometry": shape(i["geometry"])}
                for i in isochrones
            ],
            crs="EPSG:4326",
        )

        results = []

        for raster in rasters:
            raster_path = raster["path"]
            if not os.path.exists(raster_path):
                logger.error(f"Raster not found: {raster_path}")
                continue

            raster_name = os.path.basename(raster_path)
            logger.info(
                f"Computing raster stats for {len(iso_gdf)} polygons on {raster_name}"
            )

            # Individual isochrone stats
            for _, row in iso_gdf.iterrows():
                stats = _compute_stats_for_polygon(row.geometry, raster_path)
                results.append(
                    {
                        "scope": "isochrone",
                        "centroid_id": row["centroid_id"],
                        "raster": raster_name,
                        **stats,
                    }
                )

            # Intersections (pairwise & multi)
            inter_stats = _compute_intersection_stats(iso_gdf, raster_path)
            for rec in inter_stats:
                rec["scope"] = "intersection"
                rec["centroid_id"] = rec.pop("intersection")
                results.append(rec)

        # Convert to GeoDataFrame-like dict for Streamlit table
        return {"results": results}

    except Exception as e:
        logger.exception("Raster analysis failed.")
        raise HTTPException(status_code=500, detail=str(e))
