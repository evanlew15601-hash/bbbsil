#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ghidra_home="${GHIDRA_HOME:-}"

if [[ -z "$ghidra_home" || ! -x "$ghidra_home/support/analyzeHeadless" ]]; then
	printf 'Set GHIDRA_HOME to a Ghidra distribution containing support/analyzeHeadless\n' >&2
	exit 2
fi

"$repo_root/analysis/phase0/check.sh"
python3 -m unittest discover -s "$repo_root/analysis/phase1" -p 'test_*.py' -v

temporary_root="$(mktemp -d "${TMPDIR:-/tmp}/bbbsil-phase2.XXXXXX")"
trap 'rm -rf "$temporary_root"' EXIT
mkdir -p "$temporary_root/projects"
decompiled_dir="$repo_root/analysis/phase2/decompiled"
mkdir -p "$decompiled_dir"

python3 "$repo_root/analysis/phase1/extract_pe.py" \
	--output-dir "$temporary_root/extracted" \
	--manifest "$temporary_root/manifest.json"

"$ghidra_home/support/analyzeHeadless" \
	"$temporary_root/projects" \
	BbbBaseline \
	-import "$temporary_root/extracted/Bbb.exe" \
	-analysisTimeoutPerFile 180 \
	-max-cpu 2 \
	-scriptPath "$repo_root/analysis/phase2" \
	-postScript DecompileProgram.java "$decompiled_dir" \
	| tee "$temporary_root/ghidra.log"

grep -Fq 'FUNCTION_CENSUS=' "$temporary_root/ghidra.log"
grep -Fq 'UNRESOLVED_FUNCTION_COUNT=0' "$temporary_root/ghidra.log"
python3 "$repo_root/analysis/phase2/verify_census.py" \
	"$decompiled_dir/function-census.json"
printf 'PASS: extraction hashes, range tests, Ghidra analysis, and whole-program function output coverage\n'