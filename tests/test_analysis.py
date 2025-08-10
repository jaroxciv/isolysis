import pytest
import geopandas as gpd
from shapely.geometry import Point, Polygon
from loguru import logger

from isolysis.analysis import (
    compute_band_coverage,
    compute_spatial_analysis,
    pois_to_geodataframe,
    format_time_display,
)
from api.schemas import POI


@pytest.fixture
def sample_isochrones():
    """Simple test isochrones"""
    poly1 = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])  # Small
    poly2 = Polygon([(-0.5, -0.5), (-0.5, 1.5), (1.5, 1.5), (1.5, -0.5)])  # Large

    return gpd.GeoDataFrame(
        [
            {"centroid_id": "C1", "band_hours": 0.25, "geometry": poly1},
            {"centroid_id": "C1", "band_hours": 0.5, "geometry": poly2},
        ],
        crs="EPSG:4326",
    )


@pytest.fixture
def sample_pois():
    """Simple test POIs"""
    return [
        POI(id="poi1", lat=0.5, lon=0.5, name="Inside POI"),  # Inside both
        POI(id="poi2", lat=0.2, lon=0.2, name="Small POI"),  # Inside small only
        POI(id="poi3", lat=2.0, lon=2.0, name="Outside POI"),  # Outside all
    ]


class TestUtils:
    def test_format_time_display(self):
        logger.info("Testing time formatting")
        assert format_time_display(0.25) == "15min"
        assert format_time_display(1.0) == "1h"
        assert format_time_display(1.5) == "1.5h"

    def test_pois_to_geodataframe(self, sample_pois):
        logger.info("Testing POI conversion")
        gdf = pois_to_geodataframe(sample_pois)

        assert len(gdf) == len(sample_pois)
        assert gdf.crs.to_string() == "EPSG:4326"
        assert "id" in gdf.columns


class TestCoverage:
    def test_band_coverage(self, sample_isochrones, sample_pois):
        logger.info("Testing band coverage computation")
        pois_gdf = pois_to_geodataframe(sample_pois)
        coverages = compute_band_coverage(sample_isochrones, pois_gdf)

        assert len(coverages) == 2  # 2 bands

        # Check small band (0.25h) - should cover poi1, poi2
        small_band = next(c for c in coverages if c.band_hours == 0.25)
        assert small_band.poi_count == 2
        assert "poi1" in small_band.poi_ids
        assert "poi2" in small_band.poi_ids

    def test_empty_pois(self, sample_isochrones):
        logger.info("Testing coverage with empty POIs")
        empty_gdf = gpd.GeoDataFrame(columns=["id", "geometry"], crs="EPSG:4326")
        coverages = compute_band_coverage(sample_isochrones, empty_gdf)
        assert len(coverages) == 0


class TestSpatialAnalysis:
    def test_complete_analysis(self, sample_isochrones, sample_pois):
        logger.info("Testing complete spatial analysis")
        analysis = compute_spatial_analysis(sample_isochrones, sample_pois)

        assert analysis.total_pois == len(sample_pois)
        assert analysis.total_centroids == 1
        assert analysis.total_bands == 2

        # Check coverage
        assert len(analysis.coverage_analysis) == 1
        coverage = analysis.coverage_analysis[0]
        assert coverage.centroid_id == "C1"
        assert coverage.total_bands == 2

    def test_oob_analysis(self, sample_isochrones, sample_pois):
        logger.info("Testing out-of-band analysis")
        analysis = compute_spatial_analysis(sample_isochrones, sample_pois)

        # poi3 should be out of band
        oob = analysis.oob_analysis
        assert oob.total_oob_pois == 1
        assert "poi3" in oob.oob_poi_ids
        assert oob.oob_percentage > 0

    def test_empty_input(self):
        logger.info("Testing analysis with empty input")
        empty_gdf = gpd.GeoDataFrame(
            columns=["centroid_id", "band_hours", "geometry"], crs="EPSG:4326"
        )
        analysis = compute_spatial_analysis(empty_gdf, [])

        assert analysis.total_pois == 0
        assert analysis.global_coverage_percentage == 0.0


class TestPerformance:
    def test_many_pois(self, sample_isochrones):
        logger.info("Testing performance with many POIs")

        # Generate 500 POIs
        many_pois = [
            POI(id=f"poi_{i}", lat=0.5, lon=0.5, name=f"POI {i}") for i in range(500)
        ]

        import time

        start = time.time()
        analysis = compute_spatial_analysis(sample_isochrones, many_pois)
        duration = time.time() - start

        assert analysis.total_pois == 500
        assert duration < 10  # Should complete within 10 seconds
        logger.success(f"Processed {len(many_pois)} POIs in {duration:.2f}s")
