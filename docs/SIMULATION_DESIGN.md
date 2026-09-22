# DealerFlow Simulation Design

## Status

Initial design specification for the DealerFlow simulation kernel and replay/analytics architecture.

DealerFlow is a **synthetic automotive import, distribution, allocation, and supply-planning simulator** inspired by the responsibilities in BYD Canada's public Operations Planning Specialist posting.

It does **not** claim to reproduce BYD's proprietary systems, network, allocation rules, dealer network, or logistics contracts.

---

## 1. Scope Decision: National Network, Ontario-Heavy

DealerFlow should model a small **national Canadian dealer network**, rather than Ontario only.

Why:

- The role is for BYD Canada, not an Ontario-only organization.
- A national network makes import-gateway and domestic-distribution decisions meaningful.
- Vancouver versus Halifax becomes an actual planning variable.
- Rail and truck distribution become visible rather than decorative.
- Regional demand differences become useful inputs to allocation.
- Ontario can still contain the largest share of synthetic dealers, keeping the project focused on the market most relevant to the Toronto role.

Suggested initial network: roughly 15 synthetic dealers in major Canadian markets, with heavier representation in Ontario and Quebec.

Example markets:

- Vancouver
- Victoria
- Calgary
- Edmonton
- Saskatoon
- Winnipeg
- Toronto / GTA (multiple synthetic dealers)
- Hamilton
- London
- Ottawa
- Montreal (multiple synthetic dealers)
- Quebec City
- Halifax

These should be explicitly synthetic locations, not claimed real BYD dealerships.

---

## 2. Simulation Horizon

### Default measured horizon

Use **one Canadian EV quota year**:

- Start: March 1
- End: February 28/29

For the first grounded scenario, March 1, 2026 through February 28, 2027 is convenient because Canada's first China-origin EV quota year is 49,000 vehicles.

### Why one year is enough

A realistic factory-order-to-Canadian-dealer lead time is on the order of months, not a year. A one-year simulation therefore contains multiple replenishment/planning cycles, enough to expose:

- forecast error
- inventory oscillation
- shipment timing
- quota pressure
- dealer shortages
- configuration imbalances
- aging inventory
- disruptions

A two-year horizon should remain available as a scenario option, but should not be the default.

### Initialization / warm start

The measured year should **not** begin from an empty network.

Each scenario should provide or generate:

- 6–12 months of pre-simulation retail history
- starting dealer inventory
- national/compound inventory
- existing dealer backlog
- existing China orders
- vehicles already in production
- vehicles already on the ocean
- vehicles already in Canadian transport
- initial forecast state

This avoids a long artificial warm-up period while still letting the visible replay begin cleanly on Day 1.

---

## 3. Grounded Canadian Import Constraint

Canada currently applies a country-specific quota to eligible EVs originating in China.

For quota year 1:

- Total quota: 49,000 vehicles
- Quota year: March 1, 2026 to February 28, 2027
- MFN tariff inside quota: 6.1%
- Administration is currently first-come, first-served
- Shipment-specific permits are required
- Permit applications may be made up to 30 days before expected Canadian entry
- Permit validity is up to 60 days

Critically, **49,000 is not a BYD-specific quota**. It is a national quota shared across eligible China-origin EV imports.

Therefore DealerFlow should model a national quota environment:

```
CanadianEVQuota
    total_units
    used_by_dealerflow_oem
    used_by_external_importers
    remaining_units
```

External quota consumption should be an exogenous stochastic process or supplied time series.

This creates an excellent operations-planning constraint:

> A China order can be commercially desirable and physically available but still create import risk if quota availability is deteriorating before expected Canadian arrival.

### Real-world grounding sources

- Global Affairs Canada EV quota overview:
  https://www.international.gc.ca/trade-commerce/controls-controles/electric-vehicle-vehicule-electrique/index.aspx?lang=eng
- Notice to Importers No. 1168:
  https://www.international.gc.ca/trade-commerce/controls-controles/notices-avis/1168.aspx?lang=eng
- Public quota utilization:
  https://www.eics-scei.gc.ca/report-rapport/Imports_of_electric_vehicles_from_China.htm

The simulator should keep quota policy configurable so it remains useful if the real administration regime changes.

