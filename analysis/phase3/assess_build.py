#!/usr/bin/env python3
"""Assess whether available source and tools can produce a game rebuild."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
EXCLUDED_PARTS = {".git", "rea", "analysis", "decompiled", "extracted", "node_modules", "__pycache__"}
HOST_COMPILERS = ("cc", "gcc", "clang")
WINDOWS_BUILD_TOOLS = (
    "cl",
    "clang-cl",
    "i686-w64-mingw32-gcc",
    "i686-w64-mingw32-g++",
    "i686-w64-mingw32-ld",
    "x86_64-w64-mingw32-gcc",
    "lld-link",
)


def source_candidates() -> list[str]:
    candidates = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        relative = path.relative_to(PROJECT_ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        candidates.append(relative.as_posix())
    return sorted(candidates)


def run_compileability_probe(source: Path, compiler: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [compiler, "-x", "c", "-fsyntax-only", str(source)],
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
        )
        return {
            "compiler": compiler,
            "exit_code": result.returncode,
            "passed": result.returncode == 0,
            "stderr_excerpt": result.stderr[:5000],
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "compiler": compiler,
            "exit_code": None,
            "passed": False,
            "stderr_excerpt": str(error),
        }


def build_report() -> dict[str, Any]:
    p1_manifest_path = PROJECT_ROOT / "analysis/phase1/manifest.json"
    p2_census_path = PROJECT_ROOT / "analysis/phase2/decompiled/function-census.json"
    function_build_path = PROJECT_ROOT / "analysis/phase5/function-build-report.json"
    source_files = source_candidates()
    host_tools = {tool: shutil.which(tool) for tool in HOST_COMPILERS}
    windows_tools = {tool: shutil.which(tool) for tool in WINDOWS_BUILD_TOOLS}

    p1_manifest = json.loads(p1_manifest_path.read_text(encoding="utf-8"))
    p2_census = json.loads(p2_census_path.read_text(encoding="utf-8"))
    function_build = json.loads(function_build_path.read_text(encoding="utf-8"))
    game_binary = next(
        image for image in p1_manifest["embedded_images"] if image["name"] == "Bbb.exe"
    )
    entry_source = PROJECT_ROOT / "analysis/phase2/decompiled/functions/00439425_entry.c"
    compiler = host_tools.get("cc") or host_tools.get("gcc") or host_tools.get("clang")
    compile_probe = run_compileability_probe(entry_source, compiler) if compiler else {
        "compiler": None,
        "exit_code": None,
        "passed": False,
        "stderr_excerpt": "No C compiler is available.",
    }

    return {
        "schema_version": 1,
        "phase": 3,
        "status": "blocked",
        "gate_passed": False,
        "reference_binary": {
            "name": game_binary["name"],
            "sha256": game_binary["sha256"],
            "size": game_binary["size"],
        },
        "original_source_candidates": source_files,
        "original_source_candidate_count": len(source_files),
        "decompiler_output": {
            "function_count": p2_census["executable_function_count"],
            "pseudocode_count": p2_census["decompiled_function_count"],
            "assembly_fallback_count": p2_census["assembly_fallback_function_count"],
            "unresolved_count": p2_census["unresolved_function_count"],
            "compileable_as_is": compile_probe["passed"],
        },
        "function_level_build_proof": {
            "function": function_build["function"],
            "byte_identical": function_build["byte_identical"],
            "original_bytes": function_build["original_bytes"],
            "compiled_bytes": function_build["compiled_text_bytes"],
            "scope": function_build["scope"],
        },
        "host_compilers": host_tools,
        "windows_build_tools": windows_tools,
        "windows_sdk_headers_found": {
            header: any(Path(root, header).is_file() for root in ("/usr/include", "/usr/local/include"))
            for header in ("windows.h", "ddraw.h", "dsound.h")
        },
        "compileability_probe": compile_probe,
        "candidate_binary": None,
        "comparison": {
            "status": "not-run-no-rebuilt-binary",
            "byte_identical": None,
            "mismatch_bytes": None,
        },
        "blockers": [
            "No original C/C++ source or native project files were found.",
            "Ghidra pseudocode contains unresolved platform types, globals, stack symbols, and function declarations and does not compile as C as-is.",
            "No Windows-targeting compiler/linker or Windows/DirectX SDK headers are installed.",
            "The original compiler version and build flags remain unidentified.",
        ],
        "required_next_action": "Recover usable original source/project inputs, or continue an evidence-backed source reconstruction before attempting a native rebuild.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name("build-feasibility.json"),
        help="JSON feasibility report destination",
    )
    arguments = parser.parse_args()
    output_path = arguments.output.resolve()
    report = build_report()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"BUILD_STATUS={report['status']}")
    print(f"SOURCE_CANDIDATE_COUNT={report['original_source_candidate_count']}")
    print(f"PSEUDOCODE_COMPILEABLE={report['decompiler_output']['compileable_as_is']}")
    print(f"CANDIDATE_BINARY={report['candidate_binary']}")
    print(f"REPORT={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())