import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fill_template import fill

TPL = os.path.join(os.path.dirname(__file__), "..", "templates", "dossie")
FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))
IMAGES = {"retrato": "assets/retrato.png", "focos": [f"assets/foco{i}.png" for i in range(1, 6)]}

def test_dossie_fills_clean():
    html = fill(TPL, FICHA, IMAGES)
    assert "{{" not in html
    assert "IDENI MALDANER" in html and "DOSSIE" in html

if __name__ == "__main__":
    test_dossie_fills_clean(); print("OK")
