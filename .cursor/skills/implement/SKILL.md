---
name: implement
description: Build one phase of a feature plan end to end. Invoke with /implement <feature> [phase N] [tdd|no-tdd] [notes]. Reads the PRD and plan, decides whether to delegate to the tdd skill, implements and tests the phase, writes a manual test guide, logs the session in PROMPTS.md, and offers to commit and push.
disable-model-invocation: true
---

# Implement

Build one phase of `plans/<feature>.md` against `prd/<feature>.md`, from
reading the plan through to the commit.

## 1. Find the phase

- **Feature**: the first argument (`product-reviews`, or
  `@plans/product-reviews.md`). If none was given, list `plans/` and ask
  which one.
- Read `plans/<feature>.md` and `prd/<feature>.md` in full. If either is
  missing, stop and say which.
- **Phase**: the number given. Otherwise, the first phase that still has an
  unticked acceptance criterion. Check it against
  `git log --oneline` (commits named "Phase N/M of …"). If the two disagree,
  ask.
- Anything else in the arguments is an instruction for this phase and
  outranks the plan. Everything not stated comes from the PRD and plan.
- Run `git status --short` and note any files already modified. They do not
  belong to this phase. If this directory is not a git repository, say so
  and skip the commit step later.

## 2. Gather context

- Read the plan's architectural decisions, the phase itself, and the PRD
  sections behind the phase's user stories. Where the plan says "per the
  PRD", the PRD's wording is authoritative.
- Read project instructions when they exist: `AGENTS.md`, `CLAUDE.md`, and
  `docs/TESTING.md`, plus any doc those files say to read before touching
  an area this phase changes. Skip a file that is not there.
- Read the code that earlier phases built, and the existing pattern closest
  to the one this phase needs. The plan often names that pattern.

Fill any gaps from the PRD first, then from the codebase's existing patterns.
Ask only when the answer is genuinely the user's call and it changes what gets
built.

## 3. Decide on TDD

Delegate to the `tdd` skill when the phase has at least one behavior where a
wrong implementation would be costly and easy to miss by eye:

- permissions, privacy, or who can see or change what
- eligibility and business rules
- state transitions, database constraints, or invariants
- calculations, aggregations, or queries with edge cases
- security: sign-in, tokens, cooldowns, an audit log
- a public function in a module the project treats as a deep module

Skip TDD when the phase is only templates, styling, copy, seed data,
configuration or documentation, or when it wires up something that follows
an existing, tested pattern without adding a new rule. If the user passed
`tdd` or `no-tdd`, that overrides this decision.

## 4. Brief, then stop once

Present all of this in one message:

- the phase title, plus a few lines on what will be built
- the areas and files expected to change, including any migrations
- the decisions you made where the plan left a gap
- the TDD decision: yes or no, with one sentence on why

**With TDD:** read and follow `.cursor/skills/tdd/SKILL.md` now and include
its behavior list in this message. The approval it asks for is this step's
stop.

**Without TDD:** stop for approval.

After approval, the only further stops are the ones the `tdd` cycles require
and any question that is genuinely the user's call.

## 5. Build

- Follow the conventions in `AGENTS.md` or `CLAUDE.md` when one of those
  files exists. Otherwise follow the patterns already in the code. Do not
  introduce a new framework, test runner, or layout for this phase.
- With TDD, follow the `tdd` skill's rules for the approved behaviors. Every
  other acceptance criterion still gets ordinary tests.
- If the data model changes, make the migration the project already uses.
  If the phase extends a seed command, run that seed twice to confirm it is
  idempotent.
- Stay inside the phase. If you notice something a later phase needs, note
  it; do not build it.
- Before finishing, run this project's test command and its lint and format
  commands. Find them in `package.json`, `pyproject.toml`, `Makefile`, or
  the docs from step 2. A Python project that already uses uv, pytest, and
  ruff is done only when `uv run pytest`, `uv run ruff check .`, and
  `uv run ruff format .` are clean. Never finish red. If something will not
  pass, report it with its output. If the repo has no tests yet, say so
  rather than inventing a runner.
- In the plan, tick each acceptance criterion (`- [x]`) once it is built and
  either covered by a test or checked by hand. Leave any unmet criterion
  unticked and explain why.

## 6. Manual test guide

Write it for the user to follow, and give it in the reply, not in a file.
If this phase has no user-visible behavior, say that in one sentence and
skip the rest of this step.

- **Setup**: the project's real commands, in order. Include a migration
  command only when this phase added migrations, and a seed command only
  when the seed changed (warn that it resets local data). Then the command
  that starts the app, with the URL to open.
- **Accounts**: which users to sign in as, with credentials taken from the
  project's seed or docs. Never guess them. Omit this when the feature has
  no accounts.
- **Walkthroughs**: numbered steps for each scenario: where to go, what to
  click or type, and what should happen. Cover the happy path, each role
  that sees something different, validation errors, and the edge cases named
  in the acceptance criteria.
- **What to look for**: exact wording, which part of the page updates, and
  counts or states after each action. If the layout changed, include phone
  width and each theme the app already has.
- **Signs of a problem**: the symptoms that would mean something is wrong.

Leave out anything the user cannot observe.

## 7. Log the session in PROMPTS.md

When the user runs `/implement`, that is their instruction to log the
session. If `PROMPTS.md` does not exist, create it with this header and
nothing else:

    # Prompts

    A log of /implement sessions. Newest entry first.

    ---

Add the new entry at the top: right after the `---` that ends the header,
above every earlier entry. Never edit an older entry. Use this shape:

    ## YYYY-MM-DD — <Feature>: Phase N/M, <phase title>

    ### Prompts

    1. The `/implement` skill, given `<arguments>`.
    2. Every later prompt, in order, including approvals and corrections.

    ### Summary

    - **Outcome:** what was built; the test count; lint status
    - **Changes:**
      - `path/to/file` — what changed and why
    - **TDD:** the behaviors driven by tests, or why the phase skipped TDD
    - **Decisions:** gaps in the plan that you filled, and how
    - **Deviations:** recommendations the user overrode, follow-up questions
    - **Sideways:** failures and wrong turns, and how they were caught

Write the entry before step 8, so a commit can include it.

## 8. Offer to commit and push

Skip this step when the directory is not a git repository. Say that, and
stop.

Show `git status --short`. Then propose a commit message that follows the
repo's history. When this feature has no earlier commits, use:

    Added Phase <N>/<M> of <Feature title> - <what the phase delivers>

For the feature title, use the one that earlier commits for this feature
used. If there are none, use the plan's title.

Ask in the reply. Offer "Commit and push", "Commit only", and "Don't
commit". Wait for the answer.

- Stage files one path at a time; never use `git add -A` or `git add .`.
  - Always stage: the files this phase changed, the plan, and `PROMPTS.md`.
  - Stage only if the user says to: files that were already modified before
    the phase began (from step 1), local databases, and the PRD if it is
    untracked. List them in the question.
- Commit on the current branch.
- If the push fails, report the error. Never force-push.
