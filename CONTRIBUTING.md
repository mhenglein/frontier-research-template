# Contributing research

This guide is for a new contributor joining a frontier problem. Read
`AGENTS.md` for the full operating rules.

## Choose and claim work

1. Read `research/problem.md`, `STATE.md`, and the relevant records.
2. Find an open obligation or a useful next step in an existing approach.
3. Search issues and approach history before repeating an idea.
4. Post a scoped issue claim before non-trivial work:

```text
Actor/session and role:
Related approach, claim, experiment, or conjecture:
Status: ACTIVE / READY_FOR_INTEGRATION / BLOCKED / SUPERSEDED / ARCHIVE / INTEGRATED
Base commit; branch/worktree; pushed HEAD:
Exact question and deliverable:
Owned write paths:
Read-only or excluded paths:
Dependencies and limits:
Validation plan:
Local-only work: unpushed / staged / unstaged / untracked / not inspected
```

5. Use the record registry for current status and ownership. An issue refines a
   task; it does not replace the registry.

## Record an attempt

Use `templates/attempt.md` for every meaningful investigation, including a
failure or an inconclusive result. Include the exact statement, assumptions,
commands or proof, result, evidence, and what the result does not establish.

```sh
python3 scripts/research.py new A "Short route name"
python3 scripts/research.py lookup A001
python3 scripts/research.py build
```

Use `templates/proof-outline.md` before substantial supporting implementation
or formalization. A cheap falsification test can begin before the outline is
complete.

## Verify and hand off

Run the smallest relevant checks, then the full base check when practical:

```sh
python3 scripts/check.py
git diff --check
```

For a reproducibility handoff, include the exact commit, changed paths,
commands, results, source hashes, remaining obligations, and released or
retained file claims. `READY_FOR_INTEGRATION` means a pushed, commit-pinned
contribution with this evidence. It does not mean an agent stopped working.

The integrator rechecks the current combined tree, updates affected ledgers and
indexes, and records the final main commit. Do not promote a claim because an
issue closed or a test passed.
