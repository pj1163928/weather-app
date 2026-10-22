# Product decisions

Read this when writing the PRD or the plan, or when changing what the site does.

## Problem

People need a fast weather lookup for their current location and for any city or postal code. An account remembers favorites and the preferred unit. The project also produces UML diagrams and a tested Django app.

## Who can do what

Weather, search, the map, and the forecast are public. An account is required to keep favorites and to keep a unit choice across visits.

## Accounts

- Django sessions. Custom user from the first migration.
- Fields: username, email, password, temperature unit, and a separate confirmed flag. Django's active/inactive switch is not the confirmed flag.
- Username and email are both unique. Usernames cannot contain `@`. Login accepts either one: a value containing `@` is an email lookup, otherwise it is a username lookup.
- Registration shows a simulated confirmation message as a Django page. No email is sent. Login is refused until the confirm link is opened, with the message "Confirm your account first" and a way back to that message.
- "Show that message again" asks for a username or email. A still-valid confirmation link is shown again. An expired one is replaced.
- Password reset is a second simulated page. Each new request invalidates the previous reset link. After a successful reset, the person lands on the login form. The reset link does not start a session.
- Confirmation and reset links last 24 hours.
- Opening the confirm link marks the account confirmed and then shows the login form. It does not start a session.
- Passwords are entered twice on register and on reset, and use Django's built-in validators.
- Log in returns to the page the person left. Logout stays on the current place: favorites disappear and the unit switch falls back to the session.

## Units

Anyone can switch. Visitors store the choice in the session. Signed-in users store it on the account. New visitors and new accounts start on Celsius. On login, the account's unit replaces the session unit.

Metric is °C and wind in meters per second. Imperial is °F and wind in miles per hour.

## Finding a place

The weather page shows search immediately. While the browser asks for location, the page says "Finding your location…". If they allow it, that place loads. If they refuse, or the device cannot provide a location, a short note replaces that line and search stays usable. "Use my location" remains available.

Search has two modes. City search uses the city geocoder. No match shows a short message. One match opens that place. Two to five matches show a list (city, region when present, country) and wait for a choice. Postal search shows an alphabetical country dropdown and sends the two-letter code with the postal code. That lookup returns one place or none.

The selected place is stored in the query string: latitude, longitude, name, region, and country. Region may be empty. Refresh and the post-login return rebuild the label from that query string and do not geocode again. Conditions and the forecast are still loaded live.

## Weather page

Current conditions are the free OpenWeather fields: temperature, feels like, humidity, wind speed, cloudiness, pressure, and sunrise/sunset. UV is omitted.

The forecast is one card per day (date, short condition, high, low) plus an SVG line of the three-hour temperatures. Hover uses the browser tooltip for time, temperature, and condition. High, low, day labels, sunrise, and sunset use the place's local time from the timezone offset in the weather response.

HTMX updates the weather page only: city results, the selected place, the unit switch, and adding or removing a favorite. Account screens are full pages.

The Leaflet map is created once, outside the swapped fragment, on OpenStreetMap tiles. One marker shows the place name and current temperature. After a swap, a short script moves the map and the marker.

## Favorites

The list is on the weather page. A signed-in user can save the current place or a city-search row, open a saved place, and remove one. Newest save is at the top. Each user has their own list. A favorite stores the display name, region, country, latitude, and longitude. The same pin is not saved twice: latitude and longitude match to four decimal places. A visitor who chooses save goes to login and returns to that place.

## When OpenWeather fails

The weather panel shows a short message and no stack trace. A place already on screen stays, including the map marker. A first visit with nothing loaded shows the message and no marker. Search stays usable.

## Assumptions

These were accepted as common practice. Do not re-open them.

- The interface and weather descriptions are in English.
- Humidity and cloudiness are percents. Pressure stays in hPa in both unit modes.
- One Django project. An `accounts` app owns the user and action links. A `weather` app owns favorites, pages, and the OpenWeather client.
- The map shows the usual OpenStreetMap credit.
- The country dropdown is the English ISO country list, alphabetical.
- `.env.example` names `OPENWEATHER_API_KEY` and the Django secret with empty placeholders. The real key is never copied into the repo.

## Out of scope

Real email delivery, UV and the One Call product, stored weather history, JWT, favorite nicknames or drag-to-reorder, Chart.js, more than one map marker, and favorites for visitors.
