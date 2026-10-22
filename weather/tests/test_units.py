from urllib.parse import urlencode, urlparse

import pytest
from django.contrib.auth import get_user_model

from weather.client import WeatherUnavailable
from weather.views import UNIT_SESSION_KEY

User = get_user_model()

CHICAGO = {
    "latitude": "41.8781",
    "longitude": "-87.6298",
    "name": "Chicago",
    "region": "Illinois",
    "country": "United States",
}


def _current_url(params: dict | None = None) -> str:
    if not params:
        return "http://testserver/"
    return "http://testserver/?" + urlencode(params)


def _stub_weather(monkeypatch, current, forecast, urls=None, fail=None):
    def request_json(url: str):
        if fail is not None and fail["on"]:
            raise WeatherUnavailable("down")
        if urls is not None:
            urls.append(url)
        parsed = urlparse(url)
        if "geo" in parsed.path:
            raise AssertionError(url)
        if parsed.path.endswith("/forecast"):
            return forecast
        return current

    monkeypatch.setattr("weather.client.request_json", request_json)


def _switch(client, unit: str, params: dict | None = None, **extra):
    headers = {
        "HTTP_HX_REQUEST": "true",
        "HTTP_HX_CURRENT_URL": _current_url(params),
    }
    headers.update(extra)
    return client.post("/units/", {"unit": unit}, **headers)


@pytest.mark.django_db
def test_unit_switch_is_on_the_weather_page(client, monkeypatch):
    def request_json(url: str):
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/")
    body = response.content.decode()

    assert 'id="unit-switch"' in body
    assert 'hx-post="/units/"' in body
    assert 'hx-target="#weather"' in body
    assert 'hx-swap="outerHTML"' in body
    assert 'hx-push-url="false"' in body
    assert 'value="celsius" aria-pressed="true"' in body
    assert 'value="fahrenheit" aria-pressed="false"' in body
    assert ">Celsius</button>" in body
    assert ">Fahrenheit</button>" in body


@pytest.mark.django_db
def test_visitor_unit_stays_in_the_session(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    urls = []
    _stub_weather(monkeypatch, chicago_current, chicago_forecast, urls)

    switched = _switch(client, "fahrenheit", CHICAGO)
    body = switched.content.decode()

    assert switched.status_code == 200
    assert "<html" not in body
    assert "HX-Push-Url" not in switched.headers
    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"
    assert ">70°F<" in body
    assert "Feels like 66°F" in body
    assert "High 70°F" in body
    assert "Low 70°F" in body
    assert "Wind 7.8 mph" in body
    assert "Pressure 1013 hPa" in body
    assert "Humidity 60%" in body
    assert 'data-marker-temperature="70°F"' in body
    assert 'value="fahrenheit" aria-pressed="true"' in body
    assert "°C" not in body
    assert "m/s" not in body
    assert urls
    assert all("units=metric" in url for url in urls)
    assert all("geo" not in urlparse(url).path for url in urls)

    again = client.get("/", CHICAGO)
    again_body = again.content.decode()
    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"
    assert ">70°F<" in again_body
    assert "Wind 7.8 mph" in again_body
    assert 'id="place-marker">Chicago, 70°F</p>' in again_body
    assert "Pressure 1013 hPa" in again_body

    restored = _switch(client, "celsius", CHICAGO)
    restored_body = restored.content.decode()
    assert client.session[UNIT_SESSION_KEY] == "celsius"
    assert ">21°C<" in restored_body
    assert "Wind 3.5 m/s" in restored_body
    assert "°F" not in restored_body
    assert "mph" not in restored_body
    assert 'value="celsius" aria-pressed="true"' in restored_body


@pytest.mark.django_db
def test_unknown_unit_leaves_the_session(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    _stub_weather(monkeypatch, chicago_current, chicago_forecast)

    response = _switch(client, "kelvin", CHICAGO)
    body = response.content.decode()

    assert UNIT_SESSION_KEY not in client.session
    assert ">21°C<" in body
    assert "Wind 3.5 m/s" in body
    assert "70°F" not in body
    assert 'value="celsius" aria-pressed="true"' in body


@pytest.mark.django_db
def test_failed_reload_keeps_the_place_and_stores_the_unit(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    fail = {"on": False}
    _stub_weather(monkeypatch, chicago_current, chicago_forecast, fail=fail)

    loaded = client.get("/", CHICAGO)
    assert ">21°C<" in loaded.content.decode()

    fail["on"] = True
    response = _switch(client, "fahrenheit", CHICAGO)
    body = response.content.decode()

    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"
    assert "Weather could not be loaded." in body
    assert "Chicago" in body
    assert ">21°C<" in body
    assert 'data-marker-temperature="21°C"' in body
    assert 'value="fahrenheit" aria-pressed="true"' in body
    assert "Traceback" not in body

    fail["on"] = False
    again = client.get("/", CHICAGO)
    again_body = again.content.decode()
    assert ">70°F<" in again_body
    assert "Wind 7.8 mph" in again_body
    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"


@pytest.mark.django_db
def test_unit_without_a_place_is_used_on_the_next_lookup(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        assert urlparse(url).path.endswith("/weather")
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = _switch(client, "fahrenheit")
    body = response.content.decode()

    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"
    assert "Find the weather for any place." in body
    assert "70°F" in body
    assert "21°C" not in body
    assert 'id="spotlight-cards"' in body
    assert 'hx-swap-oob="innerHTML"' in body

    monkeypatch.setattr(
        "weather.client.request_json",
        _weather_after_spotlight(chicago_current, chicago_forecast),
    )
    opened = client.get("/", CHICAGO)
    opened_body = opened.content.decode()
    assert ">70°F<" in opened_body
    assert "Wind 7.8 mph" in opened_body
    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"


def _weather_after_spotlight(current, forecast):
    def request_json(url: str):
        parsed = urlparse(url)
        if "geo" in parsed.path:
            raise AssertionError(url)
        if parsed.path.endswith("/forecast"):
            return forecast
        return current

    return request_json


@pytest.mark.django_db
def test_unit_post_without_htmx_returns_to_the_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    _stub_weather(monkeypatch, chicago_current, chicago_forecast)

    response = client.post(
        "/units/",
        {"unit": "fahrenheit"},
        HTTP_REFERER=_current_url(CHICAGO),
        follow=True,
    )

    assert response.redirect_chain
    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"
    assert ">70°F<" in response.content.decode()
    assert "Wind 7.8 mph" in response.content.decode()


@pytest.mark.django_db
def test_signed_in_unit_switch_is_stored_on_the_account(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    _stub_weather(monkeypatch, chicago_current, chicago_forecast)
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password="correct-horse-battery",
    )
    user.confirmed = True
    user.temperature_unit = "celsius"
    user.save(update_fields=["confirmed", "temperature_unit"])
    client.force_login(user)

    response = _switch(client, "fahrenheit", CHICAGO)
    user.refresh_from_db()

    assert response.status_code == 200
    assert user.temperature_unit == "fahrenheit"
