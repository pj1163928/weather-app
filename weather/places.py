from dataclasses import dataclass
from urllib.parse import urlencode

from django.urls import reverse

from weather.countries import country_name


@dataclass(frozen=True)
class Place:
    latitude: float
    longitude: float
    name: str
    region: str
    country: str


def place_from_query(params) -> Place | None:
    raw_latitude = params.get("latitude")
    raw_longitude = params.get("longitude")
    name = (params.get("name") or "").strip()
    if raw_latitude in (None, "") or raw_longitude in (None, "") or not name:
        return None
    try:
        latitude = float(raw_latitude)
        longitude = float(raw_longitude)
    except ValueError:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return Place(
        latitude=latitude,
        longitude=longitude,
        name=name,
        region=params.get("region") or "",
        country=params.get("country") or "",
    )


def place_from_geocode(match: dict) -> Place | None:
    if not isinstance(match, dict):
        return None
    try:
        latitude = float(match["lat"])
        longitude = float(match["lon"])
        name = str(match["name"]).strip()
    except (KeyError, TypeError, ValueError):
        return None
    if not name or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return Place(
        latitude=latitude,
        longitude=longitude,
        name=name,
        region=str(match.get("state") or "").strip(),
        country=country_name(str(match.get("country") or "")),
    )


def place_label(place: Place) -> str:
    parts = [place.name]
    if place.region:
        parts.append(place.region)
    if place.country:
        parts.append(place.country)
    return ", ".join(parts)


def place_path(place: Place) -> str:
    query = urlencode(
        {
            "latitude": place.latitude,
            "longitude": place.longitude,
            "name": place.name,
            "region": place.region,
            "country": place.country,
        }
    )
    return f"{reverse('weather:home')}?{query}"
