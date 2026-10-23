from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlencode, urlparse

from accounts.models import TemperatureUnit
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from weather.client import (
    WeatherUnavailable,
    fetch_place,
    fetch_snapshot,
    geocode_city,
    geocode_postal,
    reverse_geocode,
)
from weather.countries import COUNTRY_NAMES
from weather.lookup import classify_query
from weather.models import Favorite, pin_key, save_favorite
from weather.places import (
    Place,
    place_from_geocode,
    place_from_query,
    place_label,
    place_path,
)
from weather.present import condition_kind, display_context, format_temperature
from weather.spotlight import SPOTLIGHT

WEATHER_UNAVAILABLE = "Weather could not be loaded."
NO_CITY_MATCH = "No matching city."
NO_POSTAL_MATCH = "No matching place."
POSTAL_NEEDS_COUNTRY = "Add a country after that postal code, such as 10115, Germany."
LAST_PLACE_SESSION_KEY = "last_place"
UNIT_SESSION_KEY = "temperature_unit"
LOCATION_ACQUIRED_SESSION_KEY = "location_acquired"
MATCH_LIMIT = 5


def home(request):
    if request.GET.get("locate") == "1":
        return _from_device_location(request)
    place = place_from_query(request.GET)
    if place is None:
        return _render_home(request, {}, prompt_for_location=True)
    return _render_place(request, place)


def search(request):
    lookup = classify_query(request.GET.get("q") or "")
    if lookup is None:
        return _message(NO_CITY_MATCH)
    if lookup.kind == "postal":
        if not lookup.country_code:
            return _message(POSTAL_NEEDS_COUNTRY)
        return _open_postal(request, lookup.text, lookup.country_code)
    return _open_city(request, lookup.text)


def suggest(request):
    raw = " ".join((request.GET.get("q") or "").split())
    if len(raw) < 2:
        return HttpResponse("")
    lookup = classify_query(raw)
    if lookup is None or lookup.kind != "city":
        return HttpResponse("")
    try:
        matches = geocode_city(lookup.text, settings.OPENWEATHER_API_KEY)
    except WeatherUnavailable:
        return _message(WEATHER_UNAVAILABLE)
    places = _places_from_matches(matches)
    if not places:
        return HttpResponse("")
    return _render_choices(request, places, title="Suggestions")


def city_search(request):
    return _open_city(request, (request.GET.get("city") or "").strip())


def postal_search(request):
    postal = (request.GET.get("postal") or "").strip()
    code = (request.GET.get("country") or "").strip().upper()
    if not postal or code not in COUNTRY_NAMES:
        return _message(NO_POSTAL_MATCH)
    return _open_postal(request, postal, code)


def unit(request):
    if request.method != "POST":
        return redirect("weather:home")
    chosen = (request.POST.get("unit") or "").strip()
    if chosen in TemperatureUnit.values:
        request.session[UNIT_SESSION_KEY] = chosen
        if request.user.is_authenticated:
            request.user.temperature_unit = chosen
            request.user.save(update_fields=["temperature_unit"])
    place = _place_on_page(request)
    if not _is_htmx(request):
        if place is None:
            return redirect("weather:home")
        return redirect(_place_push_url(place))
    if place is None:
        response = _fragment_response(
            request,
            {},
            include_unit_switch=True,
            refresh_spotlight=True,
        )
    else:
        response = _render_place(request, place, include_unit_switch=True)
    response["HX-Trigger"] = "unit-changed"
    return response


