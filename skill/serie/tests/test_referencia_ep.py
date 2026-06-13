import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
import referencia_ep as R

BIBLIA = {
    "protagonista": {"id": "lia", "nome": "Lia", "aparencia": "jovem 20 anos, cabelo escuro ondulado"},
    "elenco": [{"nome": "Teo", "aparencia": "jovem 22 anos, calmo"}],
    "elementos": [{"nome": "Piramide", "aparencia": "piramide de pedra clara"}],
}


def _ep(**kw):
    base = {"n": 1, "titulo": "T", "paginas": [{"n": 1, "paineis": [
        {"prompt": "anda pela mata", "quem": "Lia"},
        {"prompt": "olha a piramide", "usa": ["Piramide"]},
        {"prompt": "conversa", "quem": "Teo"},
    ]}]}
    base.update(kw)
    return base


def test_resolver_sem_variacao_eh_canon():
    refs = R.resolver_referencias(BIBLIA, _ep())
    assert refs["protagonista"] == "jovem 20 anos, cabelo escuro ondulado"
    assert refs["elenco"]["Teo"] == "jovem 22 anos, calmo"
    assert refs["cenario_padrao"] == ""


def test_resolver_aplica_delta_preservando_canon():
    ep = _ep(variacoes={"lia": "vestindo uniforme escolar azul-marinho",
                        "piramide": "parcialmente submersa"},
             cenario_padrao="riacho na mata, luz dourada")
    refs = R.resolver_referencias(BIBLIA, ep)
    assert refs["protagonista"].startswith("jovem 20 anos")            # canon preservado
    assert refs["protagonista"].endswith("uniforme escolar azul-marinho")  # + delta
    assert refs["elementos"]["Piramide"].endswith("parcialmente submersa")
    assert refs["cenario_padrao"] == "riacho na mata, luz dourada"


def test_aplicar_dobra_cenario_e_resolve_quem_sem_mutar_original():
    ep = _ep(variacoes={"lia": "de uniforme"}, cenario_padrao="no riacho")
    out = R.aplicar(ep, BIBLIA)
    # nao muta o ep de entrada (idempotente em re-render)
    assert ep["paginas"][0]["paineis"][0]["quem"] == "Lia"
    assert ep["paginas"][0]["paineis"][0]["prompt"] == "anda pela mata"
    # personagem efetivo
    assert out["personagem"].endswith("de uniforme")
    # cenario dobrado no fim de TODO prompt (riacho != praia)
    for p in out["paginas"][0]["paineis"]:
        assert p["prompt"].endswith("no riacho")
    # `quem` que casa um nome vira a aparencia efetiva
    assert out["paginas"][0]["paineis"][0]["quem"].endswith("de uniforme")   # Lia
    assert out["paginas"][0]["paineis"][2]["quem"] == "jovem 22 anos, calmo"  # Teo
    # elementos efetivos como lista + bloco rastreavel
    assert out["elementos"][0]["nome"] == "Piramide"
    assert out["referencias_efetivas"]["cenario_padrao"] == "no riacho"


if __name__ == "__main__":
    test_resolver_sem_variacao_eh_canon()
    test_resolver_aplica_delta_preservando_canon()
    test_aplicar_dobra_cenario_e_resolve_quem_sem_mutar_original()
    print("OK referencia_ep")
