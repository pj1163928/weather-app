from urllib.parse import urlparse

import pytest
from django.contrib.auth import get_user_model
from weather.models import Favorite

User = get_user_model()
PASSWORD = "correct-horse-battery"
PLACE = (
    "/?latitude=41.8781&longitude=-87.6298&name=Chicago"
    "&region=Illinois&country=United+States"
)


def _confirmed():
    user = User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=PASSWORD,
    )
    user.confirmed = True
    user.save(update_fields=["confirmed"])
    return user


def _weather(chicago_current, chicago_forecast):
    def request_json(url: str):
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    return request_json


@pytest.mark.django_db
def test_logout_stays_on_the_place_and_keeps_the_session_unit(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    monkeypatch.setattr(
        "weather.client.request_json",
        _weather(chicago_current, chicago_forecast),
    )
    user = _confirmed()
    Favorite.objects.create(
        user=user,
        name="Amarillo",
        region="Texas",
        country="United States",
        latitude=35.222,
        longitude=-101.8313,
        pin="35.2220:-101.8313",
    )
    client.force_login(user)
    session = client.session
    session["temperature_unit"] = "fahrenheit"
    session.save()

    response = client.post("/accounts/logout/", {"next": PLACE})
    page = client.get(PLACE)
    body = page.content.decode()

    assert response.status_code == 302
    assert response.url == PLACE
    assert "_auth_user_id" not in client.session
    assert client.session["temperature_unit"] == "fahrenheit"
    assert 'value="fahrenheit" aria-pressed="true"' in body
    assert "Amarillo" not in body
    assert ">Sign in</a>" in body
    assert ">Sign out</button>" not in body


@pytest.mark.django_db
def test_logout_rejects_an_off_site_return_and_a_get(client):
    client.force_login(_confirmed())

    off_site = client.post(
        "/accounts/logout/",
        {"next": "https://evil.example/phish"},
    )
    get = client.get("/accounts/logout/")

    assert off_site.status_code == 302
    assert off_site.url == "/"
    assert get.status_code == 405
    assert "_auth_user_id" not in client.session