@never_cache
def here(request):
    try:
        latitude = float(request.GET["latitude"])
        longitude = float(request.GET["longitude"])
    except (KeyError, TypeError, ValueError):
        return HttpResponse("")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return HttpResponse("")
    api_key = settings.OPENWEATHER_API_KEY
    try:
        matches = reverse_geocode(latitude, longitude, api_key)
        celsius, description = fetch_snapshot(latitude, longitude, api_key)
    except WeatherUnavailable:
        return HttpResponse("")
    if not matches:
        return HttpResponse("")
    found = place_from_geocode(matches[0])
    if found is None:
        return HttpResponse("")
    place = Place(
        latitude=latitude,
        longitude=longitude,
        name=found.name,
        region=found.region,
        country=found.country,
    )
    return render(
        request,
        "weather/_here.html",
        {
            "name": place.name,
            "region": place.region,
            "country": place.country,
            "temperature": format_temperature(celsius, session_unit(request)),
            "condition": description,
            "kind": condition_kind(description),
            "url": _place_push_url(place),
        },
    )


def spotlight(request):
    cards = [_spotlight_card(place) for place in SPOTLIGHT]
    api_key = settings.OPENWEATHER_API_KEY
    if api_key:
        _fill_snapshots(cards, api_key, session_unit(request))
    return render(request, "weather/_spotlight_cards.html", {"cards": cards})


def saved(request):
    return HttpResponse(_saved_cards_html(request))


def _open_city(request, city: str):
    if not city:
        return _message(NO_CITY_MATCH)
    try:
        matches = geocode_city(city, settings.OPENWEATHER_API_KEY)
    except WeatherUnavailable:
        return _message(WEATHER_UNAVAILABLE)
    places = _places_from_matches(matches)
    if len(places) == 1:
        return _render_place(request, places[0], push_url=True, results_target=True)
    if not places:
        return _message(NO_CITY_MATCH)
    return _render_choices(request, places)


def _open_postal(request, postal: str, code: str):
    match = geocode_postal(postal, code, settings.OPENWEATHER_API_KEY)
    place = place_from_geocode(match) if match else None
    if place is None:
        return _message(NO_POSTAL_MATCH)
    return _render_place(request, place, push_url=True, results_target=True)


def _from_device_location(request):
    try:
        latitude = float(request.GET["latitude"])
        longitude = float(request.GET["longitude"])
    except (KeyError, TypeError, ValueError):
        return _location_failure(request)
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return _location_failure(request)
    try:
        matches = reverse_geocode(
            latitude,
            longitude,
            settings.OPENWEATHER_API_KEY,
        )
    except WeatherUnavailable:
        return _location_failure(request)
    if not matches:
        return _location_failure(request)
    found = place_from_geocode(matches[0])
    if found is None:
        return _location_failure(request)
    place = Place(
        latitude=latitude,
        longitude=longitude,
        name=found.name,
        region=found.region,
        country=found.country,
    )
    request._mark_location_acquired = True
    return _render_place(request, place, push_url=True)


def _location_failure(request):
    context = _failed_context(request)
    if _is_htmx(request):
        return _fragment_response(request, context)
    return _render_home(request, context, prompt_for_location=False)


def _render_place(
    request,
    place,
    *,
    push_url=False,
    results_target=False,
    include_unit_switch=False,
):
    try:
        weather = fetch_place(
            place.latitude,
            place.longitude,
            settings.OPENWEATHER_API_KEY,
        )
    except WeatherUnavailable:
        if results_target:
            return _message(WEATHER_UNAVAILABLE)
        context = _failed_context(request)
        if push_url or _is_htmx(request):
            return _fragment_response(
                request,
                context,
                include_unit_switch=include_unit_switch,
            )
        return _render_home(request, context, prompt_for_location=False)
    if getattr(request, "_mark_location_acquired", False):
        request.session[LOCATION_ACQUIRED_SESSION_KEY] = True
    context = display_context(place, weather, session_unit(request))
    request.session[LAST_PLACE_SESSION_KEY] = context
    if results_target or _is_htmx(request):
        push_place = None
        if not include_unit_switch and (push_url or _is_htmx(request)):
            push_place = place
        return _fragment_response(
            request,
            context,
            place=push_place,
            retarget=results_target,
            clear_results=not include_unit_switch,
            include_unit_switch=include_unit_switch,
        )
    response = _render_home(request, context, prompt_for_location=False)
    if push_url:
        response["HX-Push-Url"] = _place_push_url(place)
    return response


