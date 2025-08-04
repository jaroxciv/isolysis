# Isolysis

**Isochrone overlap analyzer for multi-center, multi-distance spatial queries.**

## Overview

Isolysis is a modular, production-grade Python package for calculating and analyzing isochrones (reachable areas) from multiple centers (hubs) over real road networks. It supports multiple travel times, custom intervals, and easy overlay with other spatial data. The project is designed for maximum reproducibility and extensibility using OSMnx, GeoPandas, and modern software engineering practices.

## Features

* **Multi-center isochrones:** Generate isochrones for any set of centroids (hubs), each with its own travel time (rho)
* **Banding:** Isochrones can be calculated in bands (e.g., every 15 minutes up to N hours)
* **Real networks:** Uses OSMnx to compute realistic road-based isochrones (drive, walk, bike supported)
* **Preload networks:** Download and reuse national/city networks for instant analysis
* **Outputs:** Saves to GeoPackage (`.gpkg`) and produces publication-quality maps with contextily basemaps
* **Clip to boundary:** Easily restrict isochrones to city or country polygons (optional)
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

### 2. Generate isochrones

Edit `main.py` to set your centroids (see template) and run:

```sh
uv run main.py
```

This creates banded isochrones and saves to `outputs/isochrones.gpkg`.

### 3. Plot isochrones

```sh
uv run plot_isos.py
```

This reads from `outputs/isochrones.gpkg` and saves a PNG map to `outputs/isochrones_plot.png`.

## Example

See the included `main.py` for a typical workflow with two hubs in El Salvador, producing isochrones every 15 minutes up to 1 hour, using 20 kph as travel speed.

## Directory structure

```
├── main.py              # Main script for generating isochrones
├── plot_isos.py         # Plotting script for visualizing outputs
├── fetch_network.py     # Utility for downloading OSMnx road networks
├── networks/            # Saved OSMnx graphml networks (not tracked)
├── outputs/             # Output files (GeoPackages, PNGs, etc)
├── isolysis/
│   ├── __init__.py
│   ├── io.py            # I/O models (Pydantic)
│   ├── isochrone.py     # Isochrone calculation logic
│   ├── plot.py          # Plotting utilities
│   └── utils.py         # Timing, helpers
└── ...
```

## Requirements

* Python 3.9+
* [OSMnx](https://github.com/gboeing/osmnx)
* [GeoPandas](https://geopandas.org/)
* [contextily](https://contextily.readthedocs.io/)
* [pydantic](https://docs.pydantic.dev/)
* [loguru](https://github.com/Delgan/loguru)
* [uv](https://github.com/astral-sh/uv) (recommended for env management)

## Development & Contribution

* Follow modular code practices (separate logic, I/O, plotting)
* Submit PRs with descriptive commits
* Add test cases if adding new modules
