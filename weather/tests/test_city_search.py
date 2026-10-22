import html
import re
from urllib.parse import parse_qs, urlparse

import pytest

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


def _place_query(response, header: str) -> dict[str, list[str]] | None:
    pushed = response.headers.get(header)
    if not pushed:
        return None
    return parse_qs(urlparse(pushed).query)


@pytest.mark.django_db
def test_no_city_match_keeps_the_place_query_string(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if "/geo/" in parsed.path:
            return []
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get(
        "/search/city/",
        {"city": "Atlantis", **CHICAGO},
        follow=False,
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "No matching city." in body
    assert "<h1" not in body or ">Chicago</h1>" in body
    assert 'data-marker-name="Atlantis"' not in body
    for header in ("HX-Push-Url", "HX-Replace-Url"):
        query = _place_query(response, header)
        if query is None:
            continue
        assert query.get("latitude", [None])[0] == CHICAGO["latitude"]
        assert query.get("longitude", [None])[0] == CHICAGO["longitude"]
        assert query.get("name", [None])[0] == CHICAGO["name"]
        assert query.get("region", [None])[0] == CHICAGO["region"]
        assert query.get("country", [None])[0] == CHICAGO["country"]


@pytest.mark.django_db
def test_one_city_match_opens_that_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast, chicago_geocode
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if "/geo/" in parsed.path:
            return chicago_geocode
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get(
        "/search/city/",
        {"city": "Chicago", **LONDON},
        follow=False,
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert ">Chicago</h1>" in body
    assert "Illinois, United States" in body
    assert ">21°C<" in body
    assert ">London</h1>" not in body
    query = _place_query(response, "HX-Push-Url")
    assert query is not None
    assert float(query["latitude"][0]) == pytest.approx(41.8781)
    assert float(query["longitude"][0]) == pytest.approx(-87.6298)
    assert query["name"][0] == "Chicago"
    assert query["region"][0] == "Illinois"
    assert query["country"][0] == "United States"


SPRINGFIELDS = [
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
    {
        "name": "Springfield",
        "lat": 37.2153,
        "lon": -93.2982,
        "country": "US",
    },
]


@pytest.mark.django_db
def test_several_city_matches_wait_for_a_choice(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if "/geo/" in parsed.path:
            return SPRINGFIELDS
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get(
        "/search/city/",
        {"city": "Springfield", **CHICAGO},
        follow=False,
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "Springfield, Illinois, United States" in body
    assert "Springfield, Massachusetts, United States" in body
    assert "Springfield, United States" in body
    assert "Springfield, , United States" not in body
    assert ">Springfield</h1>" not in body
    for header in ("HX-Push-Url", "HX-Replace-Url"):
        query = _place_query(response, header)
        if query is None:
            continue
        assert query.get("latitude", [None])[0] == CHICAGO["latitude"]
        assert query.get("longitude", [None])[0] == CHICAGO["longitude"]
        assert query.get("name", [None])[0] == CHICAGO["name"]
        assert query.get("region", [None])[0] == CHICAGO["region"]
        assert query.get("country", [None])[0] == CHICAGO["country"]


@pytest.mark.django_db
def test_city_choices_link_to_each_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if "/geo/" in parsed.path:
            return SPRINGFIELDS
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/search/city/", {"city": "Springfield", **CHICAGO})
    body = response.content.decode()
    hrefs = [
        html.unescape(href)
        for href in re.findall(r'href="([^"]+)"', body)
        if html.unescape(href).startswith("/?")
    ]

    assert 'hx-target="#weather"' in body
    assert 'hx-swap="outerHTML"' in body
    assert len(hrefs) == 3
    query = parse_qs(urlparse(hrefs[0]).query)
    assert float(query["latitude"][0]) == pytest.approx(39.7817)
    assert float(query["longitude"][0]) == pytest.approx(-89.6501)
    assert query["name"][0] == "Springfield"
    assert query["region"][0] == "Illinois"
    assert query["country"][0] == "United States"
    plain = parse_qs(urlparse(hrefs[2]).query)
    assert plain.get("region", [""])[0] == ""
    assert plain["country"][0] == "United States"


@pytest.mark.django_db
def test_typing_a_city_lists_suggestions(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    calls = []

    def request_json(url: str):
        calls.append(url)
        if "/geo/" in urlparse(url).path:
            return SPRINGFIELDS
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    short = client.get("/search/suggest/", {"q": "S"})
    assert short.status_code == 200
    assert short.content == b""
    assert calls == []

    response = client.get("/search/suggest/", {"q": "Sp"})
    body = response.content.decode()

    assert response.status_code == 200
    assert "Suggestions" in body
    assert "Springfield, Illinois, United States" in body
    assert "Springfield, Massachusetts, United States" in body
    assert "Springfield, United States" in body
    assert ">Springfield</h1>" not in body
    assert "HX-Push-Url" not in response.headers
    assert len(calls) == 1


@pytest.mark.django_db
def test_city_search_lists_at_most_five_matches(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    matches = [
        {
            "name": f"City {index}",
            "lat": index,
            "lon": index,
            "country": "US",
            "state": f"Region {index}",
        }
        for index in range(1, 7)
    ]

    def request_json(url: str):
        if "/geo/" in urlparse(url).path:
            return matches
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/search/city/", {"city": "City"})
    body = response.content.decode()

    for index in range(1, 6):
        assert f"City {index}, Region {index}, United States" in body
    assert "City 6, Region 6, United States" not in body
