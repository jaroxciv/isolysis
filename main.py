import os
import json
import argparse
import pandas as pd
from loguru import logger
from isolysis.io import IsoRequest, Centroid, Coordinate, IsoCounts, IsoResponse
from isolysis.isochrone import compute_isochrones
from isolysis.analysis import (
    analyze_isochrone_coverage,
    analyze_isochrone_intersections,
)
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

    coords_df = pd.DataFrame([c.model_dump() for c in coords])
    points_gdf = gpd.GeoDataFrame(
        coords_df,
        geometry=gpd.points_from_xy(coords_df.lon, coords_df.lat),
        crs="EPSG:4326",
    )

    # --- Analyze isochrone coverage
    coverage_result = analyze_isochrone_coverage(gdf, points_gdf)
    intersections = analyze_isochrone_intersections(gdf, points_gdf)

    # Convert to IsoResponse
    # Expecting coverage_result to have: total_points, counts (list), oob_count, oob_ids
    response = IsoResponse(
        total_points=coverage_result["total_points"],
        counts=[
            IsoCounts(label=c["label"], count=c["count"], ids=c["ids"])
            for c in coverage_result["counts"]
        ],
        intersections=(
            [IsoCounts(**c) for c in intersections] if intersections else None
        ),
        oob_count=coverage_result["oob_count"],
        oob_ids=coverage_result["oob_ids"],
    )

    # Log results (as a table and JSON)
    output_json = json.dumps(response.model_dump(), indent=2, ensure_ascii=False)
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
