from __future__ import annotations

import os
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from collections.abc import Iterator


ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_formal.py"


FAKE_LAKE = r'''#!/usr/bin/env python3
import os
import sys

args = sys.argv[1:]
log = os.environ.get("FAKE_LAKE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(" ".join(args) + "\n")
if os.environ.get("FAKE_LAKE_MODE") == "fail-build" and args == ["build"]:
    print("simulated build failure")
    raise SystemExit(7)
if args == ["env", "lean", "--version"]:
    print("Lean (version " + os.environ.get("FAKE_LEAN_VERSION", "4.33.1") + ")")
elif args == ["env", "lean", "AxiomAudit.lean"]:
    if os.environ.get("FAKE_LAKE_MODE") == "unexpected-axiom":
        print("'FrontierResearch.infrastructure_smoke' depends on axioms: [propext]")
    elif os.environ.get("FAKE_LAKE_MODE") == "sorry-axiom":
        print("'FrontierResearch.infrastructure_smoke' depends on axioms: [sorryAx]")
    elif os.environ.get("FAKE_LAKE_MODE") == "second-module":
        print("'FrontierResearch.infrastructure_smoke' does not depend on any axioms")
        print("'ExtraModule.infrastructure_smoke' does not depend on any axioms")
    else:
        print("'FrontierResearch.infrastructure_smoke' does not depend on any axioms")
elif args == ["env", "leanchecker", "FrontierResearch"]:
    pass
elif len(args) == 3 and args[:2] == ["env", "leanchecker"]:
    pass
elif args == ["build"]:
    pass
elif len(args) == 2 and args[0] == "build" and args[1].startswith("+"):
    pass
else:
    print("unexpected fake lake command", args, file=sys.stderr)
    raise SystemExit(8)
'''


class FormalCheckTests(unittest.TestCase):
    @contextmanager
    def fixture(self, *, lake_mode: str = "", lean_version: str = "4.33.1") -> Iterator[tuple[Path, dict[str, str]]]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / "scripts").mkdir()
        (root / "formal").mkdir()
        shutil.copy2(CHECK, root / "scripts" / "check_formal.py")
        for name in (
            "AxiomAudit.lean",
            "FrontierResearch.lean",
            "audit.json",
            "lakefile.toml",
            "lake-manifest.json",
            "lean-toolchain",
        ):
            shutil.copy2(ROOT / "formal" / name, root / "formal" / name)
        fake_bin = root / "fake-bin"
        fake_bin.mkdir()
        lake = fake_bin / "lake"
        lake.write_text(FAKE_LAKE, encoding="utf-8")
        lake.chmod(lake.stat().st_mode | stat.S_IXUSR)
        lean = fake_bin / "lean"
        lean.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        lean.chmod(lean.stat().st_mode | stat.S_IXUSR)
        environment = os.environ.copy()
        environment["PATH"] = str(fake_bin) + os.pathsep + environment.get("PATH", "")
        environment["FAKE_LAKE_MODE"] = lake_mode
        environment["FAKE_LEAN_VERSION"] = lean_version
        try:
            yield root, environment
        finally:
            temporary.cleanup()

    def run_check(self, root: Path, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(root / "scripts" / "check_formal.py")],
            cwd=root,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def test_passes_with_isolated_fake_toolchain_and_runs_kernel_checker(self) -> None:
        with self.fixture() as (root, environment):
            log = root / "lake.log"
            environment["FAKE_LAKE_LOG"] = str(log)
            result = self.run_check(root, environment)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("kernel replay", result.stdout)
            self.assertIn("env leanchecker FrontierResearch", log.read_text(encoding="utf-8"))

    def test_rejects_an_unpinned_toolchain_without_touching_checkout(self) -> None:
        with self.fixture() as (root, environment):
            toolchain = root / "formal" / "lean-toolchain"
            toolchain.write_text("uncontrolled\n", encoding="utf-8")
            result = self.run_check(root, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("must pin v4.33.1", result.stdout)

    def test_rejects_missing_lake(self) -> None:
        with self.fixture() as (root, environment):
            environment["PATH"] = str(root / "fake-bin") + os.pathsep + "/usr/bin"
            (root / "fake-bin" / "lake").unlink()
            result = self.run_check(root, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lake is required", result.stdout)

    def test_rejects_runtime_version_mismatch(self) -> None:
        with self.fixture(lean_version="4.32.0") as (root, environment):
            result = self.run_check(root, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runtime Lean version mismatch", result.stdout)

    def test_rejects_runtime_release_candidate(self) -> None:
        with self.fixture(lean_version="4.33.1-rc1") as (root, environment):
            result = self.run_check(root, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runtime Lean version mismatch", result.stdout)

    def test_rejects_build_command_failure(self) -> None:
        with self.fixture(lake_mode="fail-build") as (root, environment):
            result = self.run_check(root, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("command failed (7): lake build", result.stdout)

    def test_rejects_unexpected_axiom(self) -> None:
        with self.fixture(lake_mode="unexpected-axiom") as (root, environment):
            result = self.run_check(root, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("axiom audit failed", result.stdout)

    def test_builds_and_replays_every_inventory_module(self) -> None:
        with self.fixture(lake_mode="second-module") as (root, environment):
            (root / "formal" / "ExtraModule.lean").write_text(
                "theorem ExtraModule.infrastructure_smoke (p : Prop) : p → p := id\n",
                encoding="utf-8",
            )
            audit_path = root / "formal" / "audit.json"
            inventory = json.loads(audit_path.read_text(encoding="utf-8"))
            inventory["declarations"].append(
                {
                    "name": "ExtraModule.infrastructure_smoke",
                    "module": "ExtraModule",
                    "allowed_axioms": [],
                }
            )
            audit_path.write_text(json.dumps(inventory), encoding="utf-8")
            log = root / "lake.log"
            environment["FAKE_LAKE_LOG"] = str(log)
            result = self.run_check(root, environment)
            self.assertEqual(result.returncode, 0, result.stdout)
            commands = log.read_text(encoding="utf-8")
            self.assertIn("build +FrontierResearch", commands)
            self.assertIn("build +ExtraModule", commands)
            self.assertIn("env leanchecker FrontierResearch", commands)
            self.assertIn("env leanchecker ExtraModule", commands)

    def test_sorry_axiom_cannot_be_allowlisted(self) -> None:
        with self.fixture(lake_mode="sorry-axiom") as (root, environment):
            audit_path = root / "formal" / "audit.json"
            inventory = json.loads(audit_path.read_text(encoding="utf-8"))
            inventory["declarations"][0]["allowed_axioms"] = ["sorryAx"]
            audit_path.write_text(json.dumps(inventory), encoding="utf-8")
            result = self.run_check(root, environment)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("sorryAx cannot be allowlisted", result.stdout)


if __name__ == "__main__":
    unittest.main()
