import geopandas as gpd
from itertools import combinations
from typing import List, Dict, Any
from loguru import logger


def analyze_isochrone_coverage(
    iso_gdf: gpd.GeoDataFrame, points_gdf: gpd.GeoDataFrame
) -> Dict[str, Any]:
    """
    For each isochrone (centroid + band), count how many points fall within the polygon.
    Also return total points, out-of-band counts, and IDs.
    """
    counts = []
    covered_ids = set()
    logger.info(
        f"Analyzing coverage for {len(iso_gdf)} isochrone polygons and {len(points_gdf)} points..."
    )
    for idx, row in iso_gdf.iterrows():
        band = row.get("band_hours")
        centroid_id = row.get("id") or row.get("centroid_id")
        poly = row.geometry
        matches = points_gdf[points_gdf.within(poly)]
        matched_ids = matches["id"].tolist()
        logger.debug(
            f"Isochrone {centroid_id} band {band}: {len(matched_ids)} points inside."
        )
        counts.append(
            {
                "label": f"{centroid_id}_band_{band}",
                "count": len(matched_ids),
                "ids": matched_ids,
            }
        )
        covered_ids.update(matched_ids)

    all_ids = set(points_gdf["id"])
    oob_ids = sorted(all_ids - covered_ids)
    oob_count = len(oob_ids)
    logger.info(f"Total points covered: {len(covered_ids)}; Out of band: {oob_count}")

    return {
        "total_points": len(points_gdf),
        "counts": counts,
        "oob_count": oob_count,
        "oob_ids": oob_ids,
    }


def analyze_isochrone_intersections(
    iso_gdf: gpd.GeoDataFrame,
    points_gdf: gpd.GeoDataFrame,
    min_overlap: int = 2,
) -> List[Dict[str, Any]]:
    """
    Find all intersections between isochrone polygons (from different centroids) by centroid+band,
    and count points within each intersection involving at least `min_overlap` polygons from different centroids.
    """
    from loguru import logger

    polys = []
    for idx, row in iso_gdf.iterrows():
        centroid_id = row.get("id") or row.get("centroid_id")
        band = row["band_hours"]
        label = f"{centroid_id}_{band}"
        polys.append(
            {"label": label, "centroid_id": centroid_id, "geometry": row.geometry}
        )

    results = []
    n_found = 0
    for r in range(min_overlap, len(polys) + 1):
        for combo in combinations(polys, r):
            centroid_ids = {p["centroid_id"] for p in combo}
            if len(centroid_ids) < 2:
                continue  # skip combinations that are all from same centroid
            labels = [p["label"] for p in combo]
            geoms = [p["geometry"] for p in combo]
            inter = geoms[0]
            for g in geoms[1:]:
                inter = inter.intersection(g)
                if inter.is_empty:
                    break
            if inter.is_empty:
                continue
            matches = points_gdf[points_gdf.within(inter)]
            if len(matches) == 0:
                continue
            logger.debug(
                f"Intersection {' & '.join(labels)}: {len(matches)} points inside intersection."
            )
            results.append(
                {
                    "label": " & ".join(labels),
                    "count": len(matches),
                    "ids": matches["id"].tolist(),
                }
            )
            n_found += 1
    logger.info(
        f"Found {n_found} inter-centroid intersection regions with at least {min_overlap} overlaps."
    )
    return results
