import unicodedata
from urllib.parse import parse_qs, urlparse

import pytest

LONDON = {
    "latitude": "51.5074",
    "longitude": "-0.1278",
    "name": "London",
    "region": "",
    "country": "United Kingdom",
}

CHICAGO_ZIP = {
    "zip": "60601",
    "name": "Chicago",
    "lat": 41.8781,
    "lon": -87.6298,
    "country": "US",
}


def _english_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return stripped.casefold()


def test_postal_country_list_is_alphabetical_english():
    from weather.countries import country_choices, country_code

    options = country_choices()
    labels = [label for _, label in options]

    assert labels == sorted(labels, key=_english_name)
    assert ("US", "United States") in options
    assert ("GB", "United Kingdom") in options
    assert len(options) == len(set(options))
    assert country_code("United Kingdom") == "GB"
    assert country_code("UK") == "GB"


@pytest.mark.django_db
def test_postal_search_with_no_match_keeps_the_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key-should-not-leak"

    def request_json(url: str):
        if urlparse(url).path.endswith("/zip"):
            return {}
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get(
        "/search/postal/",
        {**LONDON, "postal": "00000", "country": "US"},
        follow=False,
    )
    body = response.content.decode()

    assert response.status_code == 200
    assert "No matching place." in body
    assert "dummy-openweather-key-should-not-leak" not in body
    assert response.headers.get("HX-Push-Url") in (None, "")


@pytest.mark.django_db
def test_unknown_postal_country_does_not_call_the_geocoder(client, monkeypatch):
    def request_json(url: str):
        raise AssertionError(url)

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get(
        "/search/postal/",
        {"postal": "12345", "country": "ZZ"},
        follow=False,
    )

    assert response.status_code == 200
    assert "No matching place." in response.content.decode()


@pytest.mark.django_db
def test_postal_search_opens_the_one_place(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = "dummy-openweather-key"

    def request_json(url: str):
        parsed = urlparse(url)
        if parsed.path.endswith("/zip"):
            return CHICAGO_ZIP
        if parsed.path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get(
        "/search/postal/",
        {**LONDON, "postal": "60601", "country": "US"},
        follow=False,
    )
    body = response.content.decode()
    query = parse_qs(urlparse(response.headers["HX-Push-Url"]).query)

    assert response.status_code == 200
    assert ">Chicago</h1>" in body
    assert ">United States</p>" in body
    assert "Illinois" not in body
    assert ">21°C<" in body
    assert ">London</h1>" not in body
    assert float(query["latitude"][0]) == pytest.approx(41.8781)
    assert float(query["longitude"][0]) == pytest.approx(-87.6298)
    assert query["name"][0] == "Chicago"
    assert query.get("region", [""])[0] == ""
    assert query["country"][0] == "United States"
