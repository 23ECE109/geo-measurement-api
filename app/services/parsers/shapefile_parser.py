"""
Shapefile parser.

Accepts a .zip archive containing at minimum a .shp, .dbf, and .shx file.
Uses Fiona to open the shapefile and extract features + CRS.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import zipfile
from pathlib import Path

import fiona
import pyproj

from app.services.parsers.base import BaseParser, ParsedFeature, ParseResult

logger = logging.getLogger(__name__)


class ShapefileParser(BaseParser):
    """Parse a zipped Shapefile and return all features."""

    def parse(self, file_path: Path) -> ParseResult:
        if not zipfile.is_zipfile(file_path):
            raise ValueError(f"Expected a ZIP archive, got: {file_path.name}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(tmp_dir)

            shp_files = list(Path(tmp_dir).rglob("*.shp"))
            if not shp_files:
                raise ValueError("No .shp file found inside the ZIP archive.")

            # If multiple .shp files exist, use the first one and warn
            if len(shp_files) > 1:
                logger.warning(
                    "Multiple .shp files found; using '%s'.", shp_files[0].name
                )
            shp_path = shp_files[0]

            return self._read_shapefile(shp_path)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_crs(raw_crs) -> str:
        """
        Convert whatever Fiona gives us (dict / WKT / EPSG string) to a
        canonical EPSG or proj string.
        """
        if raw_crs is None:
            return "EPSG:4326"

        try:
            crs_obj = pyproj.CRS.from_user_input(raw_crs)
            epsg = crs_obj.to_epsg()
            if epsg:
                return f"EPSG:{epsg}"
            # Fall back to PROJJSON / WKT representation
            return crs_obj.to_string()
        except Exception:
            return str(raw_crs)

    def _read_shapefile(self, shp_path: Path) -> ParseResult:
        with fiona.open(str(shp_path)) as src:
            raw_crs = src.crs
            crs = self._normalise_crs(raw_crs)

            features: list[ParsedFeature] = []
            for idx, fiona_feature in enumerate(src):
                geom = fiona_feature.get("geometry")
                if geom is None:
                    logger.debug("Feature %d has no geometry; skipping.", idx)
                    continue

                # Fiona geometry objects are already dict-like
                geom_dict = dict(geom)
                geom_type = geom_dict.get("type", "Unknown")
                props = dict(fiona_feature.get("properties") or {})

                features.append(
                    ParsedFeature(
                        feature_index=idx,
                        geometry_type=geom_type,
                        geometry_geojson=geom_dict,
                        properties=props,
                        crs=crs,
                    )
                )

        logger.info(
            "Shapefile '%s': %d features, CRS=%s", shp_path.name, len(features), crs
        )
        return ParseResult(features=features, crs=crs, file_type="shapefile")
