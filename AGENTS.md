# Weather application

Django weather site. Decisions are closed. Do not grill them again and do not invent scope.

Read this file at the start of a task. Open a linked document only when the task matches its line. Do not open every document up front.

## Always

- Stack: Python, Django, SQLite, uv, server-rendered templates, HTMX, Tailwind CSS and DaisyUI via django-tailwind-cli, Ruff, pytest.
- Secrets live only in a root `.env`. `.env` is gitignored. Never write a real API key, password, or token into source, tests, templates, docs, or commits.
- The browser talks only to this Django app. OpenWeather is called from the server.
- Weather readings are not stored. Accounts, favorites, and action links are.
- Common-practice assumptions in the linked docs are intentional. Do not stop to re-decide them.

## Read more only when needed

| When you are about to… | Read |
| --- | --- |
| Write the PRD, the plan, or change product behavior | `docs/agents/product.md` |
| Touch auth, sessions, links, redirects, or the weather client | `docs/agents/security.md` |
| Add or edit the Mermaid UML pages | `docs/agents/diagrams.md` |
| Write or run tests | `docs/TESTING.md` |
| Continue the current session's unfinished work | `HANDOFF.md` |

Once `prd/` and `plans/` exist, those files are the source for what to build. `HANDOFF.md` is only the bridge until they do.
