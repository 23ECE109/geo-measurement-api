# Geospatial File Measurement API

A FastAPI backend service that accepts geospatial files (Shapefile or KML), extracts their features, and returns measurement information — area for Polygons, length for LineStrings — all in metric units regardless of the source coordinate reference system.

---

## Table of Contents

- [Setup](#setup)
- [API Documentation](#api-documentation)
- [Architecture](#architecture)
- [CRS Handling](#crs-handling)
- [Design Decisions](#design-decisions)
- [Learnings & Future Scope](#learnings--future-scope)

---

## Setup

### Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11 |
| pip | 23+ |

> **Windows users:** The geospatial libraries (`fiona`, `pyproj`, `shapely`) require GDAL. The easiest path is to install via [conda](https://docs.conda.io/) or use the prebuilt wheels from [Christoph Gohlke's repository](https://www.lfd.uci.edu/~gohlke/pythonlibs/).

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/geo-measurement-api.git
cd geo-measurement-api
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env to change DATABASE_URL, UPLOAD_DIR, etc.
```

The application ships with sensible defaults — SQLite database and an `uploads/` folder — so this step is optional for local development.

### 5. Run the development server

```bash
uvicorn app.main:app --reload
```

The API is now available at **http://127.0.0.1:8000**.  
Interactive docs: **http://127.0.0.1:8000/docs** (Swagger UI) or **/redoc**.

### 6. Run tests

```bash
pytest
# With coverage report:
pytest --cov=app --cov-report=term-missing
```

---

## API Documentation

### Base URL

```
http://localhost:8000/api
```

---

### `POST /api/files/`

Upload and process a geospatial file.

**Accepted formats**

| Type | Extension |
|---|---|
| Shapefile (zipped) | `.zip` (must contain `.shp`, `.dbf`, `.shx`) |
| KML | `.kml` |

**Request**

```
Content-Type: multipart/form-data

file: <binary>
```

**Example (curl)**

```bash
# KML
curl -X POST http://localhost:8000/api/files/ \
  -F "file=@/path/to/survey.kml"

# Shapefile
curl -X POST http://localhost:8000/api/files/ \
  -F "file=@/path/to/shapefile.zip"
```

**Response `201 Created`**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "survey.kml",
  "file_type": "kml",
  "feature_count": 120,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:01Z"
}
```

**Status values**

| Value | Meaning |
|---|---|
| `PENDING` | File received, not yet processed |
| `PROCESSING` | Feature extraction in progress |
| `COMPLETED` | Processing finished successfully |
| `FAILED` | An error occurred; see `error_message` |

---

### `GET /api/files/{id}/`

Retrieve metadata for a previously uploaded file.

**Example**

```bash
curl http://localhost:8000/api/files/3fa85f64-5717-4562-b3fc-2c963f66afa6/
```

**Response `200 OK`**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "survey.kml",
  "file_type": "kml",
  "feature_count": 120,
  "crs": "EPSG:4326",
  "status": "COMPLETED",
  "error_message": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:01Z"
}
```

---

### `GET /api/files/{id}/measurements/`

Retrieve per-feature measurements for an uploaded file.

**Example**

```bash
curl http://localhost:8000/api/files/3fa85f64-5717-4562-b3fc-2c963f66afa6/measurements/
```

**Response `200 OK`**

```json
{
  "file_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "feature_count": 3,
  "features": [
    {
      "id": 1,
      "feature_index": 0,
      "geometry_type": "Point",
      "geometry_geojson": { "type": "Point", "coordinates": [13.405, 52.52] },
      "properties": { "name": "City Centre" },
      "crs": "EPSG:4326",
      "area_m2": null,
      "length_m": null
    },
    {
      "id": 2,
      "feature_index": 1,
      "geometry_type": "LineString",
      "geometry_geojson": {
        "type": "LineString",
        "coordinates": [[13.405, 52.52], [13.415, 52.53]]
      },
      "properties": { "name": "Road" },
      "crs": "EPSG:4326",
      "area_m2": null,
      "length_m": 1285.34
    },
    {
      "id": 3,
      "feature_index": 2,
      "geometry_type": "Polygon",
      "geometry_geojson": {
        "type": "Polygon",
        "coordinates": [[[13.40, 52.50], [13.41, 52.50], [13.41, 52.51], [13.40, 52.51], [13.40, 52.50]]]
      },
      "properties": { "name": "Park" },
      "crs": "EPSG:4326",
      "area_m2": 617382.11,
      "length_m": null
    }
  ]
}
```

**Measurement rules**

| Geometry type | `area_m2` | `length_m` |
|---|---|---|
| `Point` / `MultiPoint` | `null` | `null` |
| `LineString` / `MultiLineString` | `null` | ✓ metres |
| `Polygon` / `MultiPolygon` | ✓ m² | `null` |
| Other (unsupported) | `null` | `null` |

---

### `GET /api/files/`

List all uploaded files (paginated).

**Query parameters**

| Parameter | Default | Description |
|---|---|---|
| `skip` | `0` | Number of records to skip |
| `limit` | `50` | Max records to return |

---

### `DELETE /api/files/{id}/`

Delete a file record, its associated features, and the file from disk.

**Response `204 No Content`**

---

### Error responses

| HTTP Code | When |
|---|---|
| `400` | Missing filename |
| `404` | File ID not found |
| `409` | Measurements requested but file not `COMPLETED` |
| `415` | Unsupported file extension |
| `422` | Request validation error |

---

## Architecture

### Application structure

```
geo-measurement-api/
├── app/
│   ├── main.py               # FastAPI app factory, middleware, startup
│   ├── core/
│   │   └── config.py         # Pydantic Settings (reads .env)
│   ├── db/
│   │   ├── base.py           # SQLAlchemy DeclarativeBase + model imports
│   │   └── session.py        # Engine, SessionLocal, get_db dependency
│   ├── models/
│   │   ├── geo_file.py       # GeoFile ORM (one row per uploaded file)
│   │   └── feature.py        # Feature ORM (one row per geographic feature)
│   ├── schemas/
│   │   └── geo_file.py       # Pydantic response schemas
│   ├── services/
│   │   ├── crs_utils.py      # UTM zone selection, reprojection helpers
│   │   ├── measurement.py    # Area / length calculation
│   │   ├── file_processor.py # Orchestrator: parse → measure → persist
│   │   └── parsers/
│   │       ├── base.py           # Abstract BaseParser, ParsedFeature, ParseResult
│   │       ├── shapefile_parser.py
│   │       └── kml_parser.py
│   └── api/
│       ├── router.py         # Mounts sub-routers
│       └── endpoints/
│           └── files.py      # /api/files/* route handlers
├── tests/
│   ├── conftest.py           # Fixtures: TestClient, in-memory DB, sample files
│   ├── test_api.py           # End-to-end endpoint tests
│   ├── test_parsers.py       # Unit tests for parsers
│   ├── test_measurement.py   # Unit tests for measurement service
│   └── test_crs_utils.py     # Unit tests for CRS utilities
├── requirements.txt
├── pyproject.toml
└── README.md
```

### File-processing flow

```
POST /api/files/
        │
        ▼
   Validate extension (.zip | .kml)
        │
        ▼
   Save file to UPLOAD_DIR with UUID filename
        │
        ▼
   Create GeoFile record (status=PENDING) in DB
        │
        ▼
   process_geo_file()
     ├─ Set status=PROCESSING
     ├─ Select parser (ShapefileParser | KMLParser)
     ├─ parser.parse(file_path) → ParseResult
     │     └─ Yields: list[ParsedFeature], crs, file_type
     ├─ For each ParsedFeature:
     │     ├─ calculate_measurements(geom, src_crs)
     │     └─ INSERT Feature row into DB
     ├─ Update GeoFile: crs, feature_count, status=COMPLETED
     └─ On error: status=FAILED, error_message saved
```

### Measurement calculation flow

```
calculate_measurements(geom_geojson, src_crs)
        │
        ▼
   Identify geometry type
        │
        ├── Unsupported type → return {area_m2: null, length_m: null}
        │
        ▼
   Deserialise GeoJSON → Shapely geometry
        │
        ▼
   get_projected_geometry(geom, src_crs)
     ├─ Is CRS geographic?
     │   ├─ No  → return as-is (already metric)
     │   └─ Yes → normalise to EPSG:4326, then reproject to UTM zone
        │
        ▼
   Apply Shapely .area or .length on the projected geometry
        │
        ▼
   Return rounded float (metres / m²)
```

---

## CRS Handling

**Problem:** Geographic CRS coordinates (latitude/longitude in degrees) cannot be used directly to compute meaningful areas or lengths because a degree of longitude varies in physical length depending on latitude.

**Strategy — dynamic UTM zone selection:**

1. Accept the file's declared CRS (e.g. `EPSG:4326`).
2. If already a projected (metric) CRS — skip reprojection.
3. Otherwise normalise to `EPSG:4326` lon/lat, then compute the UTM zone number that contains the geometry centroid:

   ```
   zone = floor((longitude + 180) / 6) + 1
   EPSG = 32600 + zone          (Northern Hemisphere)
   EPSG = 32700 + zone          (Southern Hemisphere)
   ```

4. Reproject the geometry using `pyproj.Transformer` before calling Shapely's `.area` / `.length`.

**Why UTM?**
- UTM is a globally applicable family of projections with metre-based units.
- Each 6° zone introduces ≤ 0.04% distortion, giving accurate results for most practical datasets.
- It's the de-facto standard for local/regional metric measurements.

**Fallback:** If CRS parsing fails entirely, the service falls back to `EPSG:3857` (Web Mercator) and logs a warning. Web Mercator is less accurate for area near the poles but always works as a last resort.

---

## Design Decisions

### FastAPI over Django REST Framework

FastAPI was chosen because:
- Native async support (ready for background task workers).
- Auto-generated OpenAPI docs via `/docs` with no extra configuration.
- Pydantic v2 validation is built-in, reducing boilerplate.
- Lighter footprint for a single-purpose microservice.

Django DRF was considered and would be the better choice if the service needed to grow into a full product with an admin panel, ORM migrations (Alembic is used here instead), or a richer permission system.

### Synchronous processing (vs. Celery / background tasks)

File processing currently happens **synchronously** inside the request handler. This is acceptable for the scope of this assessment and keeps the setup simple (no broker required).

For production, the natural evolution is:
1. Accept the upload, return `202 Accepted` with the file ID.
2. Dispatch processing to a Celery worker (Redis/RabbitMQ broker).
3. Poll `GET /api/files/{id}/` until `status == "COMPLETED"`.

FastAPI's `BackgroundTasks` could be a lighter intermediate step that avoids a full Celery deployment.

### SQLite → PostgreSQL migration path

SQLite is used as the default to keep local setup dependency-free. Switching to PostgreSQL requires only a one-line change to `DATABASE_URL` in `.env`. For spatial queries at scale, [PostGIS](https://postgis.net/) would be a natural next step.

### Geometry stored as GeoJSON strings

Geometry is stored as a JSON string in SQLite for portability. With PostGIS the column type would be `GEOMETRY` and queries like bounding-box intersections would be trivially fast.

### Parser strategy pattern

Each file type gets its own parser class that inherits from `BaseParser`. Adding a new format (e.g. GeoJSON, GML) requires only implementing `parse()` and registering the extension in `_select_parser()`.

### KML dual-strategy parsing

The KML parser tries `fastkml` first (handles complex namespaces, nested folders, styles) and falls back to `xml.etree.ElementTree` (stdlib, zero dependencies). This makes the application deployable even in restricted environments.

---

## Learnings & Future Scope

### Learnings

- **UTM zone edge cases:** The UTM system has special zone exceptions around Norway and Svalbard that must be implemented explicitly — easily missed.
- **Fiona CRS representation:** Fiona can return CRS as a dict, WKT string, or EPSG code depending on the GDAL version. Using `pyproj.CRS.from_user_input()` as a normaliser handles all forms cleanly.
- **fastkml API instability:** The fastkml library's public API has changed across versions. Wrapping it in a try/except with a stdlib fallback proved essential for reliability.

### Future Scope

| Area | Enhancement |
|---|---|
| **Async processing** | Move file processing to Celery workers; return `202 Accepted` and allow status polling |
| **Additional formats** | GeoJSON, GML, FlatGeobuf, GeoPackage (GPKG) |
| **Spatial queries** | Migrate to PostGIS; add bounding-box filter on `/measurements/` |
| **Streaming upload** | Chunked upload for very large files (> 500 MB) |
| **Multi-layer Shapefiles** | Currently uses first `.shp` found in ZIP; extend to return all layers |
| **Projection choice API** | Let the caller specify the target CRS via a query parameter |
| **Authentication** | API key / JWT middleware for multi-tenant deployments |
| **Caching** | Cache measurement results in Redis to avoid recomputation on repeated GETs |
| **Rate limiting** | Throttle upload endpoint per IP to prevent abuse |
| **Docker** | `Dockerfile` + `docker-compose.yml` for one-command deployment |
| **CI/CD** | GitHub Actions workflow: lint → test → build → deploy |
