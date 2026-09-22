from pathlib import Path

from dealerflow.simulation import DealerFlowSimulation


SCENARIO = Path(__file__).parents[1] / "scenarios" / "quota_year_baseline.yaml"


def run_baseline():
    return DealerFlowSimulation.from_yaml(SCENARIO).run()


def test_same_seed_produces_same_event_log() -> None:
    first = run_baseline()
    second = run_baseline()
    assert first.digest == second.digest
    assert first.summary == second.summary


def test_baseline_exercises_core_workflows() -> None:
    result = run_baseline()
    event_types = {event.event_type for event in result.events}
    expected = {
        "DEMAND_OCCURRED",
        "DEALER_ORDER_CREATED",
        "CHINA_ORDER_RECOMMENDED",
        "VIN_CREATED",
        "VIN_ALLOCATED",
        "VESSEL_ARRIVED",
        "VEHICLE_DELIVERED",
    }
    assert expected <= event_types
    assert result.summary["events"] > 0
    assert 0 <= result.summary["fill_rate"] <= 1


def test_generated_vins_are_unique_and_seventeen_characters() -> None:
    simulation = DealerFlowSimulation.from_yaml(SCENARIO)
    simulation.run()
    vins = list(simulation.vehicles)
    assert len(vins) == len(set(vins))
    assert all(len(vin) == 17 for vin in vins)
