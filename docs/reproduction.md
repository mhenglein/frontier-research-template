# Reproduction protocol

Reproduction has three separate scopes: infrastructure, research experiments,
and optional formal checking. Report them separately in the receipt. A healthy
process exit is not enough to call a scientific result reproduced.

## Base checks

Use Python 3.11 or newer. Start from a clean, committed checkout and run:

```sh
python3 scripts/check.py
```

The default check validates registry structure, generated navigation, source
paths, and repository tests. It skips registered research experiments with
`NOT_RUN` unless the `--experiments` option is supplied. It does not silently
turn a skipped research run into a pass.

## Experiment manifest

`experiments/manifest.json` is the experiment runner's canonical input:

```json
{
  "version": 1,
  "experiments": [
    {
      "id": "E001",
      "command": ["{python}", "experiments/foo.py"],
      "timeout_seconds": 60,
      "mode": "acceptance"
    }
  ]
}
```

Each entry must have a registered `Exxx` record. `command` is an argument array;
`{python}` resolves to the selected Python executable. `timeout_seconds` is a
positive bound. `mode` is either `acceptance` or `diagnostic`.

The experiment process must finish with a final JSON object on stdout containing
`status` and `summary`:

```json
{"status":"PASS","summary":"all fixtures matched","cases":12}
```

The allowed statuses are `PASS`, `FAIL`, and `UNKNOWN`. A non-zero process exit
is `FAIL`. A bounded timeout is `UNKNOWN` after the runner terminates the child.
For `acceptance`, every experiment must return `PASS`. For `diagnostic`, an
`UNKNOWN` result is recorded as `INCONCLUSIVE`; it never produces an overall
`PASS`. Any `FAIL` fails the experiment gate.

Run registered experiments into a new, empty output directory:

```sh
python3 scripts/experiments.py --output work/experiment-run
```

The runner writes stdout/stderr logs and a summary receipt containing each experiment's result. Keep these
outputs linked from the corresponding `Exxx` record; do not edit receipts by
hand.

## Fresh-clone reproduction

To reproduce the exact local `HEAD`, with no uncommitted changes:

```sh
python3 scripts/reproduce.py --output /tmp/research-reproduction
```

Reproduction always runs the registered manifest. Add `--formal` to also run
the pinned formal job:

```sh
python3 scripts/reproduce.py \
  --output /tmp/research-reproduction \
  --formal
```

The receipt records the source revision, infrastructure checks, research
experiment results, formal result, commands, limits, and any unavailable scope.
Do not label the entire project reproduced when only infrastructure passed.

`gate` reports whether the required checks satisfied their contracts. The
separate `status` is `INFRASTRUCTURE_ONLY` for an empty research suite and
`INCONCLUSIVE` when diagnostic experiments return `UNKNOWN`. Such a diagnostic
run can exit zero because it ran correctly; inspect its receipt before using
the result. Acceptance experiments returning `UNKNOWN` fail the gate. An
experiment's own `PASS` means only that its stated, bounded checks passed.

Reproduction needs Git and a clean committed checkout. Its output directory
must be new and outside that checkout. Python and optional Lean must already be
installed; the runner does not reproduce the operating system or install tools.
On Linux and macOS, timeouts kill the experiment process group. On Windows,
only the directly launched process is terminated, so avoid spawned child jobs.

Only manifest entries are executed. The receipt lists registered experiment
IDs omitted from the manifest under `not_scheduled`, including historical runs.
Review that coverage before describing a whole research result as reproduced.
