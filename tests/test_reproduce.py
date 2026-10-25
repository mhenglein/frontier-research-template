from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import reproduce


class ReproductionTests(unittest.TestCase):
    """Small synthetic git repositories exercise real clone/receipt behavior."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "source"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "scripts/check.py").write_text(
            "import json, pathlib, sys\n"
            "pathlib.Path(sys.argv[2]).write_text(json.dumps({'infrastructure':'PASS','gate':'PASS'}))\n")
        (self.root / "scripts/experiments.py").write_text(
            "import json, pathlib, sys\n"
            "out=pathlib.Path(sys.argv[2]); out.mkdir()\n"
            "(out/'receipt.json').write_text(json.dumps({'status':'INCONCLUSIVE','rows':[{'id':'E001','status':'UNKNOWN','mode':'diagnostic'}]}))\n")
        self.command("git", "init", "-q", "--initial-branch=main")
        self.command("git", "add", ".")
        self.command("git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Fixture")

    def command(self, *args):
        return subprocess.check_output(args, cwd=self.root, text=True).strip()

    def test_exact_clone_retains_inconclusive_verdict_and_hashes(self):
        receipt = reproduce.reproduce(self.root, self.base / "receipt")
        self.assertEqual(receipt["gate"], "PASS")
        self.assertEqual(receipt["status"], "INCONCLUSIVE")
        self.assertEqual(receipt["revision"], self.command("git", "rev-parse", "HEAD"))
        self.assertEqual(set(receipt["source_sha256"]), {"scripts/check.py", "scripts/experiments.py"})
        self.assertEqual(self.command("git", "status", "--porcelain"), "")

    def test_dirty_checkout_refused_before_output_created(self):
        (self.root / "unsaved.txt").write_text("preserve me")
        with self.assertRaisesRegex(ValueError, "clean checkout"):
            reproduce.reproduce(self.root, self.base / "receipt")
        self.assertFalse((self.base / "receipt").exists())

    def test_output_inside_checkout_refused(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            reproduce.reproduce(self.root, self.root / "receipt")

    def test_missing_check_receipt_is_failure(self):
        (self.root / "scripts/check.py").write_text("pass\n")
        self.command("git", "add", ".")
        self.command("git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Missing receipt")
        receipt = reproduce.reproduce(self.root, self.base / "receipt")
        self.assertEqual(receipt["gate"], "FAIL")
        self.assertEqual(receipt["status"], "FAIL")

    def replace_fixture(self, script, source):
        (self.root / "scripts" / script).write_text(source)
        self.command("git", "add", ".")
        self.command("git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "Malformed fixture")

    def test_incomplete_check_receipt_preserves_failure_receipt(self):
        self.replace_fixture("check.py", "import pathlib,sys; pathlib.Path(sys.argv[2]).write_text('{}')\n")
        receipt = reproduce.reproduce(self.root, self.base / "receipt")
        self.assertEqual(receipt["status"], "FAIL")
        self.assertIn("Malformed infrastructure receipt", receipt["error"])
        self.assertTrue((self.base / "receipt/receipt.json").is_file())

    def test_inconsistent_check_verdict_is_rejected(self):
        self.replace_fixture("check.py", "import pathlib,sys,json; pathlib.Path(sys.argv[2]).write_text(json.dumps({'infrastructure':'FAIL','gate':'PASS'}))\n")
        receipt = reproduce.reproduce(self.root, self.base / "receipt")
        self.assertEqual(receipt["status"], "FAIL")

    def test_unknown_experiment_status_is_rejected(self):
        self.replace_fixture("experiments.py", "import pathlib,sys,json\nout=pathlib.Path(sys.argv[2]);out.mkdir()\n(out/'receipt.json').write_text(json.dumps({'status':'BOGUS','rows':[]}))\n")
        receipt = reproduce.reproduce(self.root, self.base / "receipt")
        self.assertEqual(receipt["status"], "FAIL")
        self.assertIn("Malformed experiment receipt status", receipt["error"])

    def test_summary_must_match_individual_experiments(self):
        self.replace_fixture("experiments.py", "import pathlib,sys,json\nout=pathlib.Path(sys.argv[2]);out.mkdir()\n(out/'receipt.json').write_text(json.dumps({'status':'PASS','rows':[{'status':'UNKNOWN','mode':'diagnostic'}]}))\n")
        receipt = reproduce.reproduce(self.root, self.base / "receipt")
        self.assertEqual(receipt["status"], "FAIL")
        self.assertIn("disagrees", receipt["error"])


if __name__ == "__main__":
    unittest.main()
