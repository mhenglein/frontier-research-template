# Experiments

Register each reproducible experiment as an `Exxx` record and add its runner to
`experiments/manifest.json`. Keep executable code in this directory and compact
outputs in `results/`.

The manifest has this shape:

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

Every `id` must have a matching `Exxx` registry record. Use `acceptance` for a
gate that must return `PASS`, and `diagnostic` for a probe whose `UNKNOWN`
result is useful but inconclusive. The command must print one final JSON line
on stdout with `status` (`PASS`, `FAIL`, or `UNKNOWN`) and `summary`.

```json
{"status":"PASS","summary":"all fixtures matched","cases":12}
```

The runner treats a non-zero process exit as `FAIL` and a bounded timeout as
`UNKNOWN` after terminating the child. Acceptance requires `PASS`. Diagnostic
`UNKNOWN` is recorded as `INCONCLUSIVE`; it never becomes an overall `PASS`.
Any `FAIL` fails the experiment gate.

Run the manifest into a new, empty directory:

```sh
python3 scripts/experiments.py --output work/experiment-run
```

The default `python3 scripts/check.py` skips research experiments with
`NOT_RUN`; use `--experiments` to execute them. Do not convert a timeout,
memory limit, or incomplete corpus into `NO`. Save the exact command, input
coverage, seeds, environment, commit, limits, independent checker, and what
the result does not establish.
