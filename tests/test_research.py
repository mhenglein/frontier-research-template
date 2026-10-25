from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import research


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "research").mkdir()
        self.save({"version": 1, "records": []})

    def save(self, data):
        (self.root / "research/registry.json").write_text(json.dumps(data))

    def test_new_record_roundtrip_and_lookup_shape(self):
        for kind in "ACEQ":
            research.new_record(kind, "A precise question", self.root)
        research.build(self.root, check=True)
        self.assertEqual([r["id"] for r in research.load(self.root)["records"]], ["A001", "C001", "E001", "Q001"])
        research.new_record("C", "Another question", self.root)
        self.assertEqual(research.load(self.root)["records"][-1]["id"], "C002")

    def test_stale_index_rejected(self):
        research.build(self.root)
        (self.root / "research/INDEX.md").write_text("stale")
        with self.assertRaisesRegex(ValueError, "stale"):
            research.build(self.root, check=True)

    def claim(self):
        research.new_record("C", "Test claim", self.root)
        return research.load(self.root)

    def test_duplicate_id_rejected(self):
        data = self.claim()
        data["records"].append(data["records"][0].copy())
        with self.assertRaisesRegex(ValueError, "duplicate ID"):
            research.validate(data, self.root)

    def test_established_requires_evidence_and_review(self):
        data = self.claim()
        data["records"][0]["status"] = "established"
        with self.assertRaisesRegex(ValueError, "independent review"):
            research.validate(data, self.root)
        (self.root / "evidence.md").write_text("Exact proof and limitations")
        (self.root / "review.md").write_text("Independent review of exact source revision")
        data["records"][0].update(evidence=["evidence.md"], reviews=["review.md"])
        research.validate(data, self.root)

    def test_undefined_and_circular_dependencies_rejected(self):
        data = self.claim()
        data["records"][0]["depends_on"] = ["Q999"]
        with self.assertRaisesRegex(ValueError, "unknown dependency"):
            research.validate(data, self.root)
        data["records"][0]["depends_on"] = ["C001"]
        with self.assertRaisesRegex(ValueError, "Circular"):
            research.validate(data, self.root)

    def test_missing_evidence_and_escaping_paths_rejected(self):
        data = self.claim()
        data["records"][0]["evidence"] = ["missing.txt"]
        with self.assertRaisesRegex(ValueError, "Missing"):
            research.validate(data, self.root)
        data["records"][0]["evidence"] = [str(Path(__file__).resolve())]
        with self.assertRaisesRegex(ValueError, "repository-relative"):
            research.validate(data, self.root)

    def test_inactive_and_active_approach_requirements(self):
        research.new_record("A", "Attempt", self.root)
        data = research.load(self.root)
        data["records"][0]["status"] = "active"
        with self.assertRaisesRegex(ValueError, "owner"):
            research.validate(data, self.root)

    def test_invalid_status_and_unknown_text_reference_rejected(self):
        data = self.claim()
        data["records"][0]["status"] = "done"
        with self.assertRaisesRegex(ValueError, "invalid status"):
            research.validate(data, self.root)
        data["records"][0]["status"] = "conjectured"
        (self.root / data["records"][0]["path"]).write_text("# C001: Test\nDepends on C999\n")
        with self.assertRaisesRegex(ValueError, "unregistered reference"):
            research.validate(data, self.root)

    def test_new_does_not_overwrite_unregistered_work(self):
        target = self.root / "research/claims/C001.md"
        target.parent.mkdir()
        target.write_text("uncommitted work")
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            research.new_record("C", "Test", self.root)
        self.assertEqual(target.read_text(), "uncommitted work")
        self.assertEqual(research.load(self.root)["records"], [])


if __name__ == "__main__":
    unittest.main()
