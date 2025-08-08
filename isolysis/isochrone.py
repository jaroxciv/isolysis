import os
import requests
import alphashape
import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import shape, Point, MultiPoint
from typing import List, Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv
from abc import ABC, abstractmethod

load_dotenv()


def generate_time_bands(max_rho: float, interval: float = 0.5) -> List[float]:
    n_bands = int(max_rho / interval)
    bands = [round(i * interval, 2) for i in range(1, n_bands + 1)]
    if bands and bands[-1] < max_rho:
        bands.append(round(max_rho, 2))
    elif not bands:
        bands = [round(max_rho, 2)]
    return bands


def extract_local_subgraph(G, lat, lon, max_dist_m):
    import numpy as np
    from osmnx.distance import great_circle

    node_ids = list(G.nodes())
    node_x = np.array([G.nodes[n]["x"] for n in node_ids])
    node_y = np.array([G.nodes[n]["y"] for n in node_ids])
    dists = great_circle(lat, lon, node_y, node_x)
    nodes_within_radius = [n for n, d in zip(node_ids, dists) if d <= max_dist_m]
    subgraph = G.subgraph(nodes_within_radius).copy()
    return subgraph


# Abstract base class for providers
class IsochroneProvider(ABC):
    @abstractmethod
    def compute(
        self, centroids: List[Dict[str, Any]], **kwargs
    ) -> List[Dict[str, Any]]:
        pass


