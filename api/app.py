import os
import json
from typing import Any, Dict, Optional, Literal, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv, find_dotenv

import pandas as pd
import geopandas as gpd

from isolysis.isochrone import compute_isochrones
from isolysis.utils import harmonize_isochrones_columns

# ---------- ENV SETUP ----------
load_dotenv(find_dotenv(usecwd=True), override=True)

ProviderName = Literal["osmnx", "iso4app", "mapbox"]


def validate_provider_keys(provider: ProviderName) -> Optional[str]:
    """Check if required API keys are present"""
    if provider == "mapbox" and not os.getenv("MAPBOX_API_KEY"):
        return "Missing MAPBOX_API_KEY environment variable"
    if provider == "iso4app" and not os.getenv("ISO4APP_API_KEY"):
        return "Missing ISO4APP_API_KEY environment variable"
    return None


# ---------- REQUEST/RESPONSE MODELS ----------
class CentroidRequest(BaseModel):
    """Single centroid for isochrone computation"""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    rho: float = Field(..., gt=0, description="Travel time in hours")
    id: Optional[str] = Field(None, description="Centroid identifier")


class ComputeOptions(BaseModel):
    """Options for isochrone computation"""

    provider: ProviderName = Field("osmnx", description="Routing provider")
    travel_speed_kph: float = Field(30, gt=0, description="Travel speed km/h")
    num_bands: int = Field(1, ge=1, le=5, description="Number of time bands (1-5)")
    profile: Optional[str] = Field("driving", description="Travel profile")


class IsochroneRequest(BaseModel):
    """Request for computing isochrones"""

    centroids: List[CentroidRequest]
    options: ComputeOptions = Field(default_factory=ComputeOptions)


class IsochroneResult(BaseModel):
    """Single isochrone result"""

    centroid_id: str
    geojson: Dict[str, Any]


class IsochroneResponse(BaseModel):
    """Response with computed isochrones"""

    provider: str
    results: List[IsochroneResult]
    total_centroids: int
    successful_computations: int


# ---------- FASTAPI APP ----------
app = FastAPI(
    title="Isolysis Isochrone API",
    version="0.1.0",
    description="Simple, fast isochrone computation API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- ENDPOINTS ----------
@app.get("/")
def root():
    """API information"""
    return {
        "name": "Isolysis Isochrone API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
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
    Compute isochrones for multiple centroids

    Simple, straightforward isochrone computation
    """
    provider = request.options.provider

    # Validate provider
    error_msg = validate_provider_keys(provider)
    if error_msg:
        raise HTTPException(status_code=400, detail=error_msg)

    logger.info(
        f"Computing isochrones for {len(request.centroids)} centroids using {provider}"
    )

    results = []
    successful = 0

    # Process each centroid
    for centroid in request.centroids:
        centroid_id = centroid.id or f"centroid_{len(results)}"

        try:
            logger.info(
                f"Computing isochrone for {centroid_id} at ({centroid.lat}, {centroid.lon})"
            )

            # Prepare centroid data for your isochrone function
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

            # Compute isochrone using your function
            isos = compute_isochrones([centroid_data], **kwargs)

            if not isos:
                logger.warning(f"No isochrones returned for {centroid_id}")
                continue

            # Convert to GeoDataFrame and then to GeoJSON
            gdf = harmonize_isochrones_columns(isos)
            if gdf.crs is None:
                gdf.set_crs("EPSG:4326", inplace=True)

            geojson = json.loads(gdf.to_json())

            # Add to results
            results.append(IsochroneResult(centroid_id=centroid_id, geojson=geojson))

            successful += 1
            logger.success(f"Successfully computed isochrone for {centroid_id}")

        except Exception as e:
            logger.error(f"Failed to compute isochrone for {centroid_id}: {str(e)}")
            # Continue with other centroids instead of failing completely
            continue

    if successful == 0:
        raise HTTPException(status_code=502, detail="Failed to compute any isochrones")

    logger.info(
        f"Successfully computed {successful}/{len(request.centroids)} isochrones"
    )

    return IsochroneResponse(
        provider=provider,
        results=results,
        total_centroids=len(request.centroids),
        successful_computations=successful,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
