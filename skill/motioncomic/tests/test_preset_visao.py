import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import forma_c_direcao as D


def test_visao_em_presets():
    assert D.preset("acao")["visao"] is True,    "acao deve ter visao=True"
    assert D.preset("epico")["visao"] is True,   "epico deve ter visao=True"
    assert D.preset("suave")["visao"] is False,  "suave deve ter visao=False"
    assert D.preset("dinamico")["visao"] is False, "dinamico deve ter visao=False"


if __name__ == "__main__":
    test_visao_em_presets()
    print("OK")
