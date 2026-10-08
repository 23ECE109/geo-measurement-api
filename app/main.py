"""
Geospatial File Measurement API
Entry point for the FastAPI application.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the SQLite database on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "A REST API that accepts geospatial files (Shapefile / KML), "
        "extracts features, and returns measurement information such as "
        "area (Polygons) and length (LineStrings) in metric units."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["Health"])
def root() -> dict:
    """Health-check endpoint."""
    return {"status": "ok", "service": settings.PROJECT_NAME}
