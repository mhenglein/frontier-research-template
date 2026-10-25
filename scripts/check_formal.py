#!/usr/bin/env python3
"""Build the optional Lean project and audit a named theorem's axioms.

This is a proof-tool check, not a scientific completeness check. It fails when
the pinned Lean toolchain is unavailable, when the project does not build, or
when the smoke theorem acquires an unexpected axiom.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "formal"
TOOLCHAIN = "v4.33.1"
AUDIT = FORMAL / "audit.json"


def run(command: list[str], *, cwd: Path) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"required command is unavailable: {command[0]}") from exc
    if completed.returncode:
        print(completed.stdout, end="")
        raise SystemExit(f"command failed ({completed.returncode}): {' '.join(command)}")
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    for command in ("lake", "lean"):
        if shutil.which(command) is None:
            raise SystemExit(f"{command} is required; install the pinned Lean toolchain {TOOLCHAIN}")

    declared = (FORMAL / "lean-toolchain").read_text(encoding="utf-8").strip()
    if declared != TOOLCHAIN:
        raise SystemExit(f"formal/lean-toolchain must pin {TOOLCHAIN}, found {declared!r}")

    runtime = run(["lake", "env", "lean", "--version"], cwd=FORMAL)
    match = re.search(r"Lean \(version ([0-9]+\.[0-9]+\.[0-9]+)(?:,|\))", runtime)
    if not match or match.group(1) != TOOLCHAIN.removeprefix("v"):
        raise SystemExit(
            f"runtime Lean version mismatch; expected {TOOLCHAIN.removeprefix('v')}, "
            f"got {runtime.strip()!r}"
        )

    run(["lake", "build"], cwd=FORMAL)

    try:
        inventory = json.loads(AUDIT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read formal audit inventory {AUDIT}: {exc}") from exc
    version = inventory.get("version") if isinstance(inventory, dict) else None
    declarations = inventory.get("declarations") if isinstance(inventory, dict) else None
    if version != 1 or not isinstance(declarations, list) or not declarations:
        raise SystemExit("formal/audit.json must contain version 1 and a non-empty declarations list")
    names: list[str] = []
    modules: set[str] = set()
    for entry in declarations:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise SystemExit("every formal audit declaration needs a name")
        if not isinstance(entry.get("module"), str) or not isinstance(entry.get("allowed_axioms"), list):
            raise SystemExit(f"malformed formal audit declaration: {entry!r}")
        name = entry["name"]
        module = entry["module"]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", name):
            raise SystemExit(f"invalid formal audit declaration name: {name!r}")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", module):
            raise SystemExit(f"invalid formal audit module name: {module!r}")
        if not (name == module or name.startswith(module + ".")):
            raise SystemExit(f"audit declaration {name!r} is outside module {module!r}")
        if any(not isinstance(axiom, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", axiom
        ) for axiom in entry["allowed_axioms"]):
            raise SystemExit(f"malformed allowed_axioms for {name!r}")
        if "sorryAx" in entry["allowed_axioms"]:
            raise SystemExit(f"sorryAx cannot be allowlisted for {name}")
        module_path = FORMAL / (module.replace(".", "/") + ".lean")
        if not module_path.is_file():
            raise SystemExit(f"formal audit module does not exist: {module}")
        if name in names:
            raise SystemExit(f"duplicate formal audit declaration: {name}")
        names.append(name)
        modules.add(module)

    for module in sorted(modules):
        run(["lake", "build", f"+{module}"], cwd=FORMAL)

    audit = run(["lake", "env", "lean", "AxiomAudit.lean"], cwd=FORMAL)
    for entry in declarations:
        name = entry["name"]
        allowed = set(entry["allowed_axioms"])
        no_axioms = f"'{name}' does not depend on any axioms" in audit
        listed = re.search(rf"'{re.escape(name)}' depends on axioms: \[([^]]*)\]", audit)
        actual = set() if no_axioms else (
            {item.strip() for item in listed.group(1).split(",") if item.strip()}
            if listed else None
        )
        if actual is not None and "sorryAx" in actual:
            print(audit, end="")
            raise SystemExit(f"axiom audit failed for {name}; sorryAx is never permitted")
        if actual is None or actual != allowed:
            print(audit, end="")
            raise SystemExit(
                f"axiom audit failed for {name}; expected {sorted(allowed)}, "
                f"found {sorted(actual) if actual is not None else 'unreported'}"
            )

    # Recheck each compiled module with Lean's kernel checker. This consumes the
    # .olean emitted by `lake build`; it does not re-elaborate source files.
    for module in sorted(modules):
        run(["lake", "env", "leanchecker", module], cwd=FORMAL)
    print(f"formal checks: PASS ({TOOLCHAIN}; {len(names)} audited declaration(s); kernel replay)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
