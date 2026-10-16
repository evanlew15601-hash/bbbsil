# Phase 2: Baseline and Reference Tools

## Reference Binary

The analysis target is the locally extracted `Bbb.exe` from `Setup.dat`, not
`Setup.exe` (the CD installer). Its SHA-256 is recorded in
[`../phase1/manifest.json`](../phase1/manifest.json). The Phase 1 manifest maps
the PE headers and sections, and its tests prove exact range coverage against
the original containers.

Observed PE facts:

- PE32, Intel 80386, little-endian, Windows GUI.
- Image base `0x00400000`; entry RVA `0x39425`, entry VA `0x00439425`.
- `SizeOfImage` is `0x53000`; four sections: `.text`, `.rdata`, `.data`, `.rsrc`.
- PE timestamp: 2002-06-24 10:11:59 UTC as encoded in the header.
- Imports include `KERNEL32`, `USER32`, `GDI32`, `ADVAPI32`, `SHELL32`, `DDRAW`,
  and `DSOUND`.
- GNU `objdump -t` reports `no symbols`. Ghidra reported missing PDB metadata.
  No source, map, PDB, or other symbol file was found in the supplied files.

## Compiler Evidence

The image contains generic Microsoft Visual C++ runtime strings and source paths
under `E:\WORK\VSS\APP\BBB\` and `E:\WORK\VSS\API\`. The PE timestamp and
linker-version fields are recorded in the Phase 1 parser output. These facts do
not establish a specific compiler release, compiler flags, or source revision;
no compiler has been identified.

## Reference Tools

- Disassembly: GNU `objdump` and LLVM `llvm-objdump` from the host binutils/LLVM
  packages. A reproducible sample is:

  ```sh
  llvm-objdump -d --x86-asm-syntax=intel \
    --start-address=0x401000 --stop-address=0x401040 \
    analysis/phase1/extracted/Bbb.exe
  ```

- Decompiler: Ghidra 12.1.4 headless analyzer and decompiler. The official
  archive was downloaded from the National Security Agency's GitHub release
  `Ghidra_12.1.4_build`, asset
  `ghidra_12.1.4_PUBLIC_20260921.zip` (569,649,598 bytes). Its computed local
  SHA-256 is
  `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`.
  The release did not publish a separate checksum asset; this digest is a local
  reference, not a publisher-provided verification value. The ZIP integrity test
  passed.
- Runtime: Wine 11.0 in the pinned local Docker image used in Phase 0. The
  original distribution is mounted read-only, networking is disabled, and
  writable Wine state is temporary. A game launch attempt faulted under Wine;
  with Xvfb it faulted at `0x0042AE62` writing `0x91D` and timed out in the
  debugger. Game data files were not installed or extracted, so this is not a
  Windows-runtime baseline and does not establish original-game behavior.

## Ghidra Results

Ghidra 12.1.4 ran under OpenJDK 25 and loaded the file as
`x86:LE:32:default:windows`. Automatic analysis completed successfully in 57
seconds. PDB analysis was skipped because the PE has no PDB information. The
standard Windows/DirectX import libraries were not found in the configured
search paths, so those external symbols remain unresolved. Ghidra's default
Windows VS12 type archive being applied is analyzer configuration, not evidence
that the game was compiled with Visual Studio 2013.

Reproduce the end-to-end baseline with the unpacked Ghidra directory:

```sh
GHIDRA_HOME=/path/to/ghidra_12.1.4_PUBLIC \
  ./analysis/phase2/run_baseline.sh
```

The runner rechecks all Phase 0 input hashes, runs the Phase 1 extraction tests,
extracts to a fresh temporary directory, creates a temporary Ghidra project,
performs analysis, and decompiles every function Ghidra places in executable
memory. C pseudocode and the function census are written under the ignored
`decompiled/` directory. If Ghidra cannot produce C for a function, its
instruction listing is saved as an `.asm` fallback with the exact decompiler
error in the census. The runner checks that every discovered function has a
nonempty output, then removes its temporary project.

## Runtime and Gate Status

The installer completed under Wine in Phase 0; the actual game has not completed
a runtime launch. The current Wine fault is retained as an observation from an
incomplete environment (uninstalled game assets), not treated as a behavioral
conclusion. A Windows-compatible runtime with the complete installed data set
is needed for meaningful checkpoints.

**Phase 2 baseline gate:** PE architecture and segment map are validated;
disassembly and decompilation tools are available; the headless Ghidra import
and all discovered executable functions' output coverage are machine-checked by
`run_baseline.sh`. The verified whole-game pass found 878 functions: 877 have
C-like pseudocode in the ignored
[`decompiled/functions/`](decompiled/functions/) directory and one has an
assembly fallback there. The census is
[`decompiled/function-census.json`](decompiled/function-census.json). Ghidra
failed to produce pseudocode for `FUN_004125b0` with
`Cannot properly adjust input varnodes` in its `decompile`, `normalize`, and
`firstpass` styles; its instructions are preserved in the fallback file. Thus
878/878 functions have output, but only 877/878 have decompiler pseudocode.
Symbols,
compiler version, Windows SDK imports, and complete game runtime behavior remain
unavailable or unresolved. The baseline runner passed with Ghidra 12.1.4 and
OpenJDK 25; Phase 3 has not started.