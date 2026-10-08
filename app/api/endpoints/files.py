"""
File endpoints.

POST /api/files/             – Upload and process a geospatial file
GET  /api/files/{id}/        – File info / status
GET  /api/files/{id}/measurements/ – Feature measurements
GET  /api/files/             – List all uploaded files (bonus)
DELETE /api/files/{id}/      – Delete a file record and its features (bonus)
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.feature import Feature
from app.models.geo_file import GeoFile, ProcessingStatus
from app.schemas.geo_file import (
    FeatureResponse,
    GeoFileResponse,
    MeasurementsResponse,
)
from app.services.file_processor import process_geo_file

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=GeoFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a geospatial file",
    description=(
        "Accepts a `.zip` (containing a Shapefile) or a `.kml` file. "
        "Processes the file synchronously and returns the file record with "
        "status `COMPLETED` or `FAILED`."
    ),
)
def upload_file(
    file: UploadFile = File(..., description="A .zip (Shapefile) or .kml file"),
    db: Session = Depends(get_db),
) -> GeoFileResponse:
    _validate_upload(file)

    # Persist the file to disk
    suffix = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}{suffix}"
    dest_path = settings.UPLOAD_DIR / unique_name

    try:
        with dest_path.open("wb") as out_fh:
            shutil.copyfileobj(file.file, out_fh)
    finally:
        file.file.close()

    # Determine file type label
    file_type = "shapefile" if suffix == ".zip" else "kml"

    # Create DB record
    geo_file = GeoFile(
        filename=file.filename,
        file_path=str(dest_path),
        file_type=file_type,
        status=ProcessingStatus.PENDING,
    )
    db.add(geo_file)
    db.commit()
    db.refresh(geo_file)

    # Process synchronously (for an async/worker approach see README)
    process_geo_file(geo_file.id, dest_path, db)
    db.refresh(geo_file)

    return GeoFileResponse.model_validate(geo_file)


# ---------------------------------------------------------------------------
# File info
# ---------------------------------------------------------------------------


@router.get(
    "/{file_id}/",
    response_model=GeoFileResponse,
    summary="Get file information",
)
def get_file(file_id: str, db: Session = Depends(get_db)) -> GeoFileResponse:
    geo_file = _get_or_404(file_id, db)
    return GeoFileResponse.model_validate(geo_file)


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------


@router.get(
    "/{file_id}/measurements/",
    response_model=MeasurementsResponse,
    summary="Get feature measurements",
    description=(
        "Returns area (m²) for Polygon features and length (m) for "
        "LineString features.  Unsupported geometry types have `null` values."
    ),
)
def get_measurements(file_id: str, db: Session = Depends(get_db)) -> MeasurementsResponse:
    geo_file = _get_or_404(file_id, db)

    if geo_file.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File is not yet fully processed (status={geo_file.status.value}).",
        )

    features_orm = (
        db.query(Feature)
        .filter(Feature.geo_file_id == file_id)
        .order_by(Feature.feature_index)
        .all()
    )

    feature_responses = [_serialise_feature(f) for f in features_orm]

    return MeasurementsResponse(
        file_id=file_id,
        feature_count=len(feature_responses),
        features=feature_responses,
    )


# ---------------------------------------------------------------------------
# List all files (bonus)
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[GeoFileResponse],
    summary="List all uploaded files",
)
def list_files(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[GeoFileResponse]:
    files = (
        db.query(GeoFile)
        .order_by(GeoFile.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [GeoFileResponse.model_validate(f) for f in files]


# ---------------------------------------------------------------------------
# Delete (bonus)
# ---------------------------------------------------------------------------


@router.delete(
    "/{file_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file record",
)
def delete_file(file_id: str, db: Session = Depends(get_db)) -> None:
    geo_file = _get_or_404(file_id, db)

    # Remove uploaded file from disk if it still exists
    file_path = Path(geo_file.file_path)
    if file_path.exists():
        file_path.unlink()

    db.delete(geo_file)
    db.commit()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_or_404(file_id: str, db: Session) -> GeoFile:
    geo_file: GeoFile | None = db.get(GeoFile, file_id)
    if geo_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No file found with id='{file_id}'.",
        )
    return geo_file


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file has no filename.",
        )
    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{suffix}'. "
                f"Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}."
            ),
        )


def _serialise_feature(orm_feature: Feature) -> FeatureResponse:
    """Deserialise JSON string fields before building the response schema."""
    try:
        geom = json.loads(orm_feature.geometry_geojson)
    except (TypeError, json.JSONDecodeError):
        geom = {}

    try:
        props = json.loads(orm_feature.properties) if orm_feature.properties else {}
    except (TypeError, json.JSONDecodeError):
        props = {}

    return FeatureResponse(
        id=orm_feature.id,
        feature_index=orm_feature.feature_index,
        geometry_type=orm_feature.geometry_type,
        geometry_geojson=geom,
        properties=props,
        crs=orm_feature.crs,
        area_m2=orm_feature.area_m2,
        length_m=orm_feature.length_m,
    )
