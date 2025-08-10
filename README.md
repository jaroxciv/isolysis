# Isolysis

**Isochrone overlap analyzer for multi-center, multi-distance spatial queries with interactive web interface and comprehensive spatial analysis.**

## Overview

Isolysis is a modular, production-grade Python package for calculating and analyzing isochrones (reachable areas) from multiple centers (hubs) over real road networks. It supports multiple travel times, custom intervals, and comprehensive spatial analysis with POI coverage and intersection analysis. The project includes both a REST API and an interactive Streamlit web interface for real-time isochrone visualization and analysis.

## Features

### Core Analysis
* **Multi-center isochrones:** Generate isochrones for any set of centroids (hubs), each with its own travel time (rho)
* **Time banding:** Isochrones can be calculated in bands (e.g., every 15 minutes up to N hours)
* **POI coverage analysis:** Calculate how many points of interest fall within each isochrone band for every centroid
* **Intersection analysis:** Identify overlaps between service areas (isochrones) of multiple hubs and count POIs in each overlap region
* **Out-of-band analysis:** Identify POIs not covered by any isochrone

### Multiple Providers
* **OSMnx:** Real road networks using OpenStreetMap data (drive, walk, bike supported)
* **Mapbox:** Global coverage with high-performance routing and real traffic data
* **Iso4App:** European coverage with detailed routing and multiple transport modes

### Interactive Web Interface
* **Click-to-add centers:** Interactive Streamlit app with click-to-add isochrone centers
* **Real-time visualization:** Auto-updating maps with customizable scientific color schemes
* **Coordinate upload:** Bulk upload POIs via JSON files for analysis
* **Spatial analysis dashboard:** Coverage metrics, intersection analysis, and uncovered area identification
* **Dynamic mapping:** Fragment-based updates without page refresh

### REST API
* **FastAPI backend:** High-performance API with automatic documentation
* **Spatial analysis integration:** Optional POI analysis with comprehensive results
* **Multiple output formats:** GeoJSON, coverage statistics, intersection matrices
* **Provider flexibility:** Easy switching between routing providers

### Technical Features
* **Modern architecture:** Pydantic models, async processing, and clean separation of concerns
* **Comprehensive testing:** Unit tests for all analysis functions and API endpoints
* **Scientific visualization:** Matplotlib colormaps for professional isochrone display
* **Caching and optimization:** Fragment-based UI updates and efficient spatial operations

## Installation

1. Clone the repo:

   ```sh
   git clone https://github.com/jaroxciv/isolysis.git
   cd isolysis
   ```

