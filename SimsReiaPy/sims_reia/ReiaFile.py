from . import _read_uint32_le
from .ReiaFrame import ReiaFrame, read_frames
import typing


class ReiaFile:
    """A .reia video file.
    Note that all frames are held uncompressed in memory.

    Attributes
    ------------

    width
        The horizontal resolution of the video in pixels.

    height
        The vertical resolution of the video in pixels.

    frames_per_second
        The framerate of the video.

    frames
        The individual frames of the video.
    """

    width: int
    height: int
    frames_per_second: float
    frames: typing.List[ReiaFrame]


def read_from_file(stream: typing.BinaryIO) -> ReiaFile:
    reia_file = ReiaFile()

    # Assert that the file starts with the proper magic bytes.
    riff_file_magic = stream.read(4)
    if riff_file_magic != b"RIFF":
        raise ValueError(
            f"Incorrect magic at start of file, expected 'RIFF', got {riff_file_magic}"
        )

    # We can check that matches up, but unused for now.
    file_size = _read_uint32_le(stream)

    reia_header_magic = stream.read(8)
    if reia_header_magic != b"Reiahead":
        raise ValueError(
            f"Incorrect magic inside RIFF container, expected 'Reiahead', got {reia_header_magic}"
        )

    size_of_metadata = _read_uint32_le(stream)
    if size_of_metadata != 24:
        raise ValueError(f"Reiahead metadata size not 24, got {size_of_metadata}")

    # This value is checked to be always 1 in the real code. Just assert here.
    assert _read_uint32_le(stream) == 1

    reia_file.width = _read_uint32_le(stream)
    reia_file.height = _read_uint32_le(stream)
    # Assert that width and height are divisible by 32.
    assert (reia_file.width % 32) == 0
    assert (reia_file.height % 32) == 0

    # Frames per second.
    frames_per_second_numerator = _read_uint32_le(stream)
    frames_per_second_denominator = _read_uint32_le(stream)
    reia_file.frames_per_second = (
        float(frames_per_second_numerator) / frames_per_second_denominator
    )

    # Read the expected number of frames.
    num_frames = _read_uint32_le(stream)
    reia_file.frames = read_frames(stream, reia_file.width, reia_file.height)
    assert num_frames == len(reia_file.frames)

    return reia_file
