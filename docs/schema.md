# Registry schema

`research/registry.json` is the canonical metadata store. It has one top-level
object:

```json
{
  "version": 1,
  "records": []
}
```

Each record has these required fields:

| Field | Type | Meaning |
|---|---|---|
| `id` | string | Stable ID matching `A001`, `C001`, `E001`, or `Q001`. IDs are never reused. |
| `title` | string | Short human-readable name. |
| `status` | string | One of the allowed values below for the ID family. |
| `path` | string | Repository-relative Markdown or source path containing the record. |
| `owner` | string | Current owner, or empty when unassigned. Active approaches need a named owner. Historical authors belong in the record. |
| `next_step` | string | One concrete next obligation or action. |
| `depends_on` | array of strings | IDs whose meaning or evidence this record relies on. Use `[]` when there are none. |
| `evidence` | array of strings | Repository-relative files, receipts, or source paths supporting the record. |
| `reviews` | array of strings | Repository-relative independent review files or linked review artifacts. |

The checker validates the shape, ID family, status vocabulary, path format,
references, and duplicate IDs. It is a navigation and consistency check. It
does not establish a mathematical claim.

## Status vocabulary

Use the status that describes the record's scientific state:

| ID family | Meaning | Allowed statuses |
|---|---|---|
| `A` | approach or workstream | `proposed`, `active`, `blocked`, `completed`, `abandoned` |
| `C` | exact mathematical claim | `conjectured`, `supported`, `established`, `refuted`, `superseded` |
| `E` | reproducible experiment | `planned`, `completed`, `inconclusive`, `failed` |
| `Q` | open conjecture or structural hypothesis | `open`, `resolved`, `superseded` |

An `A` can be `completed` even when the route does not solve the whole problem;
the record must state its result and remaining obligations. Use `abandoned` for
a route that will not be pursued, while preserving its evidence and failure.
Use `inconclusive` for an experiment that ran without deciding the question.

A `C` marked `established` or `refuted` must have at least one evidence path and
one independent review path. `supported` can record substantial but incomplete
evidence. Use `superseded` when a later statement replaces the claim; link the
replacement and preserve the original record.

## Editing records

Create an initial approach with the helper so its ID and record path are
consistent:

```sh
python3 scripts/research.py new A "First discriminating investigation"
```

For later metadata changes, edit the relevant object in
`research/registry.json`. Keep the scientific statement, proof, experiment
protocol, or review in the file named by `path`; the registry should remain a
compact index. Add evidence and review paths only after the files exist.

After any edit, regenerate and check the index:

```sh
python3 scripts/research.py build
python3 scripts/research.py check
python3 scripts/check.py
```

Use `lookup` to inspect one record and its linked content:

```sh
python3 scripts/research.py lookup A001
```

Do not hand-edit `research/INDEX.md`. Do not change a status to make a check
pass. A failed or bounded result belongs in the record with its limits, even
when a later result repairs the route.

Each file replacement is atomic, but a multi-file update is not a database
transaction. After an interrupted update, inspect unregistered files, preserve
their content, reconcile the registry, and regenerate the index. Keep one
writer for the registry. Never delete a record to recycle its ID.