---

## 4. Real-World Demand Scaffolding

Canadian EV demand does not need to be invented from nothing.

Useful public calibration sources include:

- Statistics Canada monthly new motor vehicle sales by province, fuel type, vehicle type, and origin of manufacture:
  Table 20-10-0085-01
- Statistics Canada quarterly new ZEV registrations by geographic level:
  Table 20-10-0025-01
- Statistics Canada ZEV interactive map, including CMA/CSD geography
- Government of Canada China-EV quota utilization

DealerFlow should use these as **priors/calibration**, then generate synthetic brand/model/configuration demand.

No public BYD Canada dealer-level demand is assumed.

Suggested demand hierarchy:

```
Canada EV market
    -> province / CMA market share
        -> synthetic dealer catchment share
            -> model preference
                -> trim / colour / configuration preference
```

Demand should be stochastic, seasonal, and regionally heterogeneous.

---

## 5. Architectural Principle

The simulator and visualizer must be separate.

```
Scenario YAML
    |
    v
Validated Scenario Model
    |
    v
SimPy Simulation Kernel
    |
    +--> Immutable Event Log
    +--> State Snapshots
    +--> KPI / Planning Tables
    |
    +-----------------------------+
    |                             |
    v                             v
Animated Map Replay         Analytics / Reports
```

The map does **not** run the simulation.

It replays a completed simulation.

Benefits:

- deterministic playback
- instant seek/pause/fast-forward
- easier debugging
- reproducible scenario comparisons
- policy A/B testing using identical exogenous randomness
- map rendering is decoupled from simulation performance

---

## 6. Why SimPy

SimPy is a good fit because DealerFlow is naturally a discrete-event system.

Examples:

- a production batch waits for completion
- a VIN waits for vessel loading
- a vessel waits for departure
- a vehicle waits for customs/terminal processing
- an autorack shipment waits for capacity
- a dealer order waits for a matching VIN
- planning cycles occur weekly/monthly
- disruptions interrupt or delay processes
- constrained resources create queues

Simulation time should use **hours** internally. Most scenario parameters can remain expressed in days.

---

## 7. Domain Ontology

### 7.1 Market

Represents a demand geography.

Fields:

- id
- name
- province
- latitude / longitude
- population weight
- EV adoption factor
- seasonality parameters
- model/configuration preference profile

### 7.2 Dealer

Represents one synthetic dealership.

Fields:

- id
- name
- market_id
- location
- target_weeks_of_supply
- demand_scale
- priority_class
- stocking policy
- inventory
- backlog

### 7.3 VehicleModel

Fields:

- id
- name
- body_type
- powertrain
- lifecycle state
- launch date

### 7.4 VehicleConfiguration

The planning unit for supply/demand matching.

Fields:

- id
- model_id
- configuration_code
- trim/version
- exterior_colour
- interior_colour
- model_year
- synthetic FOB price
- quota price class where relevant

### 7.5 DealerOrder

A dealer request for replenishment/supply.

Fields:

- id
- dealer_id
- configuration_id
- quantity
- created_at
- requested_by
- priority
- allocated_quantity
- delivered_quantity
- status

States:

```
OPEN
PARTIAL
ALLOCATED
IN_TRANSIT
FULFILLED
CANCELLED
```

### 7.6 ChinaOrder

Represents the national/importer's order placed toward headquarters/factory supply.

Fields:

- id
- created_at
- approved_at
- submitted_at
- configuration quantities
- requested delivery window
- status
- planning_run_id
- recommendation basis

States:

```
DRAFT
RECOMMENDED
APPROVED
SUBMITTED
CONFIRMED
IN_PRODUCTION
SHIPPING
CLOSED
CANCELLED
```

### 7.7 ProductionBatch

A quantity-level production process before individual vehicles become operationally meaningful.

Fields:

- id
- china_order_id
- configuration_id
- quantity
- production_start
- production_complete
- factory / export origin

When production reaches the VIN-creation milestone, the batch instantiates physical Vehicle objects.

### 7.8 Vehicle

Represents one physical vehicle once a VIN exists.

Core fields:

