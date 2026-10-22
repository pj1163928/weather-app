from urllib.parse import parse_qs, unquote, urlparse

import pytest
from django.contrib.auth import get_user_model

from weather.models import Favorite

User = get_user_model()
PASSWORD = "correct-horse-battery"


def _user(username, email):
    user = User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
    )
    user.confirmed = True
    user.save(update_fields=["confirmed"])
    return user


def _chicago():
    return {
        "latitude": "41.87811",
        "longitude": "-87.62981",
        "name": "Chicago",
        "region": "Illinois",
        "country": "United States",
    }


def _london():
    return {
        "latitude": "51.5074",
        "longitude": "-0.1278",
        "name": "London",
        "region": "",
        "country": "United Kingdom",
    }


@pytest.mark.django_db
def test_a_favorite_belongs_to_one_user(client):
    owner = _user("ada", "ada@example.com")
    other = _user("grace", "grace@example.com")
    client.force_login(owner)
    added = client.post("/favorites/add/", _chicago())
    favorite = Favorite.objects.get()

    assert added.status_code == 302
    assert Favorite.objects.filter(user=owner).count() == 1

    client.force_login(other)
    page = client.get("/")
    body = page.content.decode()

    assert f"/favorites/{favorite.pk}/remove/" not in body
    assert "Chicago, Illinois, United States" not in body

    removed = client.post(f"/favorites/{favorite.pk}/remove/")

    assert removed.status_code == 404
    assert Favorite.objects.filter(pk=favorite.pk, user=owner).exists()


@pytest.mark.django_db
def test_the_same_pin_is_not_saved_twice(client):
    client.force_login(_user("ada", "ada@example.com"))
    first = _chicago()
    second = {
        **first,
        "latitude": "41.87814",
        "longitude": "-87.62984",
    }

    client.post("/favorites/add/", first)
    client.post("/favorites/add/", second)

    assert Favorite.objects.count() == 1
    saved = Favorite.objects.get()
    assert saved.pin == "41.8781:-87.6298"
    assert saved.name == "Chicago"
    assert saved.region == "Illinois"
    assert saved.country == "United States"


@pytest.mark.django_db
def test_favorites_are_listed_newest_first_and_open_by_query_string(client):
    client.force_login(_user("ada", "ada@example.com"))
    client.post("/favorites/add/", _chicago())
    client.post("/favorites/add/", _london())

    response = client.get("/")
    body = response.content.decode()
    saved = body.split('id="saved-places"', 1)[1].split('id="save-place"', 1)[0]
    london = saved.index("London, United Kingdom")
    chicago = saved.index("Chicago, Illinois, United States")
    href = saved.split('href="', 1)[1].split('"', 1)[0]
    query = parse_qs(urlparse(html_unescape(href)).query)

    assert london < chicago
    assert query["name"][0] == "London"
    assert query["latitude"][0] == "51.5074"
    assert query["country"][0] == "United Kingdom"


def html_unescape(value):
    return unquote(value.replace("&amp;", "&"))


@pytest.mark.django_db
def test_removing_a_favorite_updates_the_list(client):
    client.force_login(_user("ada", "ada@example.com"))
    client.post("/favorites/add/", _chicago())
    favorite = Favorite.objects.get()

    response = client.post(
        f"/favorites/{favorite.pk}/remove/",
        HTTP_HX_REQUEST="true",
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "No saved places yet." in body
    assert "Chicago, Illinois, United States" not in body
    assert Favorite.objects.count() == 0


@pytest.mark.django_db
def test_a_visitor_save_goes_to_login_and_returns_to_the_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)
    _user("ada", "ada@example.com")
    page = client.get(
        "/",
        {
            "latitude": "41.8781",
            "longitude": "-87.6298",
            "name": "Chicago",
            "region": "Illinois",
            "country": "United States",
        },
    )
    body = page.content.decode()
    save = body.split(">Save this place</a>", 1)[0].rsplit('href="', 1)[1]
    save = save.split('"', 1)[0]
    target = unquote(save.split("?next=", 1)[1])

    assert save.startswith("/accounts/login/?next=")
    assert target.startswith("/?latitude=41.8781&longitude=-87.6298")
    assert "name=Chicago" in target

    signed_in = client.post(
        "/accounts/login/",
        {"username": "ada", "password": PASSWORD, "next": target},
    )

    assert signed_in.status_code == 302
    assert signed_in.url == target


@pytest.mark.django_db
def test_a_city_row_can_be_saved(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        if "/geo/" in urlparse(url).path:
            return [
                {
                    "name": "Springfield",
                    "lat": 39.7817,
                    "lon": -89.6501,
                    "country": "US",
                    "state": "Illinois",
                },
                {
                    "name": "Springfield",
                    "lat": 42.1015,
                    "lon": -72.5898,
                    "country": "US",
                    "state": "Massachusetts",
                },
            ]
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)
    client.force_login(_user("ada", "ada@example.com"))

    listed = client.get("/search/city/", {"city": "Springfield"})
    body = listed.content.decode()

    assert 'hx-post="/favorites/add/"' in body
    assert 'name="name" value="Springfield"' in body

    saved = client.post(
        "/favorites/add/",
        {
            "latitude": "39.7817",
            "longitude": "-89.6501",
            "name": "Springfield",
            "region": "Illinois",
            "country": "United States",
        },
        HTTP_HX_REQUEST="true",
    )

    assert saved.status_code == 200
    assert "Springfield, Illinois, United States" in saved.content.decode()
    assert Favorite.objects.count() == 1
