# DealerFlow Reference: BYD Operations Planning Specialist

**Source:** BYD North America — Operations Planning Specialist, Toronto, Ontario, Canada  
**Job posting:** https://ca.linkedin.com/jobs/view/operations-planning-specialist-at-byd-north-america-4464092396  
**Captured:** 2026-09-22

> This is a project-oriented summary of the posting, not a verbatim copy. Its purpose is to keep DealerFlow aligned with the actual work BYD is hiring for.

## 1. Role Mission

The role connects **dealer demand** to **vehicle supply** for BYD Canada's passenger-vehicle operation.

The specialist is expected to combine hands-on operational execution with planning and analytics across:

- China/factory ordering
- Dealer order management
- VIN allocation
- Inventory and inbound supply
- Demand/supply analysis
- CRM data quality
- Operational reporting
- Cross-functional coordination

The recurring planning problem is:

> Given dealer demand, recent retail sales, current inventory, inbound vehicles, inventory age, and desired inventory coverage, what vehicles should be ordered, where should available vehicles be allocated, and which exceptions require intervention?

That problem is the core of DealerFlow.

---

## 2. Operational Entities Implied by the Posting

DealerFlow should eventually model these explicitly.

### Dealer

Relevant attributes:

- Dealer identifier
- Region / market
- Demand profile
- Sales history
- Order backlog
- Target inventory coverage
- Current inventory
- Allocated inventory
- Unfulfilled demand

### Vehicle Configuration

A vehicle is not merely a model. Matching and planning occur at configuration level.

Relevant attributes:

- Model
- Configuration / SAP code
- Trim or version
- Exterior colour
- Interior colour
- Model year

### Vehicle / VIN

Relevant attributes:

- VIN
- Configuration
- Current status
- Current location
- Dealer allocation, if any
- Inventory age
- Availability date

### Dealer Order

Relevant attributes:

- Dealer
- Requested configuration
- Quantity
- Order date
- Priority
- Fulfilled / unfulfilled quantity
- Allocation status
- Exception reason

### China / Factory Order

Relevant attributes:

- Configuration
- Quantity
- Order date
- Supply stage
- Expected production / shipment dates
- Status
- Recommended versus approved quantity

### Supply Pipeline

The posting distinguishes multiple inventory states, including concepts such as:

- Available
- Allocated
- Demo
- Inbound
- Ocean / in transit
- Other operational statuses

DealerFlow should treat inventory as a pipeline rather than a single stock number.

---

## 3. Core Planning Workflows

### 3.1 Rolling Factory Order Recommendation

Inputs:

- Dealer orders
- Retail sales history
- Current inventory
- Inbound supply
- Existing factory orders
- Inventory aging
- Target inventory coverage
- Business forecasts

Outputs:

- Recommended order quantity by model/configuration
- Recommended order mix
- Expected future inventory position
- Supply-gap warnings
- Excess-order warnings
- Configuration-imbalance warnings
- Timing-risk warnings

DealerFlow should make this one of its flagship workflows.

### 3.2 Dealer Order Management

The system should expose:

- Dealer backlog
- Fulfillment status
- Allocation requirements
- Unallocated orders
- Order exceptions

It should make clear **why** a dealer order remains unfulfilled.

Possible root causes include:

- Configuration shortage
- Inventory located elsewhere
- Vehicle not yet available
- Supply timing mismatch
- Allocation-rule conflict
- Insufficient total supply

### 3.3 VIN Allocation

Available or inbound VINs should be matched against dealer orders using required vehicle attributes.

Allocation logic should be able to consider:

- Exact model/configuration match
- Inventory availability
- Inventory aging
- Dealer demand
- Dealer order priority
- Business rules

This gives DealerFlow a natural optimization problem:

> Allocate a constrained pool of vehicles across competing dealer demand while respecting matching constraints and minimizing undesirable outcomes.

### 3.4 Inventory and Supply Planning

Important planning measures include:

