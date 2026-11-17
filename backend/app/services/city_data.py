"""Synthetic Nova City baseline data. Values are illustrative, not real measurements."""

CITY_NAME = "Nova City"
DATA_LABEL = "synthetic_demo_data"

DISTRICTS: dict[str, dict[str, float | str]] = {
    "NORTH": {
        "name": "North Quarter",
        "population": 18000,
        "daily_vehicles": 6200,
        "daily_water_m3": 2700,
        "daily_electricity_mwh": 92,
        "green_space_percent": 18,
        "commercial_share_percent": 25,
    },
    "CENTRAL": {
        "name": "Central District",
        "population": 26000,
        "daily_vehicles": 11800,
        "daily_water_m3": 4300,
        "daily_electricity_mwh": 176,
        "green_space_percent": 9,
        "commercial_share_percent": 62,
    },
    "EAST": {
        "name": "East Gardens",
        "population": 15000,
        "daily_vehicles": 4800,
        "daily_water_m3": 2250,
        "daily_electricity_mwh": 76,
        "green_space_percent": 27,
        "commercial_share_percent": 18,
    },
    "SOUTH": {
        "name": "South Works",
        "population": 21000,
        "daily_vehicles": 9100,
        "daily_water_m3": 3350,
        "daily_electricity_mwh": 210,
        "green_space_percent": 12,
        "commercial_share_percent": 48,
    },
    "WEST": {
        "name": "West Riverside",
        "population": 12000,
        "daily_vehicles": 3900,
        "daily_water_m3": 1900,
        "daily_electricity_mwh": 65,
        "green_space_percent": 31,
        "commercial_share_percent": 15,
    },
}
