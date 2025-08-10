import pytest
import requests
import json
from loguru import logger


@pytest.fixture
def sample_centroid():
    return {"lat": 51.5074, "lon": -0.1278, "rho": 1.0, "id": "test"}


@pytest.fixture
def sample_pois():
    return [
        {"id": "poi1", "lat": 51.5074, "lon": -0.1278, "name": "Central POI"},
        {"id": "poi2", "lat": 51.5200, "lon": -0.1000, "name": "North POI"},
    ]


class TestHealth:
    def test_root(self, api_url):
        logger.info(f"Testing root endpoint: {api_url}")
        response = requests.get(f"{api_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Isolysis Isochrone API"

    def test_health(self, api_url):
        logger.info("Testing health endpoint")
        response = requests.get(f"{api_url}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "mapbox" in data["available_providers"]


class TestIsochrones:
    def test_simple_isochrone(self, api_url, sample_centroid):
        logger.info("Testing simple isochrone computation")
        payload = {
            "centroids": [sample_centroid],
            "options": {"provider": "mapbox", "num_bands": 1},
        }

        response = requests.post(f"{api_url}/isochrones", json=payload, timeout=60)
        assert response.status_code == 200

        data = response.json()
        assert data["provider"] == "mapbox"
        assert data["successful_computations"] == 1
        assert len(data["results"]) == 1

        result = data["results"][0]
        assert result["centroid_id"] == "test"
        assert "geojson" in result

    def test_multi_band(self, api_url, sample_centroid):
        logger.info("Testing multi-band isochrone")
        payload = {
            "centroids": [sample_centroid],
            "options": {"provider": "mapbox", "num_bands": 3},
        }

        response = requests.post(f"{api_url}/isochrones", json=payload, timeout=90)
        assert response.status_code == 200

        data = response.json()
        result = data["results"][0]
        features = result["geojson"]["features"]

        # Should have 3 bands
        band_hours = [f["properties"].get("band_hours") for f in features]
        band_hours = [b for b in band_hours if b is not None]
        assert len(band_hours) == 3

    def test_with_pois(self, api_url, sample_centroid, sample_pois):
        logger.info("Testing isochrone with POI analysis")
        payload = {
            "centroids": [sample_centroid],
            "options": {"provider": "mapbox", "num_bands": 2},
            "pois": sample_pois,
        }

        response = requests.post(f"{api_url}/isochrones", json=payload, timeout=90)
        assert response.status_code == 200

        data = response.json()
        assert "spatial_analysis" in data
        assert data["spatial_analysis"] is not None

        analysis = data["spatial_analysis"]
        assert analysis["total_pois"] == len(sample_pois)
        assert "coverage_analysis" in analysis
        assert "intersection_analysis" in analysis


class TestErrors:
    def test_invalid_coordinates(self, api_url):
        logger.info("Testing invalid coordinates")
        payload = {
            "centroids": [{"lat": 91.0, "lon": -0.1278, "rho": 1.0}],  # Invalid lat
            "options": {"provider": "mapbox"},
        }

        response = requests.post(f"{api_url}/isochrones", json=payload)
        assert response.status_code == 422  # Validation error

    def test_missing_provider_key(self, api_url, sample_centroid):
        logger.info("Testing missing provider key")
        payload = {
            "centroids": [sample_centroid],
            "options": {"provider": "iso4app"},  # Likely missing key
        }

        response = requests.post(f"{api_url}/isochrones", json=payload)
        # Should either work (key present) or return 400 (key missing)
        assert response.status_code in [200, 400]
