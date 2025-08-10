import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from typing import List, Dict, Any, Tuple, Set
from datetime import datetime
from itertools import combinations
from loguru import logger

from api.schemas import (
    POI,
    BandCoverage,
    CentroidCoverage,
    BandIntersection,
    IntersectionMatrix,
    OutOfBandAnalysis,
    SpatialAnalysisResult,
)


def format_time_display(hours: float) -> str:
    """Convert hours to a readable time format"""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes}min"
    elif hours == int(hours):
        return f"{int(hours)}h"
    else:
        return f"{hours}h"


def pois_to_geodataframe(pois: List[POI]) -> gpd.GeoDataFrame:
    """Convert POI list to GeoDataFrame"""
    if not pois:
        return gpd.GeoDataFrame(columns=["id", "geometry"], crs="EPSG:4326")

    logger.debug(f"Converting {len(pois)} POIs to GeoDataFrame")

    data = []
    for poi in pois:
        data.append(
            {
                "id": poi.id,
                "name": poi.name,
                "region": poi.region,
                "municipality": poi.municipality,
                "geometry": Point(poi.lon, poi.lat),
                "metadata": poi.metadata,
            }
        )

    return gpd.GeoDataFrame(data, crs="EPSG:4326")


def compute_band_coverage(
    isochrones_gdf: gpd.GeoDataFrame, pois_gdf: gpd.GeoDataFrame
) -> List[BandCoverage]:
    """
    Compute coverage analysis for each isochrone band
    Fast implementation inspired by legacy analyze_isochrone_coverage()
    """
    if pois_gdf.empty:
        logger.warning("No POIs provided for coverage analysis")
        return []

    logger.info(
        f"Analyzing coverage for {len(isochrones_gdf)} isochrone polygons and {len(pois_gdf)} points..."
    )

    coverage_results = []
    total_pois = len(pois_gdf)

    for idx, row in isochrones_gdf.iterrows():
        centroid_id = row.get("centroid_id") or row.get("id")
        band_hours = row["band_hours"]
        geometry = row["geometry"]

        # Fast spatial intersection using within()
        matches = pois_gdf[pois_gdf.geometry.within(geometry)]
        poi_count = len(matches)
        poi_ids = matches["id"].tolist()

        coverage_percentage = (poi_count / total_pois * 100) if total_pois > 0 else 0.0
        band_label = format_time_display(band_hours)

        logger.debug(
            f"Isochrone {centroid_id} band {band_hours}h: {poi_count} points inside"
        )

        coverage = BandCoverage(
            centroid_id=centroid_id,
            band_hours=band_hours,
            band_label=band_label,
            poi_count=poi_count,
            poi_ids=poi_ids,
            coverage_percentage=coverage_percentage,
        )

        coverage_results.append(coverage)

    total_covered = len(set().union(*[c.poi_ids for c in coverage_results]))
    logger.info(
        f"Coverage analysis complete. Total unique POIs covered: {total_covered}/{total_pois}"
    )

    return coverage_results


def compute_centroid_coverage(
    band_coverages: List[BandCoverage],
) -> List[CentroidCoverage]:
    """Group band coverages by centroid and compute centroid-level statistics"""
    logger.debug("Computing centroid-level coverage statistics")

    # Group by centroid_id
    centroid_groups = {}
    for coverage in band_coverages:
        centroid_id = coverage.centroid_id
        if centroid_id not in centroid_groups:
            centroid_groups[centroid_id] = []
        centroid_groups[centroid_id].append(coverage)

    centroid_coverages = []

    for centroid_id, bands in centroid_groups.items():
        # Sort bands by time
        bands.sort(key=lambda x: x.band_hours)

        # Get unique POIs across all bands for this centroid
        all_poi_ids = set()
        for band in bands:
            all_poi_ids.update(band.poi_ids)

        # Find band with highest coverage
        max_coverage_band = max(bands, key=lambda x: x.poi_count) if bands else None
        max_band_label = max_coverage_band.band_label if max_coverage_band else None

        logger.debug(
            f"Centroid {centroid_id}: {len(all_poi_ids)} unique POIs across {len(bands)} bands"
        )

        centroid_coverage = CentroidCoverage(
            centroid_id=centroid_id,
            total_bands=len(bands),
            bands=bands,
            total_unique_pois=len(all_poi_ids),
            max_coverage_band=max_band_label,
        )

        centroid_coverages.append(centroid_coverage)

    return centroid_coverages


