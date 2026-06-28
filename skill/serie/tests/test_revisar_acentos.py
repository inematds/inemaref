# skill/serie/tests/test_revisar_acentos.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from revisar_acentos import corrigir, revisar_episodio


# ── corrigir ────────────────────────────────────────────────────────────────

def test_corrige_palavras_seguras():
    out, trocas, susp = corrigir("o verao chegou e o ceu virou agua de fumaca")
    assert "verão" in out and "céu" in out and "água" in out and "fumaça" in out
    assert ("verao", "verão") in trocas
    assert susp == []


def test_preserva_caixa():
    assert corrigir("nao")[0] == "não"
    assert corrigir("Nao")[0] == "Não"
    assert corrigir("NAO")[0] == "NÃO"
    assert corrigir("VOCE")[0] == "VOCÊ"


def test_idempotente_texto_ja_correto():
    txt = "O verão chegou e o céu virou água."
    out, trocas, susp = corrigir(txt)
    assert out == txt
    assert trocas == []


def test_nao_toca_funcao_palavra_frequente():
    # 'e'/'de'/'da'/'para'/'por' NAO entram (evita ruido); ficam intactos.
    out, trocas, susp = corrigir("ele e o pai de casa para todos por aqui")
    assert out == "ele e o pai de casa para todos por aqui"
    assert trocas == []


def test_ambiguo_so_avisa_nao_altera():
    out, trocas, susp = corrigir("esta casa esta quente")
    assert out == "esta casa esta quente"     # nao alterou
    assert "esta" in susp                       # mas sinalizou
    assert trocas == []


def test_vulcao_e_montanha():
    out, _, _ = corrigir("o vulcao da montanha soltou fumaca")
    assert out == "o vulcão da montanha soltou fumaça"


# ── revisar_episodio ────────────────────────────────────────────────────────

def _ep():
    return {
        "titulo": "A Agua Turva",
        "abertura": "O verao chegou e o ceu ficou cor de cobre.",
        "paginas": [{
            "n": 1, "titulo": "O ceu de cobre", "chamada": "Naquele verao o calor mudou.",
            "paineis": [
                {"prompt": "amplo plano do sitio com vulcao ao fundo",   # NAO pode mudar
                 "quem": "", "usa": ["A Montanha de Fogo"], "sfx": "TUM...",
                 "narracao": "O calor nao foi embora e a agua ficou turva.",
                 "fala": {"quem": "Teo", "texto": "A montanha ta soltando fogo!"}},
            ],
        }],
    }


def test_revisar_episodio_corrige_narrados():
    ep = _ep()
    rel = revisar_episodio(ep)
    assert ep["titulo"] == "A Água Turva"
    assert ep["abertura"].startswith("O verão chegou e o céu")
    assert ep["paginas"][0]["titulo"] == "O céu de cobre"
    assert ep["paginas"][0]["chamada"] == "Naquele verão o calor mudou."
    p = ep["paginas"][0]["paineis"][0]
    assert p["narracao"] == "O calor não foi embora e a água ficou turva."
    assert p["fala"]["texto"] == "A montanha tá soltando fogo!"
    assert len(rel["trocas"]) >= 6


def test_revisar_episodio_nao_toca_prompt_quem_usa_sfx():
    ep = _ep()
    revisar_episodio(ep)
    p = ep["paginas"][0]["paineis"][0]
    assert p["prompt"] == "amplo plano do sitio com vulcao ao fundo"   # sitio/vulcao intactos
    assert p["quem"] == "" and p["usa"] == ["A Montanha de Fogo"] and p["sfx"] == "TUM..."
    assert p["fala"]["quem"] == "Teo"                                  # so o texto muda


if __name__ == "__main__":
    test_corrige_palavras_seguras()
    test_preserva_caixa()
    test_idempotente_texto_ja_correto()
    test_nao_toca_funcao_palavra_frequente()
    test_ambiguo_so_avisa_nao_altera()
    test_vulcao_e_montanha()
    test_revisar_episodio_corrige_narrados()
    test_revisar_episodio_nao_toca_prompt_quem_usa_sfx()
    print("OK")
