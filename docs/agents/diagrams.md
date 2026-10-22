# UML diagrams

Read this when adding or editing the diagram pages.

The diagrams are static HTML outside Django, in a root `diagrams/` folder. Django does not serve them. `diagrams/index.html` links to five pages, one diagram each. Each page loads Mermaid from the internet and renders one diagram.

| Page | What it shows |
| --- | --- |
| Use case | Actors **User** and **OpenWeather**. "View place" includes "Load weather from OpenWeather." City search, postal search, and device location each include "Resolve the place with OpenWeather." "Choose among matches" extends city search only when several cities match. Register, confirm, log in, reset password, switch units, save favorite, and remove favorite are separate use cases. Save favorite notes that the account must be confirmed. |
| Class | Stored: **User**, **Favorite**, **ActionLink**. A user has zero or more favorites and zero or more links. Temporary, and marked as not stored: **Place**, **CurrentConditions**, **DailyForecast**. |
| Activity | The location journey from the weather page, with three forks: device location, city search (none / one / several), and postal code plus country. Successful branches end on that place's weather. Include refusal and no-match. |
| Sequence | Loading weather for a place already chosen. Browser to Django to OpenWeather for current conditions and the five-day forecast, then one page back. The key stays on the server. SQLite is not in this diagram. |
| State machine | The account. **Unconfirmed** cannot log in. **Confirmed** can. Register creates an unconfirmed account. A valid confirm link moves it to confirmed. Password reset does not change this state. |

Do not draw a second copy of the search journey as the state machine, and do not draw registration as the sequence diagram.
