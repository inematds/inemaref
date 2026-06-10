import os, sys, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
from overlay import render_panel
from build_motion import _spoken
from png_size import png_size

GREY = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

def test_spoken_joins_narracao_and_fala():
    assert _spoken({"narracao": "Texto.", "fala": {"quem": "Lia", "texto": "Oi."}}) == "Texto. Oi."
    assert _spoken({"narracao": "So narra."}) == "So narra."
    assert _spoken({"fala": {"quem": "Lia", "texto": "So fala."}}) == "So fala."

def test_overlay_renders_16x9(tmp="/tmp/_motion_overlay_test"):
    os.makedirs(tmp, exist_ok=True)
    bg = os.path.join(tmp, "bg.png")
    with open(bg, "wb") as f:
        f.write(GREY)
    out = os.path.join(tmp, "frame.png")
    render_panel(bg, out, fala="Posso sentar?", sfx="POW")
    assert os.path.exists(out)
    assert png_size(out) == (1280, 720), png_size(out)

if __name__ == "__main__":
    test_spoken_joins_narracao_and_fala()
    test_overlay_renders_16x9()
    print("OK")
