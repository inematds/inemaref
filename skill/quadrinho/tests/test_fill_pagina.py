import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fill_pagina import fill, _assign_positions, _font_size

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

def test_narracao_sfx_em_metades_opostas():
    # narracao e larga e o sfx e grande: na mesma metade vertical eles colidem
    pos = _assign_positions({"narracao", "sfx"})
    assert pos["narracao"].split("-")[0] != pos["sfx"].split("-")[0]
    # mesmo com rosto forcando realocacao, a regra vale
    pos = _assign_positions({"narracao", "fala", "sfx"}, occupied={"bottom-left"})
    assert pos["narracao"].split("-")[0] != pos["sfx"].split("-")[0]
    assert len(set(pos.values())) == 3  # quadrantes todos distintos

def test_sfx_sozinho_fica_no_topo():
    assert _assign_positions({"sfx"})["sfx"] == "top-right"

def test_fonte_encolhe_com_texto_longo():
    assert _font_size("narracao", "x" * 50) == 17
    assert _font_size("narracao", "x" * 160) == 13
    assert _font_size("sfx", "BOOM") == 56
    assert _font_size("sfx", "CLAP CLAP CLAP") == 30

def test_texto_longo_demais_levanta_erro():
    bad = {"titulo": "X", "paineis": [{"prompt": "a"} for _ in range(6)]}
    bad["paineis"][2]["narracao"] = "x" * 300
    try:
        fill(GRADE, bad); assert False, "should have raised"
    except ValueError as e:
        assert "painel 3" in str(e) and "narracao" in str(e)

def test_inline_styles_no_html():
    html = fill(DINAM, ROT)
    # painel 1 do fixture tem narracao + sfx: ambos saem com estilo inline
    assert 'class="narracao" style="top:0' in html
    assert 'class="sfx" style="bottom:0' in html

if __name__ == "__main__":
    test_fill_grade_clean(); test_fill_dinamico_clean()
    test_requires_six_paineis(); test_optional_fields_omitted()
    test_narracao_sfx_em_metades_opostas(); test_sfx_sozinho_fica_no_topo()
    test_fonte_encolhe_com_texto_longo(); test_texto_longo_demais_levanta_erro()
    test_inline_styles_no_html()
    print("OK")