def compute_band_intersections(
    isochrones_gdf: gpd.GeoDataFrame,
    pois_gdf: gpd.GeoDataFrame,
    min_overlap: int = 2,
    max_combinations: int = 100,
) -> IntersectionMatrix:
    """
    Fast intersection analysis inspired by legacy analyze_isochrone_intersections()
    Handles multi-way intersections efficiently using combinations
    """
    if len(isochrones_gdf) < 2 or pois_gdf.empty:
        logger.warning("Insufficient data for intersection analysis")
        return IntersectionMatrix(
            total_intersections=0,
            pairwise_intersections=[],
            multiway_intersections=[],
            max_overlap_count=0,
        )

    logger.info(
        f"Computing intersections for {len(isochrones_gdf)} isochrones with min_overlap={min_overlap}"
    )

    # Prepare polygon data with labels (legacy format for speed)
    polys = []
    for idx, row in isochrones_gdf.iterrows():
        centroid_id = row.get("centroid_id") or row.get("id")
        band_hours = row["band_hours"]
        band_label = format_time_display(band_hours)
        label = f"{centroid_id}_{band_label}"

        polys.append(
            {
                "label": label,
                "centroid_id": centroid_id,
                "band_hours": band_hours,
                "geometry": row.geometry,
            }
        )

    pairwise_intersections = []
    multiway_intersections = []
    n_found = 0

    # Use combinations to find all possible overlaps (legacy approach - very fast!)
    for r in range(min_overlap, min(len(polys) + 1, max_combinations)):
        logger.debug(f"Computing {r}-way intersections...")

        for combo in combinations(polys, r):
            # Skip combinations from same centroid
            centroid_ids = {p["centroid_id"] for p in combo}
            if len(centroid_ids) < 2:
                continue

            labels = [p["label"] for p in combo]
            geoms = [p["geometry"] for p in combo]

            # Fast intersection computation (legacy approach)
            inter = geoms[0]
            for g in geoms[1:]:
                inter = inter.intersection(g)
                if inter.is_empty:
                    break

            if inter.is_empty:
                continue

            # Count POIs in intersection
            matches = pois_gdf[pois_gdf.geometry.within(inter)]
            if len(matches) == 0:
                continue

            poi_count = len(matches)
            poi_ids = matches["id"].tolist()

            logger.debug(
                f"Intersection {' & '.join(labels)}: {poi_count} points inside"
            )

            # Create intersection object
            intersection_id = "_".join([p["label"] for p in combo])
            intersection_label = " & ".join(labels)
            centroid_bands = [(p["centroid_id"], p["band_hours"]) for p in combo]

            intersection = BandIntersection(
                intersection_id=intersection_id,
                intersection_label=intersection_label,
                centroid_bands=centroid_bands,
                poi_count=poi_count,
                poi_ids=poi_ids,
                intersection_area_km2=_calculate_area_km2(inter),
                overlap_type=f"{r}-way" if r > 2 else "2-way",
            )

            # Categorize by type
            if r == 2:
                pairwise_intersections.append(intersection)
            else:
                multiway_intersections.append(intersection)

            n_found += 1

            # Prevent computational explosion
            if n_found >= max_combinations:
                logger.warning(
                    f"Reached maximum combinations limit ({max_combinations}), stopping"
                )
                break

        if n_found >= max_combinations:
            break

    # Calculate summary statistics
    total_intersections = len(pairwise_intersections) + len(multiway_intersections)
    max_overlap_count = max(
        [2] * len(pairwise_intersections)
        + [len(inter.centroid_bands) for inter in multiway_intersections],
        default=0,
    )

    total_area = sum(
        inter.intersection_area_km2 or 0
        for inter in pairwise_intersections + multiway_intersections
    )

    logger.info(
        f"Found {n_found} intersection regions: {len(pairwise_intersections)} 2-way, {len(multiway_intersections)} multi-way"
    )

    return IntersectionMatrix(
        total_intersections=total_intersections,
        pairwise_intersections=pairwise_intersections,
        multiway_intersections=multiway_intersections,
        max_overlap_count=max_overlap_count,
        total_intersection_area_km2=total_area if total_area > 0 else None,
    )


def compute_out_of_band_analysis(
    isochrones_gdf: gpd.GeoDataFrame, pois_gdf: gpd.GeoDataFrame
) -> OutOfBandAnalysis:
    """Find POIs that are outside all isochrone coverage (legacy approach for speed)"""
    if pois_gdf.empty:
        return OutOfBandAnalysis(total_oob_pois=0, oob_poi_ids=[], oob_percentage=0.0)

    logger.debug("Computing out-of-band analysis...")

    # Fast approach: collect all covered POI IDs from individual band analysis
    covered_ids = set()
    for idx, row in isochrones_gdf.iterrows():
        matches = pois_gdf[pois_gdf.geometry.within(row.geometry)]
        covered_ids.update(matches["id"].tolist())

    # Find uncovered POIs
    all_ids = set(pois_gdf["id"])
    oob_ids = sorted(all_ids - covered_ids)

    total_pois = len(pois_gdf)
    oob_count = len(oob_ids)
    oob_percentage = (oob_count / total_pois * 100) if total_pois > 0 else 0.0

    logger.info(
        f"Out-of-band analysis: {oob_count}/{total_pois} POIs uncovered ({oob_percentage:.1f}%)"
    )

    return OutOfBandAnalysis(
        total_oob_pois=oob_count, oob_poi_ids=oob_ids, oob_percentage=oob_percentage
    )


