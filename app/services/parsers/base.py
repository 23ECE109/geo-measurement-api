"""
Abstract base class for geospatial file parsers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedFeature:
    """Represents a single parsed geographic feature."""

    feature_index: int
    geometry_type: str
    geometry_geojson: dict[str, Any]  # GeoJSON geometry dict
    properties: dict[str, Any] = field(default_factory=dict)
    crs: str = "EPSG:4326"  # CRS of the coordinates in geometry_geojson


@dataclass
class ParseResult:
    """Result returned by a parser."""

    features: list[ParsedFeature]
    crs: str  # CRS string for the whole file (e.g. "EPSG:4326")
    file_type: str  # "shapefile" | "kml"


class BaseParser(ABC):
    """
    All parsers must implement :meth:`parse`.

    They receive the path to the uploaded file (zip for Shapefile, .kml for KML)
    and return a :class:`ParseResult`.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:  # pragma: no cover
        ...
