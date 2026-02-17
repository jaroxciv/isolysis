import os
import shutil

import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from rasterio.transform import from_origin
from shapely.geometry import Polygon, mapping

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
def sample_raster():
    """Create a temporary raster file with known values inside the project directory."""
    test_dir = os.path.join(os.getcwd(), "data", "tmp", "test_rasters")
    os.makedirs(test_dir, exist_ok=True)
    path = os.path.join(test_dir, "raster_test.tif")

    data = np.arange(100, dtype=np.float32).reshape(10, 10)
    transform = from_origin(0, 10, 1, 1)

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

    yield str(path)

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


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
        assert response.status_code == 422  # Pydantic validation error

    def test_invalid_raster_path(self, sample_isochrones):
        """Should handle non-existing raster gracefully (per-polygon stats skipped, intersections may still appear)"""
        payload = {
            "isochrones": sample_isochrones,
            "rasters": [{"path": "non_existent_file.tif"}],
        }

        response = client.post("/raster-stats", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["results"], list)
        # Per-polygon stats are skipped for missing rasters, but intersection geometry
        # is still computed (with zero stats). Verify no per-isochrone results.
        isochrone_results = [
            r for r in data["results"] if r.get("scope") == "isochrone"
        ]
        assert len(isochrone_results) == 0