def compute_spatial_analysis(
    isochrones_gdf: gpd.GeoDataFrame,
    pois: List[POI],
    min_overlap: int = 2,
    max_combinations: int = 100,
) -> SpatialAnalysisResult:
    """
    Complete spatial analysis combining coverage and intersection analysis
    Optimized version using legacy algorithms for speed
    """
    logger.info(
        f"Starting spatial analysis for {len(isochrones_gdf)} isochrones and {len(pois)} POIs"
    )

    # Convert POIs to GeoDataFrame
    pois_gdf = pois_to_geodataframe(pois)

    if pois_gdf.empty:
        logger.warning("No POIs provided, returning empty analysis")
        return SpatialAnalysisResult(
            total_pois=0,
            total_centroids=(
                len(isochrones_gdf["centroid_id"].unique())
                if "centroid_id" in isochrones_gdf.columns
                else 0
            ),
            total_bands=len(isochrones_gdf),
            coverage_analysis=[],
            intersection_analysis=IntersectionMatrix(
                total_intersections=0,
                pairwise_intersections=[],
                multiway_intersections=[],
                max_overlap_count=0,
            ),
            oob_analysis=OutOfBandAnalysis(
                total_oob_pois=0, oob_poi_ids=[], oob_percentage=0.0
            ),
            global_coverage_percentage=0.0,
            most_covered_centroid=None,
            analysis_timestamp=datetime.now().isoformat(),
        )

    # Compute band coverage
    logger.debug("Computing band coverage...")
    band_coverages = compute_band_coverage(isochrones_gdf, pois_gdf)

    # Compute centroid coverage
    logger.debug("Computing centroid coverage...")
    centroid_coverages = compute_centroid_coverage(band_coverages)

    # Compute intersections
    logger.debug("Computing intersections...")
    intersection_matrix = compute_band_intersections(
        isochrones_gdf, pois_gdf, min_overlap, max_combinations
    )

    # Compute out-of-band analysis
    logger.debug("Computing out-of-band analysis...")
    oob_analysis = compute_out_of_band_analysis(isochrones_gdf, pois_gdf)

    # Calculate global statistics
    all_covered_poi_ids = set()
    for coverage in centroid_coverages:
        for band in coverage.bands:
            all_covered_poi_ids.update(band.poi_ids)

    global_coverage_percentage = (
        (len(all_covered_poi_ids) / len(pois) * 100) if pois else 0.0
    )

    # Find most covered centroid
    most_covered_centroid = None
    if centroid_coverages:
        best_centroid = max(centroid_coverages, key=lambda x: x.total_unique_pois)
        most_covered_centroid = best_centroid.centroid_id

    logger.success(
        f"Spatial analysis complete: {global_coverage_percentage:.1f}% global coverage, "
        f"{intersection_matrix.total_intersections} intersections"
    )

    return SpatialAnalysisResult(
        total_pois=len(pois),
        total_centroids=(
            len(isochrones_gdf["centroid_id"].unique())
            if "centroid_id" in isochrones_gdf.columns
            else 0
        ),
        total_bands=len(isochrones_gdf),
        coverage_analysis=centroid_coverages,
        intersection_analysis=intersection_matrix,
        oob_analysis=oob_analysis,
        global_coverage_percentage=global_coverage_percentage,
        most_covered_centroid=most_covered_centroid,
        analysis_timestamp=datetime.now().isoformat(),
    )


def _calculate_area_km2(geometry) -> float:
    """Calculate area in km² for a geometry (rough approximation)"""
    try:
        # Convert to a projected CRS for area calculation (using Web Mercator as approximation)
        gdf_temp = gpd.GeoDataFrame([{"geometry": geometry}], crs="EPSG:4326")
        gdf_projected = gdf_temp.to_crs("EPSG:3857")  # Web Mercator
        area_m2 = gdf_projected.geometry.area.iloc[0]
        return area_m2 / 1_000_000  # Convert to km²
    except:
        return 0.0


# ---------- HELPER FUNCTIONS FOR API INTEGRATION ----------
def analyze_isochrones_with_pois(
    isochrone_records: List[Dict[str, Any]],
    pois: List[POI],
    min_overlap: int = 2,
    max_combinations: int = 100,
) -> SpatialAnalysisResult:
    """
    High-level function to analyze isochrones with POIs
    Integrates with existing harmonize_isochrones_columns() workflow
    """
    logger.info(
        f"Starting isochrone analysis with {len(isochrone_records)} records and {len(pois)} POIs"
    )

    from isolysis.utils import harmonize_isochrones_columns

    # Harmonize the isochrone data
    isochrones_gdf = harmonize_isochrones_columns(isochrone_records)
    logger.debug(f"Harmonized {len(isochrones_gdf)} isochrone records")

    # Perform spatial analysis
    return compute_spatial_analysis(isochrones_gdf, pois, min_overlap, max_combinations)
