import sims_reia

import pytest
from io import BytesIO


def _pack_int(value: int) -> bytes:
    """Helper to encode int as uint32 little endian"""
    return value.to_bytes(4, byteorder="little", signed=False)


def test_throws_when_wrong_magic():
    input = BytesIO(b"hello world")

    with pytest.raises(ValueError) as excinfo:
        sims_reia.read_from_file(input)

    assert "Incorrect magic at start of file" in str(excinfo.value)


def test_throws_when_reia_header_has_wrong_magic():
    input = BytesIO(b"RIFF" + _pack_int(1) + b"NotReiahead")

    with pytest.raises(ValueError) as excinfo:
        sims_reia.read_from_file(input)

    assert "Incorrect magic inside RIFF container" in str(excinfo.value)


def test_throws_if_metadata_size_not_24():
    input = BytesIO(b"RIFF" + _pack_int(1) + b"Reiahead" + _pack_int(23))

    with pytest.raises(ValueError) as excinfo:
        sims_reia.read_from_file(input)

    assert "Reiahead metadata size not 24, got 23" in str(excinfo.value)


def test_metadata_is_correct_on_known_file():
    known_file = (
        b"RIFF"
        + b"\xf2\xac]\x00"
        + b"Reiahead\x18\x00\x00\x00\x01\x00\x00\x00\x80\x00\x00\x00\x80\x00\x00\x00"
        + b"\n\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00"
    )
    input = BytesIO(known_file)

    reia_file = sims_reia.read_from_file(input)
    assert reia_file.frames_per_second == 10.0
    assert reia_file.width == 128
    assert reia_file.height == 128
