from urllib.parse import unquote, urlparse

import pytest
from django.contrib.auth import get_user_model
from weather.views import UNIT_SESSION_KEY

User = get_user_model()

PASSWORD = "correct-horse-battery"
PLACE = (
    "/?latitude=41.8781&longitude=-87.6298&name=Chicago"
    "&region=Illinois&country=United+States"
)


def _confirmed(username="ada", email="ada@example.com"):
    user = User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
    )
    user.confirmed = True
    user.save(update_fields=["confirmed"])
    return user


@pytest.mark.django_db
def test_unconfirmed_account_cannot_log_in(client):
    User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=PASSWORD,
    )

    response = client.post(
        "/accounts/login/",
        {"username": "ada", "password": PASSWORD},
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "Confirm your account first" in body
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_unconfirmed_login_links_back_to_the_message(client):
    User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=PASSWORD,
    )

    response = client.post(
        "/accounts/login/",
        {"username": "ada", "password": PASSWORD, "next": PLACE},
    )
    body = response.content.decode()

    assert "Show that message again" in body
    assert 'href="/accounts/confirm/?next=' in body
    assert "The username or email and password do not match." not in body


@pytest.mark.django_db
def test_wrong_password_stays_anonymous(client):
    User.objects.create_user(
        username="ada",
        email="ada@example.com",
        password=PASSWORD,
    )

    response = client.post(
        "/accounts/login/",
        {"username": "ada", "password": "not-the-password"},
    )

    body = response.content.decode()

    assert response.status_code == 200
    assert "The username or email and password do not match." in body
    assert "Confirm your account first" not in body
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_accepts_username_or_email_and_returns_to_the_place(client):
    _confirmed()

    by_name = client.post(
        "/accounts/login/",
        {"username": "ada", "password": PASSWORD, "next": PLACE},
    )

    assert by_name.status_code == 302
    assert by_name.url == PLACE
    assert "_auth_user_id" in client.session

    client.logout()
    by_email = client.post(
        "/accounts/login/",
        {"username": "Ada@Example.com", "password": PASSWORD, "next": PLACE},
    )

    assert by_email.status_code == 302
    assert by_email.url == PLACE


@pytest.mark.django_db
def test_login_treats_other_values_as_an_exact_username(client):
    _confirmed()

    response = client.post(
        "/accounts/login/",
        {"username": "Ada", "password": PASSWORD, "next": PLACE},
    )

    body = response.content.decode()

    assert response.status_code == 200
    assert "The username or email and password do not match." in body
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_login_rejects_an_off_site_return_path(client):
    _confirmed()

    for candidate in ("https://evil.example/phish", "//evil.example/phish"):
        client.logout()
        response = client.post(
            "/accounts/login/",
            {"username": "ada", "password": PASSWORD, "next": candidate},
        )
        assert response.status_code == 302
        assert response.url == "/"


@pytest.mark.django_db
def test_inactive_account_stays_out_without_changing_confirmation(client):
    user = _confirmed()
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.post(
        "/accounts/login/",
        {"username": "ada", "password": PASSWORD},
    )
    body = response.content.decode()
    user.refresh_from_db()

    assert response.status_code == 200
    assert "The username or email and password do not match." in body
    assert user.confirmed is True
    assert user.is_active is False
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_weather_page_links_login_to_the_current_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)
    response = client.get(
        "/",
        {
            "latitude": "41.8781",
            "longitude": "-87.6298",
            "name": "Chicago",
            "region": "Illinois",
            "country": "United States",
        },
    )
    body = response.content.decode()
    href = body.split('href="/accounts/login/?next=', 1)[1].split('"', 1)[0]
    target = unquote(href)

    assert target.startswith("/?latitude=41.8781&longitude=-87.6298")
    assert "name=Chicago" in target
    assert "&amp;" not in target
    assert 'href="/accounts/register/?next=' in body


@pytest.mark.django_db
def test_signed_in_weather_page_shows_the_username(client, monkeypatch):
    def request_json(url: str):
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)
    client.force_login(_confirmed())

    response = client.get("/")
    body = response.content.decode()

    assert 'class="avatar-letters">AD</span>' in body
    assert 'class="sr-only">ada</span>' in body
    assert ">Sign out</button>" in body
    assert ">Sign in</a>" not in body
    assert ">Register</a>" not in body


@pytest.mark.django_db
def test_login_replaces_the_session_unit_with_the_account_unit(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)
    user = _confirmed()
    user.temperature_unit = "fahrenheit"
    user.save(update_fields=["temperature_unit"])
    session = client.session
    session[UNIT_SESSION_KEY] = "celsius"
    session.save()

    response = client.post(
        "/accounts/login/",
        {"username": "ada", "password": PASSWORD, "next": PLACE},
        follow=True,
    )
    body = response.content.decode()

    assert ">70°F<" in body
    assert "Wind 7.8 mph" in body
    assert client.session[UNIT_SESSION_KEY] == "fahrenheit"
