# DealerFlow

DealerFlow is a **synthetic automotive import, distribution, VIN-allocation, and operations-planning simulator** built around a Canadian dealer network.

Its purpose is to turn dealer demand into an auditable chain of planning and logistics decisions: dealer replenishment, China-order recommendations, production, VIN creation and allocation, ocean import, Canadian quota pressure, domestic distribution, retail fulfillment, and year-end operational analysis.

The project is inspired by the work described in BYD Canada's public Operations Planning Specialist posting. It does **not** claim access to BYD proprietary data, dealer networks, systems, allocation rules, or logistics contracts.

## Current milestone

The first milestone is the simulation kernel, not the web UI.

A scenario is defined in YAML, validated with Pydantic, executed as a deterministic discrete-event simulation with SimPy, and emitted as an immutable event log. The future animated map will replay that completed event stream rather than drive the simulation itself.

```text
Scenario YAML
    |
    v
Pydantic validation
    |
    v
SimPy simulation kernel
    |
    +--> Event log
    +--> KPI summary
    |
    +--> Animated map replay   (next)
    +--> Planning analytics    (next)
```

## Implemented in the kernel

- 365-day Canadian quota-year scenario
- 15 synthetic Canadian dealers, weighted toward Ontario
- synthetic model / trim / colour configurations
- deterministic independent random streams
- stochastic retail demand
- configurable demand and logistics disturbances
- dealer replenishment orders
- recurring China-order recommendations
- production lead times
- individual 17-character synthetic VIN creation
- inbound VIN allocation to dealer demand
- warm-start inventory and an already-at-sea shipment
- Ro-Ro shipment events into Vancouver
- port dwell, rail, and final truck delivery stages
- national China-origin EV quota consumption, including stochastic external use
- immutable event history and reproducibility digest
- end-of-run service, inventory, quota, and backlog summary

## Quick start

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'

dealerflow scenarios/quota_year_baseline.yaml
dealerflow scenarios/quota_year_baseline.yaml --events outputs/baseline.jsonl

pytest
```

The CLI prints an event-log digest. Two runs of the same scenario and seed should produce the same digest, which is important for fair policy comparisons.

## Scenario design

Human-authored scenarios use YAML. Pydantic models are the canonical schema, which will later let a GUI scenario editor target the same underlying definition.

The baseline scenario includes two example disturbances:

- an Ontario demand spike during the summer
- an 11-day delay to the third simulated ocean shipment

Disturbances are scenario data, not hard-coded special cases.

## Why individual VINs?

Demand planning begins in quantities, but allocation eventually becomes physical. DealerFlow creates individual vehicles once production completes and can allocate a specific inbound VIN to a dealer while that vehicle is still moving through the logistics pipeline.

Physical state and allocation state are deliberately separate. A VIN can be simultaneously `OCEAN` and `ALLOCATED`.

## Documentation

- [Simulation design](docs/SIMULATION_DESIGN.md)
- [BYD Operations Planning Specialist reference](docs/reference/BYD_OPERATIONS_PLANNING_SPECIALIST.md)

## Next

The next milestone is the replay/analytics layer: persisted run outputs, a Canada map with time controls, shipment inspection, dealer inventory/backlog pressure, and scenario/policy comparison.
