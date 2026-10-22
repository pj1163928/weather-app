# Weather app

## Problem Statement

People need a fast weather lookup for where they are and for any city or postal code. An account should remember favorite places and a preferred temperature unit across visits. The project also needs a tested Django site and UML diagrams of that behavior.

## Solution

A server-rendered weather site. Anyone can search, use device location, read current conditions and the forecast, switch units, and see the place on a map. An account keeps favorites and the unit choice. Confirmation and password reset are simulated pages on the site. Five static UML diagrams document the design beside the app.

## User Stories

1. As a visitor, I want search available as soon as the weather page loads, so that I can look up a place immediately.
2. As a visitor, I want the page to say "Finding your location…" while the browser asks for my location, so that I know a lookup is in progress.
3. As a visitor, I want my current location to load when I allow it, so that I see weather for where I am.
4. As a visitor, I want a short note when I refuse location or the device cannot provide it, so that I understand why weather did not load.
5. As a visitor, I want "Use my location" to remain available, so that I can try location again.
6. As a visitor, I want to search by city, so that I can look up a named place.
7. As a visitor, I want a short message when a city search has no match, so that I know to try another name.
8. As a visitor, I want one city match to open that place, so that I see its weather without an extra step.
9. As a visitor, I want two to five city matches listed as city, region when present, and country, so that I can choose the right place.
10. As a visitor, I want to search by postal code with an alphabetical country list, so that I can look up a postal area.
11. As a visitor, I want a postal lookup to open the one matching place or tell me there is none, so that I get a single clear result.
12. As a visitor, I want the chosen place kept in the page address, so that refresh and the return after login show the same place.
13. As a visitor, I want current conditions for temperature, feels like, humidity, wind speed, cloudiness, pressure, and sunrise and sunset, so that I can read the weather now.
14. As a visitor, I want one forecast card per day with the date, a short condition, the high, and the low, so that I can see the coming days.
15. As a visitor, I want a line of the three-hour temperatures, with the browser tooltip showing time, temperature, and condition, so that I can inspect the short-term trend.
16. As a visitor, I want highs, lows, day labels, sunrise, and sunset in the place's local time, so that the times match that location.
17. As anyone, I want to switch between Celsius with wind in meters per second and Fahrenheit with wind in miles per hour, so that I can read weather in familiar units.
18. As a new visitor, I want the site to start in Celsius, so that I have a predictable default.
19. As a visitor, I want my unit choice kept for the visit, so that later lookups in this browser use it.
20. As a signed-in user, I want my unit choice saved on my account, so that it follows me across visits.
21. As a signed-in user, I want my saved unit applied when I log in, so that my account preference is the one I see.
22. As a visitor, I want a map with one marker showing the place name and current temperature, so that I can see where the weather applies.
23. As a visitor, I want city results, the selected place, the unit switch, and favorite changes to update the weather page in place, so that the rest of the page stays put.
24. As a visitor, I want a short message when weather cannot be loaded, with search still usable, so that I can try another place.
25. As a visitor, I want a place already on screen, including its map marker, to remain when a later lookup fails, so that I keep the last successful result.
26. As a visitor on a first visit with nothing loaded, I want the failure message and no map marker, so that the page does not show a place it never found.
27. As a person, I want to register with a username, an email, and a password entered twice, so that I can create an account.
28. As a person who just registered, I want a page that shows a simulated confirmation message, so that I can confirm the account on the site.
29. As a person with an unconfirmed account, I want login refused with "Confirm your account first" and a way back to that message, so that I know what to do next.
30. As a person, I want to ask for the confirmation message again with a username or email, so that I can finish confirming later.
31. As a person, I want a still-valid confirmation link shown again and an expired one replaced, so that I always have a link I can open.
32. As a person, I want a valid confirmation link to confirm my account and then show the login form, so that I can sign in afterward.
33. As a person, I want a separate simulated page to reset my password, with the new password entered twice, so that I can replace a forgotten password on the site.
34. As a person, I want each new reset request to replace the previous reset link, so that only the latest link works.
35. As a person, I want a successful reset to leave me on the login form, so that I sign in with the new password.
36. As a person, I want to log in with either my username or my email, so that I can use whichever I remember.
37. As a person, I want login to return me to the page I left, so that I continue from the same place.
38. As a signed-in user, I want logout to keep me on the current place, so that I stay on the weather I was viewing.
39. As a signed-in user, I want my favorites on the weather page with the newest save at the top, so that I can return to places I care about.
40. As a signed-in user, I want to save the current place or a city-search row, open a saved place, and remove one, so that I manage my own list.
41. As a signed-in user, I want the same location saved only once, so that my list stays free of duplicate pins.
42. As a visitor who chooses save, I want to go to login and return to that place, so that I can keep it after I sign in.
43. As a reader of the project, I want five UML diagrams for use cases, classes, the location journey, loading weather, and the account, so that the design is documented beside the app.
44. As a maintainer, I want tests for confirmation, search, units, favorites, and failed lookups, so that those rules stay true as the site changes.

## Implementation Decisions

