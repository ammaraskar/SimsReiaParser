from .ReiaFile import ReiaFile
from .ReiaFrame import ReiaFrame

from PIL import Image, ImageChops

import math
import typing


def pack_uint32_le(value: int) -> bytes:
    """Encodes an int as a 32-bit little endian unsigned integer."""
    return value.to_bytes(4, byteorder="little", signed=False)


def write_reia_file(file: ReiaFile, output_stream: typing.BinaryIO):
    assert output_stream.seekable()

    # Write the magic for the RIFF container header.
    output_stream.write(b"RIFF")

    # Length of the generated output, we write a placeholder for now and then
    # seek back here to write the real length.
    output_stream.write(pack_uint32_le(1337))

    output_stream.write(b"Reiahead")
    # Size of the metadata to follow:
    #    4 bytes for unknown field (always set to 1)
    #    4 bytes for width
    #    4 bytes for height
    #    4 bytes for fps numerator
    #    4 bytes for fps denominator
    #  + 4 bytes for number of frames
    #  ------------------------------
    #  = 24
    output_stream.write(pack_uint32_le(24))
    # Unknown field.
    output_stream.write(pack_uint32_le(1))
    # Video width.
    output_stream.write(pack_uint32_le(file.width))
    # Video height.
    output_stream.write(pack_uint32_le(file.height))

    # Calculate the fps numerator and denominator.
    #
    # For compatibility with the game files we choose the same numerator as them
    # for known frame rates.
    fps_numerator = 1_000_000
    if file.frames_per_second == 10:
        fps_numerator = 10
    fps_denominator = int(fps_numerator // file.frames_per_second)
    # Frames per second data.
    output_stream.write(pack_uint32_le(fps_numerator))
    output_stream.write(pack_uint32_le(fps_denominator))
    # Number of frames.
    output_stream.write(pack_uint32_le(file.num_frames))

    # Write out the frames.
    write_reia_frames(file.frames, output_stream)

    # Seek back to the start of the file and write the RIFF container size
    # properly.
    file_size = output_stream.tell()
    output_stream.seek(4)
    # Size of what we wrote minus the magic and the size field itself.
    output_stream.write(pack_uint32_le(file_size - 8))


def write_reia_frames(
    frames: typing.Iterator[ReiaFrame], output_stream: typing.BinaryIO
):
    previous_frame_image = None
    for frame in frames:
        encoded_frame = write_reia_frame(frame.image, previous_frame_image)
        output_stream.write(b"frme")
        output_stream.write(pack_uint32_le(len(encoded_frame)))
        output_stream.write(encoded_frame)
        # Add padding to align frames to nearest 2-byte boundary if needed.
        if len(encoded_frame) % 2 != 0:
            output_stream.write(b"\x00")

        # Make sure they're all the same resolution!
        if previous_frame_image is not None:
            assert frame.image.size == previous_frame_image.size
        previous_frame_image = frame.image


def write_reia_frame(frame, previous_frame) -> bytes:
    output = bytearray()

    width, height = frame.size[0], frame.size[1]

    width_blocks = int(math.ceil(width / 32))
    height_blocks = int(math.ceil(height / 32))

    # Frames are encoded as blocks of 32x32 pixels.
    for i in range(height_blocks):
        for j in range(width_blocks):
            # x and y coordinates where the top-left corner is 0,0
            x, y = (j * 32), (i * 32)

            current_block = crop_32_by_32_block(frame, x, y)
            previous_block = None
            if previous_frame:
                previous_block = crop_32_by_32_block(previous_frame, x, y)

            block = write_reia_block(current_block, previous_block)
            output.extend(block)

    return output


def crop_32_by_32_block(frame: Image, x: int, y: int):
    """Crop out a 32x32 block at (x, y), padding if needed."""
    cropped = frame.crop((x, y, x + 32, y + 32))
    if cropped.size[0] == 32 and cropped.size[1] == 32:
        return cropped
    # Pad to 32-32
    print("Padding because block is ", cropped.size)
    result = Image.new(cropped.mode, (32, 32))
    result.paste(cropped, (0, 0))
    return result


def find_identical_runs(raw_bytes: bytes):
    """Finds consecutive 24-byte sequences in raw_bytes and returns a
    dictionary of `start_idx -> (color, start_idx, end_idx)` for runs of
    identical bytes."""
    identical_runs = {}

    previous_color, run_start_idx = raw_bytes[0:3], 0
    for i in range(3, len(raw_bytes), 3):
        color = raw_bytes[i : i + 3]
        # Just keep going if it's the same as the previous color.
        if color == previous_color:
            continue
        # Indiciates that color did not repeat, since we only made it through
        # one loop iteration.
        if i == (run_start_idx + 3):
            run_start_idx = i
            previous_color = color
            continue
        # Color stopped repeating, put it in the runs.
        identical_runs[run_start_idx] = (previous_color, run_start_idx, i)
        run_start_idx = i
        previous_color = color

    # Make sure after the loop there's not an identical run at the end.
    if i != run_start_idx:
        identical_runs[run_start_idx] = (previous_color, run_start_idx, i + 3)

    return identical_runs


def write_reia_block(block, previous_block) -> bytearray:
    # If this block is exactly identical to the previous, we can skip encoding
    # it.
    if previous_block is not None:
        diff = ImageChops.difference(block, previous_block)
        if diff.getbbox() is None:
            return bytearray(b"\x00")

    output = bytearray(b"\x01")
    # If there is a previous block we need to compute a diff of the pixel values
    # between this and the last one.
    if previous_block is not None:
        block = ImageChops.subtract_modulo(block, previous_block)

    # Iterate over each the bytes and start calculating and writing runs.
    raw_bytes = block.tobytes("raw", "BGR")
    assert len(raw_bytes) == 32 * 32 * 3

    # First run over all the values and detect runs of the same color.
    identical_runs = find_identical_runs(raw_bytes)

    # Just so sanity check.
    pixels_encoded = 0
    # Now that we have the list of runs, we can iterate through the indices and
    # perform RLE encoding.
    i = 0
    unique_colors = []
    while i < len(raw_bytes):
        color = raw_bytes[i : i + 3]
        if i not in identical_runs:
            # Not an identical run, let's add this to the unqiue colors list and
            # we'll put them all in after we get to an identical run.
            unique_colors.append(color)
            i += 3
            continue

        # If we've got a list of unique colors built up, put them in first.
        if len(unique_colors) > 0:
            pixels_encoded += len(unique_colors)
            emit_non_repeated_colors(unique_colors, output)
            unique_colors = []

        identical_color, run_start_idx, run_end_idx = identical_runs[i]
        assert color == identical_color

        num_repeated = (run_end_idx - run_start_idx) // 3
        pixels_encoded += num_repeated
        emit_repeated_color(num_repeated, color, output)

        # Skip to the end index.
        i = run_end_idx
        continue
    # If we've still got unique colors going from the end of the loop, emit
    # them now.
    if len(unique_colors) > 0:
        pixels_encoded += len(unique_colors)
        emit_non_repeated_colors(unique_colors, output)

    assert pixels_encoded == 32 * 32
    return output


def emit_repeated_color(num_repeated, color, output: bytearray):
    # A negative RLE byte n indiciates the next color should be repeated
    # (-n + 1) number of times. Since min(int8) = -128 we can only repeat
    # a color a maximum of 129 times with this scheme.
    #
    # This splits up the repeats into runs of 129.
    for _ in range(num_repeated // 129):
        rle_byte = -(129 - 1)
        rle_byte = rle_byte.to_bytes(1, byteorder="little", signed=True)

        output.extend(rle_byte)
        output.extend(color)

    remainder = num_repeated % 129
    if remainder > 0:
        rle_byte = -(remainder - 1)
        rle_byte = rle_byte.to_bytes(1, byteorder="little", signed=True)

        output.extend(rle_byte)
        output.extend(color)


def emit_non_repeated_colors(unique_colors, output: bytearray):
    # A positive RLE byte n indicates (n + 1) unique values are coming.
    #
    # Since the n is a signed 8-bit int we can't be smaller than
    #   max(int8) = 127
    # so we can only encode 128 repeats at maximum.
    #
    # This loop splits up unique_colors into chunks of 129 if needed and spits
    # them out.
    for i in range(0, len(unique_colors), 128):
        colors_chunk = unique_colors[i : i + 128]

        assert len(colors_chunk) <= 128

        rle_byte = len(colors_chunk) - 1
        rle_byte = rle_byte.to_bytes(1, byteorder="little", signed=True)
        output.extend(rle_byte)
        output.extend(b"".join(colors_chunk))
