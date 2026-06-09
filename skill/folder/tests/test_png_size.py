# skill/folder/tests/test_png_size.py
import os, sys, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from png_size import png_size

# 2x1 red PNG, base64
PNG_2x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAEklEQVR4nGP8z8Dwn4EIwDiqEAARWAIBLb0nawAAAABJRU5ErkJggg=="
)

def test_reads_dimensions(tmp="/tmp/_pngsize_test.png"):
    with open(tmp, "wb") as f:
        f.write(PNG_2x1)
    assert png_size(tmp) == (2, 1)

if __name__ == "__main__":
    test_reads_dimensions()
    print("OK")
