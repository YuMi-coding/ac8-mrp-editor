# AC8 MRP Editor

Offline save utility for **ACE COMBAT 8** campaign MRP values.

This project edits a user's own `Campaign.sav` file, updates `CurrentMRP` and `TotalMRP`, recalculates the campaign save checksum, and verifies the result before writing it back.

> Status: early prototype. The save/checksum behavior documented here has been validated against two independently game-generated saves from the tested AC8 Windows/Steam build. Future game updates may change the format.

## Scope

This tool is intended for personal, offline campaign saves only.

It does **not**:

- modify the game executable,
- bypass DRM,
- interact with online services,
- edit `OnlineAccount.sav`,
- ship or depend on game binaries, assets, or bundled save files.

## Save location

On Windows, the campaign save is typically located at:

```text
%LOCALAPPDATA%\BANDAI NAMCO Entertainment\ACE COMBAT 8\Saved\SaveGames\Campaign.sav
```

## MRP semantics

Observed behavior:

- `CurrentMRP`: current spendable balance.
- `TotalMRP`: lifetime MRP acquired.

A test purchase reduced `CurrentMRP` from `161700` to `155700` while `TotalMRP` remained `161700`.

For an `add-mrp` operation, both counters should be increased by the same amount.

## Checksum

The tested campaign save stores a `Checksum` (`UInt32Property`). The checksum is calculated over the `PackedData` payload using reflected CRC-32 with:

```text
poly    = 0xEDB88320
init    = 0xBE6E9142
xorout  = 0xFFFFFFFF
```

Known-good validation observations from two game-generated saves:

```text
CurrentMRP=161700 -> Checksum 0x704393E0
CurrentMRP=155700 -> Checksum 0xC9785199
```

These are reference observations only; no game-generated save files are included in this repository.

## Usage

```bash
python ac8save.py info Campaign.sav
python ac8save.py add-mrp Campaign.sav 10000000
```

The editor writes a backup before modifying the save and verifies the recalculated checksum.

## Safety

- Back up `Campaign.sav` before editing.
- Consider disabling Steam Cloud until the edited save is confirmed working.
- Do not commit personal save files or game binaries to this repository.

## Save format notes

See [`docs/save-format.md`](docs/save-format.md).

## Disclaimer

This is an unofficial community utility and is not affiliated with, endorsed by, or sponsored by Bandai Namco Entertainment.

ACE COMBAT and related names and trademarks are the property of their respective owners.

This repository contains only independently written source code and documentation. It does not distribute game code, executables, assets, or copyrighted save data.
