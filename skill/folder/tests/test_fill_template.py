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

def test_user_text_with_braces_is_not_a_false_positive():
    # a legenda containing a literal "{{" must NOT trip the leftover-placeholder guard
    ficha = dict(FICHA)
    ficha["focos"] = [dict(f) for f in FICHA["focos"]]
    ficha["focos"][0] = {"legenda": "ANTES {{ DEPOIS"}
    html = fill(TPL, ficha, IMAGES)
    assert "ANTES {{ DEPOIS" in html  # preserved verbatim, no exception

def test_fill_raises_when_template_slot_missing_value():
    # the guard still catches a real unfilled template placeholder
    tmpdir = "/tmp/_fill_missing_tpl"
    os.makedirs(tmpdir, exist_ok=True)
    with open(os.path.join(tmpdir, "template.html"), "w") as f:
        f.write("<p>{{nome}}</p><p>{{nao_existe}}</p>")
    try:
        fill(tmpdir, FICHA, IMAGES); assert False, "should have raised"
    except ValueError as e:
        assert "nao_existe" in str(e)

if __name__ == "__main__":
    test_fill_replaces_all_placeholders(); test_fill_rejects_wrong_foco_count()
    test_user_text_with_braces_is_not_a_false_positive()
    test_fill_raises_when_template_slot_missing_value()
    print("OK")
