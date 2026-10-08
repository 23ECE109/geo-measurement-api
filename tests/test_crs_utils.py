"""
Unit tests for CRS utility helpers.
"""

import pytest
from shapely.geometry import Point, Polygon

from app.services.crs_utils import utm_epsg_for_geometry, get_projected_geometry


class TestUtmEpsg:
    def test_berlin_utm_zone_33n(self):
        # Berlin ~13.4°E, 52.5°N → UTM zone 33N → EPSG:32633
        pt = Point(13.4, 52.5)
        assert utm_epsg_for_geometry(pt) == "EPSG:32633"

    def test_new_york_utm_zone_18n(self):
        # New York ~-74°E, 40.7°N → UTM zone 18N → EPSG:32618
        pt = Point(-74.0, 40.7)
        assert utm_epsg_for_geometry(pt) == "EPSG:32618"

    def test_southern_hemisphere(self):
        # Sydney ~151°E, -33.9°N → UTM zone 56S → EPSG:32756
        pt = Point(151.0, -33.9)
        assert utm_epsg_for_geometry(pt) == "EPSG:32756"


class TestGetProjectedGeometry:
    def test_geographic_crs_is_reprojected(self):
        poly = Polygon(
            [(13.40, 52.50), (13.41, 52.50), (13.41, 52.51), (13.40, 52.51)]
        )
        projected, target_crs = get_projected_geometry(poly, "EPSG:4326")
        assert "32633" in target_crs  # UTM zone 33N
        # Area in m² should be reasonable for a ~1 km² block
        # A 0.01° × 0.01° box near Berlin is roughly 0.75 km²
        assert projected.area > 500_000  # > 0.5 km²

    def test_already_projected_crs_unchanged(self):
        # A geometry already in a metric CRS should be returned as-is
        import pyproj
        from shapely.ops import transform

        poly_4326 = Polygon(
            [(13.40, 52.50), (13.41, 52.50), (13.41, 52.51), (13.40, 52.51)]
        )
        transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32633", always_xy=True)
        poly_32633 = transform(transformer.transform, poly_4326)

        projected, crs = get_projected_geometry(poly_32633, "EPSG:32633")
        assert crs == "EPSG:32633"
        assert projected.equals_exact(poly_32633, tolerance=1e-3)
