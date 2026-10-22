# Testing

Read this when writing or running tests.

Commands, once the project exists:

- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format .`

Pytest must not call OpenWeather and must not read a real API key. `conftest.py` provides fixed payloads for geocoding, current weather, and the forecast.

Cover these behaviors:

- An unconfirmed account cannot log in. An expired confirm or reset link does not confirm the account or change the password.
- City search: no match, one match, and several matches.
- A visitor's unit stays in the session. A signed-in user's unit stays on the account and replaces the session unit at login.
- Favorites belong to one user. Saving the same pin (four decimal places) does not create a second row.
- A failed OpenWeather call leaves the last place on screen.
- The API key never appears in HTML.

Do not drive the browser location prompt from pytest. A place can be requested directly with the query string.
