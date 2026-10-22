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


def _weather_stub(chicago_current, chicago_forecast):
    def request_json(url: str):
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    return request_json


@pytest.mark.django_db
def test_search_is_on_the_page_before_a_place_loads(client, monkeypatch):
    def request_json(url: str):
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/")
    body = response.content.decode()

    assert response.status_code == 200
    assert 'name="q"' in body
    assert ">Search</button>" in body
    assert "Around the world" in body
    assert "Tokyo" in body
    assert 'class="world-scroll"' in body
    assert "scrollLeft" in body
    assert "scrollTop" not in body
    assert 'hx-get="/search/suggest/"' in body
    assert 'data-latitude="48.8566"' in body
    assert ">Use my location</button>" in body
    assert 'data-auto="true"' in body
    assert 'data-snapshot="/here/"' in body
    assert "requestSnapshot()" in body
    assert 'data-finding="Finding your location…"' in body
    assert ">Finding your location…" not in body
    assert 'data-unavailable="Location is unavailable."' in body
    assert "Weather could not be loaded." not in body
    assert 'id="place-marker"' not in body


@pytest.mark.django_db
def test_loaded_place_does_not_ask_for_location_again(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    monkeypatch.setattr(
        "weather.client.request_json",
        _weather_stub(chicago_current, chicago_forecast),
    )

    response = client.get("/", CHICAGO)
    body = response.content.decode()

    assert 'name="q"' in body
    assert ">Search</button>" in body
    assert ">Use my location</button>" in body
    assert 'data-auto="true"' not in body
    assert "htmx:afterSwap" in body
    assert body.count("L.map(") == 1


@pytest.mark.django_db
def test_failed_weather_keeps_search(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        raise WeatherUnavailable("down")

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/", CHICAGO)
    body = response.content.decode()

    assert "Weather could not be loaded." in body
    assert 'name="q"' in body
    assert ">Search</button>" in body
    assert ">Use my location</button>" in body
    assert 'data-auto="true"' not in body
    shown = body.split('<div class="search-wrap">', 1)[1]
    assert "Chicago" not in shown


@pytest.mark.django_db
def test_device_coordinates_open_the_resolved_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if parsed.path.endswith("/reverse"):
            return [
                {
                    "name": "Chicago",
                    "lat": 41.0,
                    "lon": -87.0,
                    "country": "US",
                    "state": "Illinois",
                }
            ]
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get(
        "/",
        {"locate": "1", "latitude": "41.8781", "longitude": "-87.6298"},
        follow=False,
    )
    body = response.content.decode()
    pushed = response.headers["HX-Push-Url"]
    query = parse_qs(urlparse(pushed).query)

    assert response.status_code == 200
    assert ">Chicago</h1>" in body
    assert "Illinois, United States" in body
    assert "locate" not in pushed
    assert float(query["latitude"][0]) == pytest.approx(41.8781)
    assert float(query["longitude"][0]) == pytest.approx(-87.6298)
    assert query["name"][0] == "Chicago"
    assert query["region"][0] == "Illinois"
    assert query["country"][0] == "United States"


@pytest.mark.django_db
def test_use_my_location_hides_after_a_successful_locate(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if parsed.path.endswith("/reverse"):
            return [
                {
                    "name": "Chicago",
                    "lat": 41.8781,
                    "lon": -87.6298,
                    "country": "US",
                    "state": "Illinois",
                }
            ]
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    located = client.get(
        "/",
        {"locate": "1", "latitude": "41.8781", "longitude": "-87.6298"},
    )
    again = client.get("/")

    assert located.status_code == 200
    assert ">Use my location</button>" not in again.content.decode()


@pytest.mark.django_db
def test_a_failed_locate_keeps_use_my_location(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        if urlparse(url).path.endswith("/reverse"):
            return []
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    client.get(
        "/",
        {"locate": "1", "latitude": "41.8781", "longitude": "-87.6298"},
    )
    again = client.get("/")

    assert ">Use my location</button>" in again.content.decode()


@pytest.mark.django_db
def test_location_snapshot_stays_on_the_home_page(
    client, settings, monkeypatch, chicago_current
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if parsed.path.endswith("/reverse"):
            return [
                {
                    "name": "Chicago",
                    "lat": 41.8781,
                    "lon": -87.6298,
                    "country": "US",
                    "state": "Illinois",
                }
            ]
        assert parsed.path.endswith("/weather")
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/here/", {"latitude": "41.8781", "longitude": "-87.6298"})
    body = response.content.decode()

    assert response.status_code == 200
    assert "HX-Push-Url" not in response.headers
    assert 'class="here"' in body
    assert "Your location" in body
    assert "Chicago" in body
    assert "Illinois, United States" in body
    assert "21°C" in body
    assert "clear sky" in body
    assert "<h1" not in body
    assert "locate=1" not in body
