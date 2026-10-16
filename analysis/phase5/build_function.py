#!/usr/bin/env python3
"""Build one evidence-backed function and compare its exact code bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FUNCTIONS = (
    {
        "name": "FUN_00424010",
        "address": "0x00424010",
        "source": Path(__file__).with_name("functions") / "FUN_00424010.c",
        "offset": 0x24010,
        "size": 7,
    },
    {
        "name": "FUN_0040ffb0",
        "address": "0x0040ffb0",
        "source": Path(__file__).with_name("functions") / "FUN_0040ffb0.c",
        "offset": 0xFFB0,
        "size": 3,
    },
)
REFERENCE = PROJECT_ROOT / "analysis/phase1/extracted/Bbb.exe"
CLANG_FLAGS = [
    "--target=i686-pc-windows-msvc",
    "-O2",
    "-ffreestanding",
    "-fno-stack-protector",
    "-c",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_build(output_dir: Path, report_path: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    report_path = report_path.resolve()
    if output_dir == PROJECT_ROOT or output_dir == PROJECT_ROOT.parent:
        raise ValueError("refusing to use a broad repository directory as build output")
    if REFERENCE.resolve() == output_dir or REFERENCE.resolve().parent == output_dir:
        raise ValueError("refusing to place build outputs beside an original binary")
    if report_path == REFERENCE.resolve() or any(
        report_path == function["source"].resolve() for function in FUNCTIONS
    ):
        raise ValueError("refusing to overwrite a source input")

    clang = os.environ.get("CLANG") or shutil.which("clang")
    objcopy = os.environ.get("OBJCOPY") or shutil.which("objcopy")
    if not clang or not objcopy:
        raise RuntimeError("clang and objcopy are required for the function build")

    output_dir.mkdir(parents=True, exist_ok=True)
    reference_bytes = REFERENCE.read_bytes()
    function_reports = []
    for function in FUNCTIONS:
        object_path = output_dir / f"{function['name']}.obj"
        code_path = output_dir / f"{function['name']}.text.bin"
        compile_command = [
            clang,
            *CLANG_FLAGS,
            str(function["source"]),
            "-o",
            str(object_path),
        ]
        compile_result = subprocess.run(
            compile_command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if compile_result.returncode != 0:
            raise RuntimeError(
                f"{function['name']} compilation failed: {compile_result.stderr}"
            )

        extract_result = subprocess.run(
            [objcopy, "--dump-section", f".text={code_path}", str(object_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if extract_result.returncode != 0:
            raise RuntimeError(
                f"could not extract {function['name']} object .text: "
                f"{extract_result.stderr}"
            )

        original_code = reference_bytes[
            function["offset"] : function["offset"] + function["size"]
        ]
        if len(original_code) != function["size"]:
            raise RuntimeError(
                f"{function['name']} range exceeds the reference binary"
            )
        built_code = code_path.read_bytes()
        function_reports.append(
            {
                "function": function["name"],
                "address": function["address"],
                "source": function["source"].relative_to(PROJECT_ROOT).as_posix(),
                "reference_file_offset": function["offset"],
                "function_size": function["size"],
                "original_bytes": original_code.hex(),
                "compiled_text_bytes": built_code.hex(),
                "compiled_text_size": len(built_code),
                "byte_identical": built_code == original_code,
                "mismatch_bytes": sum(
                    left != right for left, right in zip(original_code, built_code)
                ) + abs(len(original_code) - len(built_code)),
                "object_path": object_path.relative_to(PROJECT_ROOT).as_posix()
                if object_path.is_relative_to(PROJECT_ROOT)
                else str(object_path),
                "object_sha256": digest(object_path.read_bytes()),
            }
        )

    first_function = function_reports[0]
    all_identical = all(function["byte_identical"] for function in function_reports)
    report = {
        "schema_version": 1,
        "scope": "function-object-batch; not a full-game executable",
        "function_count": len(function_reports),
        "function": first_function["function"],
        "address": first_function["address"],
        "source": first_function["source"],
        "reference_binary": "analysis/phase1/extracted/Bbb.exe",
        "reference_binary_sha256": digest(reference_bytes),
        "reference_file_offset": first_function["reference_file_offset"],
        "function_size": first_function["function_size"],
        "original_bytes": first_function["original_bytes"],
        "compiled_text_bytes": first_function["compiled_text_bytes"],
        "byte_identical": all_identical,
        "mismatch_bytes": sum(function["mismatch_bytes"] for function in function_reports),
        "compiled_text_size": sum(function["compiled_text_size"] for function in function_reports),
        "object_path": first_function["object_path"],
        "object_sha256": first_function["object_sha256"],
        "functions": function_reports,
        "compiler": subprocess.run(
            [clang, "--version"], capture_output=True, text=True, check=True
        ).stdout.splitlines()[0],
        "compiler_flags": CLANG_FLAGS,
        "link_status": "not-linked; function objects only",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("build"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(__file__).with_name("function-build-report.json"),
    )
    arguments = parser.parse_args()
    try:
        report = run_build(arguments.output_dir, arguments.report)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    for function in report["functions"]:
        print(f"FUNCTION={function['function']}")
        print(f"BYTE_IDENTICAL={function['byte_identical']}")
        print(f"ORIGINAL={function['original_bytes']}")
        print(f"COMPILED={function['compiled_text_bytes']}")
    print(f"FUNCTION_COUNT={report['function_count']}")
    print(f"REPORT={arguments.report}")
    return 0 if report["byte_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())