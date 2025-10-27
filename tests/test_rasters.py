import pytest
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import Polygon, mapping
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


@pytest.fixture
def sample_isochrones():
    """Simple isochrone geometries"""
    poly1 = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
    poly2 = Polygon([(0.5, 0.5), (0.5, 1.5), (1.5, 1.5), (1.5, 0.5)])
    return [
        {"centroid_id": "C1", "geometry": mapping(poly1)},
        {"centroid_id": "C2", "geometry": mapping(poly2)},
    ]


@pytest.fixture
def sample_raster(tmp_path):
    """Create a temporary raster file with known values"""
    data = np.arange(100, dtype=np.float32).reshape(10, 10)
    transform = from_origin(0, 10, 1, 1)
    path = tmp_path / "raster_test.tif"

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=data.shape[0],
        width=data.shape[1],
        count=1,
        dtype=data.dtype,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    return str(path)


class TestRasterStats:
    def test_valid_raster_stats(self, sample_isochrones, sample_raster):
        payload = {
            "isochrones": sample_isochrones,
            "rasters": [{"path": sample_raster}],
        }

        response = client.post("/raster-stats", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        results = data["results"]
        assert isinstance(results, list)
        assert len(results) > 0

        first = results[0]
        # Validate expected numeric fields
        for key in ["area_km2", "mean", "sum"]:
            assert key in first

    def test_missing_fields(self):
        """Should fail when required keys are missing"""
        response = client.post("/raster-stats", json={})
        assert response.status_code == 400
        data = response.json()
        assert "Missing isochrones" in data["detail"]

    def test_invalid_raster_path(self, sample_isochrones):
        """Should skip or handle non-existing raster gracefully"""
        payload = {
            "isochrones": sample_isochrones,
            "rasters": [{"path": "non_existent_file.tif"}],
        }

        response = client.post("/raster-stats", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["results"], list)
        # Should be empty due to skipped rasters
        assert len(data["results"]) == 0
