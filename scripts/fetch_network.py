# fetch_network.py

import os

import osmnx as ox
from loguru import logger


def fetch_and_save_network(
    place_name: str, network_type: str = "drive", out_dir: str = "networks"
):
    ox.settings.log_console = True
    ox.settings.use_cache = True
    os.makedirs(out_dir, exist_ok=True)
    logger.info(
        f"Downloading road network for '{place_name}' with mode '{network_type}'"
    )
    G = ox.graph_from_place(place_name, network_type=network_type)
    out_path = os.path.join(
        out_dir, f"{place_name.replace(' ', '_').lower()}_{network_type}.graphml"
    )
    ox.save_graphml(G, out_path)
    logger.success(f"Saved network to {out_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Download and save OSM road network as GraphML."
    )
    parser.add_argument("country", help="Country or place name (quoted if spaces)")
    parser.add_argument(
        "--network_type",
        default="drive",
        choices=["drive", "walk", "bike", "all"],
        help="Network type (default: drive)",
    )
    parser.add_argument(
        "--out_dir", default="networks", help="Output directory (default: networks/)"
    )
    args = parser.parse_args()
    fetch_and_save_network(args.country, args.network_type, args.out_dir)
