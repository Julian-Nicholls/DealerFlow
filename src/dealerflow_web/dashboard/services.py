from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC
from hashlib import sha256
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils import timezone

from dealerflow.config import parse_scenario
from dealerflow.simulation import DealerFlowSimulation

from .models import ScenarioRecord, SimulationEventRecord, SimulationRun


def persist_scenario_run(path: Path) -> SimulationRun:
    source = path.read_text(encoding="utf-8")
    cfg = parse_scenario(source)
    digest = sha256(source.encode("utf-8")).hexdigest()

    scenario, _ = ScenarioRecord.objects.get_or_create(
        content_sha256=digest,
        defaults={
            "name": cfg.name,
            "source_path": str(path),
            "source_yaml": source,
        },
    )
    run = SimulationRun.objects.create(
        scenario=scenario,
        status=SimulationRun.Status.RUNNING,
        seed=cfg.seed,
        start_date=cfg.start_date,
        end_date=cfg.end_date,
    )

    try:
        result = DealerFlowSimulation(cfg).run()
        rows = []
        for event in result.events:
            occurred_at = event.timestamp
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=UTC)
            rows.append(
                SimulationEventRecord(
                    run=run,
                    sequence=event.event_id,
                    simulation_day=event.simulation_day,
                    occurred_at=occurred_at,
                    event_type=event.event_type,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    location_id=event.location_id or "",
                    correlation_id=event.correlation_id or "",
                    payload=event.payload,
                )
            )

        with transaction.atomic():
            SimulationEventRecord.objects.bulk_create(rows, batch_size=1000)
            run.status = SimulationRun.Status.COMPLETE
            run.event_digest = result.digest
            run.event_count = len(rows)
            run.summary = result.summary
            run.finished_at = timezone.now()
            run.save(
                update_fields=[
                    "status",
                    "event_digest",
                    "event_count",
                    "summary",
                    "finished_at",
                ]
            )
    except Exception as exc:
        run.status = SimulationRun.Status.FAILED
        run.error = f"{type(exc).__name__}: {exc}"
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "error", "finished_at"])
        raise

    return run


def _locations(run: SimulationRun) -> dict[str, dict[str, Any]]:
    cfg = parse_scenario(run.scenario.source_yaml)
    locations = {
        f.id: {
            "id": f.id,
            "name": f.name,
            "kind": f.kind,
            "latitude": f.latitude,
            "longitude": f.longitude,
        }
        for f in cfg.facilities
    }
    for dealer in cfg.dealers:
        locations[dealer.id] = {
            "id": dealer.id,
            "name": dealer.name,
            "kind": "DEALER",
            "city": dealer.city,
            "province": dealer.province,
            "latitude": dealer.latitude,
            "longitude": dealer.longitude,
        }
    return locations


def _configuration_catalog(run: SimulationRun) -> dict[str, dict[str, Any]]:
    cfg = parse_scenario(run.scenario.source_yaml)
    return {
        c.id: {
            "id": c.id,
            "model": c.model,
            "trim": c.trim,
            "exterior_colour": c.exterior_colour,
            "interior_colour": c.interior_colour,
        }
        for c in cfg.vehicle_configurations
    }


OCEAN_ROUTE = [
    [22.58, 114.27],
    [24.5, 126.0],
    [31.0, 142.0],
    [39.0, 160.0],
    [47.0, 177.0],
    [50.0, -160.0],
    [50.5, -142.0],
    [49.13, -123.08],
]

