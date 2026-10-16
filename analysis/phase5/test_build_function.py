import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("build_function.py")


class FunctionBuildTests(unittest.TestCase):
    def test_reconstructed_functions_match_original_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            report_path = temporary_path / "report.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output-dir",
                    str(temporary_path / "build"),
                    "--report",
                    str(report_path),
                ],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertTrue(report["byte_identical"])
        self.assertEqual(report["mismatch_bytes"], 0)
        self.assertEqual(report["function_size"], 7)
        self.assertEqual(report["original_bytes"], "c70164244400c3")
        self.assertEqual(report["compiled_text_bytes"], report["original_bytes"])
        self.assertEqual(report["function_count"], 2)
        self.assertEqual(report["link_status"], "not-linked; function objects only")
        comparisons = {function["function"]: function for function in report["functions"]}
        self.assertTrue(comparisons["FUN_00424010"]["byte_identical"])
        self.assertEqual(comparisons["FUN_00424010"]["original_bytes"], "c70164244400c3")
        self.assertTrue(comparisons["FUN_0040ffb0"]["byte_identical"])
        self.assertEqual(comparisons["FUN_0040ffb0"]["original_bytes"], "8bc1c3")


if __name__ == "__main__":
    unittest.main()