- Inventory coverage
- Inventory age
- Configuration mix
- Fast-moving inventory
- Slow-moving inventory
- Current supply position
- Future projected supply position
- Backlog
- Supply pipeline

The application should distinguish between **what exists now** and **what will become available later**.

### 3.5 Data Validation and Reconciliation

The posting puts significant emphasis on operational data quality.

DealerFlow should therefore include deliberate dirty-data cases and validation logic such as:

- Missing configuration codes
- Invalid statuses
- Duplicate VINs
- Dealer orders referencing unavailable configurations
- Quantity discrepancies
- Inconsistent allocation records
- Impossible dates or state transitions

A useful portfolio feature would be an **Exceptions / Reconciliation** view that detects and explains these problems.

---

## 4. Reporting Requirements

The real role prepares daily, weekly, and monthly operational reporting.

DealerFlow dashboards should therefore answer questions such as:

- How many dealer orders are open?
- How much backlog exists?
- Which configurations are undersupplied?
- Which configurations are oversupplied?
- What is current inventory coverage?
- How much inventory is aging?
- What is inbound by status and ETA?
- Which dealers have the largest allocation gaps?
- What orders are at risk?
- What should the next factory order contain?
- What changed since the previous planning cycle?

Reports should emphasize **exceptions and decisions**, not just charts.

---

## 5. Cross-Functional Context

The role coordinates with:

- Sales
- Logistics
- Finance
- Aftersales
- Network Development
- BYD headquarters / regional teams

DealerFlow does not need to simulate entire departments, but scenarios should make their competing concerns visible.

Examples:

- Sales requests priority allocation for a dealer.
- Logistics reports a shipment delay.
- A new dealer opens and requires launch inventory.
- A product launch changes demand.
- Finance wants excess inventory reduced.
- Headquarters changes configuration availability.

These are excellent Scenario Lab inputs.

---

## 6. Capabilities the Portfolio Project Should Demonstrate

The posting values the following abilities. DealerFlow should provide evidence for as many as possible.

| Job capability | DealerFlow evidence |
| --- | --- |
| Demand and supply planning | Rolling supply forecast and factory-order recommendation |
| Inventory planning | Coverage, aging, future inventory position |
| Order management | Dealer order/backlog workflow |
| Inventory allocation | VIN-level allocation engine |
| Automotive distribution | Dealer-network and vehicle-supply domain model |
| Analytical reasoning | Forecasting, KPIs, scenario comparison |
| Excel-style operational analysis | Exportable tabular reports and transparent calculations |
| CRM / ERP familiarity | Operational records, statuses, workflows, reconciliation |
| Data accuracy | Validation and exception detection |
| Reporting / dashboards | Network overview and planning dashboards |
| Root-cause analysis | Explain unfulfilled demand and allocation gaps |
| Process improvement | Compare baseline and improved allocation/planning policies |
| Fast operational response | Scenario shocks and replanning |

---

## 7. DealerFlow Product Definition

**DealerFlow is a synthetic automotive distribution and operations-planning simulator for a Canadian dealer network.**

It models demand, dealer orders, vehicle inventory, VIN allocation, inbound supply, and factory ordering, then provides planning recommendations and operational dashboards.

Its main purpose as a portfolio project is to demonstrate the ability to reason about and implement the same class of problems described in BYD Canada's Operations Planning Specialist role.

DealerFlow should feel like a lightweight internal planning tool rather than a generic data-science notebook.

---

## 8. Initial Simulation Scope

The first useful version should remain intentionally small.

### Network

- Roughly 8–15 synthetic Canadian dealers
- Dealer-specific demand characteristics
- Geographic region retained as useful context, without requiring routing initially

### Products

- Several synthetic EV models
- Multiple configurations per model
- Configuration attributes such as trim and colour

### Demand

- Synthetic retail sales history
- Dealer orders generated from underlying demand
- Regional and configuration-level variation
- Optional promotion / launch / seasonality shocks

### Supply

- Current dealer/network inventory
- Inbound vehicles
- Factory orders
- Shipment ETAs
- Vehicle-level VIN records where allocation requires them

