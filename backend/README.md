# VanaRaksha AI backend

## Existing architecture

The repository is a Python script pipeline with a Flask API, not a FastAPI or
PostGIS application. The implemented flow is:

`FIRMS / GOES calibration -> Stage 4 environmental spread -> local GeoJSON overlay -> Stage 5 FIRMS refinement -> JSON archive -> Flask cycle API -> optional Supabase and email updates`

Stage 4 uses Open-Meteo for weather and Earth Engine Sentinel-2/SRTM layers
when those services are available. Its Earth Engine fallback is synthetic.
The calibration GOES and FIRMS fallback generators are also synthetic. Local
protected-area, settlement, and infrastructure GeoJSON files are available;
there is no ranger GPS, species, historical-fire database, PostGIS schema, or
FastAPI application in this repository.

## Simulation lifecycle

`simulation/simulation_service.py` adds a JSON-backed lifecycle to the existing
Flask server. It combines the cached FIRMS observation when present, local
GeoJSON layers, transparent configurable risk weights, a deterministic spread
estimate, biodiversity/protected-area overlap, and response availability.
Every response labels its provenance in `data_sources`; estimates are not
reported as confirmed field measurements.

Risk is calculated as the weighted sum of normalized contributors:

`temperature, humidity, wind, fuel, slope, historical_fire, rainfall, active_fire`

The result is a `0..100` score classified as `LOW`, `MODERATE`, `HIGH`,
`VERY_HIGH`, or `CRITICAL`. The current repository does not contain values for
historical fire probability, DEM slope, species habitats, or ranger units, so
those contributors are explicit baseline estimates and response units are
returned as an empty list.

## API

Existing routes remain available:

- `POST /api/advance_cycle` with `{"fire_id": "...", "demo_mode": true}`
- `POST /api/update_status` with `{"fire_id": "...", "status": "Contained"}`

New routes:

- `POST /api/simulation/start`
- `POST /api/simulation/<simulation_id>/run`
- `GET /api/simulation/<simulation_id>`
- `GET /api/simulation/<simulation_id>/timeline`
- `GET /api/simulation/<simulation_id>/fire-spread`
- `GET /api/simulation/<simulation_id>/risk-map`
- `GET /api/simulation/<simulation_id>/biodiversity-impact`
- `GET /api/simulation/<simulation_id>/response-plan`
- `GET /api/simulation/<simulation_id>/events` (Server-Sent Events)

The event stream emits this stable envelope:

```json
{
  "event": "simulation.completed",
  "simulation_id": "sim_abc123",
  "status": "COMPLETED",
  "timestamp": "2026-09-27T12:00:00Z",
  "data": {"timeline_points": 9}
}
```

Current event names are `simulation.created`, `simulation.started`, and
`simulation.completed`. The backend has no WebSocket dependency; consumers can
use the SSE endpoint now, and the same envelope can be forwarded through a
WebSocket transport later without changing the API payload.

All simulation errors use an object containing `error`; missing simulations
return HTTP 404 and invalid start input returns HTTP 400. CORS is enabled by
the existing Flask configuration. The backend has no authentication middleware
in this repository, so deployment must place it behind the existing trusted
gateway before exposing simulation controls.

Example request for a two-hour run:

```json
{
  "latitude": 30.1472,
  "longitude": 78.5925,
  "radius": 3,
  "duration_minutes": 120,
  "time_step_minutes": 15,
  "scenario": "high_wind",
  "fire_id": "sample_fire_01"
}
```

Run locally from `backend/simulation` after installing the existing project
dependencies plus Flask and Flask-CORS:

```powershell
python api_server.py
```

Then call the start route, pass its `simulation_id` to `/run`, and read the
timeline and GeoJSON routes. Archives are written under
`simulation/fire_archive`; this directory is runtime output and should not be
used as a database substitute in production.

## Testing

```powershell
python -m unittest discover -s simulation/tests -p "test_*.py"
```

The tests cover coordinate validation, archive persistence, risk contributors,
GeoJSON output, and missing FIRMS data. External service timeouts and Earth
Engine availability remain operational concerns of the existing Stage 4 path.