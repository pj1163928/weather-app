from urllib.parse import urlparse

import pytest

CHICAGO = {
    "latitude": "41.8781",
    "longitude": "-87.6298",
    "name": "Chicago",
    "region": "Illinois",
    "country": "United States",
}

API_KEY = "dummy-openweather-key-should-not-leak"


@pytest.mark.django_db
def test_api_key_never_appears_in_the_page(
    client, settings, monkeypatch, chicago_current, chicago_forecast
):
    settings.OPENWEATHER_API_KEY = API_KEY

    def request_json(url: str) -> dict:
        if urlparse(url).path.endswith("/forecast"):
            return chicago_forecast
        return chicago_current

    monkeypatch.setattr("weather.client.request_json", request_json)

    response = client.get("/", CHICAGO)
    body = response.content.decode()
    assert response.status_code == 200
    assert 'id="place-marker">Chicago, 21°C</p>' in body
    assert API_KEY not in body
