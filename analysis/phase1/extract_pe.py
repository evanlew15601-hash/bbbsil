#!/usr/bin/env python3
"""Map PE32 sections and extract validated PE images embedded in Setup.dat."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGE_FILE_MACHINE_I386 = 0x014C
IMAGE_NT_OPTIONAL_HDR32_MAGIC = 0x010B
IMAGE_SCN_MEM_EXECUTE = 0x20000000
IMAGE_SCN_MEM_READ = 0x40000000
IMAGE_SCN_MEM_WRITE = 0x80000000


class PEFormatError(ValueError):
    """Raised when a byte range does not contain a bounded PE32 image."""


@dataclass(frozen=True)
class PESection:
    name: str
    virtual_size: int
    virtual_address: int
    raw_size: int
    raw_offset: int
    characteristics: int


@dataclass(frozen=True)
class PEImage:
    base_offset: int
    machine: int
    section_count: int
    entry_rva: int
    image_base: int
    size_of_headers: int
    size_of_image: int
    declared_file_size: int
    sections: tuple[PESection, ...]


def read_u16(data: bytes, offset: int, limit: int) -> int:
    if offset < 0 or offset + 2 > limit:
        raise PEFormatError("16-bit field exceeds input bounds")
    return struct.unpack_from("<H", data, offset)[0]


def read_u32(data: bytes, offset: int, limit: int) -> int:
    if offset < 0 or offset + 4 > limit:
        raise PEFormatError("32-bit field exceeds input bounds")
    return struct.unpack_from("<I", data, offset)[0]


def parse_pe(data: bytes, base_offset: int = 0, *, strict: bool = True) -> PEImage | None:
    """Parse a bounded little-endian PE32/i386 image at an absolute offset."""
    try:
        if base_offset < 0 or base_offset + 64 > len(data):
            raise PEFormatError("truncated DOS header")
        if data[base_offset : base_offset + 2] != b"MZ":
            raise PEFormatError("missing DOS signature")

        pe_relative = read_u32(data, base_offset + 0x3C, len(data))
        pe_offset = base_offset + pe_relative
        if pe_offset + 24 > len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
            raise PEFormatError("missing or truncated PE signature")

        machine, section_count = struct.unpack_from("<HH", data, pe_offset + 4)
        optional_size = read_u16(data, pe_offset + 20, len(data))
        optional_offset = pe_offset + 24
        optional_end = optional_offset + optional_size
        if optional_end > len(data) or optional_size < 64:
            raise PEFormatError("truncated optional header")
        if machine != IMAGE_FILE_MACHINE_I386:
            raise PEFormatError(f"unsupported machine 0x{machine:04x}")
        if section_count == 0 or section_count > 96:
            raise PEFormatError("invalid section count")
        if read_u16(data, optional_offset, optional_end) != IMAGE_NT_OPTIONAL_HDR32_MAGIC:
            raise PEFormatError("optional header is not PE32")

        entry_rva = read_u32(data, optional_offset + 16, optional_end)
        image_base = read_u32(data, optional_offset + 28, optional_end)
        size_of_image = read_u32(data, optional_offset + 56, optional_end)
        size_of_headers = read_u32(data, optional_offset + 60, optional_end)
        if size_of_headers == 0 or base_offset + size_of_headers > len(data):
            raise PEFormatError("invalid or truncated PE headers")

        section_table = optional_end
        section_table_end = section_table + section_count * 40
        if section_table_end > len(data) or section_table_end > base_offset + size_of_headers:
            raise PEFormatError("section table exceeds PE headers")

        sections: list[PESection] = []
        raw_ranges: list[tuple[int, int]] = [(0, size_of_headers)]
        declared_file_size = size_of_headers
        for section_index in range(section_count):
            section_offset = section_table + section_index * 40
            raw_name = data[section_offset : section_offset + 8].split(b"\0", 1)[0]
            name = raw_name.decode("ascii", errors="replace") or f"section_{section_index}"
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", data, section_offset + 8
            )
            characteristics = read_u32(data, section_offset + 36, len(data))
            raw_end = raw_offset + raw_size
            if raw_size and (raw_offset < size_of_headers or base_offset + raw_end > len(data)):
                raise PEFormatError(f"section {name} has an invalid raw range")
            if raw_size:
                raw_ranges.append((raw_offset, raw_end))
                declared_file_size = max(declared_file_size, raw_end)
            sections.append(
                PESection(
                    name=name,
                    virtual_size=virtual_size,
                    virtual_address=virtual_address,
                    raw_size=raw_size,
                    raw_offset=raw_offset,
                    characteristics=characteristics,
                )
            )

        ordered_ranges = sorted(raw_ranges)
        for previous_range, current_range in zip(ordered_ranges, ordered_ranges[1:]):
            if current_range[0] < previous_range[1]:
                raise PEFormatError("PE raw ranges overlap")

        return PEImage(
            base_offset=base_offset,
            machine=machine,
            section_count=section_count,
            entry_rva=entry_rva,
            image_base=image_base,
            size_of_headers=size_of_headers,
            size_of_image=size_of_image,
            declared_file_size=declared_file_size,
            sections=tuple(sections),
        )
    except (PEFormatError, struct.error) as error:
        if strict:
            if isinstance(error, PEFormatError):
                raise
            raise PEFormatError("truncated PE field") from error
        return None


def find_embedded_pes(data: bytes) -> tuple[list[PEImage], int]:
    candidates: list[PEImage] = []
    mz_count = 0
    cursor = 0
    while True:
        candidate_offset = data.find(b"MZ", cursor)
        if candidate_offset < 0:
            break
        mz_count += 1
        candidate = parse_pe(data, candidate_offset, strict=False)
        if candidate is not None:
            candidates.append(candidate)
        cursor = candidate_offset + 2

    candidates.sort(key=lambda candidate: candidate.base_offset)
    for previous, current in zip(candidates, candidates[1:]):
        previous_end = previous.base_offset + previous.declared_file_size
        if current.base_offset < previous_end:
            raise PEFormatError("validated embedded PE ranges overlap")
    return candidates, mz_count


def classify_embedded_pe(data: bytes) -> tuple[str, str, list[str]]:
    lowered = data.lower()
    game_markers = (
        b"directdrawcreateex",
        b"%s\\bbbmusic.dat",
        b"%s\\bbbsound.dat",
        b"%s\\bbb.dat",
        b"software\\continuum entertainment\\bbb",
    )
    if all(marker in lowered for marker in game_markers):
        return (
            "Bbb.exe",
            "game-executable",
            [
                "DirectDrawCreateEx import string",
                "BBB music, sound, and data filename references",
                "Continuum Entertainment BBB registry path",
            ],
        )

    helper_markers = (
        b"cuninst",
        b"installdir",
        b"uninstall",
        b"software\\continuum entertainment",
    )
    if all(marker in lowered for marker in helper_markers):
        return (
            "Cuninst.exe",
            "uninstaller-executable",
            [
                "Cuninst identifier",
                "InstallDir and Uninstall strings",
                "Continuum Entertainment registry path",
            ],
        )

    return "", "unresolved-executable", []


def section_permissions(characteristics: int) -> list[str]:
    permissions = []
    if characteristics & IMAGE_SCN_MEM_READ:
        permissions.append("read")
    if characteristics & IMAGE_SCN_MEM_WRITE:
        permissions.append("write")
    if characteristics & IMAGE_SCN_MEM_EXECUTE:
        permissions.append("execute")
    return permissions


def section_type(section: PESection) -> str:
    if section.characteristics & IMAGE_SCN_MEM_EXECUTE:
        return "code"
    if section.name.lower() == ".rsrc":
        return "resources"
    return "data"


def sha256(data: bytes | memoryview) -> str:
    return hashlib.sha256(data).hexdigest()


def build_segments(
    input_name: str,
    input_data: bytes,
    known_regions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ordered_regions = sorted(known_regions, key=lambda region: region["offset"])
    segments: list[dict[str, Any]] = []
    cursor = 0

    def append_segment(
        offset: int,
        size: int,
        name: str,
        kind: str,
        permissions: list[str] | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        segment = {
            "input": input_name,
            "name": name,
            "offset": offset,
            "size": size,
            "type": kind,
            "permissions": permissions,
            "sha256": sha256(memoryview(input_data)[offset : offset + size]),
        }
        if details:
            segment.update(details)
        segments.append(segment)

    unresolved_index = 0
    for region in ordered_regions:
        region_start = region["offset"]
        region_end = region_start + region["size"]
        if region_start < cursor or region_end > len(input_data):
            raise PEFormatError(f"invalid or overlapping mapped range in {input_name}")
        if region_start > cursor:
            append_segment(
                cursor,
                region_start - cursor,
                f"{input_name}:unresolved:{unresolved_index:03d}",
                "unresolved",
                None,
            )
            unresolved_index += 1
        append_segment(
            region_start,
            region["size"],
            region["name"],
            region["type"],
            region["permissions"],
            region.get("details"),
        )
        cursor = region_end

    if cursor < len(input_data):
        append_segment(
            cursor,
            len(input_data) - cursor,
            f"{input_name}:unresolved:{unresolved_index:03d}",
            "unresolved",
            None,
        )

    if sum(segment["size"] for segment in segments) != len(input_data):
        raise PEFormatError(f"segment ranges do not cover {input_name}")
    return segments


def pe_regions(image: PEImage, label: str) -> list[dict[str, Any]]:
    regions = [
        {
            "offset": image.base_offset,
            "size": image.size_of_headers,
            "name": f"{label}:headers",
            "type": "pe-header",
            "permissions": ["read"],
            "details": {"rva": 0},
        }
    ]
    for section in image.sections:
        if section.raw_size == 0:
            continue
        regions.append(
            {
                "offset": image.base_offset + section.raw_offset,
                "size": section.raw_size,
                "name": f"{label}:{section.name}",
                "type": section_type(section),
                "permissions": section_permissions(section.characteristics),
                "details": {
                    "rva": section.virtual_address,
                    "virtual_size": section.virtual_size,
                },
            }
        )
    return regions


def describe_pe(image: PEImage) -> dict[str, Any]:
    return {
        "format": "PE32",
        "architecture": "Intel 80386",
        "endianness": "little",
        "machine": f"0x{image.machine:04x}",
        "offset": image.base_offset,
        "size": image.declared_file_size,
        "entry_rva": image.entry_rva,
        "image_base": f"0x{image.image_base:08x}",
        "size_of_image": image.size_of_image,
        "section_count": image.section_count,
    }


def write_extraction(output_dir: Path, manifest_path: Path) -> dict[str, Any]:
    setup_path = PROJECT_ROOT / "Setup.exe"
    data_path = PROJECT_ROOT / "Setup.dat"
    source_paths = (setup_path.resolve(), data_path.resolve())
    output_dir = output_dir.resolve()
    manifest_path = manifest_path.resolve()
    if any(path.parent == output_dir for path in source_paths):
        raise ValueError("extraction output must not share a directory with original inputs")
    if manifest_path in source_paths:
        raise ValueError("refusing to write a manifest over an original input")

    setup_bytes = setup_path.read_bytes()
    data_bytes = data_path.read_bytes()
    setup_image = parse_pe(setup_bytes)
    assert setup_image is not None
    embedded_images, mz_count = find_embedded_pes(data_bytes)

    candidates: list[dict[str, Any]] = []
    artifacts: list[tuple[str, int, int, bytes]] = []
    data_regions: list[dict[str, Any]] = []
    for candidate_index, image in enumerate(embedded_images, start=1):
        image_bytes = data_bytes[
            image.base_offset : image.base_offset + image.declared_file_size
        ]
        name, classification, evidence = classify_embedded_pe(image_bytes)
        if not name:
            name = f"embedded_pe_candidate_{candidate_index:03d}.exe"
        artifact_hash = sha256(image_bytes)
        candidates.append(
            {
                **describe_pe(image),
                "name": name,
                "classification": classification,
                "evidence": evidence,
                "sha256": artifact_hash,
            }
        )
        artifacts.append((name, image.base_offset, image.declared_file_size, image_bytes))
        data_regions.extend(pe_regions(image, name))

    if not embedded_images:
        raise PEFormatError("no validated PE32 images found inside Setup.dat")
    if len({artifact[0] for artifact in artifacts}) != len(artifacts):
        raise PEFormatError("embedded PE labels are ambiguous")

    setup_regions = pe_regions(setup_image, "Setup.exe")
    segments = build_segments("Setup.exe", setup_bytes, setup_regions)
    segments.extend(build_segments("Setup.dat", data_bytes, data_regions))
    inputs = [
        {
            "path": "Setup.exe",
            "size": len(setup_bytes),
            "sha256": sha256(setup_bytes),
            **describe_pe(setup_image),
        },
        {
            "path": "Setup.dat",
            "size": len(data_bytes),
            "sha256": sha256(data_bytes),
            "format": "custom installer data; schema unresolved",
            "observed_header": "01 00 00 00 [INSTALL]",
            "archive_probe": "libarchive rejected as an unrecognized archive",
            "scanned_mz_signatures": mz_count,
            "validated_embedded_pe_count": len(embedded_images),
        },
    ]
    manifest = {
        "schema_version": 1,
        "tool": "analysis/phase1/extract_pe.py",
        "inputs": inputs,
        "embedded_images": candidates,
        "segments": segments,
        "coverage": [
            {
                "input": "Setup.exe",
                "input_size": len(setup_bytes),
                "mapped_bytes": sum(
                    segment["size"] for segment in segments if segment["input"] == "Setup.exe"
                ),
                "exact": True,
            },
            {
                "input": "Setup.dat",
                "input_size": len(data_bytes),
                "mapped_bytes": sum(
                    segment["size"] for segment in segments if segment["input"] == "Setup.dat"
                ),
                "exact": True,
            },
        ],
        "artifacts": [
            {
                "path": artifact_name,
                "source": "Setup.dat",
                "offset": offset,
                "size": size,
                "sha256": sha256(payload),
            }
            for artifact_name, offset, size, payload in artifacts
        ],
    }

    output_paths = {(output_dir / artifact[0]).resolve() for artifact in artifacts}
    if manifest_path in output_paths:
        raise ValueError("manifest path conflicts with an extracted executable")

    output_dir.mkdir(parents=True, exist_ok=True)
    for artifact_name, offset, size, payload in artifacts:
        destination = output_dir / artifact_name
        if destination.resolve() in source_paths:
            raise ValueError("refusing to overwrite an original input")
        if destination.exists():
            if destination.read_bytes() != payload:
                raise FileExistsError(f"refusing to replace different output {destination}")
        else:
            destination.write_bytes(payload)
        if destination.stat().st_size != size or sha256(destination.read_bytes()) != sha256(payload):
            raise OSError(f"extracted output did not reconcile: {destination}")

    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "extracted",
        help="directory for validated embedded PE files (default: ignored extracted/)",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="manifest JSON destination (default: manifest.json in --output-dir)",
    )
    arguments = parser.parse_args()
    manifest_path = arguments.manifest or arguments.output_dir / "manifest.json"
    try:
        manifest = write_extraction(arguments.output_dir, manifest_path)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(
        f"mapped {len(manifest['segments'])} ranges across 2 inputs; "
        f"validated {len(manifest['embedded_images'])} embedded PE images"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())