- vin
- configuration_id
- production_batch_id
- produced_at
- current_node_id
- current_shipment_id
- logistics_status
- allocation_status
- retail_status
- allocated_dealer_id
- allocated_dealer_order_id
- allocation_timestamp

#### Important modeling rule

**Logistics status and allocation status are orthogonal.**

A vehicle can simultaneously be:

- physically ON_OCEAN
- commercially ALLOCATED to Ottawa

Do not collapse these into one giant vehicle status enum.

Suggested logistics states:

```
IN_PRODUCTION
FACTORY_COMPLETE
EXPORT_YARD
OCEAN
PORT_DWELL
CANADIAN_COMPOUND
RAIL
REGIONAL_COMPOUND
TRUCK
DEALER
```

Suggested allocation states:

```
UNALLOCATED
ALLOCATED
RESERVED
RELEASED
```

Suggested retail states:

```
IN_INVENTORY
DEMO
RETAIL_SOLD
OTHER
```

### 7.9 VINAllocation

Allocation must be an auditable decision record, not merely fields mutated on Vehicle.

Fields:

- id
- vin
- dealer_order_id
- dealer_id
- allocated_at
- allocation_rule
- reason
- score / priority basis
- previous_allocation_id, if reassigned
- released_at, if later released

This creates an allocation history and allows us to measure allocation churn.

### 7.10 ImportPermit

Fields:

- id
- shipment_id
- requested_at
- expected_entry_date
- quantity
- commodity / class
- approved_quantity
- valid_from
- valid_until
- status
- rejection / exception reason

States:

```
NOT_REQUESTED
PENDING
APPROVED
PARTIAL
DENIED
EXPIRED
CANCELLED
USED
```

### 7.11 Facility

Generic network node.

Types may include:

- FACTORY
- EXPORT_PORT
- IMPORT_PORT
- PORT_YARD
- NATIONAL_COMPOUND
- REGIONAL_COMPOUND
- DEALER

Fields:

- id
- type
- name
- coordinates
- optional processing capacity
- optional storage capacity

### 7.12 Shipment

A physical transport batch.

Fields:

- id
- mode
- origin
- destination
- vehicle VINs
- planned departure
- actual departure
- planned arrival
- actual arrival
- route_id
- status

Modes:

- OCEAN_RORO
- RAIL_AUTORACK
- TRUCK_CARRIER

The simulator tracks individual VINs, but the animated map should normally render **shipments**, not thousands of independent moving vehicle dots.

### 7.13 RetailSale / DemandEvent

Represents realized market demand.

Fields:

- id
- dealer_id / market_id
- desired_configuration
- timestamp
- fulfillment outcome
- fulfilled_vin
- wait time
- lost-sale flag

The initial model does not need simulated individual people.

### 7.14 ForecastSnapshot

Records what the planner believed at a point in time.

Fields:

- generated_at
- horizon
- dealer / market
- configuration
- forecast quantity
- method
- uncertainty interval

This lets us evaluate forecast quality retrospectively.

### 7.15 PlanningRun

Represents one planning cycle.

Inputs snapshot:

- retail history
- dealer orders
- available inventory
- allocated inventory
- inbound vehicles
- China orders
- inventory age
- quota outlook
- target coverage

Outputs:

- recommended China order
- allocation recommendations
- shortage/excess flags
- exceptions
- assumptions

### 7.16 Disturbance

Configurable exogenous shock.

Initial disturbance types:

- demand spike
- promotion
- model launch
- dealer opening
- factory constraint
- production delay
- vessel delay
- port congestion
- rail capacity reduction
- trucking delay
- quota consumption spike
- configuration-mix error
- manual priority request

---

## 8. VIN Allocation Semantics

The BYD posting explicitly says the specialist will:

- review dealer orders
- review available and inbound inventory
- match dealer orders to inventory using model/configuration attributes
- execute VIN allocation
- consider allocation rules, inventory availability, vehicle aging, and business requirements
- investigate unallocated orders and root causes

DealerFlow should therefore treat VIN allocation as a central workflow.

### Meaning

A dealer order initially requests a **configuration and quantity**.

A VIN allocation assigns a **specific physical vehicle** to satisfy part of that dealer order.

Example:

```
Dealer order:
    Dealer: Ottawa-01
    Configuration: MODEL_X / Premium / White / Black
    Quantity: 3

Candidate VIN pool:
    VIN-A  Vancouver compound
    VIN-B  on ocean
    VIN-C  Toronto compound
    VIN-D  allocated elsewhere

Allocation result:
    VIN-A -> Ottawa-01
    VIN-B -> Ottawa-01
    VIN-C -> Ottawa-01
```

The vehicles do not have to be physically at the dealer when allocation occurs.

The public posting explicitly refers to matching dealer orders against **available and inbound** inventory, so the simulator should permit VIN allocation while vehicles are still moving through the pipeline.

### Allocation decision factors

Initial baseline:

1. exact configuration match
2. valid/allocatable supply state
3. oldest suitable vehicle first
4. oldest/highest-priority dealer order first
5. distance / ETA tie-breaker

Later optimized policy:

- expected dealer stockout
- demand velocity
- backlog age
- projected weeks of supply
- vehicle age
- ETA
- fairness / service target
- priority overrides
- cost-to-serve

---

## 9. Logistics Chain

Synthetic baseline:

```
China factory
    -> export yard / port
    -> Ro-Ro / PCTC vessel
    -> Vancouver and/or Halifax import terminal
    -> customs / terminal / PDI dwell
    -> rail autorack and/or truck
    -> regional automotive compound
    -> truck carrier
    -> dealer
```

CN publicly describes Vancouver and Halifax as finished-vehicle gateways and operates automotive compounds and autorack capacity across its network.

DealerFlow should not claim BYD Canada currently uses a particular port, rail carrier, terminal, or routing contract unless publicly verified.

### Initial routing policy

Use a configurable routing strategy:

```
port_policy:
  strategy: nearest_total_expected_cost
  allowed_ports:
    - VANCOUVER
    - HALIFAX
```

MVP can begin with Vancouver only and add Halifax immediately afterward.

---

## 10. Lead-Time Model

Exact BYD Canada end-to-end lead times are not assumed public.

Use transparent synthetic distributions grounded in public logistics benchmarks.

Suggested initial distributions:

```
china_order_to_factory_complete:
    triangular: [21, 35, 49] days

factory_complete_to_export_departure:
    triangular: [3, 7, 14] days

china_to_vancouver_ocean:
    triangular: [15, 20, 30] days

import_terminal_dwell:
    triangular: [2, 5, 12] days

vancouver_to_ontario_rail:
    triangular: [7, 10, 18] days

regional_compound_to_dealer:
    triangular: [1, 3, 7] days
```

These are assumptions, not BYD service commitments.

They create an order-to-dealer range roughly on the order of **two to four months**, depending on production, sailing, dwell, rail timing, and disturbances.

A one-year simulation therefore remains appropriate.

Public grounding includes Transport Canada reporting a 35-day average 2023 Shanghai-to-Toronto container transit via West Coast ports, and commercial rail sources placing Vancouver-to-Toronto rail transit around a week-plus before terminal scheduling/dwell.

---

## 11. Scenario Format

Use **YAML for human-authored scenarios**.

Reasons:

- readable
- supports comments
- excellent for version control
- much less noisy than JSON
- far more pleasant than XML

Use **Pydantic models** as the source of truth.

Flow:

```
scenario.yaml
    -> Pydantic validation
    -> normalized scenario object
    -> canonical JSON snapshot / hash
    -> simulator
```

Pydantic can also generate JSON Schema for a future GUI editor.

The GUI should edit the same schema rather than creating a second scenario model.

### Example

```yaml
name: quota-year-baseline
start_date: 2026-03-01
end_date: 2027-02-28
seed: 4172

network:
  dealer_count: 15
  geography: national_ontario_heavy
  import_ports:
    - vancouver
    - halifax

quota:
  enabled: true
  national_limit: 49000
  administration: first_come_first_served
  external_usage_model: calibrated_stochastic

planning:
  china_order_cycle_days: 28
  allocation_cycle_days: 1
  target_weeks_of_supply: 8
  forecast_method: seasonal_baseline

disturbances:
  - type: demand_spike
    start_date: 2026-07-15
    duration_days: 35
    target:
      market: toronto
    multiplier: 1.45

  - type: vessel_delay
    target:
      voyage_number: 3
    delay:
      distribution: triangular
      min_days: 4
      mode_days: 9
      max_days: 18

  - type: quota_consumption_spike
    start_date: 2027-01-10
    duration_days: 21
    multiplier: 2.0
```