# OSMnx implementation
class OsmnxIsochroneProvider(IsochroneProvider):
    def compute(
        self,
        centroids: List[Dict[str, Any]],
        travel_speed_kph: float = 30,
        network_type: str = "drive",
        interval: Optional[float] = None,
        project_utm: bool = False,
        G: Optional[nx.MultiDiGraph] = None,
        max_dist_buffer: float = 1.1,
        alpha: Optional[float] = 0.01,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        results = []
        meters_per_minute = (travel_speed_kph * 1000) / 60  # Precompute

        for c in centroids:
            lon, lat = float(c["lon"]), float(c["lat"])
            max_rho = float(c.get("rho", 1.0))
            current_interval = interval if interval is not None else (max_rho / 4.0)
            bands = generate_time_bands(max_rho, current_interval)
            max_dist_m = travel_speed_kph * max_rho * 1000 * max_dist_buffer

            # Prepare local graph
            centroid_id = c.get("id", "unknown")
            if G is not None:
                logger.info(
                    "Extracting subgraph for id={} from preloaded network", centroid_id
                )
                local_G = extract_local_subgraph(G, lat, lon, max_dist_m)
            else:
                logger.info("Downloading OSMnx network for id={}", centroid_id)
                local_G = ox.graph_from_point(
                    (lat, lon), dist=max_dist_m, network_type=network_type
                )

            # Project if needed
            if project_utm and not getattr(local_G.graph, "is_projected", False):
                local_G = ox.projection.project_graph(local_G)

            # Add travel_time edge attribute once
            for _, _, _, data in local_G.edges(keys=True, data=True):
                data["travel_time"] = data["length"] / meters_per_minute

            # Find center node in projected space if needed
            center_node = ox.distance.nearest_nodes(local_G, lon, lat)

            for band in bands:
                trip_time = band * 60  # hours to minutes
                subgraph = nx.ego_graph(
                    local_G, center_node, radius=trip_time, distance="travel_time"
                )

                if subgraph.number_of_nodes() == 0:
                    logger.warning(
                        "No reachable nodes for centroid id={} band={:.2f}h",
                        centroid_id,
                        band,
                    )
                    continue

                coords = [
                    (data["x"], data["y"]) for _, data in subgraph.nodes(data=True)
                ]

                poly = None
                if len(coords) >= 4:
                    try:
                        poly = alphashape.alphashape(coords, alpha)
                        # If alpha shape is MultiPolygon, get the largest
                        if hasattr(poly, "geoms"):
                            poly = max(list(poly.geoms), key=lambda g: g.area)
                    except Exception as e:
                        logger.warning(
                            f"Alpha shape failed, falling back to convex hull: {e}"
                        )

                if poly is None:
                    # Fallback to convex hull
                    poly = MultiPoint([Point(xy) for xy in coords]).convex_hull

                results.append(
                    {
                        "centroid_id": centroid_id,
                        "band_hours": band,
                        "geometry": poly,
                        "rho": max_rho,
                        "lat": lat,
                        "lon": lon,
                    }
                )
                logger.success(
                    "Isochrone band {:.2f}h generated for id={}",
                    band,
                    centroid_id,
                )
        return results


# Iso4App implementation
class Iso4AppIsochroneProvider(IsochroneProvider):
    BASE_URL = "http://www.iso4app.net/rest/1.3/isoline.geojson"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def compute(
        self,
        centroids: List[Dict[str, Any]],
        value_type: str = "isochrone",
        travel_type: str = "motor_vehicle",
        interval: float = 1.0,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        isochrones = []
        for c in centroids:
            lat = c["lat"]
            lon = c["lon"]
            centroid_id = c.get("id", "unknown")
            rho = c.get("rho", 1.0)
            max_secs = int(float(rho) * 3600)
            bands = [
                int(t * 3600)
                for t in [i * interval for i in range(1, int(rho / interval) + 1)]
            ]
            if not bands:
                bands = [max_secs]

            # General info: which bands, etc.
            logger.info(
                f"Iso4App: Requesting isochrones for id={centroid_id}, "
                f"bands={[b // 60 for b in bands]} min, travel_type={travel_type}"
            )

            for band_secs in bands:
                params = {
                    "licKey": self.api_key,
                    "type": value_type,
                    "value": band_secs,
                    "lat": lat,
                    "lng": lon,
                    "mobility": travel_type,
                    "format": "geojson",
                }
                try:
                    response = requests.get(self.BASE_URL, params=params)
                    if response.status_code != 200:
                        logger.error(
                            f"Iso4App [{centroid_id} {band_secs // 60}min]: "
                            f"API error {response.status_code}, {response.text}"
                        )
                        continue
                    geojson = response.json()
                    poly = None
                    for feat in geojson.get("features", []):
                        if feat["geometry"]["type"] in ["Polygon", "MultiPolygon"]:
                            poly = shape(feat["geometry"])
                            break
                    if poly is not None:
                        isochrones.append(
                            {
                                "id": centroid_id,
                                "band_hours": band_secs / 3600,
                                "geometry": poly,
                            }
                        )
                        logger.success(
                            f"Iso4App: Isochrone band {band_secs // 60}min generated for id={centroid_id}"
                        )
                    else:
                        logger.warning(
                            f"Iso4App: No isochrone geometry for id={centroid_id}, band={band_secs // 60}min"
                        )
                except Exception as e:
                    logger.error(
                        f"Iso4App: Exception for id={centroid_id}, band={band_secs // 60}min: {e}"
                    )
        return isochrones


class MapboxIsochroneProvider(IsochroneProvider):
    BASE_URL = "https://api.mapbox.com/isochrone/v1/mapbox"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def compute(
        self,
        centroids: List[Dict[str, Any]],
        interval: float = 0.25,  # in hours
        profile: str = "driving",
        **kwargs,
    ) -> List[Dict[str, Any]]:
        isochrones = []
        for c in centroids:
            lat = c["lat"]
            lon = c["lon"]
            centroid_id = c.get("id", "unknown")
            rho = c.get("rho", 1.0)
            bands_hours = generate_time_bands(rho, interval)
            bands_minutes = [int(b * 60) for b in bands_hours]
            logger.info(
                f"Mapbox: Requesting isochrones for id={centroid_id}, "
                f"bands={bands_minutes} min, profile={profile}, location=({lat}, {lon})"
            )
            params = {
                "contours_minutes": ",".join(map(str, bands_minutes)),
                "polygons": "true",
                "access_token": self.api_key,
                "denoise": 1,
            }
            url = f"{self.BASE_URL}/{profile}/{lon},{lat}"
            try:
                response = requests.get(url, params=params)
                if response.status_code != 200:
                    logger.error(
                        f"MapboxIsochrone [{centroid_id}]: API error {response.status_code}, {response.text}"
                    )
                    continue

                # Mapbox returns features ordered largest (outermost) to smallest (innermost):
                # We reverse bands so the largest band matches the largest polygon.
                geojson = response.json()
                for band_h, feat in zip(
                    reversed(bands_hours), geojson.get("features", [])
                ):
                    if feat["geometry"]["type"] in ["Polygon", "MultiPolygon"]:
                        poly = shape(feat["geometry"])
                        isochrones.append(
                            {
                                "id": centroid_id,
                                "band_hours": band_h,
                                "geometry": poly,
                            }
                        )
                        logger.success(
                            f"Mapbox: Isochrone band {band_h}h generated for id={centroid_id}"
                        )
            except Exception as e:
                logger.error(f"MapboxIsochrone: Exception for id={centroid_id}: {e}")
        return isochrones


# Factory function
def get_isochrone_provider(provider: str, **kwargs) -> IsochroneProvider:
    if provider == "osmnx":
        return OsmnxIsochroneProvider()
    elif provider == "iso4app":
        api_key = kwargs.get("api_key") or os.getenv("ISO4APP_API_KEY")
        if not api_key:
            raise ValueError("api_key is required for Iso4App provider")
        return Iso4AppIsochroneProvider(api_key)
    elif provider == "mapbox":
        api_key = kwargs.get("api_key") or os.getenv("MAPBOX_API_KEY")
        if not api_key:
            raise ValueError("api_key is required for Mapbox provider")
        return MapboxIsochroneProvider(api_key)
    else:
        raise ValueError(f"Unknown isochrone provider: {provider}")


# Main interface for user code (drop-in compatible)
def compute_isochrones(centroids, provider="osmnx", **kwargs):
    iso_provider = get_isochrone_provider(provider, **kwargs)
    return iso_provider.compute(centroids, **kwargs)
