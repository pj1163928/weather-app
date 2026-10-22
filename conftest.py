import copy

import pytest

CHICAGO_CURRENT = {
    "timezone": -18000,
    "main": {
        "temp": 21.0,
        "feels_like": 19.0,
        "humidity": 60,
        "pressure": 1013,
    },
    "wind": {"speed": 3.5},
    "clouds": {"all": 12},
    "weather": [{"description": "clear sky"}],
    "sys": {"sunrise": 1729515600, "sunset": 1729555200},
}

CHICAGO_FORECAST = {
    "timezone": -18000,
    "list": [
        {
            "dt": 1729512000,
            "main": {"temp": 21.0},
            "weather": [{"description": "clear sky"}],
        }
    ],
}

CHICAGO_GEOCODE = [
    {
        "name": "Chicago",
        "lat": 41.8781,
        "lon": -87.6298,
        "country": "US",
        "state": "Illinois",
    }
]


@pytest.fixture
def chicago_current():
    return copy.deepcopy(CHICAGO_CURRENT)


@pytest.fixture
def chicago_forecast():
    return copy.deepcopy(CHICAGO_FORECAST)


@pytest.fixture
def chicago_geocode():
    return copy.deepcopy(CHICAGO_GEOCODE)
