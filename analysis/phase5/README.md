# Phase 5: Reconstruct One Function

## Reconstructed Function

`FUN_00424010` at VA `0x00424010` is a seven-byte `__fastcall` function. Its
input arrives in `ECX`; the body stores the immediate `0x00442464` to the
pointed-to 32-bit slot and returns. A direct tail-call from `0x00424916` and
the disassembly support the boundary and calling convention. The symbol remains
address-based because no semantic name is established.

`FUN_0040ffb0` at VA `0x0040ffb0` is a three-byte `__fastcall` identity
function: it returns its `ECX` argument in `EAX`. Its machine bytes are
`8b c1 c3`. Clang's integrated assembler chose the equivalent `89 c8` encoding
for a mnemonic `mov`, so this source uses the evidence-verified `.byte` sequence
to preserve the original instruction bytes exactly.

The sources are in [`functions/`](functions/). Each is compiled separately with
host Clang targeting `i686-pc-windows-msvc`, at `-O2` and freestanding settings.
The object `.text` is compared directly with each original function range.

Reproduce the object build and machine-readable comparison:

```sh
python3 analysis/phase5/build_function.py
python3 -m unittest discover -s analysis/phase5 -p 'test_*.py' -v
```

The object and extracted `.text` are in the ignored `build/` directory. The
report is [`function-build-report.json`](function-build-report.json).

## Gate and Limitations

Both function objects must match byte-for-byte; the test verifies all ten
instruction bytes. This is **not** a linked or runnable game binary. It is a
narrow compiler/source-reconstruction checkpoint, not resolution of the blocked
Phase 3 full-game build. Full-game source, import bindings, recovered types,
assets, and a compatible Windows SDK/toolchain are still required.