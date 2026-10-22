# Plan: Weather app

> Source PRD: [prd/weather-app.md](../prd/weather-app.md)

## Architectural decisions

Durable decisions that apply across all phases. The repo has no application code yet. Phases below create it.

- **Reach.** The weather page is the home page, named `weather:home` at `/`. The chosen place is not a stored record. It is the query string `latitude`, `longitude`, `name`, `region`, and `country`. Region may be empty. Refresh and the return after login rebuild the label from that query string and do not geocode again. Conditions and the forecast are still loaded live. Account screens are full page loads. Weather-page updates that swap in place are city results, the selected place, the unit switch, and adding or removing a favorite.
- **Named routes.**
  - `weather:home` `/`
  - `weather:city-search` `/search/city/`
  - `weather:postal-search` `/search/postal/`
  - `weather:unit` `/units/`
  - `weather:favorite-add` `/favorites/add/`
  - `weather:favorite-remove` `/favorites/<pk>/remove/`
  - `accounts:register` `/accounts/register/`
  - `accounts:login` `/accounts/login/`
  - `accounts:logout` `/accounts/logout/`
  - `accounts:confirm` `/accounts/confirm/<token>/`
  - `accounts:confirm-again` `/accounts/confirm/`
  - `accounts:password-reset` `/accounts/password-reset/`
  - `accounts:password-reset-confirm` `/accounts/password-reset/<token>/`
- **Identity.** A place is the query string above. A favorite is removed by its primary key, and opening one copies its stored fields into that query string. Confirmation and reset links are addressed by an unguessable token. Login looks up a value containing `@` as an email and any other value as a username. The post-login return address is a relative path on this site.
- **Data.** Weather readings are not stored. The custom user is the project's first migration, installed before that migration runs, with fields username, email, password, temperature unit, and a separate confirmed flag. Django's active flag stays independent of confirmation. Username and email are both unique. Usernames cannot contain `@`. New accounts start on Celsius. An action link belongs to one user, is single-purpose (confirm or reset), is stored on the server, and expires after 24 hours. A new reset link invalidates the previous one. A favorite belongs to one user and stores the display name, region, country, latitude, and longitude. The same pin is not saved twice: latitude and longitude match to four decimal places. Visitors store the unit in the session. Signed-in users store it on the account. On login, the account unit replaces the session unit.
- **Owner.** One Django project. The `accounts` app owns the user and the action links. The `weather` app owns favorites, the weather pages, and the OpenWeather client. The browser talks only to this Django app. OpenWeather is called from the server.
- **Auth.** Django session cookie. An unconfirmed account cannot log in. Opening a confirm or reset link does not start a session. Logout stays on the current place.
- **Units and copy.** The interface and weather descriptions are in English. New visitors start on Celsius. Metric is °C and wind in meters per second. Imperial is °F and wind in miles per hour. Humidity and cloudiness are percents. Pressure stays in hPa in both modes.
- **Secrets and tests.** `OPENWEATHER_API_KEY`, the Django secret, and any token salt live only in a root `.env`. `.env` is gitignored before the first commit. `.env.example` names `OPENWEATHER_API_KEY` and the Django secret with empty placeholders. The key stays out of templates, JavaScript, response HTML, query strings, and tests. Tests use fixed payloads for geocoding, current weather, and the forecast. They do not call OpenWeather and do not read a real API key. A place can be requested directly with the query string. The browser location prompt is not driven from the tests. Once the project exists, the checks are `uv run pytest`, `uv run ruff check .`, and `uv run ruff format .`. Story 44 is satisfied by the tests inside the phases that own those behaviors.
- **Map and diagrams.** The Leaflet map is created once, outside the swapped fragment, on OpenStreetMap tiles, with the usual OpenStreetMap credit. One marker shows the place name and current temperature. After a swap, a short script moves the map and the marker. The five UML diagrams are static HTML in a root `diagrams/` folder. Django does not serve them.

Stack pinned by the PRD: Python, Django, SQLite, uv, server-rendered templates, HTMX, Tailwind CSS and DaisyUI via django-tailwind-cli, Ruff, and pytest.

---

## Phase 1: Weather for a place in the address

**User stories**: 12, 13, 14, 15, 16, 18, 22, 24, 25, 26, 44

### What to build

The project comes up as a server-rendered weather page. The custom user model is in place before the first migration, with Celsius as its default, and no account screens yet. Opening the home page with a place in the query string shows that place's current conditions, one forecast card per day, and an SVG line of the three-hour temperatures. High, low, day labels, sunrise, and sunset use the place's local time from the timezone offset in the weather response. Hover on the line uses the browser tooltip for time, temperature, and condition. The map sits outside the fragment later phases will swap, with one marker for that place. A failed OpenWeather call shows a short message and no stack trace. A place already on screen, including its marker, stays. A first visit with nothing loaded shows the message and no marker.