def _places_from_matches(matches) -> list[Place]:
    places = []
    for match in matches:
        place = place_from_geocode(match)
        if place is not None:
            places.append(place)
    return places[:MATCH_LIMIT]


def _render_choices(request, places, title="Choose a place"):
    rows = [
        {
            "label": place_label(place),
            "url": _place_push_url(place),
            "name": place.name,
            "region": place.region,
            "country": place.country,
            "latitude": place.latitude,
            "longitude": place.longitude,
        }
        for place in places
    ]
    return render(
        request,
        "weather/_city_results.html",
        {"places": rows, "title": title},
    )


def _render_home(request, context, *, prompt_for_location):
    page = {
        **context,
        "prompt_for_location": prompt_for_location,
        "unit": session_unit(request),
    }
    if not context.get("name") and not context.get("error"):
        page["cards"] = [_spotlight_card(place) for place in SPOTLIGHT]
    return render(request, "weather/home.html", page)


def _fragment_response(
    request,
    context,
    place=None,
    *,
    retarget=False,
    clear_results=False,
    include_unit_switch=False,
    refresh_spotlight=False,
):
    html = render_to_string("weather/_weather.html", context, request=request)
    if clear_results:
        html += '<div id="city-results" hx-swap-oob="innerHTML"></div>'
        html += '<section id="spotlight" hx-swap-oob="outerHTML"></section>'
    if include_unit_switch:
        html += render_to_string(
            "weather/_unit_switch.html",
            {"unit": session_unit(request), "oob": True},
            request=request,
        )
    if refresh_spotlight and settings.OPENWEATHER_API_KEY:
        html += _spotlight_refresh(request)
    if include_unit_switch and request.user.is_authenticated:
        html += _saved_cards_html(request, oob=True)
    html += _save_place_html(request, context, oob=True)
    response = HttpResponse(html)
    if place is not None:
        response["HX-Push-Url"] = _place_push_url(place)
    if retarget:
        response["HX-Retarget"] = "#weather"
        response["HX-Reswap"] = "outerHTML"
    return response


def _failed_context(request) -> dict:
    context = {"error": WEATHER_UNAVAILABLE}
    last_place = request.session.get(LAST_PLACE_SESSION_KEY)
    if last_place:
        context.update(last_place)
    return context


def _message(text: str) -> HttpResponse:
    return HttpResponse(f'<p class="alert w-full">{text}</p>')


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def session_unit(request) -> str:
    stored = request.session.get(UNIT_SESSION_KEY)
    if stored in TemperatureUnit.values:
        return stored
    return TemperatureUnit.CELSIUS


def _place_on_page(request) -> Place | None:
    for header in ("HX-Current-URL", "Referer"):
        raw = request.headers.get(header)
        if not raw:
            continue
        place = place_from_query(_query_params(raw))
        if place is not None:
            return place
    return None


def _query_params(url: str) -> dict[str, str]:
    parsed = parse_qs(urlparse(url).query, keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items() if values}


def _place_push_url(place) -> str:
    return place_path(place)


def _spotlight_card(place: Place, temperature: str = "", condition: str = "") -> dict:
    return {
        "name": place.name,
        "country": place.country,
        "url": _place_push_url(place),
        "temperature": temperature,
        "condition": condition,
        "latitude": place.latitude,
        "longitude": place.longitude,
    }


def _fill_snapshots(cards: list[dict], api_key: str, unit: str) -> None:
    def load(card: dict) -> dict:
        try:
            celsius, description = fetch_snapshot(
                card["latitude"],
                card["longitude"],
                api_key,
            )
        except WeatherUnavailable:
            return card
        card["temperature"] = format_temperature(celsius, unit)
        card["condition"] = description
        card["kind"] = condition_kind(description)
        return card

    with ThreadPoolExecutor(max_workers=len(cards)) as pool:
        list(pool.map(load, cards))


