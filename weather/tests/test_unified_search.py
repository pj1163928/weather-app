from urllib.parse import parse_qs, urlparse

import pytest

from weather.lookup import classify_query

CHICAGO_ZIP = {
    "zip": "60601",
    "name": "Chicago",
    "lat": 41.8781,
    "lon": -87.6298,
    "country": "US",
}


def test_classify_query_detects_a_city_or_a_postal_code():
    city = classify_query("  London  ")
    us_zip = classify_query("60601-1234")
    uk = classify_query("sw1a 1aa")
    germany = classify_query("10115, Germany")
    ambiguous = classify_query("1010")

    assert city is not None and city.kind == "city" and city.text == "London"
    assert us_zip is not None
    assert us_zip.kind == "postal"
    assert us_zip.country_code == "US"
    assert us_zip.text == "60601"
    assert uk is not None and uk.kind == "postal" and uk.country_code == "GB"
    assert germany is not None
    assert germany.kind == "postal"
    assert germany.country_code == "DE"
    assert germany.text == "10115"
    assert classify_query("Paris, France").kind == "city"
    assert ambiguous is not None and ambiguous.kind == "postal"
    assert ambiguous.country_code == ""
    assert classify_query("   ") is None


@pytest.mark.django_db
def test_shared_search_opens_one_city(
    client, settings, monkeypatch, chicago_current, chicago_forecast, chicago_geocode
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if parsed.path.endswith("/direct"):
            return chicago_geocode
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/search/", {"q": "Chicago"})
    body = response.content.decode()
    query = parse_qs(urlparse(response.headers["HX-Push-Url"]).query)

    assert ">Chicago</h1>" in body
    assert query["name"][0] == "Chicago"
    assert query["country"][0] == "United States"


@pytest.mark.django_db
def test_shared_search_treats_a_zip_as_postal(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    seen = []

    def request_json(url: str):
        seen.append(url)
        parsed = urlparse(url)
        if parsed.path.endswith("/zip"):
            return CHICAGO_ZIP
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/search/", {"q": "60601"})
    body = response.content.decode()

    assert ">Chicago</h1>" in body
    assert any(urlparse(url).path.endswith("/zip") and "60601" in url for url in seen)
    assert any("US" in url for url in seen)


@pytest.mark.django_db
def test_shared_search_sends_a_named_country(client, settings, monkeypatch):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"
    seen = []

    def request_json(url: str):
        seen.append(url)
        return {}

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/search/", {"q": "10115, Germany"})

    assert response.status_code == 200
    assert "No matching place." in response.content.decode()
    assert seen
    assert urlparse(seen[0]).path.endswith("/zip")
    assert "10115" in seen[0]
    assert "DE" in seen[0]


@pytest.mark.django_db
def test_ambiguous_postal_code_asks_for_a_country(client, monkeypatch):
    def request_json(url: str):
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/search/", {"q": "1010"})

    assert "Add a country after that postal code, such as 10115, Germany." in (
        response.content.decode()
    )


@pytest.mark.django_db
def test_spotlight_adds_temperatures(client, settings, monkeypatch, chicago_current):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        assert urlparse(url).path.endswith("/weather")
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/spotlight/")
    body = response.content.decode()

    assert "Tokyo" in body
    assert "21°C" in body
    assert "clear sky" in body
    assert 'hx-target="#weather"' in body
