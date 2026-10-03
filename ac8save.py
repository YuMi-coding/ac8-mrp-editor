#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import struct
from pathlib import Path

POLY = 0xEDB88320
INIT = 0xBE6E9142
XOROUT = 0xFFFFFFFF


class SaveFormatError(RuntimeError):
    pass


def crc32_ac8(buf: bytes) -> int:
    crc = INIT
    for b in buf:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ POLY if (crc & 1) else (crc >> 1)
        crc &= 0xFFFFFFFF
    return crc ^ XOROUT


def _find_packed_data(data: bytearray) -> tuple[int, int]:
    packed_name = data.find(b"PackedData")
    if packed_name < 0:
        raise SaveFormatError("PackedData property not found")

    byte_prop = data.find(b"ByteProperty\x00", packed_name)
    if byte_prop < 0:
        raise SaveFormatError("PackedData ByteProperty not found")

    p = byte_prop + len(b"ByteProperty\x00")
    if p + 13 > len(data):
        raise SaveFormatError("PackedData metadata is truncated")

    packed_count = struct.unpack_from("<I", data, p + 9)[0]
    packed_start = p + 13
    packed_end = packed_start + packed_count
    if packed_end > len(data):
        raise SaveFormatError("PackedData payload extends beyond file")
    return packed_start, packed_end


def _find_u32_checksum_offset(data: bytearray, packed_end: int) -> int:
    checksum_name = data.find(b"Checksum", packed_end)
    if checksum_name < 0:
        raise SaveFormatError("Checksum property not found")

    u32_prop = data.find(b"UInt32Property\x00", checksum_name)
    if u32_prop < 0:
        raise SaveFormatError("Checksum UInt32Property not found")

    # UE property header layout observed in the tested AC8 build:
    # name, type, size(4), array index(4), property-guid flag(1), value(4)
    value_off = u32_prop + len(b"UInt32Property\x00") + 4 + 4 + 1
    if value_off + 4 > len(data):
        raise SaveFormatError("Checksum value is truncated")
    return value_off


def _find_int64_property_value(data: bytearray, name: bytes, start: int, end: int) -> int:
    prop = data.find(name + b"\x00", start, end)
    if prop < 0:
        raise SaveFormatError(f"{name.decode()} property not found")

    int64_prop = data.find(b"Int64Property\x00", prop, min(end, prop + 128))
    if int64_prop < 0:
        raise SaveFormatError(f"{name.decode()} is not an Int64Property")

    value_off = int64_prop + len(b"Int64Property\x00") + 4 + 4 + 1
    if value_off + 8 > end:
        raise SaveFormatError(f"{name.decode()} value is truncated")
    return value_off


def inspect_save(path: Path) -> dict[str, int | bool]:
    data = bytearray(path.read_bytes())
    packed_start, packed_end = _find_packed_data(data)
    checksum_off = _find_u32_checksum_offset(data, packed_end)
    current_off = _find_int64_property_value(data, b"CurrentMRP", packed_start, packed_end)
    total_off = _find_int64_property_value(data, b"TotalMRP", packed_start, packed_end)

    current = struct.unpack_from("<q", data, current_off)[0]
    total = struct.unpack_from("<q", data, total_off)[0]
    stored_checksum = struct.unpack_from("<I", data, checksum_off)[0]
    calculated_checksum = crc32_ac8(bytes(data[packed_start:packed_end]))

    return {
        "current_mrp": current,
        "total_mrp": total,
        "stored_checksum": stored_checksum,
        "calculated_checksum": calculated_checksum,
        "checksum_valid": stored_checksum == calculated_checksum,
    }


def add_mrp(path: Path, amount: int, backup: bool = True) -> dict[str, int | bool]:
    if amount < 0:
        raise ValueError("amount must be non-negative")

    data = bytearray(path.read_bytes())
    packed_start, packed_end = _find_packed_data(data)
    checksum_off = _find_u32_checksum_offset(data, packed_end)
    current_off = _find_int64_property_value(data, b"CurrentMRP", packed_start, packed_end)
    total_off = _find_int64_property_value(data, b"TotalMRP", packed_start, packed_end)

    stored_checksum = struct.unpack_from("<I", data, checksum_off)[0]
    calculated_checksum = crc32_ac8(bytes(data[packed_start:packed_end]))
    if stored_checksum != calculated_checksum:
        raise SaveFormatError(
            f"Refusing to edit invalid save: stored checksum 0x{stored_checksum:08X}, "
            f"calculated 0x{calculated_checksum:08X}"
        )

    current = struct.unpack_from("<q", data, current_off)[0]
    total = struct.unpack_from("<q", data, total_off)[0]
    new_current = current + amount
    new_total = total + amount

    struct.pack_into("<q", data, current_off, new_current)
    struct.pack_into("<q", data, total_off, new_total)

    new_checksum = crc32_ac8(bytes(data[packed_start:packed_end]))
    struct.pack_into("<I", data, checksum_off, new_checksum)

    if backup:
        backup_path = path.with_suffix(path.suffix + ".bak")
        if not backup_path.exists():
            shutil.copy2(path, backup_path)

    path.write_bytes(data)
    return inspect_save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="ACE COMBAT 8 campaign MRP save editor")
    sub = parser.add_subparsers(dest="command", required=True)

    info = sub.add_parser("info", help="inspect MRP values and checksum")
    info.add_argument("save", type=Path)

    add = sub.add_parser("add-mrp", help="add MRP to current and lifetime totals")
    add.add_argument("save", type=Path)
    add.add_argument("amount", type=int)
    add.add_argument("--no-backup", action="store_true")

    args = parser.parse_args()

    try:
        if args.command == "info":
            result = inspect_save(args.save)
        else:
            result = add_mrp(args.save, args.amount, backup=not args.no_backup)
    except (OSError, SaveFormatError, ValueError) as exc:
        parser.error(str(exc))

    print(f"CurrentMRP: {result['current_mrp']:,}")
    print(f"TotalMRP:   {result['total_mrp']:,}")
    print(f"Checksum:   0x{result['stored_checksum']:08X}")
    print(f"Valid:      {'yes' if result['checksum_valid'] else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
