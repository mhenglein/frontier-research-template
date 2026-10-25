#!/usr/bin/env python3
"""Run registered experiments with explicit acceptance and diagnostic outcomes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from research import ROOT, load, validate


def manifest(root: Path) -> list[dict]:
    data = json.loads((root / "experiments/manifest.json").read_text())
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("experiments"), list):
        raise ValueError("Experiment manifest must have version 1 and an experiments array")
    registry = load(root)
    validate(registry, root)
    known = {r["id"] for r in registry["records"] if r["id"].startswith("E")}
    seen = set()
    for entry in data["experiments"]:
        if not isinstance(entry, dict):
            raise ValueError("Experiment entries must be objects")
        eid = entry.get("id")
        if not isinstance(eid, str) or eid not in known or eid in seen:
            raise ValueError(f"Unregistered or duplicate experiment: {eid!r}")
        seen.add(eid)
        cmd = entry.get("command")
        if not isinstance(cmd, list) or not cmd or any(not isinstance(s, str) or not s for s in cmd):
            raise ValueError(f"{eid}: command must be a nonempty argument array")
        timeout = entry.get("timeout_seconds")
        if type(timeout) not in (int, float) or not 0 < timeout <= 3600:
            raise ValueError(f"{eid}: timeout_seconds must be between 0 and 3600")
        if entry.get("mode") not in {"acceptance", "diagnostic"}:
            raise ValueError(f"{eid}: mode must be acceptance or diagnostic")
    return data["experiments"]


def execute(entry: dict, root: Path, output: Path) -> dict:
    cmd = [sys.executable if arg == "{python}" else arg for arg in entry["command"]]
    start = time.monotonic()
    result = {"id": entry["id"], "command": entry["command"], "mode": entry["mode"],
              "timeout_seconds": entry["timeout_seconds"], "status": "FAIL"}
    stdout_path = output / f"{entry['id']}.stdout.log"
    stderr_path = output / f"{entry['id']}.stderr.log"
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            process = subprocess.Popen(cmd, cwd=root, stdout=stdout, stderr=stderr,
                                       start_new_session=os.name == "posix")
            try:
                code = process.wait(timeout=entry["timeout_seconds"])
                result["exit_code"] = code
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
                process.wait()
                result.update(status="UNKNOWN", reason="Time limit reached; search is incomplete")
                code = None
        except OSError as exc:
            result["reason"] = str(exc)
            code = None
    if code == 0:
        try:
            # Logs go to files, not an unbounded in-memory capture. Only parse a
            # bounded tail; the protocol requires one final JSON line.
            with stdout_path.open("rb") as stream:
                stream.seek(max(0, stdout_path.stat().st_size - 65536))
                lines = stream.read().decode("utf-8").strip().splitlines()
            payload = json.loads(lines[-1])
            if not isinstance(payload, dict) or payload.get("status") not in {"PASS", "FAIL", "UNKNOWN"}:
                raise ValueError("Final JSON line needs a PASS, FAIL or UNKNOWN status")
            if not isinstance(payload.get("summary"), str) or not payload["summary"].strip():
                raise ValueError("Final JSON line needs a nonempty summary")
            result.update(status=payload["status"], result=payload)
        except (ValueError, IndexError, UnicodeError) as exc:
            result["reason"] = f"Invalid experiment result: {exc}"
    elif code is not None:
        result["reason"] = f"Process failed with exit code {code}"
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    result["logs"] = [stdout_path.name, stderr_path.name]
    return result


def summarize(rows: list[dict]) -> str:
    if not rows:
        return "NOT_RUN"
    if any(r["status"] == "FAIL" or (r["status"] == "UNKNOWN" and r["mode"] == "acceptance") for r in rows):
        return "FAIL"
    return "INCONCLUSIVE" if any(r["status"] == "UNKNOWN" for r in rows) else "PASS"


def run(root: Path, output: Path) -> dict:
    entries = manifest(root)
    all_records = [r["id"] for r in load(root)["records"] if r["id"].startswith("E")]
    scheduled = {e["id"] for e in entries}
    output.mkdir(parents=True, exist_ok=False)
    rows = [execute(entry, root, output) for entry in entries]
    receipt = {"status": summarize(rows), "registered": len(all_records), "scheduled": len(entries),
               "not_scheduled": sorted(set(all_records) - scheduled), "rows": rows,
               "meaning": "Reports experiment verdicts and limits; does not establish a general scientific claim."}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = run(ROOT, args.output)
        print(json.dumps(receipt, indent=2))
        return int(receipt["status"] == "FAIL")
    except (ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
