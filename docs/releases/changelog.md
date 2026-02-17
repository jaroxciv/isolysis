# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.0] - 2026-02-17

### Added
- **`isolysis/constants.py`** — Shared constants (`CRS_WGS84`, `CRS_WEB_MERCATOR`, `SQ_METERS_PER_KM2`, `DEFAULT_MAP_CENTER`, `DEFAULT_DPI`) replacing magic strings across the codebase
- **`isolysis/raster.py`** — Core raster computation functions (zonal stats, area calculation, intersection analysis) moved out of the API layer into the library package
- **`isolysis/models.py`** — Canonical home for ALL Pydantic models, consolidating `api/schemas.py` and `isolysis/io.py` into a single source of truth
- **`api/services.py`** — Service layer extracting business logic from `api/app.py` (`process_isochrone_request`, `_run_spatial_analysis`)
- **`api/path_utils.py`** — `resolve_project_path` with path traversal security fix (containment check against project root)
- **`st_utils.py`** — Shared Streamlit/Folium utilities used by both `st_app.py` and `st_raster_app.py`, eliminating duplication
- Schema validations: `CentroidRequest.rho` max 24h, `ComputeOptions.travel_speed_kph` max 300, `IsochroneRequest.centroids` min_length=1

### Changed
- **Architecture** — `api/app.py` isochrone endpoint reduced from ~150 lines to ~10 lines delegating to service layer
- **Error propagation** — Iso4App/Mapbox API errors (rate limits, auth failures) now surface through to the UI instead of being swallowed as "no isochrones returned"
- **Performance** — Vectorized production sum via `pd.Series.apply()` instead of `iterrows()` loop; pre-computed covered POI IDs skip redundant spatial joins in out-of-band analysis; batch area projection (project GeoDataFrame once) in raster stats; cached CSV export in Streamlit
- **Dependencies** — `pyproject.toml` reorganized: moved `black`, `pytest`, `notebook` to dev group; added `streamlit`, `folium`, `streamlit-folium`, `openpyxl` to main dependencies
- **Docker** — Dockerfile and docker-compose.yml updated for new files (`translations.py`, `st_utils.py`)
- **Translations** — `translations.py` decoupled from Streamlit via lazy imports (can be used without Streamlit installed); page title changed to "Isochrone Analysis" / "Analisis de Isocronas"
- **UI labels** — "Click to Add Isochrone Centers" renamed to "Network Visualizer" / "Visualizador de Red"
- **Session state** — All `hasattr(st.session_state, ...)` replaced with `"key" in st.session_state` (7 occurrences)
- **Raster overlay cache** — Cache key now includes colormap to avoid stale overlays when switching color schemes
- `isolysis/raster.py` functions made public (dropped `_` prefix) since they are the module's exported API
- `gdf.__geo_interface__` used instead of `json.loads(gdf.to_json())` to eliminate double serialization

### Fixed
- **Security: Path traversal** — `resolve_project_path` now verifies resolved paths stay within the project root
- **Security: Request timeouts** — Added `timeout=30` to `requests.get()` in Iso4App and Mapbox providers
- **Security: Error leaking** — Raster endpoint returns generic error message instead of `str(e)`
- **HTTP status codes** — Missing provider key returns 503 (not 400); computation failure returns 500 (not 502); health endpoint returns 503 when no providers available
- **Raster overlay stale cache** — Changing colormap now correctly regenerates the overlay
- **Boundary clear** — Clearing boundary in raster app now resets `coord_center` so map returns to default position
- **Type hints** — Fixed `Optional` annotations on `plot_isochrones` parameters; `pd.Series` cast for pyright compatibility; `assert lang is not None` for type narrowing in translations

### Removed
- **Dead code** — `add_coordinates_to_map()`, `get_pos()`, `save_polygons_gpkg()`, `get_raster_center()`, `BandSummary`, `IntersectionSummary`, `AnalysisSummary`, `IsoCounts`, `IsoResponse`, `IsochroneResult.cached` field, `@st.cache_data` on mutable Folium objects, `load_dotenv()` side-effect in `isolysis/isochrone.py`, `--plot-points` CLI arg, commented debug logger, dead `band_km` branch
- **Stale shims** — Deleted `isolysis/io.py`, `api/schemas.py`, `api/utils.py` after migrating all imports to canonical locations
- **Dead files** — `tests/inputs/coordinates.json`, `conftest.py:testdir` fixture
- **Unused variables** — `MAPBOX_API_KEY`/`ISO4APP_API_KEY` in both Streamlit apps

## [0.6.0] - 2026-02-15

### Added
- **Spanish/English localization** with `translations.py` and language switcher in sidebar
- **`get_selectbox_options()`** for localized selectbox labels/values

### Fixed
- Type errors across Streamlit apps and API schemas

## [0.5.0] - 2026-02-14

### Added
- **Optional Region/Municipality parsing** from uploaded coordinate files
- **CSV export** with date suffix (`coverage_export_YYMMDD.csv`)
- **Viable status display** for per-centroid max production thresholds

### Changed
- Improved Max Production alignment in analysis display
- Taller map layout
- Added `run.sh` convenience script

### Fixed
- Type errors in models and Streamlit components

## [0.4.2] - 2026-02-10

### Changed
- Unified intersection display format between 2-way and multi-way overlaps

## [0.4.1] - 2026-02-09

### Added
- Hours/minutes toggle for travel time display
- Per-center colors and coverage tooltips
- Production viability feature with per-center max production threshold

### Changed
- Darkened default isochrone colors for better visibility

## [0.4.0] - 2026-02-07

### Added
- Raster file management (upload, overlay, delete)
- Boundary file support (GPKG, GeoJSON, ZIP shapefile)
- Raster statistics endpoint (`/raster-stats`) with zonal stats and intersection analysis
- `st_raster_app.py` — Dedicated Streamlit app for raster analysis
- Docker `streamlit-raster` service on port 8502

### Changed
- Clear buttons for isochrones, rasters, and boundary
- FeatureGroup approach to fix boundary flicker

## [0.3.0] - 2025-11-27

### Added
- Comprehensive performance analysis report
- Documentation structure with README
- Version and description read from `pyproject.toml` (single source of truth)
- API health endpoint with provider availability

### Changed
- Travel time slider changed to minutes (5-60 range)
- Metadata display (time + speed) on loaded isochrones
- Click-through on isochrone layers for overlapping creation

## [0.2.0] - 2025-11-XX

### Added
- FastAPI backend with multi-provider isochrone computation
- Iso4App and Mapbox provider classes (object-oriented design)
- Spatial analysis with POI coverage, band intersections, and Network Optimisation Index
- Streamlit frontend (`st_app.py`) with interactive Folium map
- Docker setup with API and Streamlit services
- Provider CLI argument (`--provider`) for runtime selection

## [0.1.0] - 2025-11-XX

### Added
- Initial project structure with modular package layout
- OSMnx-based isochrone computation
- Pydantic models for input/output data contracts
- Plotting utilities with contextily basemaps
- Network fetch script for OSM data