### Acceptance criteria

- [x] A query-string place renders temperature, feels like, humidity, wind speed, cloudiness, pressure, and sunrise and sunset, without geocoding again.
- [x] A new visitor sees Celsius, wind in meters per second, humidity and cloudiness as percents, and pressure in hPa.
- [x] The forecast is one card per day with the date, a short condition, the high, and the low, plus an SVG line of the three-hour temperatures whose browser tooltip shows time, temperature, and condition.
- [x] Highs, lows, day labels, sunrise, and sunset use the place's local time from the weather response's timezone offset.
- [x] The map is created once on OpenStreetMap tiles, with the usual credit, and one marker shows the place name and current temperature.
- [x] A failed lookup shows a short message and no stack trace. The last successful place and its marker remain. A first visit with nothing loaded shows the message and no marker.
- [x] Tests use fixed payloads, do not call OpenWeather, and the API key never appears in HTML.

### TDD recommendation

Recommend TDD for the three behaviors below, one test at a time. The rest of this phase, including the field layout, the SVG line, and the map, follows the normal implementation and testing process.

1. A failed lookup must leave the last successful place on screen, because the failure path is easy to ship as a blank page or a traceback, and the suite is required to lock it. Proposed test: load one query-string place from a fixed successful payload, then request a second place whose weather call fails. The response shows a short message, still shows the first place and its marker, and does not contain a traceback.
2. The API key must never reach the browser, because a template or a query string can leak it while the page still looks correct. Proposed test: render a successful place while settings hold a known dummy key. That value is absent from the response HTML.
3. Highs, lows, day labels, sunrise, and sunset must use the place's timezone offset, because UTC timestamps from the payload fall on the wrong local day when the offset is ignored. Proposed test: use a fixed forecast whose UTC times cross midnight at the place and whose offset is not zero. The day cards, the high, the low, sunrise, and sunset use the place's local dates.

---

## Phase 2: Finding a place

**User stories**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 23, 44

### What to build

The weather page shows search as soon as it loads. City search uses the city geocoder. No match shows a short message. One match opens that place. Two to five matches list city, region when present, and country, and wait for a choice. Postal search shows the English ISO country list in alphabetical order and sends the two-letter code with the postal code. That lookup opens the one matching place or says there is none. While the browser asks for location, the page says "Finding your location…". Allowing it loads that place. Refusing, or a device that cannot provide a location, replaces that line with a short note. "Use my location" stays available, and search stays usable. Choosing a place writes the query string and updates the weather page in place, including moving the map marker. Account screens stay full pages.

### Acceptance criteria

- [x] Search is on the weather page at first paint, including while location is being resolved and after a failed weather load.
- [x] City search covers no match, one match that opens the place, and a list of two to five matches shown as city, region when present, and country.
- [x] Postal search offers an alphabetical English country list and returns one place or none.
- [x] The page says "Finding your location…" while the browser asks. Allowing location loads that place. Refusal or an unavailable location shows a short note, and "Use my location" remains.
- [x] City results and the selected place update the weather page in place. The address bar keeps the place query string, and the map marker moves to the new place.
- [x] Tests cover city search for no match, one match, and several matches, using fixed geocoder payloads. They do not drive the browser location prompt.

### TDD recommendation

Recommend TDD for the three city-search outcomes below, one test at a time. Postal search, the location prompt, and the in-place map update follow the normal implementation and testing process. Tests use fixed geocoder payloads and do not drive the browser location prompt.

1. No match must show a message and leave the current place alone, because an empty result is easy to treat as a chosen city. Proposed test: submit a city whose fixed payload has no results. The response shows a short no-match message, and the place query string is unchanged.
2. One match must open that place, because a single result is easy to render as a list that still waits for a click. Proposed test: submit a city whose fixed payload has one result. The weather page updates to that place, and the query string carries its latitude, longitude, name, region, and country.
3. Several matches must wait for a choice, because two to five results are easy to collapse into the first hit. Proposed test: submit a city whose fixed payload has three results, one of them with an empty region. The response lists each match as city, region when present, and country, and the place query string stays on the place that was already open.

---

## Phase 3: Visitor unit switch

**User stories**: 17, 19, 23, 44

### What to build