---

## 12. Stochastic Design

Randomness is core to the project, but scenario comparisons must remain fair.

Use independent RNG streams derived from a root seed:

- demand
- configuration choice
- production lead times
- ocean delays
- domestic logistics
- disturbances
- external quota consumption

When comparing two planning policies, reuse the same exogenous random streams.

This is the **common random numbers** technique:

> Policy A and Policy B experience the same synthetic market demand, same vessel delay, and same quota competition. Only the policy changes.

That makes KPI differences much more defensible.

---

## 13. Simulation Processes

Initial SimPy processes:

### DemandGenerator

Creates retail demand events by dealer/configuration.

### DealerReplenishmentProcess

Converts dealer inventory position and demand into dealer orders.

### NationalPlanningProcess

Runs periodically and creates China-order recommendations.

### ChinaOrderExecutionProcess

Turns approved China orders into production batches.

### ProductionProcess

Completes batches and instantiates VIN-level Vehicle objects.

### OceanLogisticsProcess

Stages vehicles and creates Ro-Ro shipments.

### ImportPermitProcess

Requests shipment-specific permits and consumes quota when appropriate.

### PortProcess

Handles unloading, customs/processing, and dwell.

### DomesticDistributionProcess

Creates rail/truck shipments to compounds and dealers.

### VINAllocationProcess

Matches dealer orders against available + inbound VINs.

### RetailFulfillmentProcess

Matches realized demand against dealer inventory/backlog.

### DisturbanceProcess

Applies configured external shocks.

### SnapshotProcess

Emits periodic state snapshots for analytics and replay acceleration.

---

## 14. Canonical Event Log

Every meaningful state transition emits an immutable event.

Minimum schema:

```
SimulationEvent
    event_id
    simulation_time
    timestamp
    event_type
    entity_type
    entity_id
    location_id
    correlation_id
    payload
```

Example event types:

```
DEMAND_OCCURRED
RETAIL_SALE_COMPLETED
DEALER_ORDER_CREATED
PLANNING_RUN_COMPLETED
CHINA_ORDER_RECOMMENDED
CHINA_ORDER_SUBMITTED
PRODUCTION_STARTED
VIN_CREATED
VEHICLE_LOADED
VESSEL_DEPARTED
VESSEL_ARRIVED
IMPORT_PERMIT_REQUESTED
IMPORT_PERMIT_APPROVED
VEHICLE_CLEARED
RAIL_SHIPMENT_DEPARTED
RAIL_SHIPMENT_ARRIVED
VIN_ALLOCATED
VIN_REALLOCATED
TRUCK_DEPARTED
VEHICLE_DELIVERED
BACKLOG_CREATED
DISTURBANCE_STARTED
DISTURBANCE_ENDED
```

The map replays these events.

Analytics should derive as much as practical from the same event history.

---

## 15. Animated Map Model

The map should render **aggregated transport entities** while preserving VIN-level data underneath.

Visible objects:

- Ro-Ro vessels
- autorack trains / rail shipments
- truck-carrier shipments
- ports
- compounds
- dealer nodes

When a shipment is selected, show:

- VIN count
- configuration mix
- origin
- destination
- planned vs actual ETA
- allocated vs unallocated vehicles
- associated China order
- current disruption, if any

Animation uses route interpolation between shipment departure and arrival times.

A user should be able to:

- pause
- seek
- change playback speed
- select a shipment
- filter by model/configuration
- filter by allocation status
- show backlog pressure at dealers
- jump to disturbances
- compare scenario/policy runs

---

## 16. KPI / Insight Layer

### Demand / service

- retail demand
- fulfilled demand
- lost sales
- fill rate
- backlog units
- backlog age
- dealer service level

### Inventory

- total inventory
- available inventory
- allocated inventory
- inbound inventory
- inventory aging
- weeks of supply
- excess / shortage by configuration
- inventory turns

### Planning

- forecast MAE / WAPE
- China order recommendation accuracy
- projected versus actual coverage
- configuration imbalance

