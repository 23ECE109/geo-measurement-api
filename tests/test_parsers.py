"""
Unit tests for file parsers.
"""

from pathlib import Path

import pytest

from app.services.parsers.kml_parser import KMLParser
from app.services.parsers.shapefile_parser import ShapefileParser


class TestKMLParser:
    def test_parse_returns_three_features(self, sample_kml_file: Path):
        parser = KMLParser()
        result = parser.parse(sample_kml_file)
        assert len(result.features) == 3

    def test_parse_crs_is_epsg4326(self, sample_kml_file: Path):
        parser = KMLParser()
        result = parser.parse(sample_kml_file)
        assert result.crs == "EPSG:4326"

    def test_parse_geometry_types(self, sample_kml_file: Path):
        parser = KMLParser()
        result = parser.parse(sample_kml_file)
        types = {f.geometry_type for f in result.features}
        assert "Point" in types
        assert "LineString" in types
        assert "Polygon" in types

    def test_file_type_is_kml(self, sample_kml_file: Path):
        parser = KMLParser()
        result = parser.parse(sample_kml_file)
        assert result.file_type == "kml"


class TestShapefileParser:
    def test_parse_returns_features(self, sample_shapefile_zip: Path):
        parser = ShapefileParser()
        result = parser.parse(sample_shapefile_zip)
        assert len(result.features) >= 1

    def test_parse_crs(self, sample_shapefile_zip: Path):
        parser = ShapefileParser()
        result = parser.parse(sample_shapefile_zip)
        assert "4326" in result.crs

    def test_file_type_is_shapefile(self, sample_shapefile_zip: Path):
        parser = ShapefileParser()
        result = parser.parse(sample_shapefile_zip)
        assert result.file_type == "shapefile"

    def test_invalid_zip_raises(self, tmp_path: Path):
        bad_zip = tmp_path / "bad.zip"
        bad_zip.write_bytes(b"not a zip file")
        parser = ShapefileParser()
        with pytest.raises(Exception):
            parser.parse(bad_zip)
