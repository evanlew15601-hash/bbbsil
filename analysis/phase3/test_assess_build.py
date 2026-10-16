import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("assess_build.py")


class BuildAssessmentTests(unittest.TestCase):
    def test_report_does_not_claim_a_rebuild_without_buildable_source(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "report.json"
            subprocess.run(
                [sys.executable, str(SCRIPT), "--output", str(report_path)],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertFalse(report["gate_passed"])
        self.assertEqual(report["status"], "blocked")
        self.assertIsNone(report["candidate_binary"])
        self.assertEqual(report["comparison"]["status"], "not-run-no-rebuilt-binary")
        self.assertFalse(report["decompiler_output"]["compileable_as_is"])
        self.assertEqual(report["decompiler_output"]["function_count"], 878)
        self.assertEqual(report["decompiler_output"]["pseudocode_count"], 877)
        self.assertEqual(report["decompiler_output"]["assembly_fallback_count"], 1)
        self.assertTrue(report["function_level_build_proof"]["byte_identical"])
        self.assertEqual(report["function_level_build_proof"]["function"], "FUN_00424010")


if __name__ == "__main__":
    unittest.main()