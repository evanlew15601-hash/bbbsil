#!/usr/bin/env python3

import json
import sys
from pathlib import Path


def main() -> int:
    census_path = Path(sys.argv[1])
    census = json.loads(census_path.read_text(encoding="utf-8"))
    functions = census["functions"]
    function_count = census["executable_function_count"]
    if function_count == 0 or len(functions) != function_count:
        raise SystemExit("function census is empty or incomplete")

    output_statuses = {"decompiled", "assembly-fallback"}
    output_count = (
        census["decompiled_function_count"]
        + census["assembly_fallback_function_count"]
    )
    if output_count != function_count or census["unresolved_function_count"] != 0:
        raise SystemExit("not every executable function has an output")

    for function in functions:
        output_name = function["output"]
        output_path = census_path.parent / output_name
        if (
            function["status"] not in output_statuses
            or not output_path.is_file()
            or output_path.stat().st_size == 0
        ):
            raise SystemExit(f"missing output for function {function['entry']}")

    print(
        "FUNCTION_OUTPUTS: "
        f"{census['decompiled_function_count']} pseudocode, "
        f"{census['assembly_fallback_function_count']} assembly fallback, "
        f"{census['failed_function_count']} decompiler failures, "
        f"{function_count} total"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())