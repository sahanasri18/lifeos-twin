import pytest

from app.models.scenario import ScenarioRequest
from app.services.simulation import simulate_scenario


def test_zero_change_preserves_baseline():
    result = simulate_scenario(ScenarioRequest(district_id="NORTH"))
    assert result.traffic.baseline == result.traffic.projected == 6200
    assert result.water.baseline == result.water.projected == 2700
    assert result.electricity.baseline == result.electricity.projected == 92
    assert result.risk_level == "low"


def test_population_growth_increases_all_three_demands():
    result = simulate_scenario(
        ScenarioRequest(district_id="NORTH", population_change_percent=25)
    )
    assert result.traffic.projected > result.traffic.baseline
    assert result.water.projected > result.water.baseline
    assert result.electricity.projected > result.electricity.baseline
    assert result.water.change_percent == 22.5


def test_commercial_growth_increases_traffic_and_electricity():
    result = simulate_scenario(
        ScenarioRequest(district_id="CENTRAL", commercial_growth_percent=20)
    )
    assert result.traffic.projected > result.traffic.baseline
    assert result.electricity.projected > result.electricity.baseline
    assert result.water.projected > result.water.baseline


def test_district_id_is_normalized():
    result = simulate_scenario(ScenarioRequest(district_id=" east "))
    assert result.district_id == "EAST"


def test_unknown_district_is_rejected():
    with pytest.raises(ValueError, match="Unknown district"):
        simulate_scenario(ScenarioRequest(district_id="MOON"))


def test_inputs_outside_allowed_range_are_rejected():
    with pytest.raises(ValueError):
        ScenarioRequest(district_id="NORTH", population_change_percent=500)
