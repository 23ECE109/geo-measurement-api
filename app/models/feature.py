"""
ORM model representing a single geographic feature extracted from a file.
"""

from sqlalchemy import String, Integer, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    geo_file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("geo_files.id"), nullable=False, index=True
    )
    feature_index: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry_type: Mapped[str] = mapped_column(String(64), nullable=False)

    # GeoJSON representation of the geometry (original CRS)
    geometry_geojson: Mapped[str] = mapped_column(Text, nullable=False)

    # Properties / attributes stored as a JSON string
    properties: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Measurement results (None when not applicable)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    length_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # CRS of the source geometry (e.g. "EPSG:4326")
    crs: Mapped[str | None] = mapped_column(String(64), nullable=True)

    geo_file: Mapped["GeoFile"] = relationship(  # noqa: F821
        "GeoFile", back_populates="features"
    )
