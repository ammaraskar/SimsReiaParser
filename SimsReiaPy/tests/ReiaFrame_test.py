from sims_reia.ReiaFrame import read_frames

import pytest
from pathlib import Path
from io import BytesIO

from PIL import Image
from PIL import ImageChops


TEST_DATA_DIRECTORY = Path(__file__).resolve().parent / "test_data"


def test_throws_when_wrong_magic():
    input = BytesIO(b"notfrme")

    with pytest.raises(ValueError) as excinfo:
        read_frames(input, width=128, height=128)

    assert "Unexpected magic in start-of-frame" in str(excinfo.value)


def assert_images_are_same(image_one: Image, image_two: Image):
    diff = ImageChops.difference(image_one, image_two)

    assert diff.getbbox() is None


def test_parses_two_frames_correctly():
    real_frame_one = Image.open(TEST_DATA_DIRECTORY / "frame1.png").convert("RGB")
    real_frame_two = Image.open(TEST_DATA_DIRECTORY / "frame2.png").convert("RGB")

    frame_file = TEST_DATA_DIRECTORY / "first_two_frames.bin"
    with frame_file.open("rb") as f:
        frames = read_frames(f, width=128, height=128)

    assert_images_are_same(frames[0].image, real_frame_one)
    assert_images_are_same(frames[1].image, real_frame_two)
