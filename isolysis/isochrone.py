# isolysis/isochrone.py

import osmnx as ox
import networkx as nx
from shapely.geometry import MultiPoint, Point
from typing import List, Dict, Any, Optional
from loguru import logger


def generate_time_bands(max_rho: float, interval: float = 0.5) -> List[float]:
    n_bands = int(max_rho / interval)
    bands = [round(i * interval, 2) for i in range(1, n_bands + 1)]
    if bands and bands[-1] < max_rho:
        bands.append(round(max_rho, 2))
    elif not bands:
        bands = [round(max_rho, 2)]
    return bands


def extract_local_subgraph(G, lat, lon, max_dist_m):
    """
    Extract a subgraph around (lat, lon) with radius max_dist_m (meters).
    """
    import numpy as np
    from osmnx.distance import great_circle

    node_ids = list(G.nodes())
    node_x = np.array([G.nodes[n]["x"] for n in node_ids])
    node_y = np.array([G.nodes[n]["y"] for n in node_ids])
    # Calculate distances to all nodes (in meters)
    dists = great_circle(lat, lon, node_y, node_x)
    nodes_within_radius = [n for n, d in zip(node_ids, dists) if d <= max_dist_m]
    subgraph = G.subgraph(nodes_within_radius).copy()
    return subgraph


def compute_osmnx_isochrones(
    centroids: List[Dict[str, Any]],
    travel_speed_kph: float = 30,
    network_type: str = "drive",
    interval: float = 0.5,
    project_utm: bool = False,
    G: Optional[nx.MultiDiGraph] = None,  # <-- accept preloaded graph!
    max_dist_buffer: float = 1.1,
) -> List[Dict[str, Any]]:
    results = []
    for c in centroids:
        lon = float(c["lon"])
        lat = float(c["lat"])
        max_rho = float(c.get("rho", 1.0))  # maximum hours
        bands = generate_time_bands(max_rho, interval)
        max_dist_m = travel_speed_kph * max_rho * 1000 * max_dist_buffer

        # Use provided network or download subgraph as before
        if G is not None:
            logger.info(
                "Extracting subgraph for id={} from preloaded network",
                c.get("id", "unknown"),
            )
            local_G = extract_local_subgraph(G, lat, lon, max_dist_m)
            # Optionally project subgraph here
            if project_utm:
                local_G = ox.projection.project_graph(local_G)
        else:
            logger.info("Downloading OSMnx network for id={}", c.get("id", "unknown"))
            local_G = ox.graph_from_point(
                (lat, lon), dist=max_dist_m, network_type=network_type
            )
            if project_utm:
                local_G = ox.projection.project_graph(local_G)

        meters_per_minute = (travel_speed_kph * 1000) / 60
        for u, v, k, data in local_G.edges(keys=True, data=True):
            data["travel_time"] = data["length"] / meters_per_minute
        center_node = ox.distance.nearest_nodes(local_G, lon, lat)
        for band in bands:
            trip_time = band * 60  # band in hours, convert to minutes
            subgraph = nx.ego_graph(
                local_G, center_node, radius=trip_time, distance="travel_time"
            )
            node_points = [
                Point((data["x"], data["y"]))
                for node, data in subgraph.nodes(data=True)
            ]
            if node_points:
                polygon = MultiPoint(node_points).convex_hull
                results.append(
                    {
                        "centroid_id": c.get("id", "unknown"),
                        "band_hours": band,
                        "geometry": polygon,
                        "rho": max_rho,
                        "lat": lat,
                        "lon": lon,
                    }
                )
                logger.success(
                    "Isochrone band {:.2f}h generated for id={}",
                    band,
                    c.get("id", "unknown"),
                )
            else:
                logger.warning(
                    "No reachable nodes for centroid id={} band={}",
                    c.get("id", "unknown"),
                    band,
                )
    return results


def compute_isochrones(
    centroids: List[Dict[str, Any]], provider: str = "osmnx", **kwargs
) -> List[Dict[str, Any]]:
    if provider == "osmnx":
        return compute_osmnx_isochrones(centroids, **kwargs)
    else:
        raise ValueError(f"Unknown isochrone provider: {provider}")
