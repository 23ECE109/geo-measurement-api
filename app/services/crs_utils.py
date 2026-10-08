"""
CRS utility helpers.

Strategy for choosing a projected CRS:
  - For global / large-extent datasets we use the Universal Transverse Mercator
    (UTM) zone that contains the centroid of the geometry bounding box.
  - UTM gives metre-based measurements and is accurate within each 6° zone.
  - As a fallback (when the CRS is unknown or non-geographic) we reproject
    using EPSG:3857 (Web Mercator).  This is less accurate for area but always
    works as a last resort.

This approach avoids hard-coding a single CRS while still producing reliable
metric measurements for any input file.
"""

from __future__ import annotations

import math
import logging

import pyproj
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform

logger = logging.getLogger(__name__)


def utm_epsg_for_geometry(geom: BaseGeometry) -> str:
    """
    Return the EPSG code of the UTM zone that best covers *geom*.

    Parameters
    ----------
    geom:
        A Shapely geometry in EPSG:4326 (lon/lat) coordinates.

    Returns
    -------
    str
        An EPSG code string, e.g. ``"EPSG:32633"``.
    """
    centroid = geom.centroid
    lon, lat = centroid.x, centroid.y

    # Clamp to valid ranges just in case
    lon = max(-180.0, min(180.0, lon))
    lat = max(-80.0, min(84.0, lat))

    zone_number = math.floor((lon + 180) / 6) + 1

    # Special zones around Norway / Svalbard (EPSG spec)
    if 56.0 <= lat < 64.0 and 3.0 <= lon < 12.0:
        zone_number = 32
    if 72.0 <= lat < 84.0:
        if 0.0 <= lon < 9.0:
            zone_number = 31
        elif 9.0 <= lon < 21.0:
            zone_number = 33
        elif 21.0 <= lon < 33.0:
            zone_number = 35
        elif 33.0 <= lon < 42.0:
            zone_number = 37

    # Northern hemisphere: EPSG 326xx  (32600 + zone)
    # Southern hemisphere: EPSG 327xx  (32700 + zone)
    hemisphere_code = 700 if lat < 0 else 600
    epsg = 32000 + hemisphere_code + zone_number
    return f"EPSG:{epsg}"


def reproject_geometry(
    geom: BaseGeometry,
    src_crs: str,
    dst_crs: str,
) -> BaseGeometry:
    """
    Reproject *geom* from *src_crs* to *dst_crs*.

    Parameters
    ----------
    geom:
        Shapely geometry in *src_crs* coordinates.
    src_crs:
        Source CRS string (e.g. ``"EPSG:4326"``).
    dst_crs:
        Target CRS string (e.g. ``"EPSG:32633"``).

    Returns
    -------
    BaseGeometry
        The reprojected geometry.
    """
    transformer = pyproj.Transformer.from_crs(
        src_crs, dst_crs, always_xy=True
    )
    return transform(transformer.transform, geom)


def get_projected_geometry(geom: BaseGeometry, src_crs: str) -> tuple[BaseGeometry, str]:
    """
    Return *(projected_geom, projected_crs)*.

    If *src_crs* is already a projected (metric) CRS the geometry is returned
    unchanged.  Otherwise it is first normalised to EPSG:4326, then reprojected
    to the appropriate UTM zone.
    """
    try:
        crs_obj = pyproj.CRS.from_user_input(src_crs)
    except Exception:
        logger.warning("Unrecognised CRS '%s'; falling back to EPSG:3857.", src_crs)
        return reproject_geometry(geom, "EPSG:4326", "EPSG:3857"), "EPSG:3857"

    if not crs_obj.is_geographic:
        # Already projected – assume metres, return as-is
        return geom, src_crs

    # Normalise to EPSG:4326 lon/lat if needed
    if crs_obj.to_epsg() != 4326:
        geom_4326 = reproject_geometry(geom, src_crs, "EPSG:4326")
    else:
        geom_4326 = geom

    target_crs = utm_epsg_for_geometry(geom_4326)
    projected = reproject_geometry(geom_4326, "EPSG:4326", target_crs)
    return projected, target_crs
