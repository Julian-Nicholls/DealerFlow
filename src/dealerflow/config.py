from __future__ import annotations
from datetime import date
from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel,Field,model_validator

class FacilityConfig(BaseModel):
    id:str; name:str; kind:str
    latitude:float=Field(ge=-90,le=90); longitude:float=Field(ge=-180,le=180)

class DealerConfig(BaseModel):
    id:str; name:str; city:str; province:str
    latitude:float=Field(ge=-90,le=90); longitude:float=Field(ge=-180,le=180)
    demand_scale:float=Field(gt=0); target_weeks_of_supply:float=Field(default=6.0,gt=0)

class VehicleConfigurationConfig(BaseModel):
    id:str; model:str; trim:str; exterior_colour:str; interior_colour:str; daily_demand_weight:float=Field(gt=0)

class QuotaConfig(BaseModel):
    enabled:bool=True; national_limit:int=Field(default=49000,ge=0); initial_external_usage:int=Field(default=0,ge=0); external_daily_mean:float=Field(default=60.0,ge=0)

class PlanningConfig(BaseModel):
    dealer_replenishment_cycle_days:int=Field(default=7,ge=1)
    china_order_cycle_days:int=Field(default=28,ge=1)
    allocation_cycle_days:int=Field(default=1,ge=1)

class LogisticsConfig(BaseModel):
    production_days:tuple[int,int,int]=(21,35,49)
    export_staging_days:tuple[int,int,int]=(3,7,14)
    ocean_days:tuple[int,int,int]=(15,20,30)
    port_dwell_days:tuple[int,int,int]=(2,5,12)
    rail_days:tuple[int,int,int]=(7,10,18)
    truck_days:tuple[int,int,int]=(1,3,7)

    # DealerFlow fleet share aboard a larger real-world sailing.
    ocean_batch_capacity:int=Field(default=600,ge=1)
    ocean_min_dispatch:int=Field(default=120,ge=1)
    ocean_dispatch_interval_days:int=Field(default=7,ge=1)
    ocean_max_wait_days:int=Field(default=14,ge=1)

    # Domestic consolidation. A displayed rail/truck icon is a logical load.
    rail_batch_capacity:int=Field(default=180,ge=1)
    rail_min_dispatch:int=Field(default=24,ge=1)
    rail_dispatch_interval_days:int=Field(default=2,ge=1)
    rail_max_wait_days:int=Field(default=5,ge=1)

    truck_batch_capacity:int=Field(default=8,ge=1)
    truck_dispatch_interval_days:int=Field(default=1,ge=1)
    truck_max_wait_days:int=Field(default=2,ge=1)

    @model_validator(mode="after")
    def validate_logistics(self):
        for name in ("production_days","export_staging_days","ocean_days","port_dwell_days","rail_days","truck_days"):
            low,mode,high=getattr(self,name)
            if not low<=mode<=high or low<0:
                raise ValueError(f"{name} must satisfy 0 <= low <= mode <= high")
        if self.ocean_min_dispatch>self.ocean_batch_capacity:
            raise ValueError("ocean_min_dispatch cannot exceed ocean_batch_capacity")
        if self.rail_min_dispatch>self.rail_batch_capacity:
            raise ValueError("rail_min_dispatch cannot exceed rail_batch_capacity")
        return self

class DemandSpikeConfig(BaseModel):
    type:Literal["demand_spike"]; start_day:int=Field(ge=0); duration_days:int=Field(ge=1)
    dealer_id:str|None=None; province:str|None=None; configuration_id:str|None=None; multiplier:float=Field(gt=0)

class VesselDelayConfig(BaseModel):
    type:Literal["vessel_delay"]; shipment_number:int=Field(ge=1); delay_days:int=Field(ge=1)

DisturbanceConfig=DemandSpikeConfig|VesselDelayConfig

class ScenarioConfig(BaseModel):
    name:str; start_date:date; end_date:date; seed:int
    facilities:list[FacilityConfig]=Field(default_factory=list)
    dealers:list[DealerConfig]
    vehicle_configurations:list[VehicleConfigurationConfig]
    quota:QuotaConfig=Field(default_factory=QuotaConfig)
    planning:PlanningConfig=Field(default_factory=PlanningConfig)
    logistics:LogisticsConfig=Field(default_factory=LogisticsConfig)
    disturbances:list[DisturbanceConfig]=Field(default_factory=list)
    warm_start_weeks:int=Field(default=6,ge=1)

    @model_validator(mode="after")
    def validate_scenario(self):
        if self.end_date<=self.start_date:
            raise ValueError("end_date must be after start_date")
        dealer_ids=[x.id for x in self.dealers]
        facility_ids=[x.id for x in self.facilities]
        config_ids=[x.id for x in self.vehicle_configurations]
        if len(set(dealer_ids))!=len(dealer_ids):
            raise ValueError("dealer ids must be unique")
        if len(set(facility_ids))!=len(facility_ids):
            raise ValueError("facility ids must be unique")
        if set(dealer_ids)&set(facility_ids):
            raise ValueError("dealer and facility ids must not collide")
        if len(set(config_ids))!=len(config_ids):
            raise ValueError("vehicle configuration ids must be unique")
        return self

    @property
    def duration_days(self):
        return (self.end_date-self.start_date).days

def parse_scenario(text:str)->ScenarioConfig:
    return ScenarioConfig.model_validate(yaml.safe_load(text))

def load_scenario(path:str|Path)->ScenarioConfig:
    return parse_scenario(Path(path).read_text(encoding="utf-8"))
