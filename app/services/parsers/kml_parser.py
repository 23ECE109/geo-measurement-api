"""
KML parser.

KML files always use EPSG:4326 (WGS-84 lon/lat/alt).
We use `fastkml` + `lxml` to parse the XML, then fall back to a lightweight
xml.etree approach for simple single-layer KML files if fastkml is unavailable.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from shapely.geometry import mapping

from app.services.parsers.base import BaseParser, ParsedFeature, ParseResult

logger = logging.getLogger(__name__)

# KML always uses geographic WGS-84
_KML_CRS = "EPSG:4326"

# XML namespace used in KML
_KML_NS = "http://www.opengis.net/kml/2.2"
_KML_NS_22 = "{http://www.opengis.net/kml/2.2}"
_KML_NS_21 = "{http://earth.google.com/kml/2.1}"


class KMLParser(BaseParser):
    """Parse a .kml file and return all Placemark features."""

    def parse(self, file_path: Path) -> ParseResult:
        try:
            return self._parse_with_fastkml(file_path)
        except ImportError:
            logger.info("fastkml not available; using stdlib XML parser.")
        except Exception as exc:
            logger.warning("fastkml failed (%s); falling back to stdlib parser.", exc)

        return self._parse_with_etree(file_path)

    # ------------------------------------------------------------------
    # Strategy 1 – fastkml (preferred, handles complex KML / namespaces)
    # ------------------------------------------------------------------

    def _parse_with_fastkml(self, file_path: Path) -> ParseResult:
        from fastkml import kml  # type: ignore

        k = kml.KML()
        with open(file_path, "rb") as fh:
            k.from_string(fh.read())

        features: list[ParsedFeature] = []
        idx = 0

        def _walk(obj: Any) -> None:
            nonlocal idx
            # fastkml objects expose .features() iterator
            for item in getattr(obj, "features", lambda: [])():
                geom = getattr(item, "geometry", None)
                if geom is not None:
                    geom_dict = mapping(geom)
                    features.append(
                        ParsedFeature(
                            feature_index=idx,
                            geometry_type=geom_dict["type"],
                            geometry_geojson=dict(geom_dict),
                            properties=_kml_placemark_props(item),
                            crs=_KML_CRS,
                        )
                    )
                    idx += 1
                _walk(item)

        _walk(k)
        logger.info("KML '%s': %d features (fastkml)", file_path.name, len(features))
        return ParseResult(features=features, crs=_KML_CRS, file_type="kml")

    # ------------------------------------------------------------------
    # Strategy 2 – stdlib xml.etree (fallback, handles basic KML)
    # ------------------------------------------------------------------

    def _parse_with_etree(self, file_path: Path) -> ParseResult:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Detect namespace prefix
        ns = _KML_NS_22 if _KML_NS_22 in root.tag else _KML_NS_21

        placemarks = root.iter(f"{ns}Placemark")
        features: list[ParsedFeature] = []

        for idx, pm in enumerate(placemarks):
            name_el = pm.find(f"{ns}name")
            name = name_el.text if name_el is not None else f"Feature {idx}"
            desc_el = pm.find(f"{ns}description")
            description = desc_el.text if desc_el is not None else None

            props = {"name": name}
            if description:
                props["description"] = description

            geom_dict = _parse_kml_geometry(pm, ns)
            if geom_dict is None:
                continue

            features.append(
                ParsedFeature(
                    feature_index=idx,
                    geometry_type=geom_dict["type"],
                    geometry_geojson=geom_dict,
                    properties=props,
                    crs=_KML_CRS,
                )
            )

        logger.info("KML '%s': %d features (etree)", file_path.name, len(features))
        return ParseResult(features=features, crs=_KML_CRS, file_type="kml")


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _kml_placemark_props(placemark: Any) -> dict[str, Any]:
    props: dict[str, Any] = {}
    name = getattr(placemark, "name", None)
    if name:
        props["name"] = name
    description = getattr(placemark, "description", None)
    if description:
        props["description"] = description
    return props


def _parse_coords(coord_text: str) -> list[list[float]]:
    """Parse a KML <coordinates> text node into a list of [lon, lat] pairs."""
    coords = []
    for token in coord_text.strip().split():
        parts = token.split(",")
        if len(parts) >= 2:
            try:
                lon, lat = float(parts[0]), float(parts[1])
                coords.append([lon, lat])
            except ValueError:
                continue
    return coords


def _parse_kml_geometry(placemark: ET.Element, ns: str) -> dict[str, Any] | None:
    """
    Extract the first recognised geometry element from a Placemark element
    and return it as a GeoJSON geometry dict.
    """

    # Point
    point_el = placemark.find(f".//{ns}Point/{ns}coordinates")
    if point_el is not None and point_el.text:
        coords = _parse_coords(point_el.text)
        if coords:
            return {"type": "Point", "coordinates": coords[0]}

    # LineString
    ls_el = placemark.find(f".//{ns}LineString/{ns}coordinates")
    if ls_el is not None and ls_el.text:
        return {"type": "LineString", "coordinates": _parse_coords(ls_el.text)}

    # Polygon (outer ring only for simplicity; holes not yet supported)
    poly_el = placemark.find(f".//{ns}Polygon")
    if poly_el is not None:
        outer = poly_el.find(
            f".//{ns}outerBoundaryIs/{ns}LinearRing/{ns}coordinates"
        )
        rings = []
        if outer is not None and outer.text:
            rings.append(_parse_coords(outer.text))

        # Inner (hole) rings
        for inner in poly_el.findall(
            f".//{ns}innerBoundaryIs/{ns}LinearRing/{ns}coordinates"
        ):
            if inner.text:
                rings.append(_parse_coords(inner.text))

        if rings:
            return {"type": "Polygon", "coordinates": rings}

    return None
