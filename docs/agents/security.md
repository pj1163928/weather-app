# Security

Read this when touching auth, sessions, links, redirects, or the OpenWeather client.

- `OPENWEATHER_API_KEY`, the Django secret, and any token salt belong in the root `.env`. Add `.env` to `.gitignore` before the first commit.
- Do not put the key in templates, JavaScript, response HTML, query strings, or tests. Tests use fixed fake payloads.
- If a key appeared in chat, do not paste it into the project. The person running the app puts it in `.env` locally.
- All OpenWeather calls go through Django. The client fetches only this app's URLs.
- Login is a Django session cookie. There is no JWT.
- The post-login return address must be a relative path on this site.
- An unconfirmed account cannot log in. Store that as its own boolean, not as Django's `is_active` flag.
- Confirmation and reset tokens are stored server-side, expire after 24 hours, and are single-purpose. A new reset link invalidates the previous one.
- Passwords use Django's built-in validators and are collected twice on register and reset.
- Simulated mail is an HTML page. Do not add an email backend or call an email API.