- One Django project on Python, SQLite, and uv. Pages are server-rendered templates. Styling is Tailwind CSS and DaisyUI through django-tailwind-cli. Partial updates use HTMX. Ruff and pytest are the lint and test tools.
- An accounts app owns the user and the confirmation and reset links. A weather app owns favorites, the weather pages, and the OpenWeather client.
- The browser talks only to this Django app. OpenWeather is called from the server. The service key, the Django secret, and any token salt live only in a root environment file. That file is gitignored before the first commit. An example file names `OPENWEATHER_API_KEY` and the Django secret with empty placeholders. The key stays out of templates, JavaScript, response HTML, query strings, and tests.
- Weather readings are loaded live and are not stored. Accounts, favorites, and action links are stored.
- The interface and weather descriptions are in English. Humidity and cloudiness are percents. Pressure stays in hPa in both unit modes.
- The user is a custom user from the first migration. Fields are username, email, password, temperature unit, and a separate confirmed flag. Django's active flag stays independent of confirmation. Username and email are both unique. Usernames cannot contain `@`.
- Login accepts username or email. A value containing `@` is an email lookup. Any other value is a username lookup. Login uses a Django session cookie. The address used to return after login is a relative path on this site. Logout stays on the current place: favorites disappear and the unit switch falls back to the session.
- Registration and password reset collect the password twice and use Django's built-in validators. Confirmation and reset are HTML pages on the site. There is no email backend and no email API.
- Confirmation and reset tokens are stored on the server, expire after 24 hours, and are single-purpose. A new reset link invalidates the previous one. Opening a valid confirm link marks the account confirmed and then shows the login form. A successful reset also shows the login form. Neither link starts a session.
- Visitors store the unit in the session. Signed-in users store it on the account. New visitors and new accounts start on Celsius. On login, the account unit replaces the session unit. Metric is °C and wind in meters per second. Imperial is °F and wind in miles per hour.
- City search uses the city geocoder. Postal search shows the English ISO country list in alphabetical order and sends the two-letter code with the postal code. Postal lookup returns one place or none.
- The selected place is stored in the query string: latitude, longitude, name, region, and country. Region may be empty. Refresh and the post-login return rebuild the label from that query string and do not geocode again. Conditions and the forecast are still loaded live.
- Current conditions use the free OpenWeather fields listed in the user stories. The forecast is one card per day plus an SVG line of the three-hour temperatures. Hover uses the browser tooltip. High, low, day labels, sunrise, and sunset use the place's local time from the timezone offset in the weather response.
- HTMX updates the weather page only: city results, the selected place, the unit switch, and adding or removing a favorite. Account screens are full pages.
- The Leaflet map is created once, outside the swapped fragment, on OpenStreetMap tiles, with the usual OpenStreetMap credit. One marker shows the place name and current temperature. After a swap, a short script moves the map and the marker.
- A failed OpenWeather call shows a short message and no stack trace. Search stays usable.
- A favorite stores the display name, region, country, latitude, and longitude. Each user has their own list. The same pin is not saved twice: latitude and longitude match to four decimal places.
- The diagrams are static HTML in a root diagrams folder. Django does not serve them. An index page links to five pages, and each page loads Mermaid from the internet and renders one diagram.
  - Use case: actors User and OpenWeather. "View place" includes "Load weather from OpenWeather." City search, postal search, and device location each include "Resolve the place with OpenWeather." "Choose among matches" extends city search only when several cities match. Register, confirm, log in, reset password, switch units, save favorite, and remove favorite are separate use cases. Save favorite notes that the account must be confirmed.
  - Class: stored types are User, Favorite, and ActionLink. A user has zero or more favorites and zero or more links. Place, CurrentConditions, and DailyForecast are temporary and marked as not stored.
  - Activity: the location journey from the weather page, with forks for device location, city search (none, one, or several), and postal code plus country. Successful branches end on that place's weather. Refusal and no-match are included.
  - Sequence: loading weather for a place already chosen. Browser to Django to OpenWeather for current conditions and the five-day forecast, then one page back. The key stays on the server. SQLite is absent from this diagram.
  - State machine: the account. Unconfirmed cannot log in. Confirmed can. Register creates an unconfirmed account. A valid confirm link moves it to confirmed. Password reset leaves this state unchanged.
- The test suite uses fixed payloads for geocoding, current weather, and the forecast. It does not call OpenWeather and does not read a real API key. It locks in these behaviors: an unconfirmed account cannot log in; an expired confirm or reset link does not confirm the account or change the password; city search covers no match, one match, and several matches; a visitor's unit stays in the session; a signed-in user's unit stays on the account and replaces the session unit at login; favorites belong to one user; saving the same pin to four decimal places does not create a second row; a failed OpenWeather call leaves the last place on screen; the API key never appears in HTML. The browser location prompt is not driven from the tests. A place can be requested directly with the query string. Once the project exists, the checks are `uv run pytest`, `uv run ruff check .`, and `uv run ruff format .`.

## Out of Scope

Real email delivery. UV and the One Call product. Stored weather history. JWT. Favorite nicknames or drag-to-reorder. Chart.js. More than one map marker. Favorites for visitors.

## Further Notes

The repo has no application code yet. A weather API key was pasted in an earlier planning chat. It is not part of the repo, and it must not be copied into source, tests, templates, docs, or commits. The person running the app puts the key in the local environment file.

The search journey is the activity diagram. Registration is not the sequence diagram. The account lifecycle is the state machine.
