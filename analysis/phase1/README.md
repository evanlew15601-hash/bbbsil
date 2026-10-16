# Phase 1: Format Analysis and Extraction

## Findings

- `Setup.exe` is the launch target named by `Autorun.inf`. It is PE32/i386,
  little-endian, Windows GUI. Its four raw sections are parsed from PE headers.
- `Setup.dat` is a custom installer data file, not a libarchive-supported
  archive. It begins with a 32-bit value `1` followed by `[INSTALL]`; its full
  record schema remains unresolved.
- A bounded scan found 576 `MZ` byte pairs but only two non-overlapping,
  structurally valid embedded PE32/i386 images. Header and section boundaries
  validate both image extents.
- The image at `Setup.dat` offset `0x9a1d` is labeled `Bbb.exe` because its
  strings reference `DirectDrawCreateEx`, the BBB data/audio files, and the
  Continuum Entertainment BBB registry path. Its validated PE size is 303,104
  bytes.
- The image at offset `0x36dd2ae` is labeled `Cuninst.exe` because its strings
  contain `Cuninst`, `InstallDir`, and `Uninstall` references. Its validated PE
  size is 90,112 bytes.
- Remaining bytes in `Setup.dat` are explicitly classified as unresolved, not
  guessed as padding or a known asset format. The manifest reports 58,052,865
  unresolved bytes across that container.
- The embedded Portuguese license text includes a restriction against reverse
  engineering/decompilation. The user asserts ownership/authorization; that claim
  is not independently verifiable. Keep derived payloads local and confirm the
  applicable rights before any redistribution or release.

## Reproduction

Run the extractor and tests from the repository root:

```sh
python3 analysis/phase1/extract_pe.py \
  --output-dir analysis/phase1/extracted \
  --manifest analysis/phase1/manifest.json
python3 -m unittest discover -s analysis/phase1 -p 'test_*.py' -v
```

`extracted/` is ignored by Git because it contains proprietary binaries. The
repository `manifest.json` contains hashes, source offsets, PE sections,
permissions, and unresolved ranges but not payload bytes. The test performs two extractions
in temporary directories, compares their manifests, verifies each input range
is covered exactly once, and checks extracted files byte-for-byte against their
source ranges.

## Gate Status

**Passed for the analyzed binaries.** Three tests pass. They verify malformed PE
rejection, refusal to overwrite an original input, two-run manifest
determinism, exact input-range coverage, and byte-for-byte extraction of the two
embedded PE files. `file` and `objdump` independently identify both outputs as
PE32/i386 with four sections. This phase does not identify every `Setup.dat`
resource or establish game runtime behavior; the custom container schema and
the unresolved ranges remain open for evidence-based analysis.