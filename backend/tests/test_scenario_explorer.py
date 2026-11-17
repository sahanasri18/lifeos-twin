import pytest
from pydantic import ValidationError
from app.models.scenario_explorer import WhatIfRequest
from app.services.scenario_explorer import explore_scenarios


def payload():
    return {"options": [
        {"option_id": "reference", "label": "Current plan", "scenario": {"district_id": "NORTH", "population_change_percent": 0}},
        {"option_id": "growth", "label": "Population growth", "scenario": {"district_id": "NORTH", "population_change_percent": 20}},
        {"option_id": "green", "label": "Green space", "scenario": {"district_id": "NORTH", "green_space_change_percent": 30}},
    ]}


def test_explorer_returns_all_options_and_reference_deltas():
    result = explore_scenarios(WhatIfRequest(**payload()))
    assert len(result["options"]) == 3
    assert result["reference_option_id"] == "reference"
    assert result["options"][0]["deltas"]["water"]["difference_from_first"] == 0
    assert result["options"][1]["deltas"]["water"]["difference_from_first"] > 0


def test_explorer_is_deterministic():
    request = WhatIfRequest(**payload())
    assert explore_scenarios(request) == explore_scenarios(request)


def test_explorer_rejects_duplicate_ids():
    data = payload(); data["options"][1]["option_id"] = "reference"
    with pytest.raises(ValidationError):
        WhatIfRequest(**data)


def test_explorer_requires_same_district():
    data = payload(); data["options"][1]["scenario"]["district_id"] = "EAST"
    with pytest.raises(ValidationError):
        WhatIfRequest(**data)


def test_explorer_requires_two_to_six_options():
    data = payload(); data["options"] = data["options"][:1]
    with pytest.raises(ValidationError):
        WhatIfRequest(**data)


def test_explorer_rejects_out_of_range_inputs():
    data = payload(); data["options"][1]["scenario"]["population_change_percent"] = 500
    with pytest.raises(ValidationError):
        WhatIfRequest(**data)
