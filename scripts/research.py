#!/usr/bin/env python3
"""Manage a small research ledger. Checks validate records, never scientific truth."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {
    "A": ("Approaches", "research/approaches", "proposed",
          {"proposed", "active", "blocked", "completed", "abandoned"}),
    "C": ("Claims", "research/claims", "conjectured",
          {"conjectured", "supported", "established", "refuted", "superseded"}),
    "E": ("Experiments", "experiments/records", "planned",
          {"planned", "completed", "inconclusive", "failed"}),
    "Q": ("Questions", "research/questions", "open",
          {"open", "resolved", "superseded"}),
}
ID = re.compile(r"[ACEQ][0-9]{3,}\Z")


def atomic_write(path: Path, content: str) -> None:
    """Replace one complete file; cross-file integration still has one writer."""
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False, encoding="utf-8") as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def local_file(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError(f"Expected repository-relative file: {name!r}")
    target = (root / name).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f"Missing or outside-repository file: {name}")
    return target


def load(root: Path = ROOT) -> dict:
    data = json.loads((root / "research/registry.json").read_text())
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("records"), list):
        raise ValueError("registry.json must have version 1 and a records array")
    return data


def validate(data: dict, root: Path = ROOT) -> None:
    records = data["records"]
    by_id = {}
    paths = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each record must be an object")
        rid = record.get("id", "")
        if not isinstance(rid, str) or not ID.fullmatch(rid) or rid in by_id:
            raise ValueError(f"Invalid or duplicate ID: {rid!r}")
        for field in ("title", "path", "status", "owner", "next_step"):
            if not isinstance(record.get(field), str):
                raise ValueError(f"{rid}: {field} must be a string")
        if not record["title"].strip() or "\n" in record["title"]:
            raise ValueError(f"{rid}: title must be nonempty and on one line")
        if record["status"] not in KINDS[rid[0]][3]:
            raise ValueError(f"{rid}: invalid status {record['status']!r}")
        path = local_file(root, record["path"])
        if path in paths:
            raise ValueError(f"{rid}: record path already registered")
        paths.add(path)
        content = path.read_text()
        if not content.startswith(f"# {rid}: "):
            raise ValueError(f"{rid}: record must start with '# {rid}: '")
        for field in ("depends_on", "evidence", "reviews"):
            values = record.get(field)
            if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                raise ValueError(f"{rid}: {field} must be an array of strings")
            if len(values) != len(set(values)):
                raise ValueError(f"{rid}: duplicate {field} entry")
        for name in record["evidence"] + record["reviews"]:
            local_file(root, name)
        if rid.startswith("A") and record["status"] == "active":
            if record["owner"].strip().lower() in {"", "unassigned"} or not record["next_step"].strip():
                raise ValueError(f"{rid}: active approaches need an owner and next step")
        if rid.startswith("C") and record["status"] in {"established", "refuted"}:
            if not record["evidence"] or not record["reviews"]:
                raise ValueError(f"{rid}: accepted claims require evidence and independent review records")
        by_id[rid] = record
    for rid, record in by_id.items():
        for dep in record["depends_on"]:
            if dep not in by_id:
                raise ValueError(f"{rid}: unknown dependency {dep}")
            if record["status"] == "established" and by_id[dep]["status"] in {"refuted", "superseded"}:
                raise ValueError(f"{rid}: established claim depends on {dep}, which needs reassessment")
        content = local_file(root, record["path"]).read_text()
        for ref in re.findall(r"\b[ACEQ][0-9]{3,}\b", content):
            if ref not in by_id:
                raise ValueError(f"{rid}: unregistered reference {ref}")
    visiting, visited = set(), set()

    def visit(rid):
        if rid in visiting:
            raise ValueError(f"Circular dependency at {rid}")
        if rid in visited:
            return
        visiting.add(rid)
        for dep in by_id[rid]["depends_on"]:
            visit(dep)
        visiting.remove(rid)
        visited.add(rid)

    for rid in by_id:
        visit(rid)


def render(data: dict) -> str:
    lines = ["# Research index", "", "Generated from [registry.json](registry.json). Run `python3 scripts/research.py build`.",
             "", "Status describes recorded evidence, not an automated judgment of scientific truth.", ""]
    for prefix, (label, _, _, _) in KINDS.items():
        lines += [f"## {label}", ""]
        records = sorted((r for r in data["records"] if r["id"].startswith(prefix)), key=lambda r: r["id"])
        if not records:
            lines += ["No records yet.", ""]
        for r in records:
            title = r["title"].replace("[", "\\[").replace("]", "\\]")
            lines += [f"- [{r['id']}: {title}](../{r['path']}) ({r['status']})",
                      f"  - Owner: {r['owner'] or 'unassigned'}",
                      f"  - Next: {r['next_step'] or 'not recorded'}", ""]
    return "\n".join(lines)


def build(root: Path = ROOT, check: bool = False) -> None:
    data = load(root)
    validate(data, root)
    text = render(data)
    index = root / "research/INDEX.md"
    if check:
        if not index.is_file() or index.read_text() != text:
            raise ValueError("research/INDEX.md is stale; run python3 scripts/research.py build")
    else:
        atomic_write(index, text)


def new_record(kind: str, title: str, root: Path = ROOT) -> str:
    data = load(root)
    validate(data, root)
    if not title.strip() or "\n" in title or "\r" in title:
        raise ValueError("Provide a nonempty single-line title")
    number = max((int(r["id"][1:]) for r in data["records"] if r["id"].startswith(kind)), default=0) + 1
    rid = f"{kind}{number:03d}"
    known = {r["id"] for r in data["records"]} | {rid}
    for ref in re.findall(r"\b[ACEQ][0-9]{3,}\b", title):
        if ref not in known:
            raise ValueError(f"Unregistered reference in title: {ref}")
    _, directory, status, _ = KINDS[kind]
    path = f"{directory}/{rid}.md"
    target = root / path
    if target.exists():
        raise ValueError(f"Refusing to overwrite unregistered file: {path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    headings = {
        "A": ["Exact question and assumptions", "Proposed route and missing steps", "Dated attempts", "Evidence and limitations", "Next discriminating test"],
        "C": ["Exact statement and assumptions", "Evidence and verification scope", "Independent review", "Dependencies and affected claims", "Limitations and corrections"],
        "E": ["Hypothesis and coverage", "Command, inputs, seeds and limits", "Result and source revision", "Independent checker", "What this does not establish"],
        "Q": ["Exact question and assumptions", "Why it matters", "Candidate routes", "Discriminating test", "Resolution and remaining scope"],
    }
    content = f"# {rid}: {title}\n\nStatus, owner, dependencies and evidence paths live in `research/registry.json`.\n"
    content += "".join(f"\n## {heading}\n\nNot recorded yet.\n" for heading in headings[kind])
    atomic_write(target, content)
    data["records"].append({"id": rid, "title": title, "status": status, "path": path,
                            "owner": "", "next_step": "Define the question and its acceptance criteria.",
                            "depends_on": [], "evidence": [], "reviews": []})
    atomic_write(root / "research/registry.json", json.dumps(data, indent=2) + "\n")
    build(root)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build")
    commands.add_parser("check")
    lookup = commands.add_parser("lookup")
    lookup.add_argument("id")
    new = commands.add_parser("new")
    new.add_argument("kind", choices=KINDS)
    new.add_argument("title")
    args = parser.parse_args()
    try:
        if args.command == "new":
            print(new_record(args.kind, args.title))
        elif args.command == "lookup":
            data = load()
            validate(data)
            record = next((r for r in data["records"] if r["id"] == args.id), None)
            if record is None:
                raise ValueError(f"Unknown record: {args.id}")
            print(json.dumps({**record, "content": local_file(ROOT, record["path"]).read_text()}, indent=2))
        else:
            build(check=args.command == "check")
            print("Research index: PASS")
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
