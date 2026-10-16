#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest="$repo_root/analysis/phase0/input-sha256.txt"

cd "$repo_root"
sha256sum --check --strict "$manifest"

expected_count="$(awk 'END { print NR }' "$manifest")"
actual_count="$(find . -maxdepth 2 -type f \
  ! -path './.git/*' \
  ! -path './rea/*' \
  ! -path './analysis/*' \
  | wc -l)"

if [[ "$actual_count" -ne "$expected_count" ]]; then
  printf 'FAIL: manifest lists %s inputs; found %s in the distribution root\n' \
    "$expected_count" "$actual_count" >&2
  exit 1
fi

printf 'PASS: all %s inventoried distribution files match their recorded SHA-256 hashes\n' \
  "$expected_count"