### Allocation

- VIN allocation latency
- unallocated dealer orders
- allocation churn / reassignment count
- age of vehicles at allocation
- dealer fairness / service dispersion

### Logistics

- order-to-dealer lead time
- stage dwell times
- on-time arrival rate
- port dwell
- rail/truck transit
- disruption impact

### Quota

- DealerFlow OEM quota consumption
- external quota consumption
- national remaining quota
- permit success/failure
- vehicles delayed or blocked by quota
- stranded supply exposure

---

## 17. Role-Coverage Matrix

DealerFlow can demonstrate nearly every **functional/technical** responsibility in the posting.

| Posting area | DealerFlow representation |
| --- | --- |
| China order recommendations | NationalPlanningProcess |
| China order execution/status | ChinaOrder workflow |
| Dealer orders | DealerOrder workflow |
| VIN allocation | VINAllocation engine + audit history |
| Available/inbound inventory matching | Allocation candidate pool |
| Inventory planning | coverage, aging, mix, future position |
| Demand/supply analysis | stochastic demand + forecasts + pipeline |
| Inbound monitoring | shipment/vehicle event history |
| Port/yard/logistics coordination | logistics stages and exceptions |
| Allocation-gap root cause | exception diagnostics |
| Rolling planning | recurring PlanningRun |
| Supply shortages / excess | KPI + exception engine |
| Product/dealer launches | configurable disturbances/scenarios |
| CRM-style data execution | operational workbench / state records |
| Data validation/reconciliation | validation rules + exception reports |
| Daily/weekly/monthly reporting | analytics layer |
| Dashboarding | replay + KPI UI |
| Excel proficiency | later workbook/export feature |

What a simulator cannot honestly demonstrate by itself:

- real stakeholder management
- actual BYD CRM/ERP experience
- Mandarin communication
- hands-on work in BYD's dealer network
- driver-license requirement

The project should not pretend otherwise.

---

## 18. Data Quality / Reconciliation Feature

Because internally generated simulation data would otherwise be unrealistically clean, DealerFlow should eventually support an optional **operational data anomaly layer**.

Possible injected anomalies:

- duplicate VIN record
- missing configuration code
- inconsistent dealer-order quantity
- impossible status transition
- allocation pointing to unavailable VIN
- stale shipment ETA
- orphaned China-order line

These should be caught by explicit validation rules and surfaced in an Exceptions/Reconciliation view.

This directly demonstrates the posting's CRM/data-quality responsibilities without contaminating the core simulation logic.

---

## 19. Initial Implementation Order

### Milestone 1 — Kernel

- scenario schema
- seeded RNG streams
- synthetic national dealer network
- configuration catalogue
- demand generation
- DealerOrder
- ChinaOrder
- Vehicle/VIN creation
- simple logistics pipeline
- event log

### Milestone 2 — Allocation + planning

- available/inbound candidate pool
- baseline VIN allocation
- backlog/root-cause diagnostics
- rolling forecast
- China-order recommendation
- inventory coverage
- quota constraint

### Milestone 3 — Replay

- geographic nodes
- shipment trajectories
- time scrubber
- play/pause/speed
- dealer pressure visualization
- shipment inspection

### Milestone 4 — Policy comparison

- baseline policy
- improved policy
- identical random streams
- end-of-year KPI comparison
- disturbance scenarios

### Milestone 5 — Operational workbench

- CRM-like order tables
- VIN allocation view
- manual override/reallocation
- exceptions/reconciliation
- Excel/CSV export
- management summary

---

## 20. North-Star Demo

A strong DealerFlow demo should support this narrative:

> We begin a Canadian quota year with existing dealer inventory, backlog, inbound vehicles, and China orders. Demand evolves stochastically across a synthetic national dealer network. DealerFlow forecasts requirements, recommends China orders, tracks production and individual VINs, manages import-permit/quota exposure, moves shipments through ocean/port/rail/truck stages, allocates inbound VINs to dealer demand, and reports service, inventory, logistics, allocation, and planning performance over the year.

Then:

> Re-run the exact same synthetic year under a different allocation/planning policy or disturbance scenario and quantify what changed.

That is the core DealerFlow product.
