from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# Type aliases
ProviderName = Literal["osmnx", "iso4app", "mapbox"]


# ---------- REQUEST/RESPONSE MODELS ----------
class CentroidRequest(BaseModel):
    """Single centroid for isochrone computation"""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    rho: float = Field(..., gt=0, description="Travel time in hours")
    id: Optional[str] = Field(None, description="Centroid identifier")
    max_production: Optional[float] = Field(
        None, description="Max production threshold for this centroid"
    )


class ComputeOptions(BaseModel):
    """Options for isochrone computation"""

    provider: ProviderName = Field("osmnx", description="Routing provider")
    travel_speed_kph: float = Field(30, gt=0, description="Travel speed km/h")
    num_bands: int = Field(
        1, ge=1, le=1, description="Number of time bands (Fixed to 1)"
    )
    profile: Optional[str] = Field("driving", description="Travel profile")

    # --- Iso4App specific ---
    iso4app_type: Optional[str] = Field(
        "isochrone", description="Iso4App isoline type: isochrone or isodistance"
    )
    iso4app_mobility: Optional[str] = Field(
        "motor_vehicle",
        description="Iso4App mobility: motor_vehicle, bicycle, pedestrian",
    )
    iso4app_speed_type: Optional[str] = Field(
        "normal", description="Iso4App speed type: very_low, low, normal, fast"
    )
    iso4app_speed_limit: Optional[float] = Field(
        None,
        gt=0,
        description="Iso4App maximum speed (km/h) used only for isochrone type",
    )


class IsochroneRequest(BaseModel):
    """Request for computing isochrones"""

    centroids: List[CentroidRequest]
    options: ComputeOptions = Field(default_factory=ComputeOptions)
    pois: Optional[List["POI"]] = Field(
        None, description="Points of interest for analysis"
    )


# ---------- POI MODELS ----------
class POI(BaseModel):
    """Point of Interest for analysis"""

    id: str = Field(..., description="Unique POI identifier")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    name: Optional[str] = Field(None, description="POI name")
    region: Optional[str] = Field(None, description="Region")
    municipality: Optional[str] = Field(None, description="Municipality")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional POI data")


# ---------- COVERAGE ANALYSIS MODELS ----------
class BandCoverage(BaseModel):
    """Coverage analysis for a single isochrone band"""

    centroid_id: str = Field(..., description="Centroid identifier")
    band_hours: float = Field(..., description="Band time in hours")
    band_label: str = Field(
        ..., description="Human-readable band label (e.g., '15min', '1h')"
    )
    poi_count: int = Field(..., ge=0, description="Number of POIs within this band")
    poi_ids: List[str] = Field(
        default_factory=list, description="List of POI IDs within band"
    )
    coverage_percentage: Optional[float] = Field(
        None, description="Percentage of total POIs covered"
    )
    production_sum: Optional[float] = Field(
        None, description="Sum of Prod values for POIs in band"
    )
    viable: Optional[bool] = Field(
        None, description="True if production_sum <= max_production"
    )


class CentroidCoverage(BaseModel):
    """Complete coverage analysis for one centroid across all bands"""

    centroid_id: str = Field(..., description="Centroid identifier")
    total_bands: int = Field(..., description="Number of bands for this centroid")
    bands: List[BandCoverage] = Field(..., description="Coverage data per band")
    total_unique_pois: int = Field(
        ..., description="Total unique POIs covered across all bands"
    )
    max_coverage_band: Optional[str] = Field(
        None, description="Band with highest coverage"
    )


# ---------- INTERSECTION ANALYSIS MODELS ----------
class BandIntersection(BaseModel):
    """Intersection analysis between two or more isochrone bands"""

    intersection_id: str = Field(..., description="Unique intersection identifier")
    intersection_label: str = Field(
        ..., description="Human-readable label (e.g., 'C1_15min & C2_30min')"
    )

    # Participating bands
    centroid_bands: List[tuple[str, float]] = Field(
        ..., description="List of (centroid_id, band_hours) pairs"
    )

    # POI analysis
    poi_count: int = Field(..., ge=0, description="Number of POIs in intersection")
    poi_ids: List[str] = Field(
        default_factory=list, description="POI IDs in intersection"
    )

    # Geometry info
    intersection_area_km2: Optional[float] = Field(
        None, description="Intersection area in km²"
    )

    # Metadata
    overlap_type: str = Field(
        ..., description="Type of overlap (e.g., '2-way', '3-way', 'multi')"
    )


