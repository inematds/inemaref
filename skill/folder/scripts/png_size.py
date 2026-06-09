# skill/folder/scripts/png_size.py
import struct

def png_size(path):
    """Return (width, height) of a PNG by reading its IHDR chunk."""
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    width, height = struct.unpack(">II", head[16:24])
    return (width, height)
