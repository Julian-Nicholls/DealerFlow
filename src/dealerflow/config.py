from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


class DealerConfig(BaseModel):
    id: str
    name: str
    city: str
    province: str
    latitude: float
    longitude: float
    demand_scale: float = Field(gt=0)
    target_weeks_of_supply: float = Field(default=6.0, gt=0)


class VehicleConfigurationConfig(BaseModel):
    id: str
    model: str
    trim: str
    exterior_colour: str
    interior_colour: str
    daily_demand_weight: float = Field(gt=0)


class QuotaConfig(BaseModel):
    enabled: bool = True
    national_limit: int = Field(default=49_000, ge=0)
    initial_external_usage: int = Field(default=0, ge=0)
    external_daily_mean: float = Field(default=60.0, ge=0)


class PlanningConfig(BaseModel):
    dealer_replenishment_cycle_days: int = Field(default=7, ge=1)
    china_order_cycle_days: int = Field(default=28, ge=1)
    allocation_cycle_days: int = Field(default=1, ge=1)


class LogisticsConfig(BaseModel):
    production_days: tuple[int, int, int] = (21, 35, 49)
    export_staging_days: tuple[int, int, int] = (3, 7, 14)
    ocean_days: tuple[int, int, int] = (15, 20, 30)
    port_dwell_days: tuple[int, int, int] = (2, 5, 12)
    rail_days: tuple[int, int, int] = (7, 10, 18)
    truck_days: tuple[int, int, int] = (1, 3, 7)
    batch_capacity: int = Field(default=600, ge=1)

    @model_validator(mode="after")
    def validate_triangles(self) -> "LogisticsConfig":
        for name in (
            "production_days",
            "export_staging_days",
            "ocean_days",
            "port_dwell_days",
            "rail_days",
            "truck_days",
        ):
            low, mode, high = getattr(self, name)
            if not low <= mode <= high:
                raise ValueError(f"{name} must satisfy low <= mode <= high")
            if low < 0:
                raise ValueError(f"{name} cannot contain negative durations")
        return self


class DemandSpikeConfig(BaseModel):
    type: Literal["demand_spike"]
    start_day: int = Field(ge=0)
    duration_days: int = Field(ge=1)
    dealer_id: str | None = None
    province: str | None = None
    configuration_id: str | None = None
    multiplier: float = Field(gt=0)


class VesselDelayConfig(BaseModel):
    type: Literal["vessel_delay"]
    shipment_number: int = Field(ge=1)
    delay_days: int = Field(ge=1)


DisturbanceConfig = DemandSpikeConfig | VesselDelayConfig


class ScenarioConfig(BaseModel):
    name: str
    start_date: date
    end_date: date
    seed: int
    dealers: list[DealerConfig]
    vehicle_configurations: list[VehicleConfigurationConfig]
    quota: QuotaConfig = Field(default_factory=QuotaConfig)
    planning: PlanningConfig = Field(default_factory=PlanningConfig)
    logistics: LogisticsConfig = Field(default_factory=LogisticsConfig)
    disturbances: list[DisturbanceConfig] = Field(default_factory=list)
    warm_start_weeks: int = Field(default=6, ge=1)

    @model_validator(mode="after")
    def validate_scenario(self) -> "ScenarioConfig":
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        dealer_ids = [dealer.id for dealer in self.dealers]
        if len(set(dealer_ids)) != len(dealer_ids):
            raise ValueError("dealer ids must be unique")
        config_ids = [config.id for config in self.vehicle_configurations]
        if len(set(config_ids)) != len(config_ids):
            raise ValueError("vehicle configuration ids must be unique")
        return self

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days


def load_scenario(path: str | Path) -> ScenarioConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return ScenarioConfig.model_validate(data)
