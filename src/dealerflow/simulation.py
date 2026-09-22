from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
import math
from pathlib import Path

import simpy

from .config import DemandSpikeConfig, ScenarioConfig, VesselDelayConfig, load_scenario
from .domain import AllocationStatus, DealerState, LogisticsStatus, Shipment, Vehicle
from .events import EventLog, SimulationEvent
from .rng import RandomStreams, poisson


@dataclass(frozen=True, slots=True)
class SimulationResult:
    scenario_name: str
    events: tuple[SimulationEvent, ...]
    digest: str
    summary: dict[str, float | int]


class DealerFlowSimulation:
    def __init__(self, scenario: ScenarioConfig) -> None:
        self.scenario = scenario
        self.env = simpy.Environment()
        self.rng = RandomStreams(scenario.seed)
        self.event_log = EventLog()
        self.dealers = {
            d.id: DealerState(
                dealer_id=d.id,
                inventory={c.id: [] for c in scenario.vehicle_configurations},
                backlog={c.id: 0 for c in scenario.vehicle_configurations},
                open_orders={c.id: 0 for c in scenario.vehicle_configurations},
            )
            for d in scenario.dealers
        }
        self.vehicles: dict[str, Vehicle] = {}
        self.shipments: dict[str, Shipment] = {}
        self._dealer_cfg = {d.id: d for d in scenario.dealers}
        self._event_id = self._vin_no = self._order_no = self._batch_no = self._shipment_no = 1
        self._external_quota = scenario.quota.initial_external_usage
        self._own_quota = self._quota_blocked = 0
        self._supply_outstanding: dict[str, int] = defaultdict(int)
        self._vessel_delays = {
            d.shipment_number: d.delay_days
            for d in scenario.disturbances
            if isinstance(d, VesselDelayConfig)
        }

    @classmethod
    def from_yaml(cls, path: str | Path) -> "DealerFlowSimulation":
        return cls(load_scenario(path))

    def run(self) -> SimulationResult:
        self._warm_start()
        self.env.process(self._daily_demand())
        self.env.process(self._dealer_replenishment())
        self.env.process(self._china_planning())
        self.env.process(self._allocation())
        self.env.process(self._disturbance_markers())
        if self.scenario.quota.enabled:
            self.env.process(self._external_quota_use())
        self.env.run(until=self.scenario.duration_days)
        return SimulationResult(
            self.scenario.name,
            self.event_log.events,
            self.event_log.digest(),
            self._summary(),
        )

    def _warm_start(self) -> None:
        rng = self.rng.get("warm_start")
        for dealer in self.scenario.dealers:
            state = self.dealers[dealer.id]
            for config in self.scenario.vehicle_configurations:
                weekly = dealer.demand_scale * config.daily_demand_weight * 7
                target = max(1, round(weekly * dealer.target_weeks_of_supply))
                for _ in range(max(0, round(target * rng.uniform(.65, 1.10)))):
                    v = self._new_vehicle(config.id, LogisticsStatus.DEALER, -rng.uniform(1, 90))
                    v.allocation_status = AllocationStatus.ALLOCATED
                    v.allocated_dealer_id = dealer.id
                    state.inventory[config.id].append(v.vin)

        inbound = []
        for config in self.scenario.vehicle_configurations:
            weekly = sum(d.demand_scale * config.daily_demand_weight * 7 for d in self.scenario.dealers)
            for _ in range(max(1, round(weekly * 2.5))):
                v = self._new_vehicle(config.id, LogisticsStatus.OCEAN, -rng.uniform(14, 45))
                inbound.append(v.vin)

        arrival = rng.uniform(7, 18)
        shipment = Shipment(
            id="SEA-00001", mode="OCEAN_RORO", number=1,
            origin="CHINA_EXPORT_PORT", destination="VANCOUVER", vins=inbound,
            planned_departure_day=-20, planned_arrival_day=arrival, actual_departure_day=-20,
        )
        self.shipments[shipment.id] = shipment
        self._shipment_no = 2
        self.env.process(self._ocean_arrival(shipment, arrival))
        self._emit("SIMULATION_INITIALIZED", "scenario", self.scenario.name, payload={
            "starting_inventory": sum(len(v) for d in self.dealers.values() for v in d.inventory.values()),
            "starting_inbound": len(inbound),
        })
        self._emit("STARTING_PIPELINE_REGISTERED", "shipment", shipment.id, "PACIFIC_OCEAN", payload={
            "vin_count": len(inbound), "expected_arrival_day": round(arrival, 2)
        })

    def _daily_demand(self):
        while True:
            day = int(self.env.now)
            for dealer in self.scenario.dealers:
                state = self.dealers[dealer.id]
                for config in self.scenario.vehicle_configurations:
                    mean = dealer.demand_scale * config.daily_demand_weight
                    mean *= self._demand_multiplier(day, dealer.id, dealer.province, config.id)
                    qty = poisson(self.rng.get(f"demand:{dealer.id}:{config.id}"), mean)
                    if not qty:
                        continue
                    state.demand += qty
                    self._emit("DEMAND_OCCURRED", "dealer", dealer.id, dealer.id, payload={
                        "configuration_id": config.id, "quantity": qty
                    })
                    for _ in range(qty):
                        if state.inventory[config.id]:
                            vin = state.inventory[config.id].pop(0)
                            state.sales += 1
                            self._emit("RETAIL_SALE_COMPLETED", "vehicle", vin, dealer.id, payload={
                                "dealer_id": dealer.id, "configuration_id": config.id
                            })
                        else:
                            state.backlog[config.id] += 1
                            self._emit("BACKLOG_CREATED", "dealer", dealer.id, dealer.id, payload={
                                "configuration_id": config.id, "backlog": state.backlog[config.id]
                            })
            yield self.env.timeout(1)

    def _dealer_replenishment(self):
        yield self.env.timeout(.25)
        while True:
            for dealer in self.scenario.dealers:
                state = self.dealers[dealer.id]
                for config in self.scenario.vehicle_configurations:
                    target = math.ceil(
                        dealer.demand_scale * config.daily_demand_weight * 7 * dealer.target_weeks_of_supply
                    )
                    needed = max(
                        0,
                        target + state.backlog[config.id]
                        - len(state.inventory[config.id])
                        - state.open_orders[config.id],
                    )
                    if needed:
                        oid = f"DO-{self._order_no:06d}"; self._order_no += 1
                        state.open_orders[config.id] += needed
                        self._emit("DEALER_ORDER_CREATED", "dealer_order", oid, dealer.id, payload={
                            "dealer_id": dealer.id, "configuration_id": config.id, "quantity": needed
                        })
            yield self.env.timeout(self.scenario.planning.dealer_replenishment_cycle_days)

    def _china_planning(self):
        yield self.env.timeout(1)
        while True:
            open_by_config = defaultdict(int)
            for state in self.dealers.values():
                for config_id, qty in state.open_orders.items():
                    open_by_config[config_id] += qty

            required = {}
            for config_id, open_qty in open_by_config.items():
                pipeline = sum(
                    1 for v in self.vehicles.values()
                    if v.configuration_id == config_id
                    and v.logistics_status not in {LogisticsStatus.DEALER, LogisticsStatus.QUOTA_BLOCKED}
                )
                required[config_id] = max(0, open_qty - pipeline - self._supply_outstanding[config_id])

            if sum(required.values()):
                order_id = f"CO-{self._batch_no:05d}"; self._batch_no += 1
                self._emit("CHINA_ORDER_RECOMMENDED", "china_order", order_id, payload={
                    "quantities": required, "total_units": sum(required.values())
                })
                for config_id, qty in required.items():
                    if qty:
                        self._supply_outstanding[config_id] += qty
                        self.env.process(self._supply_batch(order_id, config_id, qty))
            yield self.env.timeout(self.scenario.planning.china_order_cycle_days)

    def _supply_batch(self, order_id: str, config_id: str, qty: int):
        rng = self.rng.get("logistics")
        self._emit("PRODUCTION_STARTED", "production_batch", order_id, payload={
            "configuration_id": config_id, "quantity": qty
        })
        yield self.env.timeout(rng.triangular(*self.scenario.logistics.production_days))
        self._supply_outstanding[config_id] = max(0, self._supply_outstanding[config_id] - qty)

        vins = []
        for _ in range(qty):
            v = self._new_vehicle(config_id, LogisticsStatus.FACTORY_COMPLETE)
            vins.append(v.vin)
            self._emit("VIN_CREATED", "vehicle", v.vin, "CHINA_FACTORY", order_id, {
                "configuration_id": config_id
            })
        yield self.env.timeout(.01)
        yield self.env.timeout(rng.triangular(*self.scenario.logistics.export_staging_days))

        cap = self.scenario.logistics.batch_capacity
        for i in range(0, len(vins), cap):
            chunk = vins[i:i + cap]
            number = self._shipment_no; self._shipment_no += 1
            sid = f"SEA-{number:05d}"
            transit = rng.triangular(*self.scenario.logistics.ocean_days)
            delay = self._vessel_delays.get(number, 0)
            transit += delay
            if delay:
                self._emit("DISTURBANCE_APPLIED", "shipment", sid, "PACIFIC_OCEAN", payload={
                    "type": "vessel_delay", "delay_days": delay
                })
            shipment = Shipment(
                id=sid, mode="OCEAN_RORO", number=number,
                origin="CHINA_EXPORT_PORT", destination="VANCOUVER", vins=chunk,
                planned_departure_day=self.env.now, planned_arrival_day=self.env.now + transit,
                actual_departure_day=self.env.now,
            )
            self.shipments[sid] = shipment
            for vin in chunk:
                self.vehicles[vin].logistics_status = LogisticsStatus.OCEAN
            self._emit("VESSEL_DEPARTED", "shipment", sid, "CHINA_EXPORT_PORT", order_id, {
                "vin_count": len(chunk), "destination": "VANCOUVER"
            })
            self.env.process(self._ocean_arrival(shipment, transit))

    def _ocean_arrival(self, shipment: Shipment, transit: float):
        yield self.env.timeout(transit)
        shipment.actual_arrival_day = self.env.now
        eligible = shipment.vins
        if self.scenario.quota.enabled:
            remaining = max(0, self.scenario.quota.national_limit - self._external_quota - self._own_quota)
            admitted = min(remaining, len(shipment.vins))
            eligible = shipment.vins[:admitted]
            blocked = shipment.vins[admitted:]
            self._own_quota += admitted
            self._quota_blocked += len(blocked)
            for vin in blocked:
                self.vehicles[vin].logistics_status = LogisticsStatus.QUOTA_BLOCKED
            if blocked:
                self._emit("QUOTA_BLOCKED", "shipment", shipment.id, "VANCOUVER", payload={
                    "blocked_units": len(blocked), "remaining_quota_before_arrival": remaining
                })

        self._emit("VESSEL_ARRIVED", "shipment", shipment.id, "VANCOUVER", payload={
            "vin_count": len(shipment.vins), "admitted_count": len(eligible)
        })
        for vin in eligible:
            self.vehicles[vin].logistics_status = LogisticsStatus.PORT_DWELL

        rng = self.rng.get("logistics")
        yield self.env.timeout(rng.triangular(*self.scenario.logistics.port_dwell_days))
        self._emit("VEHICLES_CLEARED", "shipment", shipment.id, "VANCOUVER", payload={"vin_count": len(eligible)})
        for vin in eligible:
            self.vehicles[vin].logistics_status = LogisticsStatus.CANADIAN_COMPOUND
            self.env.process(self._domestic_delivery(self.vehicles[vin]))

    def _domestic_delivery(self, vehicle: Vehicle):
        while vehicle.allocated_dealer_id is None:
            yield self.env.timeout(1)
        dealer = self._dealer_cfg[vehicle.allocated_dealer_id]
        rng = self.rng.get("logistics")

        if dealer.province != "BC":
            vehicle.logistics_status = LogisticsStatus.RAIL
            self._emit("RAIL_SHIPMENT_DEPARTED", "vehicle", vehicle.vin, "VANCOUVER", payload={"dealer_id": dealer.id})
            yield self.env.timeout(rng.triangular(*self.scenario.logistics.rail_days))
            vehicle.logistics_status = LogisticsStatus.REGIONAL_COMPOUND
            self._emit("RAIL_SHIPMENT_ARRIVED", "vehicle", vehicle.vin, f"{dealer.province}_COMPOUND", payload={"dealer_id": dealer.id})

        vehicle.logistics_status = LogisticsStatus.TRUCK
        self._emit("TRUCK_DEPARTED", "vehicle", vehicle.vin, f"{dealer.province}_COMPOUND", payload={"dealer_id": dealer.id})
        yield self.env.timeout(rng.triangular(*self.scenario.logistics.truck_days))
        vehicle.logistics_status = LogisticsStatus.DEALER

        state = self.dealers[dealer.id]
        state.inventory[vehicle.configuration_id].append(vehicle.vin)
        if state.open_orders[vehicle.configuration_id] > 0:
            state.open_orders[vehicle.configuration_id] -= 1
        if state.backlog[vehicle.configuration_id] > 0:
            state.backlog[vehicle.configuration_id] -= 1
            state.inventory[vehicle.configuration_id].remove(vehicle.vin)
            state.sales += 1
            self._emit("BACKLOG_FULFILLED", "vehicle", vehicle.vin, dealer.id, payload={
                "configuration_id": vehicle.configuration_id
            })
        self._emit("VEHICLE_DELIVERED", "vehicle", vehicle.vin, dealer.id, payload={
            "dealer_id": dealer.id, "configuration_id": vehicle.configuration_id
        })

    def _allocation(self):
        while True:
            candidates = [
                v for v in self.vehicles.values()
                if v.allocation_status == AllocationStatus.UNALLOCATED
                and v.logistics_status not in {LogisticsStatus.IN_PRODUCTION, LogisticsStatus.QUOTA_BLOCKED, LogisticsStatus.DEALER}
            ]
            candidates.sort(key=lambda v: (v.created_day, v.vin))
            for vehicle in candidates:
                choices = []
                for dealer_id, state in self.dealers.items():
                    allocated = sum(
                        1 for other in self.vehicles.values()
                        if other.configuration_id == vehicle.configuration_id
                        and other.allocated_dealer_id == dealer_id
                        and other.logistics_status != LogisticsStatus.DEALER
                    )
                    uncovered = state.open_orders[vehicle.configuration_id] - allocated
                    if uncovered > 0:
                        pressure = state.backlog[vehicle.configuration_id] * 1000 + uncovered
                        choices.append((pressure, dealer_id))
                if choices:
                    _, dealer_id = max(choices, key=lambda x: (x[0], x[1]))
                    vehicle.allocation_status = AllocationStatus.ALLOCATED
                    vehicle.allocated_dealer_id = dealer_id
                    vehicle.allocated_day = self.env.now
                    self._emit("VIN_ALLOCATED", "vehicle", vehicle.vin, payload={
                        "dealer_id": dealer_id,
                        "configuration_id": vehicle.configuration_id,
                        "allocation_rule": "backlog_then_uncovered_order",
                    })
            yield self.env.timeout(self.scenario.planning.allocation_cycle_days)

    def _external_quota_use(self):
        while True:
            remaining = max(0, self.scenario.quota.national_limit - self._external_quota - self._own_quota)
            if remaining:
                qty = min(remaining, poisson(self.rng.get("external_quota"), self.scenario.quota.external_daily_mean))
                if qty:
                    self._external_quota += qty
                    self._emit("EXTERNAL_QUOTA_CONSUMED", "quota", "CANADA_EV_QUOTA", payload={
                        "quantity": qty, "external_usage": self._external_quota
                    })
            yield self.env.timeout(1)

    def _disturbance_markers(self):
        for d in self.scenario.disturbances:
            if isinstance(d, DemandSpikeConfig):
                self.env.process(self._spike_marker(d))
        yield self.env.timeout(self.scenario.duration_days)

    def _spike_marker(self, d: DemandSpikeConfig):
        yield self.env.timeout(d.start_day)
        entity = f"demand-spike-{d.start_day}"
        self._emit("DISTURBANCE_STARTED", "disturbance", entity, payload={
            "type": d.type, "dealer_id": d.dealer_id, "province": d.province,
            "configuration_id": d.configuration_id, "multiplier": d.multiplier
        })
        yield self.env.timeout(d.duration_days)
        self._emit("DISTURBANCE_ENDED", "disturbance", entity, payload={"type": d.type})

    def _demand_multiplier(self, day: int, dealer_id: str, province: str, config_id: str) -> float:
        multiplier = 1.0
        for d in self.scenario.disturbances:
            if not isinstance(d, DemandSpikeConfig):
                continue
            if not d.start_day <= day < d.start_day + d.duration_days:
                continue
            if d.dealer_id and d.dealer_id != dealer_id:
                continue
            if d.province and d.province != province:
                continue
            if d.configuration_id and d.configuration_id != config_id:
                continue
            multiplier *= d.multiplier
        return multiplier

    def _new_vehicle(self, config_id: str, status: LogisticsStatus, created_day: float | None = None) -> Vehicle:
        vin = f"DF{self.scenario.seed % 10000:04d}{self._vin_no:011d}"
        self._vin_no += 1
        vehicle = Vehicle(
            vin=vin,
            configuration_id=config_id,
            created_day=self.env.now if created_day is None else created_day,
            logistics_status=status,
        )
        self.vehicles[vin] = vehicle
        return vehicle

    def _emit(self, event_type: str, entity_type: str, entity_id: str,
              location_id: str | None = None, correlation_id: str | None = None,
              payload: dict | None = None) -> None:
        timestamp = datetime.combine(self.scenario.start_date, time.min) + timedelta(days=self.env.now)
        self.event_log.append(SimulationEvent(
            event_id=self._event_id,
            simulation_day=float(self.env.now),
            timestamp=timestamp,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            location_id=location_id,
            correlation_id=correlation_id,
            payload=payload or {},
        ))
        self._event_id += 1

    def _summary(self) -> dict[str, float | int]:
        demand = sum(d.demand for d in self.dealers.values())
        sales = sum(d.sales for d in self.dealers.values())
        backlog = sum(sum(d.backlog.values()) for d in self.dealers.values())
        inventory = sum(sum(len(v) for v in d.inventory.values()) for d in self.dealers.values())
        return {
            "demand_units": demand,
            "sales_units": sales,
            "ending_backlog_units": backlog,
            "ending_dealer_inventory_units": inventory,
            "fill_rate": round(sales / demand if demand else 1.0, 4),
            "vehicles_created": len(self.vehicles),
            "dealerflow_quota_used": self._own_quota,
            "external_quota_used": self._external_quota,
            "quota_blocked_units": self._quota_blocked,
            "events": len(self.event_log.events),
        }
