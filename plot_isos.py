import argparse
import geopandas as gpd
import json
from isolysis.plot import plot_isochrones

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot banded isochrones by provider")
    parser.add_argument(
        "--provider",
        type=str,
        required=True,
        choices=["osmnx", "iso4app", "mapbox"],
        help="Isochrone provider (used for input/output file naming)",
    )
    parser.add_argument(
        "--plot-points",
        action="store_true",
        help="If set, overlay the points from data/coords.json"
    )
    args = parser.parse_args()

    gpkg_path = f"outputs/{args.provider}_isochrones.gpkg"
    out_png = f"outputs/{args.provider}_isochrones_plot.png"

    # Optionally load points if requested
    points_gdf = None
    if args.plot_points:
        with open("data/coords.json", encoding="utf-8") as f:
            coords = json.load(f)
        # Create GeoDataFrame from list of dicts
        points_gdf = gpd.GeoDataFrame(
            coords,
            geometry=gpd.points_from_xy([c["lon"] for c in coords], [c["lat"] for c in coords]),
            crs="EPSG:4326"
        )

    plot_isochrones(
        gpkg_path=gpkg_path,
        out_png=out_png,
        provider=args.provider,
        points_gdf=points_gdf,
    )
