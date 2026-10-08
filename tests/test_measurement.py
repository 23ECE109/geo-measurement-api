"""
Unit tests for the measurement service.
"""

import pytest

from app.services.measurement import calculate_measurements


class TestCalculateMeasurements:
    def test_polygon_area(self):
        # A 0.01° × 0.01° box near Berlin
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [13.40, 52.50],
                    [13.41, 52.50],
                    [13.41, 52.51],
                    [13.40, 52.51],
                    [13.40, 52.50],
                ]
            ],
        }
        result = calculate_measurements(geom, "EPSG:4326")
        assert result["area_m2"] is not None
        assert result["area_m2"] > 0
        assert result["length_m"] is None

    def test_linestring_length(self):
        geom = {
            "type": "LineString",
            "coordinates": [[13.405, 52.52], [13.415, 52.53]],
        }
        result = calculate_measurements(geom, "EPSG:4326")
        assert result["length_m"] is not None
        assert result["length_m"] > 0
        assert result["area_m2"] is None

    def test_point_no_measurements(self):
        geom = {"type": "Point", "coordinates": [13.4, 52.5]}
        result = calculate_measurements(geom, "EPSG:4326")
        assert result["area_m2"] is None
        assert result["length_m"] is None

    def test_unsupported_geometry_no_crash(self):
        # "TIN" is not a standard GeoJSON type; should return None values
        geom = {"type": "TIN", "coordinates": []}
        result = calculate_measurements(geom, "EPSG:4326")
        assert result["area_m2"] is None
        assert result["length_m"] is None

    def test_multipolygon_area(self):
        geom = {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [13.40, 52.50],
                        [13.41, 52.50],
                        [13.41, 52.51],
                        [13.40, 52.51],
                        [13.40, 52.50],
                    ]
                ]
            ],
        }
        result = calculate_measurements(geom, "EPSG:4326")
        assert result["area_m2"] is not None
        assert result["area_m2"] > 0

    def test_multilinestring_length(self):
        geom = {
            "type": "MultiLineString",
            "coordinates": [
                [[13.405, 52.52], [13.415, 52.53]],
                [[13.415, 52.53], [13.425, 52.54]],
            ],
        }
        result = calculate_measurements(geom, "EPSG:4326")
        assert result["length_m"] is not None
        assert result["length_m"] > 0
