import pytest
from pydantic import ValidationError
from app.models.forecast import ForecastRequest
from app.services.forecast_service import forecast_scenario


def request_payload(**overrides):
    payload = {
        "scenario": {"district_id": "CENTRAL", "population_change_percent": 20},
        "years": 5,
        "traffic_annual_growth_percent": 2,
        "water_annual_growth_percent": 2.5,
        "electricity_annual_growth_percent": 3,
    }
    payload.update(overrides)
    return payload


def test_forecast_returns_year_zero_through_horizon():
    result = forecast_scenario(ForecastRequest(**request_payload()))
    assert len(result["timeline"]) == 6
    assert [row["year"] for row in result["timeline"]] == list(range(6))
    assert result["timeline"][0]["metrics"]["traffic"]["projected"] == result["scenario_start"]["traffic"]["projected"]


def test_forecast_uses_compound_growth_and_is_monotonic_for_positive_rate():
    result = forecast_scenario(ForecastRequest(**request_payload(years=3)))
    values = [row["metrics"]["water"]["projected"] for row in result["timeline"]]
    assert values[0] < values[1] < values[2] < values[3]
    assert values[3] == round(values[0] * (1.025 ** 3), 2)


def test_zero_growth_keeps_metric_constant():
    result = forecast_scenario(ForecastRequest(**request_payload(
        years=4, traffic_annual_growth_percent=0,
        water_annual_growth_percent=0, electricity_annual_growth_percent=0,
    )))
    for metric in ("traffic", "water", "electricity"):
        values = [row["metrics"][metric]["projected"] for row in result["timeline"]]
        assert len(set(values)) == 1


def test_negative_growth_decreases_projection():
    result = forecast_scenario(ForecastRequest(**request_payload(years=2, traffic_annual_growth_percent=-5)))
    values = [row["metrics"]["traffic"]["projected"] for row in result["timeline"]]
    assert values[2] < values[1] < values[0]


def test_forecast_is_deterministic():
    request = ForecastRequest(**request_payload())
    assert forecast_scenario(request) == forecast_scenario(request)


@pytest.mark.parametrize("years", [0, 11, -1])
def test_rejects_forecast_horizon_out_of_range(years):
    with pytest.raises(ValidationError):
        ForecastRequest(**request_payload(years=years))


@pytest.mark.parametrize("field", ["traffic_annual_growth_percent", "water_annual_growth_percent", "electricity_annual_growth_percent"])
def test_rejects_unreasonable_growth_assumptions(field):
    with pytest.raises(ValidationError):
        ForecastRequest(**request_payload(**{field: 51}))


def test_rejects_unknown_district():
    with pytest.raises(ValueError, match="Unknown district"):
        forecast_scenario(ForecastRequest(**request_payload(scenario={"district_id": "MARS"})))
