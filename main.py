import os
from loguru import logger
from isolysis.io import IsoRequest, Centroid, Coordinate
from isolysis.isochrone import compute_isochrones
from isolysis.utils import log_timing
import geopandas as gpd

import osmnx as ox


@log_timing
def main():
    # Prepare output directory
    out_dir = "outputs"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "isochrones.gpkg")

    # Optional: path to predownloaded network
    network_path = os.path.join("networks", "el_salvador_drive.graphml")
    G = None
    if os.path.exists(network_path):
        logger.info(f"Loading predownloaded network: {network_path}")
        G = ox.load_graphml(network_path)
    else:
        logger.warning(
            f"Predownloaded network not found, will download on demand: {network_path}"
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

    # Generate banded isochrones (e.g., every 0.5h up to rho)
    isochrones = compute_isochrones(
        centroids,
        provider="osmnx",
        travel_speed_kph=20,
        interval=0.25,  # 30 min bands
        project_utm=False,
        G=G,
    )
    logger.info("Generated {} banded isochrones.", len(isochrones))

    # Save as GPKG with all attributes
    gdf = gpd.GeoDataFrame(isochrones, geometry="geometry", crs="EPSG:4326")
    gdf.to_file(out_path, driver="GPKG", layer="isochrones")
    logger.success(f"Isochrone polygons saved to {out_path}")


if __name__ == "__main__":
    main()
