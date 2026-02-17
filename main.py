import argparse
import json
import os

import osmnx as ox
from loguru import logger

from api.schemas import POI
from isolysis.analysis import compute_spatial_analysis
from isolysis.io import Centroid, Coordinate, IsoRequest
from isolysis.isochrone import compute_isochrones
from isolysis.utils import harmonize_isochrones_columns, log_timing


@log_timing
def main():
    parser = argparse.ArgumentParser(description="Isochrone computation CLI")
    parser.add_argument(
        "--provider",
        type=str,
        choices=["osmnx", "iso4app", "mapbox"],
        default="osmnx",
        help="Which provider to use for isochrone calculation",
    )
    parser.add_argument(
        "--plot-points",
        action="store_true",
        help="If set, plots the coordinates (points) together with the isochrones",
    )
    args = parser.parse_args()

    out_dir = "outputs"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{args.provider}_isochrones.gpkg")

    # Optionally load network for OSMnx
    G = None
    if args.provider == "osmnx":
        graph_path = os.path.join("networks", "el_salvador_drive.graphml")
        if os.path.exists(graph_path):
            logger.info(f"Loading predownloaded network: {graph_path}")
            G = ox.load_graphml(graph_path)
        else:
            logger.warning(
                f"No predownloaded network found at {graph_path}, will download on the fly"
            )

    with open("data/coords.json", encoding="utf-8") as f:
        coords = [Coordinate(**c) for c in json.load(f)]

    centroids = [
        Centroid(id="hub1", lat=13.6900881, lon=-89.249961, rho=1),
        Centroid(id="hub2", lat=13.4785139, lon=-88.2103747, rho=1),
        Centroid(id="hub3", lat=13.9837809, lon=-89.6406763, rho=1),
    ]
    req = IsoRequest(
        coordinates=coords,
        centroids=centroids,
    )
    centroids_dicts = [c.model_dump() for c in req.centroids]

    isochrones = compute_isochrones(
        centroids_dicts,
        provider=args.provider,
        travel_speed_kph=30,
        interval=0.25,
        G=G,
    )
    logger.info("Generated {} banded isochrones.", len(isochrones))

    gdf = harmonize_isochrones_columns(isochrones)
    gdf.to_file(out_path, driver="GPKG", layer="isochrones")
    logger.success(f"Isochrone polygons saved to {out_path}")

    # Convert coordinates to POIs for spatial analysis
    pois = [
        POI(
            id=c.id or f"poi_{i}",
            lat=c.lat,
            lon=c.lon,
            name=c.name,
            region=c.region,
            municipality=c.municipality,
            metadata=None,
        )
        for i, c in enumerate(coords)
    ]

    # Run spatial analysis
    result = compute_spatial_analysis(gdf, pois)

    # Log results
    output_json = json.dumps(
        result.model_dump(), indent=2, ensure_ascii=False, default=str
    )
    logger.info(
        "Isochrone coverage analysis result:\n{}",
        output_json,
    )

    # Save as JSON in outputs/
    results_path = os.path.join("outputs", "isochrone_coverage.json")
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(output_json)

    logger.success(f"Isochrone coverage results saved to {results_path}")


if __name__ == "__main__":
    main()
