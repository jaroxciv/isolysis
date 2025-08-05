# Isolysis

**Isochrone overlap analyzer for multi-center, multi-distance spatial queries.**

## Overview

Isolysis is a modular, production-grade Python package for calculating and analyzing isochrones (reachable areas) from multiple centers (hubs) over real road networks. It supports multiple travel times, custom intervals, and easy overlay with other spatial data. The project is designed for reproducibility and extensibility using OSMnx, GeoPandas, and modern software engineering practices.

## Features

* **Multi-center isochrones:** Generate isochrones for any set of centroids (hubs), each with its own travel time (rho)
* **Banding:** Isochrones can be calculated in bands (e.g., every 15 minutes up to N hours)
* **Coverage analysis:** Calculate how many input points (e.g., health units, facilities, deliveries) fall within each isochrone band for every centroid
* **Intersection analysis:** Identify overlaps between service areas (isochrones) of multiple hubs and count points in each overlap region (by band)
* **Real networks:** Uses OSMnx to compute realistic road-based isochrones (drive, walk, bike supported)
* **Multiple providers:** Use OSMnx, Mapbox, or Iso4App APIs for isochrone calculation
* **Preload networks:** Download and reuse national/city networks for instant analysis
* **Outputs:** Saves to GeoPackage (`.gpkg`), outputs results as JSON, and produces publication-quality maps with contextily basemaps
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

   Or, use `uv add <pkg>` as needed.

## Usage

### 1. Download/prepare a road network (recommended for speed)

```sh
uv run fetch_network.py "El Salvador"
```

This saves the national road network to `networks/el_salvador_drive.graphml` for future use.

### 2. Generate isochrones and analyze coverage

Edit `main.py` (or use your own request) to set your centroids (hubs) and input points (e.g., health units) and run:

```sh
uv run main.py --provider mapbox
```

* Isochrone polygons are saved to `outputs/{provider}_isochrones.gpkg`
* Coverage results (how many points fall within each band, which are out-of-band, and intersections) saved to `outputs/isochrone_coverage.json`

### 3. Plot isochrones (optionally overlay points)

```sh
uv run plot_isos.py --provider mapbox
```

* Reads from `outputs/{provider}_isochrones.gpkg`
* Saves map to `outputs/{provider}_isochrones_plot.png`
* Add `--plot-points` to overlay points

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

## Directory structure

```
├── main.py              # Main script for generating isochrones & coverage
├── plot_isos.py         # Plotting script for visualizing outputs
├── fetch_network.py     # Utility for downloading OSMnx road networks
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
* [OSMnx](https://github.com/gboeing/osmnx)
* [GeoPandas](https://geopandas.org/)
* [contextily](https://contextily.readthedocs.io/)
* [pydantic](https://docs.pydantic.dev/)
* [loguru](https://github.com/Delgan/loguru)
* [uv](https://github.com/astral-sh/uv) (recommended for env management)

## Development & Contribution

* Modular code: keep logic, I/O, plotting, and analysis separate
* Submit PRs with descriptive commits
* Add test cases if adding new modules
* See example workflows in `main.py` and `plot_isos.py`

For more details and advanced usage, see code comments and individual module docstrings.
