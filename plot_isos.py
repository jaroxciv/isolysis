import argparse
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
    args = parser.parse_args()

    gpkg_path = f"outputs/{args.provider}_isochrones.gpkg"
    out_png = f"outputs/{args.provider}_isochrones_plot.png"

    plot_isochrones(
        gpkg_path=gpkg_path,
        out_png=out_png,
        provider=args.provider,
    )
