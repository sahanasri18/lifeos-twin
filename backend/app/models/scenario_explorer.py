from pydantic import BaseModel, Field, field_validator
from app.models.scenario import ScenarioRequest


class WhatIfOption(BaseModel):
    option_id: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    label: str = Field(min_length=1, max_length=80)
    scenario: ScenarioRequest


class WhatIfRequest(BaseModel):
    options: list[WhatIfOption] = Field(min_length=2, max_length=6)

    @field_validator("options")
    @classmethod
    def unique_option_ids(cls, options):
        ids = [item.option_id for item in options]
        if len(ids) != len(set(ids)):
            raise ValueError("Option IDs must be unique.")
        districts = {item.scenario.district_id for item in options}
        if len(districts) != 1:
            raise ValueError("All options must use the same district for a fair comparison.")
        return options
