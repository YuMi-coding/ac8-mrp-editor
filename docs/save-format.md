# ACE COMBAT 8 campaign save format notes

These notes document observations from the tested AC8 Windows/Steam build and two independently game-generated `Campaign.sav` files.

## Container

`Campaign.sav` is an Unreal-style `GVAS` save. The campaign payload is stored under a property named `PackedData`.

Relevant fields observed inside the payload:

- `CurrentMRP` — `Int64Property`
- `TotalMRP` — `Int64Property`

An application-level `Checksum` is stored outside the packed payload as a `UInt32Property`.

## MRP behavior

Observed pair of saves:

```text
Save A
CurrentMRP = 161700
TotalMRP   = 161700
Checksum   = 0x704393E0

Save B, after spending 6000 MRP
CurrentMRP = 155700
TotalMRP   = 161700
Checksum   = 0xC9785199
```

This indicates:

- `CurrentMRP` is the spendable balance.
- `TotalMRP` is a lifetime-earned/acquired counter and does not decrease on purchase.

Therefore an operation that *adds earned MRP* should increase both values by the same amount. An operation that merely changes the spendable balance may reasonably change only `CurrentMRP`, but that behavior has not yet been tested in-game by this project.

## Checksum

For the tested build, the checksum is reflected CRC-32 over the exact `PackedData` payload bytes.

Parameters:

```text
width   = 32
poly    = 0xEDB88320  # reflected representation
init    = 0xBE6E9142
xorout  = 0xFFFFFFFF
refin   = true
refout  = true
```

Pseudo-code:

```python
crc = 0xBE6E9142
for byte in packed_data:
    crc ^= byte
    for _ in range(8):
        crc = (crc >> 1) ^ 0xEDB88320 if crc & 1 else crc >> 1
        crc &= 0xFFFFFFFF
checksum = crc ^ 0xFFFFFFFF
```

The parameters above reproduce both known-good checksum values listed earlier.

## `PackedData` boundary detection

The current prototype locates the ASCII property name `PackedData`, then the following `ByteProperty\0` type marker. In the tested file layout, the byte array length is a little-endian `uint32` at offset `+9` from the end of the `ByteProperty\0` marker and payload begins at `+13`.

This is intentionally documented as an observation rather than a stable public format contract. A future AC8 update may change serialization details.

## Property-value offsets

For the tested build, relevant Unreal property headers appear as:

```text
property name
property type
size        uint32
array index uint32
has guid    uint8
value       ...
```

The prototype uses that observed layout to locate `Int64Property` and `UInt32Property` values.

## Validation strategy

Before modifying a save, an editor should:

1. Locate the `PackedData` range.
2. Locate the stored `Checksum`.
3. Recalculate the checksum over unmodified `PackedData`.
4. Refuse to edit if stored and calculated checksums differ.
5. Update the requested fields.
6. Recalculate and write the checksum.
7. Re-read the result and verify it before reporting success.

This prevents the editor from silently modifying an already-corrupt or unsupported save.

## Scope and limitations

Confirmed only for the tested AC8 Windows/Steam campaign saves. Not yet validated for:

- other game versions or patches,
- other platforms,
- `OnlineAccount.sav`,
- replay saves,
- fields other than MRP,
- arbitrary Unreal `GVAS` files.

Do not ship copyrighted game binaries or personal save files as test fixtures. Prefer synthetic byte fixtures or checksum/property test vectors.
