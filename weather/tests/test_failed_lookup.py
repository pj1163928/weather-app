from urllib.parse import parse_qs, urlparse

import pytest

from weather.client import WeatherUnavailable

CHICAGO = {
    "latitude": "41.8781",
    "longitude": "-87.6298",
    "name": "Chicago",
    "region": "Illinois",
    "country": "United States",
}

LONDON = {
    "latitude": "51.5074",
    "longitude": "-0.1278",
    "name": "London",
    "region": "",
    "country": "United Kingdom",
}


def _coordinates(url: str) -> tuple[float, float]:
    query = parse_qs(urlparse(url).query)
    return float(query["lat"][0]), float(query["lon"][0])


def _is_london(latitude: float, longitude: float) -> bool:
    return abs(latitude - 51.5074) < 1e-4 and abs(longitude - (-0.1278)) < 1e-4


def _is_chicago(latitude: float, longitude: float) -> bool:
    return abs(latitude - 41.8781) < 1e-4 and abs(longitude - (-87.6298)) < 1e-4


@pytest.mark.django_db
def test_failed_lookup_keeps_the_last_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str) -> dict:
        latitude, longitude = _coordinates(url)
        if _is_london(latitude, longitude):
            raise WeatherUnavailable("down")
        if _is_chicago(latitude, longitude):
            if urlparse(url).path.endswith("/forecast"):
                return chicago_forecast
            return chicago_current
        raise WeatherUnavailable("unknown place")

    monkeypatch.setattr("weather.client.request_json", request_json)

    first = client.get("/", CHICAGO)
    assert first.status_code == 200
    first_body = first.content.decode()
    assert 'id="place-marker">Chicago, 21°C</p>' in first_body

    second = client.get("/", LONDON)
    assert second.status_code == 200
    body = second.content.decode()
    assert "Weather could not be loaded." in body
    assert 'id="place-marker">Chicago, 21°C</p>' in body
    shown = body.split('<div class="search-wrap">', 1)[1]
    assert "London" not in shown
    assert "Traceback" not in body
