"""
File processing orchestrator.

Ties together:
  1. Parser selection (Shapefile vs KML)
  2. Feature extraction
  3. Measurement calculation
  4. Persistence to the database
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.geo_file import GeoFile, ProcessingStatus
from app.models.feature import Feature
from app.services.parsers.shapefile_parser import ShapefileParser
from app.services.parsers.kml_parser import KMLParser
from app.services.parsers.base import ParseResult
from app.services.measurement import calculate_measurements

logger = logging.getLogger(__name__)


def _select_parser(file_path: Path):
    suffix = file_path.suffix.lower()
    if suffix == ".zip":
        return ShapefileParser()
    if suffix == ".kml":
        return KMLParser()
    raise ValueError(f"Unsupported file type: '{suffix}'. Expected .zip or .kml.")


def process_geo_file(geo_file_id: str, file_path: Path, db: Session) -> None:
    """
    Main entry point called after an upload.

    Updates *geo_file* status to PROCESSING → COMPLETED (or FAILED).
    All database operations happen in the provided *db* session; the caller
    is responsible for committing / rolling back.
    """
    geo_file: GeoFile | None = db.get(GeoFile, geo_file_id)
    if geo_file is None:
        logger.error("GeoFile id=%s not found in DB.", geo_file_id)
        return

    geo_file.status = ProcessingStatus.PROCESSING
    db.commit()

    try:
        parser = _select_parser(file_path)
        result: ParseResult = parser.parse(file_path)

        _persist_features(geo_file, result, db)

        geo_file.crs = result.crs
        geo_file.feature_count = len(result.features)
        geo_file.status = ProcessingStatus.COMPLETED
        db.commit()

        logger.info(
            "GeoFile id=%s processed successfully: %d features, CRS=%s.",
            geo_file_id,
            geo_file.feature_count,
            geo_file.crs,
        )

    except Exception as exc:
        db.rollback()
        logger.exception("Processing failed for GeoFile id=%s: %s", geo_file_id, exc)

        # Re-fetch after rollback
        geo_file = db.get(GeoFile, geo_file_id)
        if geo_file:
            geo_file.status = ProcessingStatus.FAILED
            geo_file.error_message = str(exc)[:1024]
            db.commit()


def _persist_features(geo_file: GeoFile, result: ParseResult, db: Session) -> None:
    """Insert all parsed features (with measurements) into the database."""
    for parsed in result.features:
        measurements = calculate_measurements(
            parsed.geometry_geojson, parsed.crs
        )
        feature = Feature(
            geo_file_id=geo_file.id,
            feature_index=parsed.feature_index,
            geometry_type=parsed.geometry_type,
            geometry_geojson=json.dumps(parsed.geometry_geojson),
            properties=json.dumps(parsed.properties),
            crs=parsed.crs,
            area_m2=measurements.get("area_m2"),
            length_m=measurements.get("length_m"),
        )
        db.add(feature)
