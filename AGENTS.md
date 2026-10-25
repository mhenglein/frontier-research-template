# Research operating rules

The repository is the shared memory of the project. A chat, notebook, local
branch, or issue comment may contain useful context, but an important result is
not part of the project until it is recorded here.

## Before starting

Read these files in order:

1. `research/problem.md` for the exact question and notation.
2. `STATE.md` for the current frontier and active ownership.
3. `research/INDEX.md` and `research/registry.json` for existing records.
4. The relevant approach, claim, experiment, or conjecture record.

Search open issues and recent pull requests before repeating an approach. Use a
scoped issue claim for non-trivial research, review, formalization, tooling, or
documentation work. An unassigned record or a quiet branch is not free work.

## Established problem statement

Once the user approves the problem statement, `research/problem.md` is read-only
for agents unless the user explicitly authorizes a change. Record ambiguities
and proposed corrections in a GitHub Issue. Explore variants in separate
research records, clearly distinguishing them from the approved problem.

Update `STATE.md` and research records within your assigned scope as knowledge
changes. New findings do not authorize changes to the approved research target.

## Scientific method

- Take one precise question at a time. State the target, assumptions, and acceptable outcomes.
- Write an end-to-end route before substantial implementation or formalization.
- Define every object, constructor, transition, quantifier, and boundary case.
- Test the weakest statement that would answer the question. Do not replace a missing global argument with a growing list of local lemmas.
- Try targeted falsification early. Keep a direct independent predicate or checker for important witnesses and counterexamples.
- Separate conjectures, proof sketches, ordinary proofs, formal proofs, and bounded computation.
- A bounded or interrupted search is `UNKNOWN`, not `NO`.
- Record failed, repaired, and inconclusive attempts. Preserve the old argument and link the repair.
- Finish each investigation with result, evidence, confidence or status, limitations, implications, and one next question.
- If a claim changes, inspect its dependents and record which uses were rechecked. Do not silently leave an old claim at a known entry point.

## Canonical records

`research/registry.json` is the source for record metadata. `research/INDEX.md`
is generated. Stable IDs are never reused:

- `Axxx`: approach or workstream.
- `Cxxx`: exact mathematical claim.
- `Exxx`: reproducible experiment.
- `Qxxx`: open conjecture or structural hypothesis.

Each record has `id`, `title`, `status`, `path`, `owner`, `next_step`,
`depends_on`, `evidence`, and `reviews`. Evidence and review paths are
repository-relative. The checker enforces the record shape and status rules; it
does not prove mathematics. A `C` record marked `established` or `refuted` must
name both evidence and review paths.

Keep source papers in `sources/` with provenance and checksums. Keep dated
working notes in `notes/`. Keep compact, reproducible outputs in `results/`.
Never commit credentials, scratch exports, or extracted private data.

## Collaboration and integration

Exploration may be parallel. Integration is serialized and reviewed.

- Use a named branch and separate worktree for each implementation or proof attempt.
- Give each worker a base commit, exact question, allowed paths, dependencies, limits, and required evidence.
- Use one writer per path. Shared ledgers, generated indexes, import aggregators, and workflows need an explicit integrator.
- Research workers do not publish directly to `main`. An owner-authorized integrator reviews and validates the combined tree.
- Record a visible issue claim with session, base SHA, branch, write paths, excluded paths, validation plan, and local-only work.
- Release file ownership explicitly when stopping, completing, or handing off. A timestamp, missing assignee, or queued task does not release a path.
- Preserve disagreements and competing results until evidence resolves them. Do not overwrite a worker's branch or use force updates.

Before integration, re-read the current `main`, issue comments, and branch
heads. Check the actual patch and declarations, then run the relevant checks on
the combined tree. Record exact revisions and distinguish `PASS`, `FAIL`,
`PENDING`, `SKIPPED`, and `NOT RUN`. A skipped check is not a pass.

## Formalization and review

Use formalization when it resolves a named semantic risk, disputed implication,
or stable critical dependency. Keep existing proof interfaces stable while an
argument is still being explored. A compiled theorem is not a complete result
until its ordinary meaning, hypotheses, imported definitions, and dependency
scope have been read back.

Independent review should check definitions, quantifiers, both directions of a
reduction, imported theorem hypotheses, and coverage or termination. A second
implementation that repeats the same optimization is not independent evidence.

## Reproducibility

Record commands, inputs, seeds, limits, tool versions, source hashes, and the
commit used. Run the repository checks after organizational changes and the
experiment commands relevant to changed files. Run `scripts/reproduce.py` from
a clean committed checkout before calling a result reproducible.
