import json
import os
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from api import rasters
from api.schemas import (
    IsochroneRequest,
    IsochroneResponse,
    IsochroneResult,
    ProviderName,
)
from isolysis.analysis import analyze_isochrones_with_pois
from isolysis.isochrone import compute_isochrones
from isolysis.utils import harmonize_isochrones_columns

# ---------- ENV SETUP ----------
load_dotenv(find_dotenv(usecwd=True), override=True)


def validate_provider_keys(provider: ProviderName) -> Optional[str]:
    """Check if required API keys are present"""
    if provider == "mapbox" and not os.getenv("MAPBOX_API_KEY"):
        return "Missing MAPBOX_API_KEY environment variable"
    if provider == "iso4app" and not os.getenv("ISO4APP_API_KEY"):
        return "Missing ISO4APP_API_KEY environment variable"
    return None


# ---------- FASTAPI APP ----------
app = FastAPI(
    title="Isolysis Isochrone API",
    version="0.2.0",
    description="Isochrone computation API with spatial analysis capabilities",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Additional routers ---
app.include_router(rasters.router)


# ---------- ENDPOINTS ----------
@app.get("/")
def root():
    """API information"""
    return {
        "name": "Isolysis Isochrone API",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Multi-provider isochrone computation",
            "Spatial analysis with POIs",
            "Coverage and intersection analysis",
        ],
    }


@app.get("/health")
def health_check():
    """Health check with provider availability"""
    available_providers = []
    for provider in ["osmnx", "iso4app", "mapbox"]:
        if not validate_provider_keys(provider):
            available_providers.append(provider)

    return {
        "status": "healthy",
        "available_providers": available_providers,
        "unavailable_providers": [
            p for p in ["osmnx", "iso4app", "mapbox"] if p not in available_providers
        ],
    }


@app.post("/isochrones", response_model=IsochroneResponse)
def compute_isochrones_endpoint(request: IsochroneRequest):
    """
    Compute isochrones for multiple centroids with optional spatial analysis

    - Computes isochrones using specified provider
    - Optionally analyzes POI coverage and intersections if POIs provided
    - Returns both geometric data and rich analysis results
    """
    provider = request.options.provider

    # Validate provider
    error_msg = validate_provider_keys(provider)
    if error_msg:
        raise HTTPException(status_code=400, detail=error_msg)

    logger.info(
        f"Computing isochrones for {len(request.centroids)} centroids using {provider}"
    )
    if request.pois:
        logger.info(f"POI analysis requested for {len(request.pois)} points")

    results = []
    successful = 0
    all_isochrone_records = []  # Collect for spatial analysis

    # Process each centroid
    for centroid in request.centroids:
        centroid_id = centroid.id or f"centroid_{len(results)}"

        try:
            logger.info(
                f"Computing isochrone for {centroid_id} at ({centroid.lat}, {centroid.lon})"
            )

            # Prepare centroid data for isochrone function
            centroid_data = {
                "lat": centroid.lat,
                "lon": centroid.lon,
                "rho": centroid.rho,
                "id": centroid_id,
            }

            # Prepare computation arguments
            kwargs = {
                "provider": provider,
                "travel_speed_kph": request.options.travel_speed_kph,
                "num_bands": request.options.num_bands,
            }

            if request.options.profile:
                kwargs["profile"] = request.options.profile

            # --- Iso4App specific parameters ---
            kwargs.update(
                {
                    "value_type": request.options.iso4app_type,
                    "travel_type": request.options.iso4app_mobility,
                    "speed_type": request.options.iso4app_speed_type,
                    "speed_limit": request.options.iso4app_speed_limit,
                }
            )

            # Compute isochrone using your function
            isos = compute_isochrones([centroid_data], **kwargs)

            if not isos:
                logger.warning(f"No isochrones returned for {centroid_id}")
                continue

            # Store for spatial analysis
            all_isochrone_records.extend(isos)

            # Convert to GeoDataFrame and then to GeoJSON
            gdf = harmonize_isochrones_columns(isos)
            if gdf.crs is None:
                gdf.set_crs("EPSG:4326", inplace=True)

            geojson = json.loads(gdf.to_json())

            # Create result
            results.append(
                IsochroneResult(
                    centroid_id=centroid_id,
                    geojson=geojson,
                    cached=False,  # Could implement caching logic here
                )
            )

            successful += 1
            logger.success(f"Successfully computed isochrone for {centroid_id}")

        except Exception as e:
            logger.error(f"Failed to compute isochrone for {centroid_id}: {str(e)}")
            # Continue with other centroids instead of failing completely
            continue

    if successful == 0:
        raise HTTPException(status_code=502, detail="Failed to compute any isochrones")

    # Perform spatial analysis if POIs provided
    spatial_analysis = None
    if request.pois and all_isochrone_records:
        try:
            logger.info("Computing spatial analysis...")
            spatial_analysis = analyze_isochrones_with_pois(
                all_isochrone_records,
                request.pois,
                min_overlap=2,  # Configurable parameters
                max_combinations=100,
            )
            logger.success(
                f"Spatial analysis completed: {spatial_analysis.global_coverage_percentage:.1f}% coverage, "
                f"{spatial_analysis.intersection_analysis.total_intersections} intersections, "
                f"Network Optimisation Index computed: {spatial_analysis.network_optimization_index:.3f}"
            )
        except Exception as e:
            logger.error(f"Spatial analysis failed: {str(e)}")
            # Continue without spatial analysis rather than failing
            spatial_analysis = None
    elif request.pois and not all_isochrone_records:
        logger.warning(
            "POIs provided but no isochrones computed, skipping spatial analysis"
        )
    elif not request.pois:
        logger.debug("No POIs provided, skipping spatial analysis")

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


@app.get("/providers")
def list_providers():
    """List available isochrone providers and their status"""
    providers_info = {}

    for provider in ["osmnx", "iso4app", "mapbox"]:
        error = validate_provider_keys(provider)
        providers_info[provider] = {
            "available": error is None,
            "error": error,
            "features": {
                "osmnx": [
                    "Free",
                    "OpenStreetMap data",
                    "Global coverage",
                    "Offline capable",
                ],
                "iso4app": [
                    "European coverage",
                    "High precision",
                    "Multiple transport modes",
                ],
                "mapbox": ["Global coverage", "Fast computation", "Real traffic data"],
            }.get(provider, []),
        }

    return {"providers": providers_info, "default": "osmnx"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
