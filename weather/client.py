import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

OPENWEATHER_ORIGIN = "https://api.openweathermap.org/data/2.5"
GEOCODE_ORIGIN = "https://api.openweathermap.org/geo/1.0"


class WeatherUnavailable(Exception):
    pass


@dataclass(frozen=True)
class CurrentConditions:
    temperature_c: float
    feels_like_c: float
    humidity: int
    wind_speed_ms: float
    cloudiness: int
    pressure_hpa: int
    description: str
    sunrise_unix: int
    sunset_unix: int
    timezone_offset_seconds: int


@dataclass(frozen=True)
class ForecastSlot:
    time_unix: int
    temperature_c: float
    description: str


@dataclass(frozen=True)
class PlaceWeather:
    current: CurrentConditions
    slots: tuple[ForecastSlot, ...]
    timezone_offset_seconds: int


def request_json(url: str) -> dict | list:
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise WeatherUnavailable("OpenWeather request failed") from exc
    if not isinstance(payload, dict | list):
        raise WeatherUnavailable("OpenWeather response was incomplete")
    return payload


def geocode_city(city: str, api_key: str) -> list[dict]:
    query = urlencode({"q": city, "limit": 5, "appid": api_key})
    payload = request_json(f"{GEOCODE_ORIGIN}/direct?{query}")
    if not isinstance(payload, list):
        raise WeatherUnavailable("OpenWeather response was incomplete")
    return payload


def geocode_postal(postal: str, country_code: str, api_key: str) -> dict | None:
    query = urlencode({"zip": f"{postal},{country_code}", "appid": api_key})
    try:
        payload = request_json(f"{GEOCODE_ORIGIN}/zip?{query}")
    except WeatherUnavailable:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def reverse_geocode(latitude: float, longitude: float, api_key: str) -> list[dict]:
    query = urlencode(
        {
            "lat": latitude,
            "lon": longitude,
            "limit": 1,
            "appid": api_key,
        }
    )
    payload = request_json(f"{GEOCODE_ORIGIN}/reverse?{query}")
    if not isinstance(payload, list):
        raise WeatherUnavailable("OpenWeather response was incomplete")
    return payload


def fetch_place(latitude: float, longitude: float, api_key: str) -> PlaceWeather:
    current = request_json(_url("weather", latitude, longitude, api_key))
    forecast = request_json(_url("forecast", latitude, longitude, api_key))
    return parse_place(current, forecast)


def fetch_snapshot(
    latitude: float, longitude: float, api_key: str
) -> tuple[float, str]:
    current = request_json(_url("weather", latitude, longitude, api_key))
    try:
        return float(current["main"]["temp"]), _description(current)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise WeatherUnavailable("OpenWeather response was incomplete") from exc


def parse_place(current: dict, forecast: dict) -> PlaceWeather:
    try:
        conditions = CurrentConditions(
            temperature_c=float(current["main"]["temp"]),
            feels_like_c=float(current["main"]["feels_like"]),
            humidity=int(current["main"]["humidity"]),
            wind_speed_ms=float(current["wind"]["speed"]),
            cloudiness=int(current["clouds"]["all"]),
            pressure_hpa=int(current["main"]["pressure"]),
            description=_description(current),
            sunrise_unix=int(current["sys"]["sunrise"]),
            sunset_unix=int(current["sys"]["sunset"]),
            timezone_offset_seconds=_offset_seconds(current),
        )
        slots = tuple(
            ForecastSlot(
                time_unix=int(entry["dt"]),
                temperature_c=float(entry["main"]["temp"]),
                description=_description(entry),
            )
            for entry in forecast["list"]
        )
        if not slots:
            raise WeatherUnavailable("OpenWeather response was incomplete")
        return PlaceWeather(
            current=conditions,
            slots=slots,
            timezone_offset_seconds=_offset_seconds(forecast),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherUnavailable("OpenWeather response was incomplete") from exc


def _offset_seconds(payload: dict) -> int:
    if "timezone" in payload:
        return int(payload["timezone"])
    city = payload.get("city")
    if isinstance(city, dict) and "timezone" in city:
        return int(city["timezone"])
    raise KeyError("timezone")


def _description(payload: dict) -> str:
    weather = payload["weather"]
    return str(weather[0]["description"])


def _url(kind: str, latitude: float, longitude: float, api_key: str) -> str:
    query = urlencode(
        {
            "lat": latitude,
            "lon": longitude,
            "units": "metric",
            "appid": api_key,
        }
    )
    return f"{OPENWEATHER_ORIGIN}/{kind}?{query}"
