def _read_uint32_le(stream) -> int:
    """Read a 32-bit little endian unsigned integer."""
    return int.from_bytes(stream.read(4), byteorder="little", signed=False)


from .ReiaFile import ReiaFile, read_from_file
from .ReiaFrame import ReiaFrame
from .encoder import write_reia_file
