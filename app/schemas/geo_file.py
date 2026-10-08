"""
Pydantic response / request schemas for GeoFile resources.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class GeoFileResponse(BaseModel):
    """Serialises a GeoFile ORM object for the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    feature_count: int
    crs: str | None
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class FeatureResponse(BaseModel):
    """Serialises a single Feature ORM object."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    feature_index: int
    geometry_type: str
    geometry_geojson: Any  # will be deserialized from JSON string in the endpoint
    properties: Any        # same
    crs: str | None
    area_m2: float | None
    length_m: float | None


class MeasurementsResponse(BaseModel):
    """Wraps a list of feature measurements for a file."""

    file_id: str
    feature_count: int
    features: list[FeatureResponse]
