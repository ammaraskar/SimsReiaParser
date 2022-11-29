from . import _read_uint32_le
from PIL import Image, ImageChops
import typing


class ReiaFrame:
    """A single frame of video."""

    image: Image

    def __init__(self, image) -> None:
        self.image = image


def read_single_pixel(stream: typing.BinaryIO) -> bytes:
    # We reverse here with `::-1` because the RGB value is stored as little endian.
    pixel_value = stream.read(3)[::-1]
    return pixel_value


def read_32_by_32_pixel_block(stream: typing.BinaryIO) -> Image:
    num_pixels = 32 * 32
    # 3 bytes for the RGB channels per pixel.
    image_data = bytearray(num_pixels * 3)

    i = 0
    while i < num_pixels:
        rle_byte = stream.read(1)
        assert rle_byte != b""

        rle_value = int.from_bytes(rle_byte, byteorder="big", signed=True)

        if rle_value < 0:
            # Negative RLE value means we are going to be repeating the next
            # color -n times.
            num_repeats = -rle_value
            pixel = read_single_pixel(stream)
            for _ in range(num_repeats + 1):
                image_data[(i * 3) : (i * 3) + 3] = pixel
                i += 1
        else:
            # Positive RLE value means we are going to be getting n unique
            # pixels.
            num_unique_pixels = rle_value
            for _ in range(num_unique_pixels + 1):
                pixel = read_single_pixel(stream)
                image_data[(i * 3) : (i * 3) + 3] = pixel
                i += 1

    return Image.frombytes("RGB", (32, 32), bytes(image_data))


def read_single_frame(
    stream: typing.BinaryIO, width: int, height: int, previous_frame: Image
) -> Image:
    image = Image.new("RGB", (width, height))

    # Frames are encoded as blocks of 32x32 pixels.
    for i in range(width // 32):
        for j in range(height // 32):
            # x and y coordinates where the top-left corner is 0,0
            x, y = (j * 32), (i * 32)
            # First bit tells us if we should expect a new 32x32 pixel block or re-use
            # the one from the previous frame.
            if stream.read(1) != b"\x00":
                block = read_32_by_32_pixel_block(stream)
                if previous_frame is not None:
                    previous_block = previous_frame.image.crop((x, y, x + 32, y + 32))
                    # Compute `(x+y) & 0xFF` for each pixel in this block and
                    # the previous block. (The blocks encode the diff from the
                    # previous frame to the current frame).
                    block = ImageChops.add_modulo(block, previous_block)
                image.paste(block, (x, y))
                continue

            # Okay, try to re-use the previous block :)
            if previous_frame is None:
                raise ValueError("32x32 block not sent but no previous frame")
            last_block = previous_frame.image.crop((x, y, x + 32, y + 32))
            image.paste(last_block, (x, y))

    return ReiaFrame(image)


def create_frame_reader(
    stream: typing.BinaryIO, width: int, height: int
) -> typing.Iterator[ReiaFrame]:
    """Returns a generator that will return Reia frames from the given stream
    at a particular width and height."""
    previous_frame = None

    # Keep reading frames until the end of the file.
    frame_magic = stream.read(4)
    while frame_magic != b"":
        # Make sure this is a valid start-of-frame.
        if frame_magic != b"frme":
            raise ValueError(
                f"Unexpected magic in start-of-frame, expected 'frme' got {frame_magic}"
            )

        frame_size = _read_uint32_le(stream)
        frame = read_single_frame(stream, width, height, previous_frame)
        previous_frame = frame
        yield frame

        # Frames get padded to be aligned on 2-byte boundaries, so consume the
        # padding (if any).
        padding = frame_size % 2
        stream.read(padding)

        # Read the next set of magic.
        frame_magic = stream.read(4)


def read_frames(stream: typing.BinaryIO, width: int, height: int) -> typing.List[ReiaFrame]:
    """A convenience non-generated version of create_frame_reader that holds all
    frames in memory.
    """
    return list(create_frame_reader(stream, width, height))
