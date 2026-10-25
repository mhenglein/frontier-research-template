from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import experiments
import research


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "research").mkdir()
        (self.root / "experiments").mkdir()
        (self.root / "research/registry.json").write_text('{"version":1,"records":[]}')
        research.new_record("E", "Infrastructure fixture", self.root)

    def manifest(self, program=None, mode="acceptance", timeout=5):
        entries = [] if program is None else [{"id": "E001", "command": ["{python}", "-c", program],
                                               "mode": mode, "timeout_seconds": timeout}]
        (self.root / "experiments/manifest.json").write_text(json.dumps({"version": 1, "experiments": entries}))

    def run_fixture(self):
        return experiments.run(self.root, self.root / "output")

    def test_empty_suite_is_not_run(self):
        self.manifest()
        self.assertEqual(self.run_fixture()["status"], "NOT_RUN")

    def test_success_requires_explicit_verdict(self):
        self.manifest("print('completed successfully')")
        self.assertEqual(self.run_fixture()["status"], "FAIL")

    def test_valid_success(self):
        self.manifest('print(\'{"status":"PASS","summary":"Witness checked independently"}\')')
        receipt = self.run_fixture()
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["rows"][0]["exit_code"], 0)

    def test_nonzero_exit_overrides_pass_payload(self):
        self.manifest('import sys; print(\'{"status":"PASS","summary":"bad"}\'); sys.exit(2)')
        self.assertEqual(self.run_fixture()["status"], "FAIL")

    def test_diagnostic_unknown_is_inconclusive(self):
        self.manifest('print(\'{"status":"UNKNOWN","summary":"Bound exhausted"}\')', mode="diagnostic")
        self.assertEqual(self.run_fixture()["status"], "INCONCLUSIVE")

    def test_acceptance_unknown_fails_gate_without_changing_verdict(self):
        self.manifest('print(\'{"status":"UNKNOWN","summary":"Bound exhausted"}\')')
        receipt = self.run_fixture()
        self.assertEqual(receipt["status"], "FAIL")
        self.assertEqual(receipt["rows"][0]["status"], "UNKNOWN")

    def test_timeout_stays_unknown(self):
        self.manifest("import time; time.sleep(30)", mode="diagnostic", timeout=0.05)
        receipt = self.run_fixture()
        self.assertEqual(receipt["status"], "INCONCLUSIVE")
        self.assertEqual(receipt["rows"][0]["status"], "UNKNOWN")

    def test_invalid_manifest_rejected(self):
        self.manifest("pass")
        path = self.root / "experiments/manifest.json"
        data = json.loads(path.read_text())
        data["experiments"][0]["id"] = "E999"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "Unregistered"):
            self.run_fixture()
        self.assertFalse((self.root / "output").exists())

    def test_existing_output_not_overwritten(self):
        self.manifest()
        (self.root / "output").mkdir()
        with self.assertRaises(FileExistsError):
            self.run_fixture()


if __name__ == "__main__":
    unittest.main()
