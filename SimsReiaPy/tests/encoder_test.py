from sims_reia import ReiaFile, ReiaFrame, write_reia_file
from sims_reia import encoder
from sims_reia.ReiaFrame import read_frames
from .ReiaFrame_test import TEST_DATA_DIRECTORY

from io import BytesIO

from PIL import Image


def test_find_identical_runs_works_when_no_runs():
    input = b"\x00\x00\x00" + b"\x00\x00\x01"
    assert encoder.find_identical_runs(input) == {}


def test_find_identical_runs_finds_runs_at_start_of_data():
    input = b"\x00\x00\x00" + b"\x00\x00\x00" + b"\x00\x00\x01"
    assert encoder.find_identical_runs(input) == {0: (b"\x00\x00\x00", 0, 6)}


def test_find_identical_runs_finds_runs_at_end_of_data():
    input = b"\x00\x00\x01" + b"\x00\x00\x00" + b"\x00\x00\x00"
    assert encoder.find_identical_runs(input) == {3: (b"\x00\x00\x00", 3, 9)}


def test_find_identical_runs_handles_multiples_runs():
    input = b"\x00\x00\x01" + b"\x00\x00\x01" + b"\x00\x00\x00" + b"\x00\x00\x00"
    assert encoder.find_identical_runs(input) == {
        0: (b"\x00\x00\x01", 0, 6),
        6: (b"\x00\x00\x00", 6, 12),
    }


def test_encodes_to_expected_file():
    real_frame_one = Image.open(TEST_DATA_DIRECTORY / "frame1.png").convert("RGB")
    real_frame_two = Image.open(TEST_DATA_DIRECTORY / "frame2.png").convert("RGB")

    test_file = ReiaFile()
    test_file.width = 128
    test_file.height = 128
    test_file.frames_per_second = 10
    test_file.frames = [ReiaFrame(real_frame_one), ReiaFrame(real_frame_two)]

    output = BytesIO()
    write_reia_file(test_file, output)

    # Try to round-trip the data.
    print(output.getvalue()[:50])
    output.seek(0x2C)
    frames = read_frames(output, width=128, height=128)