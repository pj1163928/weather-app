from urllib.parse import urlparse

import pytest

from weather.client import WeatherUnavailable

CHICAGO = {
    "latitude": "41.8781",
    "longitude": "-87.6298",
    "name": "Chicago",
    "region": "Illinois",
    "country": "United States",
}


def _stub_chicago(monkeypatch, chicago_current, chicago_forecast, urls):
    def request_json(url: str) -> dict:
        urls.append(url)
        if "geo" in urlparse(url).path:
            raise WeatherUnavailable("geocoder was called")
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)


@pytest.mark.django_db
def test_query_string_place_renders_metric_conditions(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    urls = []
    _stub_chicago(monkeypatch, chicago_current, chicago_forecast, urls)

    response = client.get("/", CHICAGO)
    body = response.content.decode()
    assert response.status_code == 200
    assert "<h1" in body and "Chicago" in body
    assert "Illinois, United States" in body
    assert ">21°C<" in body
    assert 'class="temp-range"' in body
    assert "High 21°C" in body
    assert "Low 21°C" in body
    assert "Feels like 19°C" in body
    assert 'class="feels"' in body
    assert 'class="day-icon"' in body
    stats = body.split('class="readings"', 1)[1].split("</section>", 1)[0]
    assert "Feels like" not in stats
    assert "Humidity 60%" in body
    assert "Wind 3.5 m/s" in body
    assert "Cloudiness 12%" in body
    assert "Pressure 1013 hPa" in body
    assert "°F" not in body
    assert "mph" not in body
    assert urls
    assert all(urlparse(url).path.startswith("/data/2.5/") for url in urls)
    assert all("geo" not in urlparse(url).path for url in urls)


@pytest.mark.django_db
def test_first_visit_shows_the_message_and_no_marker(client, monkeypatch):
    def request_json(url: str) -> dict:
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/")
    body = response.content.decode()
    assert response.status_code == 200
    assert "Find the weather for any place." in body
    assert "A city name, a ZIP" not in body
    assert "Weather could not be loaded." not in body
    assert 'id="place-marker"' not in body
    assert "Traceback" not in body


@pytest.mark.django_db
def test_failed_first_lookup_has_no_marker(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str) -> dict:
        raise WeatherUnavailable("down")

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/", CHICAGO)
    body = response.content.decode()
    assert response.status_code == 200
    assert "Weather could not be loaded." in body
    assert 'id="place-marker"' not in body
    shown = body.split('<div class="search-wrap">', 1)[1]
    assert "Chicago" not in shown
    assert "Traceback" not in body


@pytest.mark.django_db
def test_map_uses_openstreetmap_and_one_marker(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    _stub_chicago(monkeypatch, chicago_current, chicago_forecast, [])

    response = client.get("/", CHICAGO)
    body = response.content.decode()
    weather_at = body.index('id="weather"')
    map_at = body.index('id="map"')
    tiles_at = body.index("tile.openstreetmap.org")
    assert weather_at < map_at < tiles_at
    assert body.count("L.map(") == 1
    assert "https://tile.openstreetmap.org/{z}/{x}/{y}.png" in body
    assert "{s}.tile.openstreetmap.org" not in body
    assert "strict-origin-when-cross-origin" in body
    assert "OpenStreetMap" in body
    assert 'id="place-marker">Chicago, 21°C</p>' in body
    assert 'data-marker-name="Chicago"' in body
    assert 'data-marker-temperature="21°C"' in body


@pytest.mark.django_db
def test_forecast_timezone_on_the_city_still_loads(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    forecast = {
        "city": {"timezone": chicago_forecast["timezone"]},
        "list": chicago_forecast["list"],
    }

    def request_json(url: str) -> dict:
        if urlparse(url).path.endswith("/forecast"):
            return forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/", CHICAGO)
    body = response.content.decode()

    assert response.status_code == 200
    assert ">Chicago</h1>" in body
    assert ">21°C<" in body
    assert "Weather could not be loaded." not in body
