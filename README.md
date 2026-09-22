# DealerFlow

DealerFlow is a **synthetic automotive import, distribution, VIN-allocation, and operations-planning simulator** built around a Canadian dealer network.

Its purpose is to turn dealer demand into an auditable chain of planning and logistics decisions: dealer replenishment, China-order recommendations, production, VIN creation and allocation, ocean import, Canadian quota pressure, domestic distribution, retail fulfillment, and year-end operational analysis.

The project is inspired by the work described in BYD Canada's public Operations Planning Specialist posting. It does **not** claim access to BYD proprietary data, dealer networks, systems, allocation rules, or logistics contracts.

## Architecture

```text
Scenario YAML
    ↓
Pydantic validation
    ↓
SimPy simulation kernel
    ↓
immutable event log + KPIs
    ↓
Django persistence (SQLite)
    ↓
run browser / replay / analytics
```

The simulation package remains framework-independent. Django orchestrates runs, persists outputs, and presents them.

## Current capabilities

- 365-day Canadian quota-year simulation
- 15 synthetic Canadian dealers, Ontario-heavy
- stochastic demand and configurable disturbances
- dealer replenishment and recurring China-order recommendations
- synthetic VIN creation and inbound allocation
- Ro-Ro / port / rail / truck logistics events
- shared national EV quota pressure
- deterministic independent RNG streams
- persisted simulation runs and event histories
- Django run history and KPI view
- time-scrubbable event replay
- SQLite persistence
- Docker/Compose deployment

## Run with Docker

```bash
docker compose up --build
```

Then open:

```text
http://localhost:8000
```

Press **Run baseline year** to execute and persist the canonical scenario.

SQLite lives in the named `dealerflow_data` Docker volume.

## Run without Docker

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

python manage.py migrate
python manage.py runserver
```

The framework-independent CLI still works:

```bash
dealerflow scenarios/quota_year_baseline.yaml
```

## Cloudflare Tunnel target

The intended public-demo shape is:

```text
Cloudflare Tunnel
      ↓
host :8000
      ↓
Docker / Gunicorn / Django
      ↓
SQLite volume
```

For a public hostname, configure `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, a real `DJANGO_SECRET_KEY`, and disable debug mode.

## Why SQLite?

This is a low-concurrency portfolio application with tens of thousands of rows per simulation run, not an OLTP system. SQLite minimizes operational overhead and is more than adequate at this scale.

The persistence layer remains conventional Django ORM, so PostgreSQL can be introduced later without touching the simulation kernel.

## Documentation

- [Simulation design](docs/SIMULATION_DESIGN.md)
- [BYD Operations Planning Specialist reference](docs/reference/BYD_OPERATIONS_PLANNING_SPECIALIST.md)

## Next

- animated geographic replay
- planning/allocation policy comparison
- scenario editor
- VIN/allocation workbench
- calibrated Canadian EV demand inputs
- reconciliation/error injection
- CSV/Excel outputs
