import os
from itertools import combinations
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException
from loguru import logger

import rasterio
import geopandas as gpd
from rasterstats import zonal_stats
from shapely.geometry import shape
from shapely import intersection_all


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
            f"{len([i for i in intersections if i['type']==f'{r}-way'])} valid"
        )

    total_area = sum(i.get("area_km2", 0) or 0 for i in intersections)
    logger.info(
        f"Finished intersection analysis → total={len(intersections)} "
        f"({sum(1 for i in intersections if i['type']=='2-way')} two-way, "
        f"{sum(1 for i in intersections if '3-way' in i['type'])} three-way+), "
        f"aggregate area={total_area:.3f} km²"
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
                area_km2 = _compute_area_km2(row.geometry)
                results.append(
                    {
                        "scope": "isochrone",
                        "centroid_id": row["centroid_id"],
                        # "raster": raster_name,
                        "type": "1-way",
                        "area_km2": area_km2,
                        **stats,
                    }
                )

            # Intersections (pairwise & multi)
            inter_stats = _compute_intersection_stats(iso_gdf, raster_path)
            for rec in inter_stats:
                rec["scope"] = "intersection"
                results.append(rec)

        # Convert to GeoDataFrame-like dict for Streamlit table
        return {"results": results}

    except HTTPException:
        # Let FastAPI handle it as-is (preserves original status)
        raise
    except Exception as e:
        logger.exception("Raster analysis failed.")
        raise HTTPException(status_code=500, detail=str(e))
