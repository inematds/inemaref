import os, sys, json, base64, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
from build_pagina import build_pagina
from png_size import png_size

GREY = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
ROT = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "roteiro-visionario.json")))
GRADE = os.path.join(os.path.dirname(__file__), "..", "templates", "grade-uniforme")

def fake_generate(prompt, out_path, **kw):
    with open(out_path, "wb") as f: f.write(GREY)
    return out_path

def test_build_produces_page(out="/tmp/_build_pagina_test"):
    if os.path.exists(out): shutil.rmtree(out)
    png = build_pagina(ROT, template_dir=GRADE, out_dir=out, generate_fn=fake_generate)
    base = os.path.join(out, ROT["id"])
    assert os.path.exists(os.path.join(base, "pagina.html"))
    assert os.path.exists(png) and png_size(png) == (1200, 1600)
    for i in range(1, 7):
        assert os.path.exists(os.path.join(base, "assets", f"panel{i}.png"))
    html = open(os.path.join(base, "pagina.html")).read()
    assert 'href="file:///' in html and 'href="style.css"' not in html
    saved = json.load(open(os.path.join(base, "roteiro.json")))
    assert saved["id"] == ROT["id"]

if __name__ == "__main__":
    test_build_produces_page(); print("OK")
