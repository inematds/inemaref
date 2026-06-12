import os, sys, json, base64, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
from build_pagina import build_pagina
from png_size import png_size

GREY = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
ROT = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "roteiro-visionario.json")))
DINAM = os.path.join(os.path.dirname(__file__), "..", "templates", "manga-dinamico")

def fake_generate(prompt, out_path, **kw):
    with open(out_path, "wb") as f: f.write(GREY)
    return out_path

def test_moldura_dark_injects_root(out="/tmp/_moldura_dark"):
    if os.path.exists(out): shutil.rmtree(out)
    build_pagina(ROT, DINAM, out_dir=out, generate_fn=fake_generate,
                 moldura="dark", kicker="SERIE X", accent="#e2a23b")
    html = open(os.path.join(out, ROT["id"], "pagina.html")).read()
    assert "--gutter:#1b1b1b" in html.replace(" ", "")
    assert "--accent:#e2a23b" in html.replace(" ", "")
    assert "SERIE X" in html

def test_moldura_white_injects_root(out="/tmp/_moldura_white"):
    if os.path.exists(out): shutil.rmtree(out)
    build_pagina(ROT, DINAM, out_dir=out, generate_fn=fake_generate, moldura="white")
    html = open(os.path.join(out, ROT["id"], "pagina.html")).read()
    assert "--gutter:#ffffff" in html.replace(" ", "")

def test_emits_textless_png(out="/tmp/_textless"):
    if os.path.exists(out): shutil.rmtree(out)
    png = build_pagina(ROT, DINAM, out_dir=out, generate_fn=fake_generate)
    base = os.path.dirname(png)
    tl_png = os.path.join(base, "pagina-textless.png")
    tl_html = os.path.join(base, "pagina-textless.html")
    assert os.path.exists(tl_png) and png_size(tl_png) == (1200, 1600)
    h = open(tl_html).read().replace(" ", "")
    assert ".narracao,.fala,.sfx{display:none" in h

if __name__ == "__main__":
    test_moldura_dark_injects_root()
    test_moldura_white_injects_root()
    test_emits_textless_png()
    print("OK moldura")
