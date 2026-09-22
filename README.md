# DealerFlow

DealerFlow is a **synthetic automotive import, distribution, VIN-allocation, and operations-planning simulator** built around a Canadian dealer network.

It turns dealer demand into an auditable chain of planning and logistics decisions: dealer replenishment, China-order recommendations, production, VIN creation and allocation, ocean import, Canadian quota pressure, domestic distribution, retail fulfillment, and year-end analysis.

The project is inspired by the work described in BYD Canada's public Operations Planning Specialist posting. It does **not** claim access to BYD proprietary data, dealer networks, systems, allocation rules, or logistics contracts.

## Architecture

```text
Scenario YAML
    ↓
Pydantic validation
    ↓
SimPy simulation kernel
    ↓
event log + KPI summary
    ↓
Django + SQLite
    ↓
animated replay + run analytics
```

The browser replay watches a completed simulation; it does not drive the simulation itself. That keeps runs deterministic and makes policy A/B comparisons possible using the same stochastic world.

## Current capabilities

- 365-day Canadian quota-year scenario
- 15 synthetic Canadian dealers, weighted toward Ontario
- synthetic factory, port, compound, and dealer geography
- stochastic retail demand and configurable disturbances
- dealer replenishment and recurring China-order recommendations
- individual synthetic VIN creation and inbound allocation
- warm-start inventory and already-in-transit supply
- Ro-Ro, port, rail, and truck logistics events
- shared Canadian China-origin EV quota pressure
- deterministic named RNG streams
- Django persistence for scenarios, runs, events, and KPI summaries
- animated Leaflet replay with timeline, playback speed, dealer backlog pressure, quota usage, and aggregated shipment movement
- SQLite by default
- Docker Compose deployment

## Run with Docker

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000
```

Press **Run baseline year**. The run executes synchronously for now, persists its event log to SQLite, and opens the replay page when complete.

The database lives in the `dealerflow_data` Docker volume.

## Run without Docker

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

python manage.py migrate
python manage.py runserver
```

Persist a scenario directly:

```bash
python manage.py run_scenario scenarios/quota_year_baseline.yaml
```

The framework-independent simulator CLI remains available:

```bash
dealerflow scenarios/quota_year_baseline.yaml
dealerflow scenarios/quota_year_baseline.yaml --events outputs/baseline.jsonl
```

## Cloudflare Tunnel

DealerFlow is local-first. A Cloudflare Tunnel can point at the host's exposed port `8000`; Cloudflare does not need to run inside the Compose stack.

For a public hostname set:

```text
DJANGO_ALLOWED_HOSTS=dealerflow.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://dealerflow.example.com
DJANGO_SECRET_KEY=<a real secret>
DJANGO_DEBUG=0
```

See `.env.example` for the expected variables.

## Why SQLite?

The expected workload is small: one portfolio user, a handful of simulation runs, and tens of thousands of event rows per run. SQLite removes unnecessary operational overhead while remaining more than adequate for the current workload.

The Django persistence layer is conventional, so moving to PostgreSQL later would not require changing the simulation kernel or replay API.

## Scenario design

Human-authored scenarios use YAML and Pydantic remains the canonical schema.

Facilities and dealers carry their own coordinates. The replay layer therefore has no hidden geography assumptions, and future Halifax/multi-gateway scenarios can change routing without frontend rewrites.

The baseline currently includes:

- an Ontario demand spike
- an 11-day delay to the third simulated ocean shipment

## Why individual VINs?

Planning begins in quantities; allocation eventually becomes physical.

DealerFlow creates individual vehicles when production completes and can allocate a specific inbound VIN to a dealer while that vehicle is still in the logistics pipeline. Physical state and allocation state are separate, so a VIN can simultaneously be `OCEAN` and `ALLOCATED`.

## Documentation

- [Simulation design](docs/SIMULATION_DESIGN.md)
- [BYD Operations Planning Specialist reference](docs/reference/BYD_OPERATIONS_PLANNING_SPECIALIST.md)

## Next

- planning/allocation policy comparison
- scenario editor
- richer inventory and VIN workbench
- Halifax / multi-gateway routing
- calibrated Canadian EV demand inputs
- reconciliation/error injection
- Excel/CSV outputs
