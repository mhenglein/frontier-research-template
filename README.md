# Frontier research template

This repository is a starter for a hard, open research problem. It keeps the
scientific state, attempted routes, evidence, reviews, and reproducibility
checks in one clone that humans and agents can share.

It is a new implementation inspired by the structure and working practices of
[subtype-entailment](https://github.com/mhenglein/subtype-entailment), especially
its stable research records, explicit uncertainty, independent checking, and
fresh-clone reproduction. The reference snapshot was commit
`7df2216127d065e952e6b639a4074608df78ba7c`.

## Start a new problem

Use [Use this template](https://github.com/mhenglein/frontier-research-template/generate)
to create your own remote repository. If you are inspecting the starter itself,
clone it read-only; do not push project work back to the template repository.
Use Python 3.11 or newer. The default macOS `python3` can still be 3.9, so
check `python3 --version` first.

```sh
git clone https://github.com/YOUR-ACCOUNT/YOUR-PROBLEM.git my-problem
cd my-problem
python3 --version
python3 scripts/check.py
python3 scripts/research.py new A "First discriminating investigation"
```

Then edit `research/problem.md`, commit the problem statement, and create the
first issue or workstream before doing substantial research.

The repository can also be used as a GitHub template. Template settings do not
transfer to a repository created from it, so enable Issues, Actions, and the
research checks after the first workflow run. This template does not claim that
branch protection or required reviews are active.

## The working model

`research/problem.md` defines the question and its scope. `STATE.md` is the
short current frontier. `research/registry.json` is the canonical metadata for
approaches (`Axxx`), claims (`Cxxx`), experiments (`Exxx`), and conjectures
(`Qxxx`). `research/INDEX.md` is generated from that registry and is navigation,
not a second source of truth.

Each record names an owner, status, dependencies, evidence, reviews, and one
next step. Use `UNKNOWN` when a bounded search does not decide the question.
Record failed and inconclusive attempts so future work does not repeat them.

```sh
python3 scripts/research.py build
python3 scripts/research.py check
python3 scripts/research.py lookup A001  # after creating A001
python3 scripts/check.py
```

`scripts/reproduce.py` makes a clean temporary clone of the exact committed
checkout, reruns the base checks and registered experiments, and writes a
machine-readable receipt. Add `--formal` to include the pinned Lean audit:

Commit your problem setup and new records before running reproduction.

```sh
python3 scripts/reproduce.py --output /tmp/research-reproduction
# With the pinned Lean toolchain installed:
python3 scripts/reproduce.py --output /tmp/research-reproduction-formal --formal
```

The default checks skip registered research experiments with `NOT_RUN`. This
keeps a fresh clone useful before a project has configured its experiment
environment. See [the experiment protocol](docs/reproduction.md).

Optional formal support lives under `formal/` and is documented in
`formal/README.md`. If the pinned Lean toolchain is installed, run:

```sh
python3 scripts/check_formal.py
```

Formal checking is evidence for the checked declarations. It does not replace
an ordinary mathematical readback of definitions, quantifiers, hypotheses, or
the route from the input to the conclusion.

## First contribution

Read `AGENTS.md`, `research/problem.md`, and `STATE.md`. Search the registry and
existing approach records before opening a new route. Choose one exact question,
write a short proof outline or falsification plan, and claim only the files you
will edit. Use a named branch and separate worktree for implementation. Have an
independent person or checker review important claims before moving them to
`established` or `refuted`.

The project is progressing when it discharges a named obligation, rules out a
route, or improves the evidence for a claim. Commit counts, agent agreement,
and green syntax checks are useful signals but are not scientific results.

## License

The template is intended to be released under the MIT License. The repository's
`LICENSE` file is the legal source for that grant; add or retain it when you
publish a derived project.
