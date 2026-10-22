import re
from urllib.parse import urlparse

import pytest

from weather.client import WeatherUnavailable

SYDNEY = {
    "latitude": "-33.8688",
    "longitude": "151.2093",
    "name": "Sydney",
    "region": "New South Wales",
    "country": "Australia",
}

# UTC+10. These UTC instants fall on the previous local day when the offset is ignored.
OFFSET = 36000
WEDNESDAY_EVENING = 1792584000  # Wed 21 Oct 2026 22:00 local, Wed 12:00 UTC
THURSDAY_NIGHT = 1792594800  # Thu 22 Oct 2026 01:00 local, Wed 15:00 UTC
THURSDAY_EARLY = 1792605600  # Thu 22 Oct 2026 04:00 local, Wed 18:00 UTC
THURSDAY_NOON = 1792634400  # Thu 22 Oct 2026 12:00 local, Thu 02:00 UTC
SUNRISE = 1792615320  # Thu 22 Oct 2026 06:42 local, Wed 20:42 UTC
SUNSET = 1792656900  # Thu 22 Oct 2026 18:15 local, Thu 08:15 UTC

CURRENT = {
    "timezone": OFFSET,
    "main": {
        "temp": 17.0,
        "feels_like": 16.0,
        "humidity": 55,
        "pressure": 1016,
    },
    "wind": {"speed": 4.0},
    "clouds": {"all": 20},
    "weather": [{"description": "broken clouds"}],
    "sys": {"sunrise": SUNRISE, "sunset": SUNSET},
}

FORECAST = {
    "timezone": OFFSET,
    "list": [
        {
            "dt": WEDNESDAY_EVENING,
            "main": {"temp": 10.0},
            "weather": [{"description": "clear sky"}],
        },
        {
            "dt": THURSDAY_NIGHT,
            "main": {"temp": 20.0},
            "weather": [{"description": "rain"}],
        },
        {
            "dt": THURSDAY_EARLY,
            "main": {"temp": 5.0},
            "weather": [{"description": "snow"}],
        },
        {
            "dt": THURSDAY_NOON,
            "main": {"temp": 15.0},
            "weather": [{"description": "few clouds"}],
        },
    ],
}


def _assert_day(
    body: str, heading: str, condition: str, average: str, high: str, low: str
) -> None:
    pattern = (
        rf"<h2>\s*{re.escape(heading)}\s*</h2>[\s\S]*?"
        rf"{re.escape(condition)}[\s\S]*?"
        rf'class="day-temp">{re.escape(average)}</p>[\s\S]*?'
        rf"High {re.escape(high)}[\s\S]*?"
        rf"Low {re.escape(low)}"
    )
    assert re.search(pattern, body), (
        f"expected a day card for {heading} with {condition}, "
        f"{average}, High {high}, Low {low}"
    )


@pytest.mark.django_db
def test_forecast_uses_the_place_timezone_offset(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str) -> dict:
        if urlparse(url).path.endswith("/forecast"):
            return FORECAST
        return CURRENT

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/", SYDNEY)
    body = response.content.decode()
    assert response.status_code == 200
    _assert_day(body, "Wed, Oct 21", "clear sky", "10°C", "10°C", "10°C")
    _assert_day(body, "Thu, Oct 22", "few clouds", "13°C", "20°C", "5°C")
    assert "Sunrise Thu, Oct 22, 6:42 AM" in body
    assert "Sunset Thu, Oct 22, 6:15 PM" in body


@pytest.mark.django_db
def test_hourly_forecast_uses_local_time(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    _stub_sydney(monkeypatch)

    response = client.get("/", SYDNEY)
    body = response.content.decode()
    assert response.status_code == 200
    assert 'aria-label="Hourly forecast"' in body
    assert 'title="Wed, Oct 21, 10:00 PM, 10°C, clear sky"' in body
    assert 'title="Thu, Oct 22, 1:00 AM, 20°C, rain"' in body
    assert ">10 PM<" in body
    assert ">1 AM<" in body


@pytest.mark.django_db
def test_failed_lookup_keeps_the_local_forecast(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str) -> dict:
        query_latitude = float(urlparse(url).query.split("lat=")[1].split("&")[0])
        if abs(query_latitude - (-33.8688)) > 1e-3:
            raise WeatherUnavailable("down")
        if urlparse(url).path.endswith("/forecast"):
            return FORECAST
        return CURRENT

    monkeypatch.setattr("weather.client.request_json", request_json)

    client.get("/", SYDNEY)
    response = client.get(
        "/",
        {
            "latitude": "51.5074",
            "longitude": "-0.1278",
            "name": "London",
            "region": "",
            "country": "United Kingdom",
        },
    )
    body = response.content.decode()
    assert "Weather could not be loaded." in body
    _assert_day(body, "Wed, Oct 21", "clear sky", "10°C", "10°C", "10°C")
    assert "Sunrise Thu, Oct 22, 6:42 AM" in body
    shown = body.split('<div class="search-wrap">', 1)[1]
    assert "London" not in shown


def _stub_sydney(monkeypatch) -> None:
    def request_json(url: str) -> dict:
        if urlparse(url).path.endswith("/forecast"):
            return FORECAST
        return CURRENT

    monkeypatch.setattr("weather.client.request_json", request_json)
