# skill/folder/tests/test_render.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from render import render_html_to_png
from png_size import png_size

def test_renders_fixed_size(tmpdir="/tmp/_render_test"):
    os.makedirs(tmpdir, exist_ok=True)
    html = os.path.join(tmpdir, "p.html")
    png = os.path.join(tmpdir, "p.png")
    with open(html, "w") as f:
        f.write("<html><body style='margin:0;background:#c00'></body></html>")
    render_html_to_png(html, png, 400, 300)
    assert os.path.exists(png), "png not produced"
    assert png_size(png) == (400, 300), f"got {png_size(png)}"

if __name__ == "__main__":
    test_renders_fixed_size()
    print("OK")