def _favorite_cards(request) -> list[dict]:
    if not request.user.is_authenticated:
        return []
    cards = []
    for favorite in request.user.favorites.all():
        card = _spotlight_card(favorite.as_place())
        card.update(
            pk=favorite.pk,
            display_label=favorite.display_label(),
            open_path=favorite.open_path(),
        )
        cards.append(card)
    if cards and settings.OPENWEATHER_API_KEY:
        _fill_snapshots(cards, settings.OPENWEATHER_API_KEY, session_unit(request))
    return cards


def _saved_cards_html(
    request, *, oob: bool = False, cards: list[dict] | None = None
) -> str:
    if cards is None:
        cards = _favorite_cards(request)
    return render_to_string(
        "weather/_saved_cards.html",
        {"cards": cards, "oob": oob},
        request=request,
    )


def _spotlight_refresh(request) -> str:
    cards = [_spotlight_card(place) for place in SPOTLIGHT]
    _fill_snapshots(cards, settings.OPENWEATHER_API_KEY, session_unit(request))
    inner = render_to_string(
        "weather/_spotlight_cards.html",
        {"cards": cards},
        request=request,
    )
    return f'<div id="spotlight-cards" hx-swap-oob="innerHTML">{inner}</div>'


def _save_place_context(request, source, *, oob: bool) -> dict:
    place = None
    name = source.get("name")
    latitude = source.get("latitude")
    longitude = source.get("longitude")
    if name and latitude not in (None, "") and longitude not in (None, ""):
        place = Place(
            latitude=float(latitude),
            longitude=float(longitude),
            name=name,
            region=source.get("region") or "",
            country=source.get("country") or "",
        )
    saved = False
    if place is not None and request.user.is_authenticated:
        saved = Favorite.objects.filter(
            user=request.user,
            pin=pin_key(place.latitude, place.longitude),
        ).exists()
    return {
        "oob": oob,
        "place": place,
        "saved": saved,
        "place_url": place_path(place) if place is not None else "",
        "user": request.user,
    }


def _save_place_html(request, context, *, oob: bool) -> str:
    return render_to_string(
        "weather/_save_place.html",
        _save_place_context(request, context, oob=oob),
        request=request,
    )


def _saved_places_html(request, cards: list[dict] | None = None) -> str:
    if cards is None:
        cards = _favorite_cards(request)
    return render_to_string(
        "weather/_saved_places.html",
        {"favorites": cards},
        request=request,
    )


def saved_list(request):
    return HttpResponse(_saved_places_html(request))


def _favorites_response(request, context: dict | None = None) -> HttpResponse:
    if context is None:
        context = request.session.get(LAST_PLACE_SESSION_KEY) or {}
    cards = _favorite_cards(request)
    html = _saved_places_html(request, cards)
    html += _save_place_html(request, context, oob=True)
    html += _saved_cards_html(request, oob=True, cards=cards)
    return HttpResponse(html)


@require_POST
def favorite_add(request):
    place = place_from_query(request.POST)
    if place is None:
        return redirect("weather:home")
    if not request.user.is_authenticated:
        login = reverse("accounts:login")
        query = urlencode({"next": place_path(place)})
        return redirect(f"{login}?{query}")
    save_favorite(request.user, place)
    if _is_htmx(request):
        return _favorites_response(request)
    return redirect(place_path(place))


@require_POST
def favorite_remove(request, pk: int):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    owned = Favorite.objects.filter(pk=pk, user=request.user)
    if not owned.exists():
        return HttpResponse(status=404)
    owned.delete()
    if _is_htmx(request):
        return _favorites_response(request)
    from accounts.views import next_path

    return redirect(next_path(request, request.POST.get("next")))
