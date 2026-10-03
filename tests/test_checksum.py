from ac8save import crc32_ac8


def test_crc_empty_payload():
    # Deterministic regression vector for the AC8 CRC parameters.
    assert crc32_ac8(b"") == 0x41916EBD


def test_crc_small_payload():
    assert crc32_ac8(b"ACE COMBAT 8") == 0x1B87EAF3


def test_crc_binary_payload():
    assert crc32_ac8(bytes(range(32))) == 0x0E00558B