Anyone on the weather page can switch units, and the page updates in place. The visitor's choice is stored in the session and used for later lookups in that browser. Metric shows °C and wind in meters per second. Imperial shows °F and wind in miles per hour. Pressure stays in hPa. The map marker's temperature updates with the switch.

### Acceptance criteria

- [x] The unit switch updates the weather page in place, including the marker temperature.
- [x] Celsius pairs with wind in meters per second. Fahrenheit pairs with wind in miles per hour. Pressure stays in hPa either way.
- [x] A visitor's choice persists in the session and is the unit used on the next lookup in that browser.
- [x] Tests show the visitor's unit stays in the session.

### TDD recommendation

This phase has no TDD candidates. The visitor's unit is one session value, and the acceptance test above can lock it once the switch exists.

---

## Phase 4: Register, confirm, and log in

**User stories**: 27, 28, 29, 30, 31, 32, 36, 37, 44

### What to build

A person can register with a username, an email, and a password entered twice. The password uses Django's built-in validators. Registration shows a simulated confirmation message as a Django page. No email is sent. Login is refused until the confirm link is opened, with the message "Confirm your account first" and a way back to that message. "Show that message again" asks for a username or email. A still-valid confirmation link is shown again. An expired one is replaced. Opening a valid confirm link marks the account confirmed and then shows the login form, without starting a session. Login accepts username or email and returns to the relative path the person left, including the place query string.

### Acceptance criteria

- [x] Registration collects username, email, and the password twice, rejects a username that contains `@`, and enforces Django's password validators. Username and email are unique.
- [x] A new account is unconfirmed. The confirmed flag is separate from Django's active flag. The account's unit starts at Celsius.
- [x] After registration, a Django page shows the simulated confirmation message. There is no email backend and no email API.
- [x] An unconfirmed login is refused with "Confirm your account first" and a way back to that message. A valid confirm link marks the account confirmed and shows the login form without starting a session. Links expire after 24 hours. An expired link does not confirm the account.
- [x] Asking again with a username or email shows a still-valid confirmation link again and replaces an expired one.
- [x] Login treats a value containing `@` as an email and any other value as a username, then returns to the relative path the person left.
- [x] Tests lock that an unconfirmed account cannot log in and that an expired confirm link does not confirm the account.

### TDD recommendation

Recommend TDD for the three behaviors below, one test at a time. Registration fields, password validators, and the simulated message page follow the normal implementation and testing process.

1. An unconfirmed account must not log in, because a user that is active in Django's sense can still be unconfirmed, and skipping the separate flag would open the account early. Proposed test: post the login form for an unconfirmed user with the right password. The response contains "Confirm your account first" and the client stays anonymous.
2. An expired confirm link must not confirm the account, because the flag is easy to set before the 24-hour expiry is checked. Proposed test: open a confirm link whose stored expiry is in the past. The account stays unconfirmed.
3. A valid confirm link must confirm the account without starting a session, because the link should change one flag and then show login, and it is easy to call `login` in the same request. Proposed test: open a confirm link that is still inside 24 hours. The account is confirmed, the response is the login form, and the client stays anonymous.

---

## Phase 5: Password reset

**User stories**: 33, 34, 35, 44

### What to build

A separate simulated page starts a password reset. No email is sent. The new password is entered twice and checked with Django's built-in validators. Each new request invalidates the previous reset link. A valid link sets the new password and shows the login form without starting a session. Confirmation state is unchanged. The link expires after 24 hours.

### Acceptance criteria

- [x] The reset page is separate from confirmation. No email is sent.
- [x] The new password is entered twice and checked with Django's built-in validators.
- [x] Each new reset request invalidates the previous reset link. A successful reset shows the login form and does not start a session.
- [x] An expired reset link does not change the password. Reset does not change whether the account is confirmed.
- [x] Tests lock that an expired reset link does not change the password.

### TDD recommendation

Recommend TDD for the three behaviors below, one test at a time. The simulated reset page and Django's password validators follow the normal implementation and testing process.

1. An expired reset link must not change the password, because expiry is a separate check from accepting the two password fields. Proposed test: submit a new password twice on a reset link whose stored expiry is in the past. The old password still authenticates, and the new one does not.
2. A new reset request must invalidate the previous link, because leaving the older token alive means a stale link can still set a password. Proposed test: issue two reset links for the same account. Submit a new password on the first link. The password is unchanged.
3. A successful reset must not start a session or change confirmation, because the same request that sets the password is easy to turn into a login or a confirm. Proposed test: complete a valid reset for an unconfirmed account. The new password is stored, the account stays unconfirmed, the response is the login form, and the client stays anonymous.

---

