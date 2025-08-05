import os
import argparse
from loguru import logger
from isolysis.io import IsoRequest, Centroid, Coordinate
from isolysis.isochrone import compute_isochrones
from isolysis.utils import log_timing, harmonize_isochrones_columns
import geopandas as gpd
import osmnx as ox


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

    req = IsoRequest(
        coordinates=[
            Coordinate(id="a", lat=13.7, lon=-89.2),
            Coordinate(id="b", lat=13.72, lon=-89.19),
        ],
        centroids=[
            Centroid(id="hub1", lat=13.6900881, lon=-89.249961, rho=1),
            Centroid(id="hub2", lat=13.4785139, lon=-88.2103747, rho=1),
        ],
    )
    centroids = [c.model_dump() for c in req.centroids]

    isochrones = compute_isochrones(
        centroids,
        provider=args.provider,
        travel_speed_kph=30,
        interval=0.25,
        G=G,
    )
    logger.info("Generated {} banded isochrones.", len(isochrones))

    gdf = harmonize_isochrones_columns(isochrones)
    gdf.to_file(out_path, driver="GPKG", layer="isochrones")
    logger.success(f"Isochrone polygons saved to {out_path}")


if __name__ == "__main__":
    main()
