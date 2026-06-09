import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fill_template import fill

TPL = os.path.join(os.path.dirname(__file__), "..", "templates", "editorial-revista")
FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))
IMAGES = {"retrato": "assets/retrato.png",
          "focos": [f"assets/foco{i}.png" for i in range(1, 6)]}

def test_fill_replaces_all_placeholders():
    html = fill(TPL, FICHA, IMAGES)
    assert "{{" not in html, "unreplaced placeholder remains"
    assert "IDENI MALDANER" in html
    assert "assets/retrato.png" in html
    assert "assets/foco5.png" in html
    assert "SETUP DE CONFIANCA" in html
    assert "Coragem radical" in html
    assert "Corajosa sob pressao." in html

def test_fill_rejects_wrong_foco_count():
    bad = dict(FICHA); bad["focos"] = FICHA["focos"][:3]
    try:
        fill(TPL, bad, IMAGES); assert False, "should have raised"
    except ValueError:
        pass

if __name__ == "__main__":
    test_fill_replaces_all_placeholders(); test_fill_rejects_wrong_foco_count(); print("OK")
