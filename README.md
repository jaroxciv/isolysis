# Isolysis

**Isochrone overlap analyzer for multi-center, multi-distance spatial queries with interactive web interface.**

## Overview

Isolysis is a modular, production-grade Python package for calculating and analyzing isochrones (reachable areas) from multiple centers (hubs) over real road networks. It supports multiple travel times, custom intervals, and easy overlay with other spatial data. The project includes both a REST API and an interactive Streamlit web interface for real-time isochrone visualization and analysis.

## Features

### Core Analysis
* **Multi-center isochrones:** Generate isochrones for any set of centroids (hubs), each with its own travel time (rho)
* **Banding:** Isochrones can be calculated in bands (e.g., every 15 minutes up to N hours)
* **Coverage analysis:** Calculate how many input points (e.g., health units, facilities, deliveries) fall within each isochrone band for every centroid
* **Intersection analysis:** Identify overlaps between service areas (isochrones) of multiple hubs and count points in each overlap region (by band)

### Multiple Providers
* **OSMnx:** Real road networks using OpenStreetMap data (drive, walk, bike supported)
* **Mapbox:** Global coverage with high-performance routing
* **Iso4App:** European coverage with detailed routing

### Web Interface
* **Interactive Streamlit app:** Click-to-add isochrone centers with real-time visualization
* **Dynamic mapping:** Auto-updating maps with customizable color schemes
* **Coordinate upload:** Bulk upload points via JSON files
* **Multiple travel modes:** Support for different transportation types

### Technical Features
* **REST API:** FastAPI backend for programmatic access
* **Preload networks:** Download and reuse national/city networks for instant analysis
* **Outputs:** Saves to GeoPackage (`.gpkg`), outputs results as JSON, and produces publication-quality maps
* **Modern, testable codebase:** Modularized functions, Pydantic I/O, logging, and CLI utilities

## Installation

1. Clone the repo:

   ```sh
   git clone https://github.com/jaroxciv/isolysis.git
   cd isolysis
   ```

2. Install dependencies (recommended: [uv](https://github.com/astral-sh/uv)):

   ```sh
   uv venv
   uv add -r requirements.txt
   ```

3. Set up environment variables:

   ```sh
   cp .env.example .env
   # Edit .env with your API keys (optional for OSMnx)
   ```

## Quick Start

### Web Interface (Recommended)

1. Start the API server:
   ```sh
   uv run uvicorn api.app:app --reload --port 8000
   ```

2. Launch the Streamlit interface:
   ```sh
   uv run streamlit run st_app.py
   ```

3. Open your browser to `http://localhost:8501` and start clicking on the map!

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

The REST API provides programmatic access to isochrone calculation:

```python
import requests

# Calculate isochrones via API
payload = {
    "centroids": [
        {"lat": 51.5074, "lon": -0.1278, "rho": 1.0, "id": "london"}
    ],
    "options": {
        "provider": "mapbox",
        "travel_speed_kph": 25,
        "num_bands": 3
    }
}

response = requests.post("http://localhost:8000/isochrones", json=payload)
result = response.json()
```

## Web Interface Features

* **Interactive mapping:** Click anywhere to add isochrone centers
* **Provider selection:** Choose between OSMnx, Mapbox, or Iso4App
* **Time bands:** Generate 1-5 equally-spaced time bands
* **Color schemes:** 9 scientific colormaps (viridis, plasma, magma, etc.)
* **Coordinate upload:** Bulk upload points from JSON files
* **Real-time updates:** Dynamic map updates without page refresh
* **Export capabilities:** Download results as GeoPackage or JSON

## Coordinate Upload Format

Upload points as JSON arrays with this structure:

```json
[
  {
    "region": "Región Occidental",
    "department": "SO",
    "municipality": "Juayua",
    "unit_sis": "Básica",
    "name": "UCSF Juayua SO Los Naranjos",
    "lat": 13.8780542,
    "lon": -89.67343,
    "id": "b4067328-f7fe-42be-a6c9-84550461c9f3"
  }
]
```

## Example: Coverage/Intersection Output

`outputs/isochrone_coverage.json` (truncated):

```json
{
  "total_points": 100,
  "counts": [
    {"label": "hub1_band_0.5", "count": 12, "ids": ["...", ...]},
    {"label": "hub2_band_1.0", "count": 7, "ids": ["...", ...]},
    ...
  ],
  "intersections": [
    {"label": "hub1_1.0 & hub2_1.0", "count": 4, "ids": ["...", ...]},
    {"label": "hub1_0.5 & hub2_0.5", "count": 2, "ids": ["...", ...]},
    ...
  ],
  "oob_count": 5,
  "oob_ids": ["id1", "id2", ...]
}
```

## Directory Structure

```
├── st_app.py            # Streamlit web interface
├── main.py              # Main script for generating isochrones & coverage
├── plot_isos.py         # Plotting script for visualizing outputs
├── fetch_network.py     # Utility for downloading OSMnx road networks
├── api/
│   ├── app.py           # FastAPI REST server
│   └── utils.py         # API utility functions
├── networks/            # Saved OSMnx graphml networks (not tracked)
├── outputs/             # Output files (GeoPackages, JSON, PNGs, etc)
├── data/                # Input points (e.g., coords.json)
├── isolysis/
│   ├── __init__.py
│   ├── io.py            # I/O models (Pydantic)
│   ├── isochrone.py     # Isochrone calculation logic
│   ├── plot.py          # Plotting utilities
│   ├── utils.py         # Timing, helpers
│   ├── analysis.py      # Coverage/intersection analysis
└── ...
```

## Requirements

* Python 3.12+
* [OSMnx](https://github.com/gboeing/osmnx) - Road network analysis
* [GeoPandas](https://geopandas.org/) - Spatial data processing
* [FastAPI](https://fastapi.tiangolo.com/) - REST API framework
* [Streamlit](https://streamlit.io/) - Web interface
* [Folium](https://python-visualization.github.io/folium/) - Interactive mapping
* [Pydantic](https://docs.pydantic.dev/) - Data validation
* [Loguru](https://github.com/Delgan/loguru) - Logging
* [uv](https://github.com/astral-sh/uv) - Package management

## Configuration

Set up your `.env` file with API keys:

```env
MAPBOX_API_KEY=your_mapbox_token_here
ISO4APP_API_KEY=your_iso4app_key_here
```

## Development & Contribution

* **Modular architecture:** Separate concerns for isochrone calculation, API, and UI
* **Type safety:** Full Pydantic models for data validation
* **Modern practices:** Fragments, caching, and dynamic updates in Streamlit
* **Multiple providers:** Extensible provider system for different routing services
* **Test coverage:** Add test cases for new modules
* **Clean commits:** Descriptive commit messages and atomic changes

### Development Setup

1. Install development dependencies:
   ```sh
   uv add --dev pytest black isort mypy
   ```

2. Run tests:
   ```sh
   uv run pytest
   ```

3. Format code:
   ```sh
   uv run black . && uv run isort .
   ```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

For more details and advanced usage, see code comments and individual module docstrings.