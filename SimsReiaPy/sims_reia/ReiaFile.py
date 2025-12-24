from . import _read_uint32_le
from .ReiaFrame import ReiaFrame, create_frame_reader
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
        An iterator over the individual frames of the video. Note that this
        can only be iterated over once, so save any frames you need or turn
        this into a list.
    """

    width: int
    height: int
    frames_per_second: float
    num_frames: int
    frames: typing.Iterator[ReiaFrame]

    def __init__(self, width, height, frames_per_second, num_frames, frames) -> None:
        self.width = width
        self.height = height

        self.frames_per_second = frames_per_second
        self.num_frames = num_frames
        self.frames = frames


def read_from_file(stream: typing.BinaryIO) -> ReiaFile:
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

    # The next integer is always 1.
    always_1 = _read_uint32_le(stream)
    if always_1 != 1:
        raise ValueError(f"Unexpected integer, expected 1, got {always_1}")

    width = _read_uint32_le(stream)
    height = _read_uint32_le(stream)

    # Frames per second.
    frames_per_second_numerator = _read_uint32_le(stream)
    frames_per_second_denominator = _read_uint32_le(stream)
    frames_per_second = (
        float(frames_per_second_numerator) / frames_per_second_denominator
    )

    # Read the expected number of frames.
    num_frames = _read_uint32_le(stream)
    frames = create_frame_reader(stream, width, height)

    return ReiaFile(width, height, frames_per_second, num_frames, frames)
