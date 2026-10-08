"""
Integration tests for the /api/files/ endpoints.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest


class TestUploadEndpoint:
    def test_upload_kml_returns_201(self, client, sample_kml_file: Path):
        with open(sample_kml_file, "rb") as fh:
            resp = client.post(
                "/api/files/",
                files={"file": ("test.kml", fh, "application/vnd.google-earth.kml+xml")},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "test.kml"
        assert data["status"] == "COMPLETED"
        assert data["feature_count"] == 3

    def test_upload_shapefile_returns_201(self, client, sample_shapefile_zip: Path):
        with open(sample_shapefile_zip, "rb") as fh:
            resp = client.post(
                "/api/files/",
                files={"file": ("test_shapefile.zip", fh, "application/zip")},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "COMPLETED"
        assert data["feature_count"] >= 1

    def test_upload_unsupported_type_returns_415(self, client):
        resp = client.post(
            "/api/files/",
            files={"file": ("data.geojson", b'{"type":"FeatureCollection"}', "application/json")},
        )
        assert resp.status_code == 415

    def test_upload_no_file_returns_422(self, client):
        resp = client.post("/api/files/")
        assert resp.status_code == 422


class TestGetFileEndpoint:
    def test_get_existing_file(self, client, sample_kml_file: Path):
        with open(sample_kml_file, "rb") as fh:
            upload = client.post(
                "/api/files/",
                files={"file": ("test.kml", fh, "application/vnd.google-earth.kml+xml")},
            )
        file_id = upload.json()["id"]

        resp = client.get(f"/api/files/{file_id}/")
        assert resp.status_code == 200
        assert resp.json()["id"] == file_id

    def test_get_nonexistent_file_returns_404(self, client):
        resp = client.get("/api/files/does-not-exist/")
        assert resp.status_code == 404


class TestMeasurementsEndpoint:
    def test_measurements_contain_area_for_polygon(self, client, sample_kml_file: Path):
        with open(sample_kml_file, "rb") as fh:
            upload = client.post(
                "/api/files/",
                files={"file": ("test.kml", fh, "application/vnd.google-earth.kml+xml")},
            )
        file_id = upload.json()["id"]

        resp = client.get(f"/api/files/{file_id}/measurements/")
        assert resp.status_code == 200
        data = resp.json()

        # Find polygon feature
        polygons = [f for f in data["features"] if f["geometry_type"] == "Polygon"]
        assert polygons, "Expected at least one Polygon feature"
        assert polygons[0]["area_m2"] is not None
        assert polygons[0]["area_m2"] > 0

    def test_measurements_contain_length_for_linestring(self, client, sample_kml_file: Path):
        with open(sample_kml_file, "rb") as fh:
            upload = client.post(
                "/api/files/",
                files={"file": ("test.kml", fh, "application/vnd.google-earth.kml+xml")},
            )
        file_id = upload.json()["id"]

        resp = client.get(f"/api/files/{file_id}/measurements/")
        assert resp.status_code == 200
        data = resp.json()

        lines = [f for f in data["features"] if f["geometry_type"] == "LineString"]
        assert lines, "Expected at least one LineString feature"
        assert lines[0]["length_m"] is not None
        assert lines[0]["length_m"] > 0

    def test_measurements_point_has_no_values(self, client, sample_kml_file: Path):
        with open(sample_kml_file, "rb") as fh:
            upload = client.post(
                "/api/files/",
                files={"file": ("test.kml", fh, "application/vnd.google-earth.kml+xml")},
            )
        file_id = upload.json()["id"]

        resp = client.get(f"/api/files/{file_id}/measurements/")
        assert resp.status_code == 200
        points = [f for f in resp.json()["features"] if f["geometry_type"] == "Point"]
        assert points
        assert points[0]["area_m2"] is None
        assert points[0]["length_m"] is None

    def test_measurements_404_for_unknown_file(self, client):
        resp = client.get("/api/files/ghost-id/measurements/")
        assert resp.status_code == 404


class TestListEndpoint:
    def test_list_files(self, client, sample_kml_file: Path):
        with open(sample_kml_file, "rb") as fh:
            client.post(
                "/api/files/",
                files={"file": ("test.kml", fh, "application/vnd.google-earth.kml+xml")},
            )
        resp = client.get("/api/files/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1


class TestDeleteEndpoint:
    def test_delete_file(self, client, sample_kml_file: Path):
        with open(sample_kml_file, "rb") as fh:
            upload = client.post(
                "/api/files/",
                files={"file": ("test.kml", fh, "application/vnd.google-earth.kml+xml")},
            )
        file_id = upload.json()["id"]

        del_resp = client.delete(f"/api/files/{file_id}/")
        assert del_resp.status_code == 204

        get_resp = client.get(f"/api/files/{file_id}/")
        assert get_resp.status_code == 404
