"""
Measurement service.

Calculates area (Polygon / MultiPolygon) and length
(LineString / MultiLineString) in metric units after reprojecting the
geometry to an appropriate projected CRS.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from shapely.geometry import shape, mapping
from shapely.geometry.base import BaseGeometry

from app.services.crs_utils import get_projected_geometry

logger = logging.getLogger(__name__)

# Geometry types that support area calculation
_AREA_TYPES = {"Polygon", "MultiPolygon"}

# Geometry types that support length calculation
_LENGTH_TYPES = {"LineString", "MultiLineString", "LinearRing"}

# Geometry types explicitly supported for measurement (others are handled
# gracefully – no measurement, no error)
_SUPPORTED_TYPES = _AREA_TYPES | _LENGTH_TYPES | {"Point", "MultiPoint", "GeometryCollection"}


def calculate_measurements(
    geom_geojson: dict[str, Any],
    src_crs: str,
) -> dict[str, float | None]:
    """
    Calculate area and/or length for a single feature geometry.

    Parameters
    ----------
    geom_geojson:
        A GeoJSON-like geometry dict (``{"type": ..., "coordinates": ...}``).
    src_crs:
        The CRS of the input geometry (e.g. ``"EPSG:4326"``).

    Returns
    -------
    dict with keys:
        ``area_m2``  – area in square metres (or ``None``)
        ``length_m`` – length in metres (or ``None``)
    """
    result: dict[str, float | None] = {"area_m2": None, "length_m": None}

    geom_type = geom_geojson.get("type", "")

    if geom_type not in _SUPPORTED_TYPES:
        logger.info("Geometry type '%s' is not supported for measurement; skipping.", geom_type)
        return result

    try:
        geom: BaseGeometry = shape(geom_geojson)
    except Exception as exc:
        logger.warning("Failed to parse geometry: %s", exc)
        return result

    if geom.is_empty:
        return result

    try:
        projected_geom, _ = get_projected_geometry(geom, src_crs)
    except Exception as exc:
        logger.warning("Reprojection failed: %s", exc)
        return result

    if geom_type in _AREA_TYPES:
        result["area_m2"] = round(projected_geom.area, 4)

    if geom_type in _LENGTH_TYPES:
        result["length_m"] = round(projected_geom.length, 4)

    return result
