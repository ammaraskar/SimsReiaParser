# SimsReiaParser
Libraries to parse and (maybe) encode .reia file for sims2

https://user-images.githubusercontent.com/773529/204124123-9a72bdbb-1de3-4cf7-a1da-d0724fc9d3bc.mp4

## Format Details

`.reia` files are how Sims2 stores the videos for its neighborhood previews in
its main menu. They seem to be a relatively custom format, this is an overview
on how it encodes video data:

### Header

`.reia` files first have a header with metadata, the fields are:


| Offsets       | Type   | Description (values in hex)                                   |
|---------------|--------|---------------------------------------------------------------|
| `0x00 - 0x03` | Magic  | `52 49 46 46` "RIFF"                                          |
| `0x04 - 0x07` | uint32 | Size of the "chunk" which is the rest of the file             |
| `0x08 - 0x0f` | Magic  | `52 65 69 61 68 65 61 64` "Reiahead"                          |
| `0x10 - 0x13` | uint32 | `18` Size of the metadata to follow (always 24 in practice)   |
| `0x14 - 0x17` | uint32 | `01` Unknown, always 1                                        |
| `0x18 - 0x1b` | uint32 | Horizontal resolution in pixels                               |
| `0x1c - 0x1f` | uint32 | Vertical resolution in pixels                                 |
| `0x20 - 0x23` | uint32 | Frames per second numerator (see below)                       |
| `0x24 - 0x27` | uint32 | FPS denominator. FPS given by `fps_numerator/fps_denominator` |
| `0x28 - 0x2b` | uint32 | Number of frames in the file                                  |
| `...`         | frames | See below                                                     |

### Frames

After the header, there are a sequence of frames. Each frame is 

| Offsets       | Type       | Description (values in hex)      |
|---------------|------------|----------------------------------|
| `0x00 - 0x03` | Magic      | `66 72 6d 65` "frme"             |
| `0x04 - 0x07` | uint32     | Size of the frame data to follow |
| `...`         | Frame Data | See below                        |

Note that the frame data is padded to be 2-byte aligned. So if the frame size
was `3`, there will be `4` bytes of data **instead of 3** before the next
`frme` magic bytes.

### Frame Data - Run Length Encoding

The format uses some interesting tricks for compression: run-length encoding,
encoding differences in pixel values between frames and reusing blocks of pixels
that stay the same.

Each pixel has a standard 24-bit color depth storing 8-bits for the RGB channels
in little endian.

Images are stored in blocks of `32x32` pixels. So a reia file with a resolution
of `128x128` is constructed of `4x4 = 16` blocks. Each block is parsed as
follows:

* A single byte is read. `0` indicates this `32x32` block should be reused from
  the previous frame. Any other value means the block data is to follow.

* A byte is read and treated as a signed 8-bit integer `n`:
    - If the value is negative, then a single pixel value should be read and
      repeated `(-n) + 1` times.
    - If the value is positive, then `n + 1` unique pixel values should be read.

* The pixel values retrieved are *relative* to the previous frame unless it is
  the first frame of the file. So a change from a red value of `200` to `205` is
  encoded as `5`. A change from `255` to `0` is encoded as `1`.
  
  In order to get the actual pixel value you must use `(previous + current) & 0xFF`.
