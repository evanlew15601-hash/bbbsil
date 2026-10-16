import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path(__file__).with_name("extract_pe.py")


class PEExtractionTests(unittest.TestCase):
    def test_invalid_dos_signature_is_rejected(self):
        command = [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, {str(SCRIPT.parent)!r}); "
                "from extract_pe import parse_pe, PEFormatError; "
                "data = bytearray(128); data[0:2] = b'NO'; "
                "\ntry:\n parse_pe(bytes(data))\nexcept PEFormatError:\n raise SystemExit(0)\n"
                "raise SystemExit(1)"
            ),
        ]
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)

    def test_manifest_cannot_overwrite_original_input(self):
        original_path = PROJECT_ROOT / "Setup.exe"
        original_hash = hashlib.sha256(original_path.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temporary_root:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--output-dir",
                    str(Path(temporary_root) / "extracted"),
                    "--manifest",
                    str(original_path),
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to write a manifest", result.stderr)
        self.assertEqual(
            hashlib.sha256(original_path.read_bytes()).hexdigest(), original_hash
        )

    def test_extraction_is_deterministic_and_ranges_reconcile(self):
        with tempfile.TemporaryDirectory() as temporary_root:
            temporary_path = Path(temporary_root)
            output_directories = [temporary_path / "first", temporary_path / "second"]
            manifest_bytes = []
            for output_directory in output_directories:
                subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--output-dir",
                        str(output_directory),
                    ],
                    cwd=PROJECT_ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                manifest_bytes.append((output_directory / "manifest.json").read_bytes())

            self.assertEqual(manifest_bytes[0], manifest_bytes[1])
            manifest = json.loads(manifest_bytes[0])
            inputs = {item["path"]: item for item in manifest["inputs"]}
            segments_by_input = {name: [] for name in inputs}
            for segment in manifest["segments"]:
                segments_by_input[segment["input"]].append(segment)

            for input_name, input_record in inputs.items():
                source = (PROJECT_ROOT / input_name).read_bytes()
                self.assertEqual(len(source), input_record["size"])
                self.assertEqual(hashlib.sha256(source).hexdigest(), input_record["sha256"])
                cursor = 0
                for segment in sorted(
                    segments_by_input[input_name], key=lambda item: item["offset"]
                ):
                    self.assertEqual(segment["offset"], cursor)
                    byte_range = source[cursor : cursor + segment["size"]]
                    self.assertEqual(
                        hashlib.sha256(byte_range).hexdigest(), segment["sha256"]
                    )
                    cursor += segment["size"]
                self.assertEqual(cursor, len(source))

            candidates = {item["name"]: item for item in manifest["embedded_images"]}
            self.assertEqual(candidates["Bbb.exe"]["offset"], 0x9A1D)
            self.assertEqual(candidates["Bbb.exe"]["size"], 303104)
            self.assertEqual(candidates["Cuninst.exe"]["offset"], 0x36DD2AE)
            self.assertEqual(candidates["Cuninst.exe"]["size"], 90112)

            data_bytes = (PROJECT_ROOT / "Setup.dat").read_bytes()
            for artifact in manifest["artifacts"]:
                source_range = data_bytes[
                    artifact["offset"] : artifact["offset"] + artifact["size"]
                ]
                for output_directory in output_directories:
                    extracted = (output_directory / artifact["path"]).read_bytes()
                    self.assertEqual(extracted, source_range)
                    self.assertEqual(
                        hashlib.sha256(extracted).hexdigest(), artifact["sha256"]
                    )


if __name__ == "__main__":
    unittest.main()