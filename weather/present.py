from datetime import UTC, datetime, timedelta, timezone

from weather.client import PlaceWeather
from weather.places import Place

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


MPH_PER_MS = 2.2369362920544
FAHRENHEIT = "fahrenheit"


def display_context(place: Place, weather: PlaceWeather, unit: str = "celsius") -> dict:
    offset = weather.timezone_offset_seconds
    temperature = _temperature(weather.current.temperature_c, unit)
    days = _days(weather, offset, unit)
    today = days[0] if days else {}
    return {
        "name": place.name,
        "region": place.region,
        "country": place.country,
        "latitude": place.latitude,
        "longitude": place.longitude,
        "temperature": temperature,
        "high": today.get("high", ""),
        "low": today.get("low", ""),
        "feels_like": _temperature(weather.current.feels_like_c, unit),
        "humidity": weather.current.humidity,
        "wind": _wind(weather.current.wind_speed_ms, unit),
        "cloudiness": weather.current.cloudiness,
        "pressure_hpa": weather.current.pressure_hpa,
        "marker_name": place.name,
        "marker_temperature": temperature,
        "condition": weather.current.description,
        "kind": condition_kind(weather.current.description),
        "sunrise": _format_moment(
            weather.current.sunrise_unix,
            weather.current.timezone_offset_seconds,
        ),
        "sunset": _format_moment(
            weather.current.sunset_unix,
            weather.current.timezone_offset_seconds,
        ),
        "days": days,
        "hours": _hours(weather, offset, unit),
    }


def _days(weather: PlaceWeather, offset: int, unit: str) -> list[dict]:
    grouped: dict = {}
    for slot in weather.slots:
        local = _local(slot.time_unix, offset)
        grouped.setdefault(local.date(), []).append((local, slot))
    days = []
    for entries in grouped.values():
        closest = min(entries, key=lambda item: (_noon_distance(item[0]), item[0]))
        temperatures = [item[1].temperature_c for item in entries]
        days.append(
            {
                "heading": _format_day(entries[0][0]),
                "condition": closest[1].description,
                "kind": condition_kind(closest[1].description),
                "average": _temperature(sum(temperatures) / len(temperatures), unit),
                "high": _temperature(max(temperatures), unit),
                "low": _temperature(min(temperatures), unit),
            }
        )
    return days


def _hours(weather: PlaceWeather, offset: int, unit: str) -> list[dict]:
    hours = []
    seen_dates = set()
    for slot in weather.slots:
        local = _local(slot.time_unix, offset)
        day = local.date()
        first_of_day = day not in seen_dates
        seen_dates.add(day)
        hours.append(
            {
                "time": _format_hour(local),
                "day_label": WEEKDAYS[local.weekday()] if first_of_day else "",
                "temperature": _temperature(slot.temperature_c, unit),
                "condition": slot.description,
                "kind": condition_kind(slot.description),
                "label": (
                    f"{_format_day(local)}, {_format_clock(local)}, "
                    f"{_temperature(slot.temperature_c, unit)}, {slot.description}"
                ),
            }
        )
    return hours


def _local(unix: int, offset: int) -> datetime:
    return datetime.fromtimestamp(unix, UTC).astimezone(
        timezone(timedelta(seconds=offset))
    )


def _format_day(moment: datetime) -> str:
    weekday = WEEKDAYS[moment.weekday()]
    month = MONTHS[moment.month - 1]
    return f"{weekday}, {month} {moment.day}"


def _format_hour(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    period = "AM" if moment.hour < 12 else "PM"
    return f"{hour} {period}"


def _format_clock(moment: datetime) -> str:
    hour = moment.hour % 12 or 12
    period = "AM" if moment.hour < 12 else "PM"
    return f"{hour}:{moment.minute:02d} {period}"


def _format_moment(unix: int, offset: int) -> str:
    moment = _local(unix, offset)
    return f"{_format_day(moment)}, {_format_clock(moment)}"


def format_temperature(celsius: float, unit: str = "celsius") -> str:
    if unit == FAHRENHEIT:
        return f"{round(celsius * 9 / 5 + 32)}°F"
    return f"{round(celsius)}°C"


def _wind(speed_ms: float, unit: str) -> str:
    if unit == FAHRENHEIT:
        return f"{speed_ms * MPH_PER_MS:.1f} mph"
    return f"{speed_ms:.1f} m/s"


def condition_kind(description: str) -> str:
    text = description.casefold()
    if "snow" in text or "sleet" in text:
        return "snow"
    if "thunder" in text:
        return "storm"
    if "rain" in text or "drizzle" in text:
        return "rain"
    if any(word in text for word in ("mist", "fog", "haze", "smoke", "dust")):
        return "mist"
    if any(
        phrase in text
        for phrase in ("few cloud", "scattered", "broken cloud", "partly")
    ):
        return "partly"
    if "cloud" in text or "overcast" in text:
        return "cloud"
    return "clear"


def _temperature(celsius: float, unit: str) -> str:
    return format_temperature(celsius, unit)


def _noon_distance(moment: datetime) -> float:
    noon = moment.replace(hour=12, minute=0, second=0, microsecond=0)
    return abs((moment - noon).total_seconds())