## Phase 6: Favorites

**User stories**: 23, 39, 40, 41, 42, 44

### What to build

A signed-in user sees their favorites on the weather page, newest save at the top. They can save the current place or a city-search row, open a saved place, and remove one. The list updates in place. A favorite stores the display name, region, country, latitude, and longitude. Each user has their own list. Saving the same pin again, matched to four decimal places, does not add a second row. A visitor who chooses save goes to login and, after a later sign-in, returns to that place.

### Acceptance criteria

- [x] The signed-in user's favorites appear on the weather page with the newest save first. Adding, opening, and removing update the page in place.
- [x] The current place and a city-search row can both be saved. Opening a favorite loads that place through the query string.
- [x] A favorite stores the display name, region, country, latitude, and longitude, and belongs only to that user.
- [x] Saving a pin whose latitude and longitude match an existing favorite to four decimal places does not create a second row.
- [x] A visitor who chooses save is sent to login and returns to that place after signing in.
- [x] Tests lock that favorites belong to one user and that the four-decimal-place pin is not saved twice.

### TDD recommendation

Recommend TDD for the two behaviors below, one test at a time. Listing, opening, and the visitor's redirect through login follow the normal implementation and testing process.

1. A favorite must belong to one user, because a missing owner check shows or deletes another account's places. Proposed test: user A saves a place. User B's weather page does not list it, and user B's request to the remove URL for that primary key leaves A's row in place.
2. The same pin must not be saved twice, because the match is to four decimal places, so a later save that differs only after that still has to hit the existing row. Proposed test: save a place, then save it again with latitude and longitude that match to four decimal places and differ after that. The user has one favorite row.

---

## Phase 7: Account unit and logout

**User stories**: 20, 21, 38, 44

### What to build

A signed-in user who switches units stores that choice on the account. Logging in applies the account unit and replaces whatever the session held. Logout stays on the current place: the favorites list disappears, and the unit switch falls back to the session.

### Acceptance criteria

- [x] Switching units while signed in saves the choice on the account and updates the weather page in place.
- [x] On login, the account unit replaces the session unit and is the unit the page shows.
- [x] Logout leaves the person on the current place, removes the favorites list, and leaves the unit switch on the session value.
- [x] Tests lock that a signed-in user's unit stays on the account and replaces the session unit at login.

### TDD recommendation

Recommend TDD for the two behaviors below, one test at a time. Logout returning to the current place follows the normal implementation and testing process.

1. A signed-in unit switch must be stored on the account, because writing only the session would lose the choice at the next login. Proposed test: as a signed-in user whose account is Celsius, switch to Fahrenheit. The account's temperature unit is Fahrenheit.
2. Login must replace the session unit with the account unit, because the browser can hold the opposite choice from the account, and the page has to show the account's. Proposed test: the session is Celsius and the account is Fahrenheit. After login, the weather page shows Fahrenheit and wind in miles per hour, and the session unit is Fahrenheit.

---

## Phase 8: UML diagrams

**User stories**: 43

### What to build

A root `diagrams/` folder of static HTML, not served by Django. An index page links to five pages. Each page loads Mermaid from the internet and renders one diagram. The search journey is the activity diagram. Registration is not the sequence diagram. The account lifecycle is the state machine.

### Acceptance criteria

- [x] `diagrams/index.html` links to five pages, and Django does not serve that folder.
- [x] Use case: actors User and OpenWeather. "View place" includes "Load weather from OpenWeather." City search, postal search, and device location each include "Resolve the place with OpenWeather." "Choose among matches" extends city search only when several cities match. Register, confirm, log in, reset password, switch units, save favorite, and remove favorite are separate use cases. Save favorite notes that the account must be confirmed.
- [x] Class: stored types are User, Favorite, and ActionLink. A user has zero or more favorites and zero or more links. Place, CurrentConditions, and DailyForecast are temporary and marked as not stored.
- [x] Activity: the location journey from the weather page, with forks for device location, city search (none, one, or several), and postal code plus country. Successful branches end on that place's weather. Refusal and no-match are included.
- [x] Sequence: loading weather for a place already chosen. Browser to Django to OpenWeather for current conditions and the five-day forecast, then one page back. The key stays on the server. SQLite is absent.
- [x] State machine: the account. Unconfirmed cannot log in. Confirmed can. Register creates an unconfirmed account. A valid confirm link moves it to confirmed. Password reset leaves this state unchanged.

### TDD recommendation

This phase has no TDD candidates. It is static HTML in `diagrams/`, and Django does not serve those pages, so there is no server behavior for a test to pin down before the pages exist.
