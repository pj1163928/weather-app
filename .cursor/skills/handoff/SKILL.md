---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up. Invoke with /handoff. An optional note after the command says what the next session will focus on.
disable-model-invocation: true
---

# Handoff

Write a handoff document summarizing the current conversation so a fresh agent can continue the work. Save to `HANDOFF.md` in the repository root, overwriting that file if it exists.

Include a "suggested skills" section listing skills that the agent should invoke.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.