import os
import time
import json
import hashlib
from typing import Any, Dict, Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
from dotenv import load_dotenv, find_dotenv

import pandas as pd
import geopandas as gpd

from isolysis.io import IsoRequest, IsoResponse, IsoCounts
from isolysis.isochrone import compute_isochrones
from isolysis.utils import harmonize_isochrones_columns
from isolysis.analysis import (
    analyze_isochrone_coverage,
    analyze_isochrone_intersections,
)

# ---------- env / setup ----------
load_dotenv(find_dotenv(usecwd=True), override=True)

ProviderName = Literal["osmnx", "iso4app", "mapbox"]


def _missing_key_for(provider: ProviderName) -> Optional[str]:
    if provider == "mapbox" and not (os.getenv("MAPBOX_API_KEY") or "").strip():
        return "Missing MAPBOX_API_KEY"
    if provider == "iso4app" and not (os.getenv("ISO4APP_API_KEY") or "").strip():
        return "Missing ISO4APP_API_KEY"
    return None


# Simple in-memory cache (10 minutes)
_CACHE: Dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 600  # seconds


def _cache_key(provider: str, payload: Dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"{provider}:{hashlib.sha1(blob).hexdigest()}"


def _cache_get(key: str):
    entry = _CACHE.get(key)
    if not entry:
        return None
    ts, val = entry
    if time.time() - ts > _CACHE_TTL:
        _CACHE.pop(key, None)
        return None
    return val


def _cache_set(key: str, value: Any):
    _CACHE[key] = (time.time(), value)


# ---------- request/response DTOs ----------
class ComputeOptions(BaseModel):
    provider: ProviderName = Field(..., description="Which engine to use")
    interval: Optional[float] = Field(
        None, gt=0, description="Band interval (hours), defaults to rho/4 if not provided"
    )
    travel_speed_kph: float = Field(30, gt=0, description="Only used by osmnx")
    profile: Optional[str] = Field("driving", description="Mapbox profile")
    denoise: Optional[float] = Field(None, description="Mapbox denoise [0..1]")
    generalize: Optional[float] = Field(None, description="Mapbox generalize meters")


class ComputeRequest(BaseModel):
    isorequest: IsoRequest
    options: ComputeOptions


class IsoServiceResponse(BaseModel):
    provider: ProviderName
    interval: Optional[float]
    coverage: Optional[IsoResponse]
    polygons_geojson: Dict[str, Any]


# ---------- FastAPI app ----------
app = FastAPI(title="Isolysis API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/isochrones", response_model=IsoServiceResponse)
def isochrones(req: ComputeRequest):
    # Key check for external providers
    missing = _missing_key_for(req.options.provider)
    if missing:
        raise HTTPException(status_code=400, detail=missing)

    # Cache key
    key = _cache_key(
        req.options.provider,
        {
            "centroids": [c.model_dump() for c in req.isorequest.centroids],
            "n_points": (
                len(req.isorequest.coordinates) if req.isorequest.coordinates else 0
            ),
        },
    )
    cached = _cache_get(key)
    if cached:
        logger.info("Serving /isochrones from cache")
        return cached

    # Compute isochrones
    centroids_payload = [c.model_dump() for c in req.isorequest.centroids]
    kwargs: Dict[str, Any] = {
        "provider": req.options.provider,
        "travel_speed_kph": req.options.travel_speed_kph,
    }
    if req.options.interval is not None:
        kwargs["interval"] = req.options.interval
    if req.options.profile:
        kwargs["profile"] = req.options.profile
    if req.options.denoise is not None:
        kwargs["denoise"] = req.options.denoise
    if req.options.generalize is not None:
        kwargs["generalize"] = req.options.generalize

    isos = compute_isochrones(centroids_payload, **kwargs)
    if not isos:
        raise HTTPException(status_code=502, detail="Provider returned no isochrones")

    # Harmonize -> GeoDataFrame
    gdf = harmonize_isochrones_columns(isos)
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)

    # --- Optional analysis, if coordinates are provided
    coverage_resp = None
    if req.isorequest.coordinates:
        # Convert coordinates into points GeoDataFrame
        coords_df = pd.DataFrame([c.model_dump() for c in req.isorequest.coordinates])
        points_gdf = gpd.GeoDataFrame(
            coords_df,
            geometry=gpd.points_from_xy(coords_df.lon, coords_df.lat),
            crs="EPSG:4326",
        )

        # Coverage + inter-centroid intersections
        coverage = analyze_isochrone_coverage(gdf, points_gdf)
        intersections = analyze_isochrone_intersections(gdf, points_gdf)
        coverage_resp = IsoResponse(
            total_points=coverage["total_points"],
            counts=[IsoCounts(**c) for c in coverage["counts"]],
            intersections=([IsoCounts(**c) for c in intersections] or None),
            oob_count=coverage["oob_count"],
            oob_ids=coverage["oob_ids"],
        )

    # Build service response
    service_resp = IsoServiceResponse(
        provider=req.options.provider,
        interval=req.options.interval,
        coverage=coverage_resp,
        polygons_geojson=json.loads(gdf.to_json()),
    )

    _cache_set(key, service_resp)
    return service_resp


@app.get("/")
def read_root():
    return {"message": "Welcome to the Isochrone Service API"}

