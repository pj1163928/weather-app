# Handoff

Next session: write the PRD, then a phased plan that TDD can execute. Do not build the Django project in that session until a plan phase is approved and the TDD skill has stopped for its own approvals.

The repo has no application code. Product decisions are closed and live in the docs below. Do not re-interview. The person asked to stop granular questions and to use common practice for anything left unstated.

## Suggested skills

Invoke in this order:

1. `to-prd` — write `prd/weather-app.md` from `docs/agents/product.md`, `docs/agents/security.md`, `docs/agents/diagrams.md`, and `docs/TESTING.md`. That skill says not to interview. Do not add scope.
2. `prd-to-plan` — write `plans/weather-app.md`. This is the skill that produces the plan. It may ask only whether the phase split is too coarse or too fine. Tracer-bullet slices, each one demoable through model, view, template, and tests.
3. `tdd` — only after the user approves a phase. Pick at most three behaviors, stop for approval, and follow that skill's red/green stops. Do not treat TDD as the way to write the PRD or the plan. Configuration, copy, and the Mermaid pages are not TDD candidates.

## Read first

- `AGENTS.md` — short index. Open linked docs only when needed.
- `docs/agents/product.md` — behavior, assumptions, and out of scope.
- `docs/agents/security.md` — secrets, proxy, sessions, links.
- `docs/agents/diagrams.md` — the five Mermaid pages.
- `docs/TESTING.md` — fake OpenWeather and the behaviors to lock in.

Do not duplicate those files into the PRD as new decisions. Synthesize them into the PRD template.

## Repo state

No Django project, no `prd/`, no `plans/`, no `.env`. `PROMPTS.md` is the AI usage log. An API key was pasted in chat during planning. It is not in the repo. Do not copy it into any file. `.env.example` may name the variable with an empty value.

## Out of scope for the next session

Implementing the app, drawing the final Mermaid pages, and calling OpenWeather.
