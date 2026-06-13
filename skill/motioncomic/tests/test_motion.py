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

def test_gen_image_usa_generate_fn_injetado(tmp="/tmp/_motion_gen"):
    """Seam do QC na Forma A: _gen_image usa o generate_fn injetado (em vez do
    imgclient) e monta o prompt completo (quem + cena + no text)."""
    import build_motion as BM
    os.makedirs(tmp, exist_ok=True)
    calls = []
    def fake(full, out, **kw):
        calls.append((full, kw)); open(out, "w").close()
    BM._gen_image("uma cena", "heroi", os.path.join(tmp, "x.png"), generate_fn=fake)
    assert calls, "generate_fn injetado nao foi chamado"
    full, kw = calls[0]
    assert "heroi" in full and "uma cena" in full and "no text" in full
    assert kw["width"] == BM.GEN_W and kw["height"] == BM.GEN_H and kw.get("negative_prompt")


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
    test_gen_image_usa_generate_fn_injetado()
    test_overlay_renders_16x9()
    print("OK")
