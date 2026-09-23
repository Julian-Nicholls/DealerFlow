from pathlib import Path

from dealerflow.config import load_scenario


SCENARIO = Path(__file__).parents[1] / "scenarios" / "quota_year_baseline.yaml"


def test_baseline_scenario_loads() -> None:
    scenario = load_scenario(SCENARIO)
    assert scenario.duration_days == 365
    assert scenario.quota.national_limit == 49_000
    assert len(scenario.dealers) == 15
    assert len(scenario.vehicle_configurations) == 6
    assert scenario.logistics.ocean_batch_capacity == 600
    assert scenario.logistics.ocean_min_dispatch == 120
    assert scenario.logistics.rail_batch_capacity == 180
    assert scenario.logistics.truck_batch_capacity == 8