2. Install dependencies using [uv](https://github.com/astral-sh/uv):

   ```sh
   uv venv
   uv sync
   ```

3. Set up environment variables:

   ```sh
   cp .env.example .env
   # Edit .env with your API keys (optional for OSMnx)
   ```

## Quick Start

### Web Interface (Recommended)

**Option 1: Use the PowerShell script (Windows):**
```powershell
.\run.ps1
```

**Option 2: Manual startup:**
```sh
# Terminal 1: Start API server
uv run uvicorn api.app:app --reload --port 8000

# Terminal 2: Start Streamlit interface  
uv run streamlit run st_app.py
```

Then open your browser to `http://localhost:8501` and start clicking on the map!

### Command Line Usage

1. Download/prepare a road network (recommended for speed):
   ```sh
   uv run fetch_network.py "El Salvador"
   ```

2. Generate isochrones and analyze coverage:
   ```sh
   uv run main.py --provider mapbox
   ```

3. Plot results:
   ```sh
   uv run plot_isos.py --provider mapbox --plot-points
   ```

## API Usage

The REST API provides programmatic access to isochrone calculation and spatial analysis:

```python
import requests

# Calculate isochrones with POI analysis
payload = {
    "centroids": [
        {"lat": 51.5074, "lon": -0.1278, "rho": 1.0, "id": "london"}
    ],
    "options": {
        "provider": "mapbox",
        "travel_speed_kph": 25,
        "num_bands": 3
    },
    "pois": [
        {"id": "poi1", "lat": 51.5074, "lon": -0.1278, "name": "Central POI"},
        {"id": "poi2", "lat": 51.5200, "lon": -0.1000, "name": "North POI"}
    ]
}

response = requests.post("http://localhost:8000/isochrones", json=payload)
result = response.json()

# Access spatial analysis results
analysis = result["spatial_analysis"]
print(f"Coverage: {analysis['global_coverage_percentage']:.1f}%")
print(f"Intersections: {analysis['intersection_analysis']['total_intersections']}")
```

## Web Interface Features

* **Interactive mapping:** Click anywhere to add isochrone centers with real-time computation
* **Provider selection:** Choose between OSMnx, Mapbox, or Iso4App with automatic availability detection
* **Time bands:** Generate 1-5 equally-spaced time bands with proper formatting (e.g., "20min, 40min, 1h")
* **Scientific color schemes:** 9 matplotlib colormaps (viridis, plasma, magma, etc.) for professional visualization
* **Coordinate upload:** Bulk upload POIs from JSON files with metadata support
* **Spatial analysis dashboard:** 
  - Coverage metrics (Total POIs, Coverage %, Intersections, Covered, Uncovered)
  - Per-center coverage analysis with best-performing bands
  - Intersection analysis showing 2-way and multi-way overlaps
  - Out-of-band analysis identifying uncovered areas
* **Real-time updates:** Fragment-based map updates without page refresh
* **Export capabilities:** Download results as GeoPackage or JSON

## Spatial Analysis Output

The API returns comprehensive spatial analysis when POIs are provided:

```json
{
  "spatial_analysis": {
    "total_pois": 100,
    "global_coverage_percentage": 78.5,
    "coverage_analysis": [
      {
        "centroid_id": "london",
        "total_unique_pois": 45,
        "bands": [
          {
            "band_label": "20min",
            "poi_count": 12,
            "coverage_percentage": 12.0
          }
        ]
      }
    ],
    "intersection_analysis": {
      "total_intersections": 3,
      "pairwise_intersections": [
        {
          "intersection_label": "london_20min & manchester_30min",
          "poi_count": 8
        }
      ]
    },
    "oob_analysis": {
      "total_oob_pois": 21,
      "oob_percentage": 21.0
    }
  }
}
```

## Coordinate Upload Format

Upload POIs as JSON arrays with this structure:

```json
[
  {
    "id": "b4067328-f7fe-42be-a6c9-84550461c9f3",
    "lat": 13.8780542,
    "lon": -89.67343,
    "name": "UCSF Juayua SO Los Naranjos",
    "region": "Región Occidental",
    "municipality": "Juayua"
  }
]
```

## Testing

Run the comprehensive test suite:

```sh
# Run all tests
uv run pytest tests

# Run API tests only (requires running server)
uv run pytest tests/test_api.py

# Run analysis tests only  
uv run pytest tests/test_analysis.py

# Run with coverage
uv run pytest tests --cov=isolysis --cov=api
```

## Directory Structure

```
├── st_app.py            # Interactive Streamlit web interface
├── run.ps1              # PowerShell script to run both services
├── main.py              # CLI script for batch isochrone generation
├── plot_isos.py         # Visualization script
├── fetch_network.py     # Network download utility
├── api/
│   ├── app.py           # FastAPI REST server with spatial analysis
│   ├── schemas.py       # Pydantic models for requests/responses
│   └── utils.py         # API utility functions
├── isolysis/
│   ├── isochrone.py     # Multi-provider isochrone calculation
│   ├── analysis.py      # Spatial analysis functions (coverage, intersections)
│   ├── io.py            # I/O models and validation
│   ├── utils.py         # Core utilities and harmonization
│   └── plot.py          # Plotting utilities
├── tests/
│   ├── test_api.py      # API integration tests
│   ├── test_analysis.py # Analysis function unit tests
│   ├── conftest.py      # Test configuration
│   └── inputs/          # Test data files
├── networks/            # Cached OSMnx networks (not tracked)
├── outputs/             # Generated files (GeoPackages, maps, analysis)
└── data/                # Input datasets
```

## Requirements

* Python 3.12+
* **Core Libraries:**
  - [OSMnx](https://github.com/gboeing/osmnx) - Road network analysis
  - [GeoPandas](https://geopandas.org/) - Spatial data processing
  - [Shapely](https://shapely.readthedocs.io/) - Geometric operations
* **Web Framework:**
  - [FastAPI](https://fastapi.tiangolo.com/) - REST API with automatic docs
  - [Streamlit](https://streamlit.io/) - Interactive web interface
  - [Folium](https://python-visualization.github.io/folium/) - Interactive mapping
* **Data & Validation:**
  - [Pydantic](https://docs.pydantic.dev/) - Data validation and serialization
  - [Loguru](https://github.com/Delgan/loguru) - Structured logging
* **Scientific Computing:**
  - [Matplotlib](https://matplotlib.org/) - Scientific colormaps
  - [NumPy](https://numpy.org/) & [Pandas](https://pandas.pydata.org/) - Data processing
* **Development:**
  - [uv](https://github.com/astral-sh/uv) - Fast Python package manager
  - [pytest](https://pytest.org/) - Testing framework

## Configuration

Set up your `.env` file with optional API keys for enhanced providers:

```env
# Optional: For Mapbox provider (global coverage, real traffic)
MAPBOX_API_KEY=your_mapbox_token_here

# Optional: For Iso4App provider (European coverage, high precision)  
ISO4APP_API_KEY=your_iso4app_key_here

# OSMnx works without API keys (free, global coverage)
```

## Development & Testing

### Development Setup

1. Install development dependencies:
   ```sh
   uv add --dev pytest pytest-cov black
   ```

2. Run tests:
   ```sh
   uv run pytest tests -v
   ```

3. Format code:
   ```sh
   uv run black .
   ```

### Architecture Principles

* **Modular design:** Separate isochrone calculation, spatial analysis, API, and UI
* **Type safety:** Full Pydantic models for data validation and API contracts
* **Performance:** Fragment-based UI updates, spatial indexing, and efficient algorithms
* **Provider abstraction:** Easy to add new routing providers
* **Comprehensive testing:** Unit tests for all analysis functions and API endpoints
* **Clean separation:** Analysis functions independent of web frameworks

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with comprehensive tests
4. Ensure code formatting: `uv run black . && uv run isort .`
5. Run the test suite: `uv run pytest tests`
6. Submit a pull request with clear description

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with modern Python ecosystem: FastAPI, Streamlit, Pydantic
- Spatial analysis powered by OSMnx, GeoPandas, and Shapely
- Scientific visualization using Matplotlib colormaps
- Testing infrastructure with pytest and comprehensive coverage

For more details and advanced usage, see the API documentation at `/docs` when running the server, and explore the comprehensive test suite in the `tests/` directory.