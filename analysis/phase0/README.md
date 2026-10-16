# Phase 0: Inventory and Safety

## Status

**Input integrity: pass. Clean-baseline evidence: unresolved.** The first
pre-edit Git snapshot reported the supplied files as untracked. A later check at
the same `HEAD` found all supplied paths in the commit tree and only the new
Phase 0 records untracked. This inconsistent Git evidence means the clean
baseline requirement is not claimed as satisfied. No supplied file has been
staged, rewritten, or intentionally changed by this work. The nested `rea/`
repository is clean. The project owner explicitly directed continuing to Phase 1;
this is recorded as an exception to the unresolved clean-baseline check, not as
proof that the original baseline was clean.

## Inventory

- Root baseline observed: commit `fb5f5fa9ac956f7bb59249de412b78e847935020` on
  `main`; current commit tree contains the supplied root files. See the Git
  status discrepancy in the status and evidence notes.
- Distribution: 43 files, 87,003,684 bytes, rooted at the repository top level.
- Launch configuration: `Autorun.inf` opens `SETUP.EXE`.
- Supplied executable: `Setup.exe`, 471,040 bytes, PE32 Windows GUI, Intel
  80386, image base `0x00400000`, entry RVA `0x708a`, linker version 6.0,
  PE timestamp 2002-06-24. SHA-256:
  `0e88d3fc1caf3f0e595a18cc992aca330e981ec1e5f0fc01584d5a1fb3629d46`.
- Installer payload: `Setup.dat`, 58,446,081 bytes. SHA-256:
  `97fa68e97505a9b13952e7bb6993a1ef4e122e3b31d73bc1bf3f82efc442728e`.
- `strings` on `Setup.dat` names embedded `Bbb.exe`, `BBB.dat`,
  `BBBMusic.dat`, and `BBBSound.dat`. These remain unextracted in Phase 0;
  `Bbb.exe` is the likely game executable, not the supplied `Setup.exe`.
- Additional inputs: DirectX cabinet files and setup libraries, 20 small JPEGs,
  and 10 Portuguese HTML manual pages.
- No game source, map, PDB, or standalone `Bbb.exe` was found in the supplied
  distribution root. No compiler for the game has been identified.
- The manual says the game is Big Brother Brasil and describes installation
  with DirectX 8.0. Its credits name Brasoft Studios and Continuum Entertainment
  and identify programming staff. The user asserts the game files are theirs;
  that authorization is not independently verifiable here. Keep analysis local
  and do not publish the original files or extracted payload without confirmed
  distribution rights.

## Environment and Preservation

- Environment: Ubuntu 24.04.5 LTS; root repository commit above; nested `rea/`
  repository commit `180ba03bfddd5916251e81e97a500b1ede7a9eea` is clean.
- Available: `file`, `sha256sum`, GNU `objdump`, `readelf`, `strings`,
  `bsdtar`, and Docker Engine 29.8.0.
- Not available on the host: Wine, `7z`, or `cabextract`. No local Docker image
  was present when checked.
- The original files retain their observed mode `666`; do not treat permissions
  as write protection. Their contents are checked by `check.sh` against the
  pinned manifest.
- The original game/install content is already present in the repository tree.
  Only the Phase 0 records are new in this work; do not publish the payload
  without confirmed distribution rights.

## Plan and Gates

| Phase | Status | Next required gate |
| --- | --- | --- |
| 0. Inventory and safety | Input hashes pass; baseline discrepancy exception authorized | Retain the discrepancy in the evidence log; do not publish original inputs |
| 1. Format analysis and extraction | Passed for Setup.exe and embedded PE ranges | Continue to Phase 2 only on a new project-owner instruction |
| 2. Baseline and reference tools | Passed with documented tool/runtime limitations | Phase 3 requires a source/build feasibility assessment |
| 3. Reproducible build | Blocked: no buildable source or Windows toolchain | Continue evidence-backed source reconstruction; do not claim a build or binary comparison |
| 4. Function and symbol census | Not started | Executable-region classification and measured coverage |
| 5. Reconstruct one function | Two functions match exactly; broader gates pending | Expand only from verified function-level evidence |
| 6. Scale with AI | Not started | Regression-tested batch with stable denominators |
| 7. Runtime validation | Not started | Reproducible original/reconstruction comparisons |
| 8. Cleanup and readability | Not started | Recomputed match rates and regression checks |
| 9. Release | Not started | Fresh-clone reproduction with authorized local inputs |

## Evidence Log

- `file Setup.exe` and `objdump -x Setup.exe`: PE32 GUI, i386, four sections,
  image base and entry-point details above. These identify the installer, not
  necessarily the game executable.
- `Autorun.inf`: points to `SETUP.EXE`.
- `strings -a Setup.dat`: includes game executable and resource filenames.
- `MANUAL/intro.htm`: describes the CD installer and DirectX 8.0.
- `MANUAL/creditos.htm`: names the production/development companies and staff.
- `strings -a Setup.exe`: includes Visual C++ runtime text and source paths under
  `C:\Work\VSS\App\BBB\Setup\`. This is installer evidence only and does not
  identify the game compiler.
- `sha256sum` over all 43 root distribution files is pinned in
  `input-sha256.txt`; `check.sh` validates each hash and the inventory count.
- Initial pre-edit Git status reported the distribution files untracked; a later
  check at the same root `HEAD` showed 44 tracked tree entries (43 distribution
  files plus the `rea` gitlink), with only the new Phase 0 records untracked.
  `git diff --cached` was empty. The origin of this change in reported state is
  unknown, so a clean pre-edit baseline is not asserted.
- The project owner explicitly requested continuing to Phase 1 despite the
  unresolved baseline discrepancy. Extraction is limited to read-only inputs,
  generated output paths, and machine-checked range/hash reconciliation.
- The project owner later instructed `fix it` after Phase 3 was blocked by the
  absence of buildable source. This authorizes a narrow source-reconstruction
  probe; Phase 3 remains blocked and no whole-game executable is claimed.
- The integrity check `bash analysis/phase0/check.sh` passed after the Wine run:
  all 43 distribution files matched their recorded hashes and inventory count.
- Runtime check: `Setup.exe` was invoked as `timeout --signal=TERM --kill-after=5s
  45s wine Setup.exe` in `scottyhardy/docker-wine@sha256:2133f429d75dd4f652580554279212105bf91d9eafd5ff8e7773dbe83a8b5b2f`.
  The container had networking disabled, the repository bind mount was
  read-only, and the Wine prefix was temporary. Wine printed
  `SETUP_EXIT=0`. This establishes an installer process exit under Wine only;
  it does not establish successful installation, game launch, or game runtime
  behavior. The earlier attempts failed during container setup and were stopped.

## Known Limitations and Next Actions

- The exact game executable is embedded in `Setup.dat`; identifying/extracting
  it is Phase 1 and has not been performed.
- The game executable remains embedded in `Setup.dat`; no game installation or
  game launch was established by running the setup program under Wine.
- Reconcile why the first Git status reported the distribution as untracked
  while the same `HEAD` now contains those files. Do not stage, move, or publish
  original inputs to resolve this discrepancy.
- The baseline discrepancy remains an exception to close before any public
  release; it does not establish permission to distribute proprietary payloads.