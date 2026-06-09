import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fill_pagina import fill

GRADE = os.path.join(os.path.dirname(__file__), "..", "templates", "grade-uniforme")
DINAM = os.path.join(os.path.dirname(__file__), "..", "templates", "manga-dinamico")
ROT = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "roteiro-visionario.json")))

def test_fill_grade_clean():
    html = fill(GRADE, ROT)
    assert "{{" not in html
    assert "O VISIONARIO" in html
    assert html.count('class="panel"') == 6
    assert 'src="assets/panel6.png"' in html
    assert "CLICK!" in html                       # sfx painel 1
    assert "Vai um picole?!" in html              # fala painel 2
    assert "ate montou circo" in html             # narracao painel 2

def test_fill_dinamico_clean():
    html = fill(DINAM, ROT)
    assert "{{" not in html and html.count('class="panel"') == 6

def test_requires_six_paineis():
    bad = dict(ROT); bad["paineis"] = ROT["paineis"][:4]
    try:
        fill(GRADE, bad); assert False, "should have raised"
    except ValueError:
        pass

def test_optional_fields_omitted():
    one = {"titulo": "X", "paineis": [{"prompt": "a"} for _ in range(6)]}
    html = fill(GRADE, one)
    assert "{{" not in html
    assert "narracao" not in html and "fala" not in html and "sfx" not in html

if __name__ == "__main__":
    test_fill_grade_clean(); test_fill_dinamico_clean()
    test_requires_six_paineis(); test_optional_fields_omitted()
    print("OK")
