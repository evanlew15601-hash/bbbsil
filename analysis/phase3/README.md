# Phase 3: Reproducible Build Feasibility

## Result: Blocked

No rebuilt game binary was produced. The repository has no original C/C++ source,
Visual Studio project, map, or PDB. The 877 Ghidra C-like pseudocode files are
not compilable source as-is: the entry-point compileability probe fails on
unknown Windows/Ghidra types, unresolved globals and stack symbols, and
undeclared functions. One function has an assembly fallback.

The host has Linux Clang 18 and GCC 13, but no Windows compiler/linker or Windows
SDK/DirectX headers. The original compiler release and build flags remain
unknown. Using host GCC with guessed declarations would not produce a
behaviorally meaningful or comparable Windows game, so no placeholder binary
is labeled a rebuild.

One function has since been reconstructed and compiled to an i386 Windows COFF
object with a byte-identical seven-byte `.text` range. Its source, object, and
comparison report are documented in [`../phase5/README.md`](../phase5/README.md).
That is not a linked game executable and does not remove the full-build blockers.
This narrow recovery was performed in response to the project owner's `fix it`
instruction; the Phase 3 gate remains blocked pending a complete source/build
path.

The machine-readable result is [`build-feasibility.json`](build-feasibility.json).
Regenerate it with:

```sh
python3 analysis/phase3/assess_build.py
```

The script records whether usable source exists, the actual compiler/tool
availability, a compileability probe, the Phase 2 function totals, and the fact
that binary comparison was not run because there is no candidate rebuilt binary.
Its test ensures the report cannot misrepresent this state as a successful
rebuild:

```sh
python3 -m unittest discover -s analysis/phase3 -p 'test_*.py' -v
```

## Gate

**Not passed.** The runnable assessment and regression test pass, but the
required native build and machine-readable byte comparison do not exist because
there is no buildable source/toolchain combination. A valid next action is to
continue the source reconstruction from the function census, with a proper
Windows/DirectX SDK and recovered types/imports, then attempt a candidate build.
Until then there is no binary to compare and no basis for a matching-build claim.