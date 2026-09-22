from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class LogisticsStatus(StrEnum):
    IN_PRODUCTION = "IN_PRODUCTION"
    FACTORY_COMPLETE = "FACTORY_COMPLETE"
    EXPORT_YARD = "EXPORT_YARD"
    OCEAN = "OCEAN"
    PORT_DWELL = "PORT_DWELL"
    CANADIAN_COMPOUND = "CANADIAN_COMPOUND"
    RAIL = "RAIL"
    REGIONAL_COMPOUND = "REGIONAL_COMPOUND"
    TRUCK = "TRUCK"
    DEALER = "DEALER"
    QUOTA_BLOCKED = "QUOTA_BLOCKED"


class AllocationStatus(StrEnum):
    UNALLOCATED = "UNALLOCATED"
    ALLOCATED = "ALLOCATED"
    RELEASED = "RELEASED"


@dataclass(slots=True)
class DealerState:
    dealer_id: str
    inventory: dict[str, list[str]] = field(default_factory=dict)
    backlog: dict[str, int] = field(default_factory=dict)
    open_orders: dict[str, int] = field(default_factory=dict)
    sales: int = 0
    demand: int = 0
    lost_sales: int = 0


@dataclass(slots=True)
class Vehicle:
    vin: str
    configuration_id: str
    created_day: float
    logistics_status: LogisticsStatus
    allocation_status: AllocationStatus = AllocationStatus.UNALLOCATED
    allocated_dealer_id: str | None = None
    allocated_day: float | None = None


@dataclass(slots=True)
class Shipment:
    id: str
    mode: str
    number: int
    origin: str
    destination: str
    vins: list[str]
    planned_departure_day: float
    planned_arrival_day: float
    actual_departure_day: float | None = None
    actual_arrival_day: float | None = None
