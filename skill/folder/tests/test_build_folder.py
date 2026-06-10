import os, sys, json, base64, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from build_folder import build_folder
from referencia import validate_referencia
from png_size import png_size

GREY = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))
TPL = os.path.join(os.path.dirname(__file__), "..", "templates", "editorial-revista")

def fake_generate(prompt, out_path, **kw):
    with open(out_path, "wb") as f: f.write(GREY)
    return out_path

def test_build_produces_all_artifacts(out="/tmp/_build_folder_test"):
    if os.path.exists(out): shutil.rmtree(out)
    ref = build_folder(FICHA, template_dir=TPL, arte="foto", out_dir=out,
                       modo="texto", foto_origem=None, generate_fn=fake_generate)
    base = os.path.join(out, FICHA["id"])
    assert os.path.exists(os.path.join(base, "folder.html"))
    # css href must be rewritten to an ABSOLUTE file:// url, else chromium
    # silently drops the stylesheet and the layout collapses (regression guard).
    html = open(os.path.join(base, "folder.html")).read()
    assert 'href="file:///' in html, "css href not rewritten to absolute file:// url"
    assert 'href="style.css"' not in html, "relative style.css href left in html"
    assert os.path.exists(os.path.join(base, "folder.png"))
    assert png_size(os.path.join(base, "folder.png")) == (1200, 1600)
    assert os.path.exists(os.path.join(base, "assets", "retrato.png"))
    for i in range(1, 6):
        assert os.path.exists(os.path.join(base, "assets", f"foco{i}.png"))
    saved = json.load(open(os.path.join(base, "referencia.json")))
    validate_referencia(saved)
    assert saved == ref

if __name__ == "__main__":
    test_build_produces_all_artifacts(); print("OK")
