#!/usr/bin/env python3
"""Check repository structure and tooling; optionally execute research experiments."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

from research import ROOT, build
import experiments


def check_links(root: Path) -> None:
    for document in root.rglob("*.md"):
        if any(part in {".git", ".lake", ".elan", "work", ".venv"} for part in document.relative_to(root).parts):
            continue
        for target in re.findall(r"\]\(([^\s)]+)\)", document.read_text()):
            url = urlsplit(target.strip("<>"))
            if url.scheme or url.netloc or not url.path:
                continue
            path = (document.parent / unquote(url.path)).resolve()
            if not path.is_relative_to(root.resolve()) or not path.exists():
                raise ValueError(f"Broken local link in {document.relative_to(root)}: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiments", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    receipt = {"infrastructure": "FAIL", "research_experiments": {"status": "NOT_RUN"},
               "formal": "NOT_RUN", "python": sys.version.split()[0]}
    code = 1
    try:
        if sys.version_info < (3, 11):
            raise ValueError("Python 3.11 or newer is required; CI uses Python 3.12")
        build(check=True)
        experiments.manifest(ROOT)
        check_links(ROOT)
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT)
        if result.returncode:
            raise ValueError("Tooling regression tests failed")
        receipt["infrastructure"] = "PASS"
        if args.experiments:
            with tempfile.TemporaryDirectory(prefix="research-experiments-") as temporary:
                receipt["research_experiments"] = experiments.run(ROOT, Path(temporary) / "run")
                # Receipts embedded here contain verdicts, not durable log files.
                for row in receipt["research_experiments"]["rows"]:
                    row.pop("logs", None)
        code = int(receipt["research_experiments"]["status"] == "FAIL")
    except (ValueError, OSError) as exc:
        receipt["error"] = str(exc)
    receipt["gate"] = "PASS" if code == 0 else "FAIL"
    research_status = receipt["research_experiments"]["status"]
    receipt["status"] = ("FAIL" if code else
                         "INFRASTRUCTURE_ONLY" if research_status == "NOT_RUN" else research_status)
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
