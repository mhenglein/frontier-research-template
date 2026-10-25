#!/usr/bin/env python3
"""Check a clean clone of the current commit and retain a source-pinned receipt."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

from research import ROOT


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def reproduce(root: Path, output: Path, formal: bool = False) -> dict:
    if git("status", "--porcelain", "--untracked-files=all", root=root):
        raise ValueError("Commit or preserve pending changes first; reproduction requires a clean checkout")
    revision = git("rev-parse", "HEAD", root=root)
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError("Choose an output directory outside the source checkout")
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"revision": revision, "created_utc": datetime.now(timezone.utc).isoformat(),
               "python": sys.version.split()[0], "platform": platform.platform(),
               "infrastructure": "NOT_RUN", "research_experiments": {"status": "NOT_RUN"},
               "formal": "NOT_RUN", "gate": "FAIL", "commands": [],
               "scope": "Fresh source checkout with existing installed runtimes; not an OS or toolchain installation test."}
    try:
        with tempfile.TemporaryDirectory(prefix="research-reproduction-") as temporary:
            clone = Path(temporary) / "checkout"
            subprocess.run(["git", "clone", "--quiet", "--no-local", "--", str(root.resolve()), str(clone)], check=True)
            subprocess.run(["git", "checkout", "--quiet", "--detach", revision], cwd=clone, check=True)
            files = git("ls-files", "-z", root=clone).split("\0")
            receipt["source_sha256"] = {name: hashlib.sha256((clone / name).read_bytes()).hexdigest() for name in files if name}
            check_receipt = output / "checks.json"
            command = [sys.executable, "scripts/check.py", "--receipt", str(check_receipt.resolve())]
            with (output / "checks.log").open("w") as log:
                result = subprocess.run(command, cwd=clone, stdout=log, stderr=subprocess.STDOUT)
            receipt["commands"].append({"command": ["{python}", "scripts/check.py", "--receipt", "checks.json"], "exit_code": result.returncode})
            checks = json.loads(check_receipt.read_text())
            receipt["infrastructure"] = checks["infrastructure"]
            if result.returncode or checks["gate"] != "PASS":
                raise ValueError("Fresh-clone infrastructure checks failed; see checks.log")
            command = [sys.executable, "scripts/experiments.py", "--output", str((output / "experiments").resolve())]
            with (output / "experiments.log").open("w") as log:
                result = subprocess.run(command, cwd=clone, stdout=log, stderr=subprocess.STDOUT)
            receipt["commands"].append({"command": ["{python}", "scripts/experiments.py", "--output", "experiments"], "exit_code": result.returncode})
            receipt["research_experiments"] = json.loads((output / "experiments/receipt.json").read_text())
            if result.returncode or receipt["research_experiments"]["status"] == "FAIL":
                raise ValueError("Research experiment gate failed; see experiments/")
            if formal:
                with (output / "formal.log").open("w") as log:
                    result = subprocess.run([sys.executable, "scripts/check_formal.py"], cwd=clone, stdout=log, stderr=subprocess.STDOUT)
                receipt["formal"] = "PASS" if result.returncode == 0 else "FAIL"
                receipt["commands"].append({"command": ["{python}", "scripts/check_formal.py"], "exit_code": result.returncode})
                if result.returncode:
                    raise ValueError("Formal checks failed; see formal.log")
            if git("status", "--porcelain", "--untracked-files=all", root=clone):
                raise ValueError("Checks changed the source checkout")
            receipt["gate"] = "PASS"
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        receipt["error"] = str(exc)
    research_status = receipt["research_experiments"]["status"]
    receipt["status"] = ("FAIL" if receipt["gate"] == "FAIL" else
                         "INCONCLUSIVE" if research_status == "INCONCLUSIVE" else
                         "INFRASTRUCTURE_ONLY" if research_status == "NOT_RUN" else "PASS")
    # A formal infrastructure smoke proof is reported separately, never as a
    # research result. Read the named declaration inventory for its exact scope.
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    try:
        receipt = reproduce(ROOT, args.output, args.formal)
        print(json.dumps({k: v for k, v in receipt.items() if k != "source_sha256"}, indent=2))
        return int(receipt["gate"] != "PASS")
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
