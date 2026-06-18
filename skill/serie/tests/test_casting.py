"""TDD para casting.py — gerar_fichas e _prompt_ficha."""
import os
import sys
import json
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import casting

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

BIBLIA = {
    "elenco": [
        {"nome": "Aurora", "aparencia": "girl 10yo brown hair green eyes"},
        {"nome": "Elisa",  "aparencia": "woman 40yo dark hair brown eyes"},
    ],
    "elementos": [
        {"nome": "Arvore da Praça", "aparencia": "old oak tree wide trunk"},
        {"nome": "Caderno Amarelo", "aparencia": "yellow spiral notebook worn"},
    ],
}

ARTE_POS = "watercolor illustration, soft lines"
TMP = "/tmp/_casting_test"


def _reset():
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP, exist_ok=True)


# ---------------------------------------------------------------------------
# helper: mock generate_fn
# ---------------------------------------------------------------------------

def _make_mock():
    calls = []

    def mock_fn(prompt, out_path, width=1024, height=1024):
        calls.append({"prompt": prompt, "out_path": out_path,
                      "width": width, "height": height})
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "w").write("x")

    return mock_fn, calls


# ---------------------------------------------------------------------------
# testes
# ---------------------------------------------------------------------------

def test_prompt_ficha():
    p = casting._prompt_ficha("girl 10yo brown hair", "watercolor, soft lines")
    assert "girl 10yo brown hair" in p
    assert "watercolor, soft lines" in p
    assert "single subject isolated" in p
    assert "no text" in p


def test_gerar_fichas_chama_mock_e_retorna_dict():
    _reset()
    mock_fn, calls = _make_mock()

    ancoras = casting.gerar_fichas(BIBLIA, TMP, ARTE_POS, mock_fn)

    # 4 entidades → 4 chamadas ao mock
    assert len(calls) == 4, f"esperado 4 chamadas, got {len(calls)}"

    # chaves lowercase
    assert "aurora" in ancoras
    assert "elisa" in ancoras
    assert "arvore da praça" in ancoras  # nome.lower(), não slug
    assert "caderno amarelo" in ancoras

    # arquivos existem
    for path in ancoras.values():
        assert os.path.exists(path), f"arquivo ausente: {path}"

    # ancoras.json gravado
    json_path = os.path.join(TMP, "casting", "ancoras.json")
    assert os.path.exists(json_path), "ancoras.json não gravado"
    loaded = json.loads(open(json_path).read())
    assert loaded == ancoras


def test_gerar_fichas_idempotente():
    """Segunda chamada: arquivos já existem → 0 novas chamadas ao mock."""
    # roda primeira vez (arquivos criados pelo teste anterior ou recria)
    _reset()
    mock_fn1, calls1 = _make_mock()
    casting.gerar_fichas(BIBLIA, TMP, ARTE_POS, mock_fn1)
    assert len(calls1) == 4

    # segunda vez: sem reset — arquivos já existem
    mock_fn2, calls2 = _make_mock()
    casting.gerar_fichas(BIBLIA, TMP, ARTE_POS, mock_fn2)
    assert len(calls2) == 0, f"esperado 0 chamadas (idempotente), got {len(calls2)}"


def test_protagonista_retrato_linkado():
    """Protagonista com retrato existente → ancoras recebe alias por id."""
    _reset()

    biblia_com_prot = dict(BIBLIA)
    biblia_com_prot["protagonista"] = {
        "id": "aurora",
        "nome": "Aurora",
        "aparencia": "girl 10yo brown hair green eyes",
    }

    # cria retrato fake na estrutura esperada
    retrato_dir = os.path.join(TMP, "biblia", "aurora", "assets")
    os.makedirs(retrato_dir, exist_ok=True)
    retrato_path = os.path.join(retrato_dir, "retrato.png")
    open(retrato_path, "w").write("retrato")

    mock_fn, calls = _make_mock()
    # aurora já está no elenco → ficha gerada; retrato deve sobrescrever p/ ancoras[id]
    ancoras = casting.gerar_fichas(biblia_com_prot, TMP, ARTE_POS, mock_fn)

    assert "aurora" in ancoras
    # o caminho do protagonista deve ser o retrato (pois existe)
    assert ancoras["aurora"] == retrato_path


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_prompt_ficha()
    print("test_prompt_ficha ... OK")

    test_gerar_fichas_chama_mock_e_retorna_dict()
    print("test_gerar_fichas_chama_mock_e_retorna_dict ... OK")

    test_gerar_fichas_idempotente()
    print("test_gerar_fichas_idempotente ... OK")

    test_protagonista_retrato_linkado()
    print("test_protagonista_retrato_linkado ... OK")

    print("\nOK")
