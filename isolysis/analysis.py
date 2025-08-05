# isolysis/analysis.py

import geopandas as gpd
from typing import List, Dict, Any


def analyze_isochrone_coverage(
    iso_gdf: gpd.GeoDataFrame, points_gdf: gpd.GeoDataFrame
) -> List[Dict[str, Any]]:
    """
    For each isochrone (centroid + band), count how many points fall within the polygon.
    Returns a list of dicts per centroid and band.
    """
    results = []
    for idx, row in iso_gdf.iterrows():
        band = row.get("band_hours")  # or whatever standardized column
        centroid_id = row.get("id") or row.get("centroid_id")
        poly = row.geometry
        matches = points_gdf[points_gdf.within(poly)]
        results.append(
            {
                "centroid_id": centroid_id,
                "band_hours": band,
                "count": len(matches),
                "ids": matches["id"].tolist(),
            }
        )
    return results
