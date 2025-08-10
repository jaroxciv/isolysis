# isolysis/io.py

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Coordinate(BaseModel):
    id: Optional[str] = Field(None, description="Unique identifier for the point")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    region: Optional[str] = Field(None, description="Region name")
    department: Optional[str] = Field(None, description="Department (state/province)")
    municipality: Optional[str] = Field(None, description="Municipality")
    unit_sis: Optional[str] = Field(None, description="Health unit or SIS unit name")
    name: Optional[str] = Field(None, description="Full name of facility/unit")


class Centroid(BaseModel):
    id: str = Field(..., description="Unique identifier for the centroid/hub")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    rho: float = Field(..., gt=0, description="Travel time (in hours) for isochrone")


class IsoRequest(BaseModel):
    coordinates: Optional[List[Coordinate]] = Field(
        None, description="Points to be analyzed"
    )
    centroids: List[Centroid] = Field(..., description="Isochrone centers")

    @field_validator("centroids")
    @classmethod
    def centroids_not_empty(cls, v):
        if not v or len(v) < 1:
            raise ValueError("At least one centroid is required.")
        return v


class IsoCounts(BaseModel):
    label: str = Field(..., description="Identifier for the isochrone or intersection")
    count: int = Field(..., description="Number of points in this region")
    ids: List[str] = Field(..., description="IDs of points in this region")


class IsoResponse(BaseModel):
    total_points: int
    counts: List[IsoCounts]
    intersections: Optional[List[IsoCounts]] = None
    oob_count: int
    oob_ids: List[str]