class IntersectionMatrix(BaseModel):
    """Complete intersection analysis matrix"""

    total_intersections: int = Field(
        ..., description="Total number of intersections found"
    )

    # Two-way intersections (most common)
    pairwise_intersections: List[BandIntersection] = Field(
        default_factory=list, description="All 2-way band intersections"
    )

    # Multi-way intersections (3+ bands overlapping)
    multiway_intersections: List[BandIntersection] = Field(
        default_factory=list, description="All 3+ way band intersections"
    )

    # Summary stats
    max_overlap_count: int = Field(
        ..., description="Maximum number of bands overlapping in one area"
    )
    total_intersection_area_km2: Optional[float] = Field(
        None, description="Total area of all intersections"
    )


# ---------- OUT-OF-BAND ANALYSIS ----------
class OutOfBandAnalysis(BaseModel):
    """Analysis of POIs not covered by any isochrone"""

    total_oob_pois: int = Field(
        ..., ge=0, description="Number of POIs outside all isochrones"
    )
    oob_poi_ids: List[str] = Field(
        default_factory=list, description="POI IDs outside coverage"
    )
    oob_percentage: float = Field(
        ..., description="Percentage of POIs outside coverage"
    )


# ---------- COMPREHENSIVE ANALYSIS RESULT ----------
class SpatialAnalysisResult(BaseModel):
    """Complete spatial analysis result combining coverage and intersections"""

    # Input summary
    total_pois: int = Field(..., description="Total number of POIs analyzed")
    total_centroids: int = Field(..., description="Total number of centroids")
    total_bands: int = Field(
        ..., description="Total number of bands across all centroids"
    )

    # Network Optimisation
    network_optimization_index: Optional[float] = Field(
        None, description="Network Optimization Index (NOI) = (X - Y - Z) / total_pois"
    )

    # Coverage analysis
    coverage_analysis: List[CentroidCoverage] = Field(
        ..., description="Coverage per centroid"
    )

    # Intersection analysis
    intersection_analysis: IntersectionMatrix = Field(
        ..., description="Complete intersection analysis"
    )

    # Out-of-band analysis
    oob_analysis: OutOfBandAnalysis = Field(
        ..., description="POIs outside all coverage"
    )

    # Global statistics
    global_coverage_percentage: float = Field(
        ..., description="Overall POI coverage percentage"
    )
    most_covered_centroid: Optional[str] = Field(
        None, description="Centroid with highest POI coverage"
    )
    analysis_timestamp: str = Field(..., description="ISO timestamp of analysis")


# ---------- UPDATED API RESPONSE MODELS ----------
class IsochroneResult(BaseModel):
    """Single isochrone result with optional analysis"""

    centroid_id: str
    geojson: Dict[str, Any]
    cached: bool = Field(default=False, description="Whether result was cached")

    # Optional analysis (populated when POIs provided)
    coverage: Optional[CentroidCoverage] = Field(
        None, description="Coverage analysis if POIs provided"
    )


class IsochroneResponse(BaseModel):
    """Response with computed isochrones and optional spatial analysis"""

    provider: str
    results: List[IsochroneResult]
    total_centroids: int
    successful_computations: int

    # Optional comprehensive analysis
    spatial_analysis: Optional[SpatialAnalysisResult] = Field(
        None, description="Complete spatial analysis if POIs were provided"
    )


# ---------- HELPER MODELS FOR STREAMLIT ----------
class BandSummary(BaseModel):
    """Simplified band summary for UI display"""

    label: str = Field(..., description="Display label (e.g., 'Center1 - 15min')")
    poi_count: int = Field(..., description="POI count")
    percentage: float = Field(..., description="Percentage of total POIs")


class IntersectionSummary(BaseModel):
    """Simplified intersection summary for UI display"""

    label: str = Field(
        ..., description="Intersection label (e.g., 'C1_15min & C2_30min')"
    )
    poi_count: int = Field(..., description="POI count in intersection")
    participating_bands: List[str] = Field(..., description="List of band labels")


class AnalysisSummary(BaseModel):
    """High-level summary for dashboard display"""

    total_pois: int
    covered_pois: int
    coverage_percentage: float

    top_bands: List[BandSummary] = Field(..., description="Top 5 bands by coverage")
    top_intersections: List[IntersectionSummary] = Field(
        ..., description="Top 5 intersections by POI count"
    )

    oob_count: int = Field(..., description="Out-of-band POI count")
    oob_percentage: float = Field(..., description="Out-of-band percentage")


# Enable forward references
POI.model_rebuild()
IsochroneRequest.model_rebuild()
