# Optional Lean lane

This directory is an optional proof lane for a frontier-research repository.
The included theorem is an infrastructure smoke test. It says nothing about a
future project's scientific problem.

The pinned toolchain is Lean `v4.33.1`. From the repository root, run:

```sh
python3 scripts/check_formal.py
```

The check builds the package, checks the runtime version, audits every
declaration listed in `formal/audit.json`, and runs `lake env leanchecker
FrontierResearch` against the compiled `.olean`. `leanchecker` replays the
compiled declaration through Lean's kernel; it does not replace an independent
mathematical review.

When adding a reviewed formal claim:

1. Put definitions and theorems in a named module under `formal/`.
2. Add an `#print axioms` line for the declaration to `AxiomAudit.lean`.
3. Add its fully qualified name, source module, and permitted axioms to
   `formal/audit.json`.
4. Record the exact statement, quantifiers, hypotheses, and semantic mapping in
   the relevant research claim and review files.

The audit inventory is intentionally explicit. A declaration is not covered by
the formal check until it appears in both the Lean audit module and the JSON
inventory. A passing build or kernel replay does not promote a conjecture to an
established research result.