RAIL_CORRIDORS = {
    "AB_COMPOUND": [
        [49.13, -123.08],
        [50.67, -120.33],
        [51.05, -114.07],
    ],
    "SK_COMPOUND": [
        [49.13, -123.08],
        [50.67, -120.33],
        [51.05, -114.07],
        [50.45, -104.62],
        [52.13, -106.67],
    ],
    "MB_COMPOUND": [
        [49.13, -123.08],
        [50.67, -120.33],
        [51.05, -114.07],
        [50.45, -104.62],
        [49.90, -97.14],
    ],
    "ON_COMPOUND": [
        [49.13, -123.08],
        [50.67, -120.33],
        [51.05, -114.07],
        [50.45, -104.62],
        [49.90, -97.14],
        [49.77, -94.49],
        [48.38, -89.25],
        [46.49, -84.35],
        [43.68, -79.63],
    ],
    "QC_COMPOUND": [
        [49.13, -123.08],
        [50.67, -120.33],
        [51.05, -114.07],
        [50.45, -104.62],
        [49.90, -97.14],
        [49.77, -94.49],
        [48.38, -89.25],
        [46.49, -84.35],
        [43.68, -79.63],
        [45.50, -73.57],
    ],
    "NS_COMPOUND": [
        [49.13, -123.08],
        [50.67, -120.33],
        [51.05, -114.07],
        [50.45, -104.62],
        [49.90, -97.14],
        [49.77, -94.49],
        [48.38, -89.25],
        [46.49, -84.35],
        [43.68, -79.63],
        [45.50, -73.57],
        [46.09, -64.78],
        [44.65, -63.58],
    ],
}


def _route_geometry(
    mode: str,
    origin_id: str,
    destination_id: str,
    locations: dict[str, dict[str, Any]],
) -> list[list[float]]:
    if mode == "OCEAN_RORO":
        return OCEAN_ROUTE
    if mode == "RAIL_AUTORACK" and destination_id in RAIL_CORRIDORS:
        return RAIL_CORRIDORS[destination_id]

    origin = locations.get(origin_id)
    destination = locations.get(destination_id)
    if not origin or not destination:
        return []
    return [
        [origin["latitude"], origin["longitude"]],
        [destination["latitude"], destination["longitude"]],
    ]


