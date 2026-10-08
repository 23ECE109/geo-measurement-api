"""
Pytest fixtures shared across the test suite.
"""

from __future__ import annotations

import io
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use an in-memory SQLite DB for tests
TEST_DATABASE_URL = "sqlite://"

# Patch settings BEFORE importing app modules that read them at import time
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp()

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    _engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db_session(engine):
    """Return a DB session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    """TestClient with the DB dependency overridden."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# File fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_kml_file(tmp_path: Path) -> Path:
    """A minimal valid KML file with one Point, one LineString, one Polygon."""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>Test Point</name>
      <Point>
        <coordinates>13.405,52.52,0</coordinates>
      </Point>
    </Placemark>
    <Placemark>
      <name>Test Line</name>
      <LineString>
        <coordinates>
          13.405,52.52,0
          13.415,52.53,0
          13.425,52.54,0
        </coordinates>
      </LineString>
    </Placemark>
    <Placemark>
      <name>Test Polygon</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              13.40,52.50,0
              13.41,52.50,0
              13.41,52.51,0
              13.40,52.51,0
              13.40,52.50,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
    kml_path = tmp_path / "test.kml"
    kml_path.write_text(content, encoding="utf-8")
    return kml_path


@pytest.fixture()
def sample_shapefile_zip(tmp_path: Path) -> Path:
    """
    Create a minimal Shapefile ZIP in-memory using fiona.
    Contains one Polygon feature in EPSG:4326.
    """
    import fiona
    from fiona.crs import CRS
    from shapely.geometry import mapping, Polygon as ShapelyPolygon

    shp_dir = tmp_path / "shp"
    shp_dir.mkdir()
    shp_path = shp_dir / "test.shp"

    schema = {
        "geometry": "Polygon",
        "properties": {"name": "str", "value": "float"},
    }
    with fiona.open(
        str(shp_path),
        "w",
        driver="ESRI Shapefile",
        schema=schema,
        crs=CRS.from_epsg(4326),
    ) as dst:
        poly = ShapelyPolygon(
            [(13.40, 52.50), (13.41, 52.50), (13.41, 52.51), (13.40, 52.51)]
        )
        dst.write(
            {
                "geometry": mapping(poly),
                "properties": {"name": "test_polygon", "value": 42.0},
            }
        )

    zip_path = tmp_path / "test_shapefile.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in shp_dir.iterdir():
            zf.write(f, arcname=f.name)

    return zip_path
