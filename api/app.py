import os
import tomllib
from pathlib import Path
from typing import List, Optional, get_args

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api import rasters
from isolysis.models import (
    IsochroneRequest,
    IsochroneResponse,
    ProviderName,
)
from api.services import process_isochrone_request

# ---------- ENV SETUP ----------
load_dotenv(find_dotenv(usecwd=True), override=True)


# ---------- READ PROJECT METADATA ----------
def get_project_metadata():
    """Read project metadata from pyproject.toml"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]


PROJECT_TITLE = "Isolysis Isochrone API"
PROJECT_METADATA = get_project_metadata()


def validate_provider_keys(provider: ProviderName) -> Optional[str]:
    """Check if required API keys are present"""
    if provider == "mapbox" and not os.getenv("MAPBOX_API_KEY"):
        return "Missing MAPBOX_API_KEY environment variable"
    if provider == "iso4app" and not os.getenv("ISO4APP_API_KEY"):
        return "Missing ISO4APP_API_KEY environment variable"
    return None


# ---------- FASTAPI APP ----------
app = FastAPI(
    title=PROJECT_TITLE,
    version=PROJECT_METADATA["version"],
    description=PROJECT_METADATA["description"],
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
        "name": PROJECT_TITLE,
        "version": PROJECT_METADATA["version"],
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
    all_providers: List[ProviderName] = list(get_args(ProviderName))
    available_providers: List[ProviderName] = []
    for provider in all_providers:
        if not validate_provider_keys(provider):
            available_providers.append(provider)

    status = "healthy" if available_providers else "degraded"
    response = {
        "status": status,
        "available_providers": available_providers,
        "unavailable_providers": [
            p for p in all_providers if p not in available_providers
        ],
    }

    if not available_providers:
        raise HTTPException(status_code=503, detail=response)

    return response


@app.post("/isochrones", response_model=IsochroneResponse)
def compute_isochrones_endpoint(request: IsochroneRequest):
    """Compute isochrones for multiple centroids with optional spatial analysis"""
    error_msg = validate_provider_keys(request.options.provider)
    if error_msg:
        raise HTTPException(status_code=503, detail=error_msg)
    try:
        return process_isochrone_request(request)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/providers")
def list_providers():
    """List available isochrone providers and their status"""
    providers_info = {}

    for provider in get_args(ProviderName):
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
