"""Service layer for isochrone endpoint business logic."""

from typing import Dict, List, Optional

from loguru import logger

from isolysis.analysis import analyze_isochrones_with_pois
from isolysis.constants import CRS_WGS84
from isolysis.isochrone import compute_isochrones
from isolysis.models import (
    IsochroneRequest,
    IsochroneResponse,
    IsochroneResult,
    SpatialAnalysisResult,
)
from isolysis.utils import harmonize_isochrones_columns


def process_isochrone_request(request: IsochroneRequest) -> IsochroneResponse:
    """
    Process an isochrone computation request with optional spatial analysis.

    Returns IsochroneResponse on success.
    Raises ValueError if no isochrones could be computed.
    """
    provider = request.options.provider

    logger.info(
        f"Computing isochrones for {len(request.centroids)} centroids using {provider}"
    )
    if request.pois:
        logger.info(f"POI analysis requested for {len(request.pois)} points")

    results: List[IsochroneResult] = []
    successful = 0
    all_isochrone_records = []
    errors: List[str] = []

    # Process each centroid
    for idx, centroid in enumerate(request.centroids):
        centroid_id = centroid.id or f"centroid_{idx}"

        try:
            logger.info(
                f"Computing isochrone for {centroid_id} at ({centroid.lat}, {centroid.lon})"
            )

            centroid_data = {
                "lat": centroid.lat,
                "lon": centroid.lon,
                "rho": centroid.rho,
                "id": centroid_id,
            }

            kwargs = {
                "provider": provider,
                "travel_speed_kph": request.options.travel_speed_kph,
                "num_bands": request.options.num_bands,
            }

            if request.options.profile:
                kwargs["profile"] = request.options.profile

            kwargs.update(
                {
                    "value_type": request.options.iso4app_type,
                    "travel_type": request.options.iso4app_mobility,
                    "speed_type": request.options.iso4app_speed_type,
                    "speed_limit": request.options.iso4app_speed_limit,
                }
            )

            isos = compute_isochrones([centroid_data], **kwargs)

            if not isos:
                logger.warning(f"No isochrones returned for {centroid_id}")
                errors.append(f"{centroid_id}: no isochrones returned")
                continue

            all_isochrone_records.extend(isos)

            # Convert to GeoDataFrame and then to GeoJSON
            gdf = harmonize_isochrones_columns(isos)
            if gdf.crs is None:
                gdf.set_crs(CRS_WGS84, inplace=True)

            geojson = gdf.__geo_interface__

            results.append(
                IsochroneResult(
                    centroid_id=centroid_id,
                    geojson=geojson,
                    coverage=None,
                )
            )

            successful += 1
            logger.success(f"Successfully computed isochrone for {centroid_id}")

        except Exception as e:
            logger.error(f"Failed to compute isochrone for {centroid_id}: {str(e)}")
            errors.append(f"{centroid_id}: {e}")
            continue

    if successful == 0:
        reason = errors[0] if len(errors) == 1 else f"{len(errors)} failures"
        raise ValueError(f"Failed to compute any isochrones — {reason}")

    # Perform spatial analysis if POIs provided
    spatial_analysis = _run_spatial_analysis(request, all_isochrone_records)

    logger.info(
        f"Successfully computed {successful}/{len(request.centroids)} isochrones"
    )

    return IsochroneResponse(
        provider=provider,
        results=results,
        total_centroids=len(request.centroids),
        successful_computations=successful,
        spatial_analysis=spatial_analysis,
    )


def _run_spatial_analysis(
    request: IsochroneRequest,
    all_isochrone_records: list,
) -> Optional[SpatialAnalysisResult]:
    """Run spatial analysis if POIs are provided."""
    if not request.pois:
        logger.debug("No POIs provided, skipping spatial analysis")
        return None

    if not all_isochrone_records:
        logger.warning(
            "POIs provided but no isochrones computed, skipping spatial analysis"
        )
        return None

    try:
        logger.info("Computing spatial analysis...")
        max_production_by_centroid: Dict[str, float] = {}
        for idx, centroid in enumerate(request.centroids):
            centroid_id = centroid.id or f"centroid_{idx}"
            if centroid.max_production is not None:
                max_production_by_centroid[centroid_id] = centroid.max_production

        result = analyze_isochrones_with_pois(
            all_isochrone_records,
            request.pois,
            min_overlap=2,
            max_combinations=100,
            max_production_by_centroid=max_production_by_centroid
            if max_production_by_centroid
            else None,
        )
        logger.success(
            f"Spatial analysis completed: {result.global_coverage_percentage:.1f}% coverage, "
            f"{result.intersection_analysis.total_intersections} intersections, "
            f"Network Optimisation Index computed: {result.network_optimization_index:.3f}"
        )
        return result
    except Exception as e:
        logger.error(f"Spatial analysis failed: {str(e)}")
        return None