### Planning

- Baseline demand forecast
- Target inventory coverage
- Factory-order recommendation
- Baseline VIN allocation
- Improved allocation strategy
- Explainable exception detection

---

## 9. Recommended Core KPIs

Candidate metrics:

- Order fill rate
- Dealer service level
- Backlog units
- Backlog age
- Unallocated orders
- Days / weeks of supply
- Inventory age
- Aging inventory percentage
- Configuration shortage
- Excess inventory
- Forecast error
- Allocation efficiency
- Dealer demand coverage
- Future projected coverage
- Units inbound by pipeline stage

We should avoid inventing automotive-industry formulas where we do not know BYD's actual internal definitions. Every metric should therefore have a documented formula in DealerFlow.

---

## 10. Scenario Lab Candidates

High-value scenarios derived from the role:

1. **Shipment delay**  
   An inbound vessel is delayed and projected dealer coverage falls.

2. **Regional demand spike**  
   One market suddenly sells substantially more vehicles than forecast.

3. **Configuration mismatch**  
   Network inventory is numerically healthy but concentrated in unwanted trims or colours.

4. **Dealer launch**  
   A new dealer enters the network and requires initial stock.

5. **Promotion**  
   Demand for one model/configuration increases rapidly.

6. **Aging inventory intervention**  
   Old vehicles should receive allocation preference where demand permits.

7. **Factory constraint**  
   Headquarters reduces availability of one configuration.

8. **Priority exception**  
   Sales requests a manual priority allocation, creating consequences elsewhere.

For each scenario DealerFlow should show:

- Before state
- Trigger
- Baseline response
- Recommended response
- KPI impact
- Remaining risks / exceptions

---

## 11. MVP Acceptance Target

The first end-to-end milestone should be able to:

1. Generate a synthetic dealer network.
2. Generate vehicle configurations.
3. Generate historical dealer sales/demand.
4. Generate dealer orders.
5. Generate current and inbound inventory.
6. Match inventory to dealer orders.
7. Allocate VINs under a documented baseline rule.
8. Identify unfulfilled demand and explain its root cause.
9. Calculate basic inventory/backlog KPIs.
10. Generate a recommended future factory order by configuration.
11. Advance simulation time and update the supply/demand state.
12. Reproduce the run from a fixed random seed.

A CLI implementation is enough for this milestone.

The dashboard comes after the underlying planning system is coherent.

---

## 12. Likely Phase-2 Features

After the MVP kernel works:

- Django/PostgreSQL persistence
- Network Overview dashboard
- Demand Planning view
- Allocation workbench
- Supply Pipeline view
- Exceptions / Reconciliation view
- Scenario Lab
- CSV / Excel export
- Historical planning snapshots
- What-if controls
- Optimization-based allocation
- Forecast comparison
- Basic geographic visualization

---

## 13. Guardrails

### Synthetic Data Only

DealerFlow should not imply access to BYD internal data, processes, configuration codes, CRM schemas, allocation rules, or proprietary systems.

Where real BYD terminology comes directly from the public job posting, that terminology may be used as domain inspiration, but implementation details should remain explicitly synthetic.

### Explainability Over Cleverness

A planning specialist needs to explain recommendations.

Forecasts, allocations, shortages, and suggested factory orders should expose their assumptions and calculations.

### Baseline Before Optimization

Implement an understandable baseline policy first.

Then demonstrate whether a more sophisticated policy improves measurable outcomes.

### Operational Software, Not Merely ML

The posting is heavily operational. Forecasting is useful, but DealerFlow should primarily demonstrate that forecasts can be turned into reliable orders, allocations, exception handling, and decisions.

---

## 14. Design North Star

A successful DealerFlow demo should let us say:

> A new shipment has arrived into a constrained Canadian dealer network. DealerFlow can show current demand, inventory and backlog; allocate specific vehicles to dealer orders; explain what cannot be fulfilled; project future supply coverage; and recommend what the next factory order should contain.

That single flow touches most of the substantive work described in the posting.