def _legacy_movements(
    events: list[dict[str, Any]],
    locations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build movements for runs created before shipments became first-class on every leg."""
    ocean: dict[str, dict[str, Any]] = {}
    rail: dict[str, dict[str, Any]] = {}
    truck: dict[str, dict[str, Any]] = {}
    raw: list[dict[str, Any]] = []

    for event in events:
        typ = event["event_type"]
        eid = event["entity_id"]
        day = float(event["simulation_day"])
        payload = event["payload"] or {}

        if typ == "STARTING_PIPELINE_REGISTERED" and payload.get("expected_arrival_day") is not None:
            raw.append({
                "id": eid,
                "mode": "OCEAN_RORO",
                "origin_id": "CHINA_EXPORT_PORT",
                "destination_id": "VANCOUVER",
                "start_day": -20.0,
                "end_day": float(payload["expected_arrival_day"]),
                "count": int(payload.get("vin_count", 1)),
            })
        elif typ == "VESSEL_DEPARTED":
            ocean[eid] = event
        elif typ == "VESSEL_ARRIVED" and eid in ocean:
            departure = ocean.pop(eid)
            raw.append({
                "id": eid,
                "mode": "OCEAN_RORO",
                "origin_id": departure["location_id"] or "CHINA_EXPORT_PORT",
                "destination_id": event["location_id"] or "VANCOUVER",
                "start_day": float(departure["simulation_day"]),
                "end_day": day,
                "count": int((departure["payload"] or {}).get("vin_count", 1)),
            })
        elif typ == "RAIL_SHIPMENT_DEPARTED":
            rail[eid] = event
        elif typ == "RAIL_SHIPMENT_ARRIVED" and eid in rail:
            departure = rail.pop(eid)
            raw.append({
                "id": eid,
                "mode": "RAIL_AUTORACK",
                "origin_id": departure["location_id"] or "VANCOUVER",
                "destination_id": event["location_id"],
                "start_day": float(departure["simulation_day"]),
                "end_day": day,
                "count": 1,
            })
        elif typ == "TRUCK_DEPARTED":
            truck[eid] = event
        elif typ == "VEHICLE_DELIVERED" and eid in truck:
            departure = truck.pop(eid)
            dealer = payload.get("dealer_id") or event["location_id"]
            raw.append({
                "id": eid,
                "mode": "TRUCK_CARRIER",
                "origin_id": departure["location_id"],
                "destination_id": dealer,
                "start_day": float(departure["simulation_day"]),
                "end_day": day,
                "count": 1,
            })

    for movement in raw:
        movement["route"] = _route_geometry(
            movement["mode"],
            movement["origin_id"],
            movement["destination_id"],
            locations,
        )
    return raw


def _shipment_movements(
    events: list[dict[str, Any]],
    locations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    departures: dict[str, dict[str, Any]] = {}
    movements: list[dict[str, Any]] = []

    departure_types = {
        "VESSEL_DEPARTED": "OCEAN_RORO",
        "RAIL_SHIPMENT_DEPARTED": "RAIL_AUTORACK",
        "TRUCK_DEPARTED": "TRUCK_CARRIER",
    }
    arrival_types = {
        "VESSEL_ARRIVED",
        "RAIL_SHIPMENT_ARRIVED",
        "TRUCK_ARRIVED",
    }

    for event in events:
        typ = event["event_type"]
        eid = event["entity_id"]
        payload = event["payload"] or {}

        if typ in departure_types and event["entity_type"] == "shipment":
            departures[eid] = event
        elif typ in arrival_types and eid in departures:
            departure = departures.pop(eid)
            depart_payload = departure["payload"] or {}
            mode = depart_payload.get("mode") or departure_types[departure["event_type"]]
            origin = depart_payload.get("origin") or departure["location_id"]
            destination = payload.get("destination") or event["location_id"]
            movement = {
                "id": eid,
                "entity_type": "shipment",
                "mode": mode,
                "origin_id": origin,
                "destination_id": destination,
                "start_day": float(departure["simulation_day"]),
                "end_day": float(event["simulation_day"]),
                "count": int(depart_payload.get("vin_count", 1)),
                "configuration_mix": depart_payload.get("configuration_mix", {}),
                "vins": depart_payload.get("vins", []),
            }
            movement["route"] = _route_geometry(
                mode, origin, destination, locations
            )
            movements.append(movement)

    return sorted(movements, key=lambda item: item["start_day"])


def build_replay_payload(run: SimulationRun) -> dict[str, Any]:
    locations = _locations(run)
    events = list(
        run.events.order_by("sequence").values(
            "sequence",
            "simulation_day",
            "event_type",
            "entity_type",
            "entity_id",
            "location_id",
            "correlation_id",
            "payload",
        )
    )

    pressure: list[dict[str, Any]] = []
    markers: list[dict[str, Any]] = []
    quota: list[dict[str, Any]] = []
    sales: list[dict[str, Any]] = []

    marker_types = {
        "CHINA_ORDER_RECOMMENDED",
        "VESSEL_ARRIVED",
        "RAIL_SHIPMENT_ARRIVED",
        "DISTURBANCE_STARTED",
        "DISTURBANCE_ENDED",
        "DISTURBANCE_APPLIED",
        "QUOTA_BLOCKED",
    }

    for event in events:
        day = float(event["simulation_day"])
        typ = event["event_type"]
        eid = event["entity_id"]
        payload = event["payload"] or {}

        if typ == "BACKLOG_CREATED":
            pressure.append({
                "day": day,
                "dealer_id": eid,
                "delta": 1,
            })
        elif typ == "BACKLOG_FULFILLED":
            pressure.append({
                "day": day,
                "dealer_id": payload.get("dealer_id") or event["location_id"],
                "delta": -1,
            })
        elif typ == "EXTERNAL_QUOTA_CONSUMED":
            quota.append({
                "day": day,
                "external_usage": int(payload.get("external_usage", 0)),
            })
        elif typ == "RETAIL_SALE_COMPLETED":
            sales.append({
                "day": day,
                "dealer_id": payload.get("dealer_id") or event["location_id"],
                "vin": eid,
                "configuration_id": payload.get("configuration_id"),
            })

        if typ in marker_types:
            markers.append({
                "day": day,
                "type": typ,
                "entity_id": eid,
                "location_id": event["location_id"],
                "payload": payload,
            })

    movements = _shipment_movements(events, locations)
    if not movements:
        movements = _legacy_movements(events, locations)

    return {
        "run": {
            "id": run.pk,
            "scenario": run.scenario.name,
            "start_date": run.start_date.isoformat(),
            "end_date": run.end_date.isoformat(),
            "duration_days": (run.end_date - run.start_date).days,
            "seed": run.seed,
            "digest": run.event_digest,
            "summary": run.summary,
        },
        "locations": list(locations.values()),
        "movements": movements,
        "pressure_events": pressure,
        "markers": markers,
        "quota_series": quota,
        "sales": sales,
    }


def _state_at_day(run: SimulationRun, day: float) -> dict[str, Any]:
    catalog = _configuration_catalog(run)
    locations = _locations(run)
    vehicles: dict[str, dict[str, Any]] = {}
    shipments: dict[str, dict[str, Any]] = {}
    backlog: dict[str, Counter] = defaultdict(Counter)
    open_orders: dict[str, Counter] = defaultdict(Counter)

    events = run.events.filter(simulation_day__lte=day).order_by("sequence")

    def vehicle(vin: str) -> dict[str, Any]:
        return vehicles.setdefault(
            vin,
            {
                "vin": vin,
                "configuration_id": None,
                "logistics_status": "UNKNOWN",
                "allocation_status": "UNALLOCATED",
                "allocated_dealer_id": None,
                "location_id": None,
                "shipment_id": None,
                "sold": False,
            },
        )

    for event in events.iterator(chunk_size=2000):
        payload = event.payload or {}
        typ = event.event_type
        eid = event.entity_id

        if typ == "WARM_START_VEHICLE":
            item = vehicle(eid)
            item.update({
                "configuration_id": payload.get("configuration_id"),
                "logistics_status": "DEALER",
                "allocation_status": "ALLOCATED",
                "allocated_dealer_id": payload.get("dealer_id"),
                "location_id": event.location_id,
            })

        elif typ == "VIN_CREATED":
            item = vehicle(eid)
            item.update({
                "configuration_id": payload.get("configuration_id"),
                "logistics_status": "FACTORY_COMPLETE",
                "location_id": event.location_id or "CHINA_FACTORY",
            })

        elif typ == "VIN_ALLOCATED":
            item = vehicle(eid)
            item["allocation_status"] = "ALLOCATED"
            item["allocated_dealer_id"] = payload.get("dealer_id")

        elif typ == "EXPORT_STAGING_COMPLETED":
            for vin in payload.get("vins", []):
                item = vehicle(vin)
                item["logistics_status"] = "EXPORT_YARD"
                item["location_id"] = event.location_id or "CHINA_EXPORT_PORT"

        elif typ in {"STARTING_PIPELINE_REGISTERED", "VESSEL_DEPARTED"}:
            shipment_id = eid
            vins = payload.get("vins", [])
            shipments[shipment_id] = {
                "id": shipment_id,
                "mode": payload.get("mode", "OCEAN_RORO"),
                "origin_id": payload.get("origin", "CHINA_EXPORT_PORT"),
                "destination_id": payload.get("destination", "VANCOUVER"),
                "vins": vins,
                "start_day": payload.get("planned_departure_day", event.simulation_day),
                "end_day": payload.get("planned_arrival_day"),
                "status": "IN_TRANSIT",
                "configuration_mix": payload.get("configuration_mix", {}),
            }
            vin_configs = payload.get("vin_configurations", {})
            for vin in vins:
                item = vehicle(vin)
                if not item.get("configuration_id"):
                    item["configuration_id"] = vin_configs.get(vin)
                item["logistics_status"] = "OCEAN"
                item["shipment_id"] = shipment_id
                item["location_id"] = None

        elif typ == "VESSEL_ARRIVED":
            shipment = shipments.get(eid)
            if shipment:
                shipment["status"] = "ARRIVED"
                shipment["end_day"] = event.simulation_day
                for vin in shipment["vins"]:
                    item = vehicle(vin)
                    item["logistics_status"] = "PORT_DWELL"
                    item["location_id"] = event.location_id or "VANCOUVER"
                    item["shipment_id"] = None

        elif typ == "VEHICLES_CLEARED":
            for vin in payload.get("vins", []):
                item = vehicle(vin)
                item["logistics_status"] = "CANADIAN_COMPOUND"
                item["location_id"] = event.location_id or "VANCOUVER"

        elif typ in {"RAIL_SHIPMENT_DEPARTED", "TRUCK_DEPARTED"}:
            shipment_id = eid
            vins = payload.get("vins", [])
            mode = payload.get(
                "mode",
                "RAIL_AUTORACK"
                if typ == "RAIL_SHIPMENT_DEPARTED"
                else "TRUCK_CARRIER",
            )
            status = "RAIL" if mode == "RAIL_AUTORACK" else "TRUCK"
            shipments[shipment_id] = {
                "id": shipment_id,
                "mode": mode,
                "origin_id": payload.get("origin") or event.location_id,
                "destination_id": payload.get("destination"),
                "vins": vins,
                "start_day": event.simulation_day,
                "end_day": payload.get("planned_arrival_day"),
                "status": "IN_TRANSIT",
                "configuration_mix": payload.get("configuration_mix", {}),
            }
            vin_configs = payload.get("vin_configurations", {})
            for vin in vins:
                item = vehicle(vin)
                if not item.get("configuration_id"):
                    item["configuration_id"] = vin_configs.get(vin)
                item["logistics_status"] = status
                item["shipment_id"] = shipment_id
                item["location_id"] = None

        elif typ in {"RAIL_SHIPMENT_ARRIVED", "TRUCK_ARRIVED"}:
            shipment = shipments.get(eid)
            if shipment:
                shipment["status"] = "ARRIVED"
                shipment["end_day"] = event.simulation_day
                status = (
                    "REGIONAL_COMPOUND"
                    if typ == "RAIL_SHIPMENT_ARRIVED"
                    else "DEALER"
                )
                for vin in shipment["vins"]:
                    item = vehicle(vin)
                    item["logistics_status"] = status
                    item["location_id"] = event.location_id
                    item["shipment_id"] = None

        elif typ == "VEHICLE_DELIVERED":
            item = vehicle(eid)
            dealer_id = payload.get("dealer_id") or event.location_id
            config_id = payload.get("configuration_id")
            item["logistics_status"] = "DEALER"
            item["location_id"] = dealer_id
            item["shipment_id"] = None
            if dealer_id and config_id and open_orders[dealer_id][config_id] > 0:
                open_orders[dealer_id][config_id] -= 1

        elif typ == "RETAIL_SALE_COMPLETED":
            item = vehicle(eid)
            item["sold"] = True
            item["logistics_status"] = "RETAIL_SOLD"
            item["location_id"] = payload.get("dealer_id") or event.location_id

        elif typ == "DEALER_ORDER_CREATED":
            dealer_id = payload.get("dealer_id") or event.location_id
            config_id = payload.get("configuration_id")
            if dealer_id and config_id:
                open_orders[dealer_id][config_id] += int(payload.get("quantity", 0))

        if typ == "BACKLOG_CREATED":
            config_id = payload.get("configuration_id")
            if config_id:
                backlog[eid][config_id] += 1
        elif typ == "BACKLOG_FULFILLED":
            dealer_id = payload.get("dealer_id") or event.location_id
            config_id = payload.get("configuration_id")
            if dealer_id and config_id and backlog[dealer_id][config_id] > 0:
                backlog[dealer_id][config_id] -= 1

    # Derive configuration metadata once so every inspector can use the same shape.
    for item in vehicles.values():
        item["configuration"] = catalog.get(item["configuration_id"], {})

    return {
        "vehicles": vehicles,
        "shipments": shipments,
        "backlog": backlog,
        "open_orders": open_orders,
        "catalog": catalog,
        "locations": locations,
    }


def inspect_entity(
    run: SimulationRun,
    day: float,
    entity_type: str,
    entity_id: str,
) -> dict[str, Any]:
    state = _state_at_day(run, day)
    vehicles = state["vehicles"]
    catalog = state["catalog"]

    if entity_type == "shipment":
        shipment = state["shipments"].get(entity_id)
        if not shipment:
            return {
                "kind": "shipment",
                "id": entity_id,
                "missing": True,
                "day": day,
            }
        contents = [vehicles[vin] for vin in shipment["vins"] if vin in vehicles]
        mix = Counter(item["configuration_id"] for item in contents)
        shipment = dict(shipment)
        shipment["kind"] = "shipment"
        shipment["day"] = day
        shipment["vehicle_count"] = len(contents)
        shipment["configuration_mix"] = [
            {
                "configuration_id": config_id,
                "configuration": catalog.get(config_id, {}),
                "count": count,
            }
            for config_id, count in sorted(mix.items())
        ]
        shipment["vehicles"] = contents[:250]
        shipment["vehicle_list_truncated"] = len(contents) > 250
        return shipment

    if entity_type == "location":
        location = state["locations"].get(entity_id)
        if not location:
            return {
                "kind": "location",
                "id": entity_id,
                "missing": True,
                "day": day,
            }

        present = [
            item
            for item in vehicles.values()
            if item["location_id"] == entity_id and not item["sold"]
        ]
        mix = Counter(item["configuration_id"] for item in present)
        result = {
            **location,
            "kind": "location",
            "day": day,
            "vehicle_count": len(present),
            "configuration_mix": [
                {
                    "configuration_id": config_id,
                    "configuration": catalog.get(config_id, {}),
                    "count": count,
                }
                for config_id, count in sorted(mix.items())
            ],
            "vehicles": present[:250],
            "vehicle_list_truncated": len(present) > 250,
        }

        if location.get("kind") == "DEALER":
            result["backlog_units"] = sum(state["backlog"][entity_id].values())
            result["open_order_units"] = sum(
                state["open_orders"][entity_id].values()
            )
            result["backlog_by_configuration"] = dict(
                state["backlog"][entity_id]
            )
            result["open_orders_by_configuration"] = dict(
                state["open_orders"][entity_id]
            )
            result["inbound_allocated"] = sum(
                1
                for item in vehicles.values()
                if item["allocated_dealer_id"] == entity_id
                and item["logistics_status"]
                not in {"DEALER", "RETAIL_SOLD"}
            )
        return result

    if entity_type == "vin":
        item = vehicles.get(entity_id)
        if not item:
            return {
                "kind": "vin",
                "id": entity_id,
                "missing": True,
                "day": day,
            }
        history = list(
            run.events.filter(
                entity_id=entity_id,
                simulation_day__lte=day,
            )
            .order_by("sequence")
            .values(
                "simulation_day",
                "event_type",
                "location_id",
                "correlation_id",
                "payload",
            )
        )
        return {
            "kind": "vin",
            "day": day,
            **item,
            "history": history[-40:],
        }

    return {
        "kind": entity_type,
        "id": entity_id,
        "missing": True,
        "day": day,
    }
