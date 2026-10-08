"""
Base declarative class.  Import all models here so that
Base.metadata.create_all() picks them up in one shot.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Side-effect imports – keep them here so init_db() sees every table
from app.models.geo_file import GeoFile  # noqa: E402, F401
from app.models.feature import Feature  # noqa: E402, F401
