# skill/serie/tests/test_lint_paineis.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from lint_paineis import contar_entidades, lint_episodio


# ── contar_entidades ────────────────────────────────────────────────────────

def test_sem_quem_com_usa():
    # quem ausente → protagonista (1) + usa 3 itens → total 4
    p = {"usa": ["A", "B", "C"]}
    assert contar_entidades(p) == 4

def test_sem_quem_sem_usa():
    # narração pura: quem ausente → 1, usa ausente → 0 → total 1
    p = {}
    assert contar_entidades(p) == 1

def test_quem_vazio_com_usa():
    # quem="" → 0 pessoas; usa=["A"] → 1 → total 1
    p = {"quem": "", "usa": ["A"]}
    assert contar_entidades(p) == 1

def test_quem_explicito_sem_usa():
    # quem="Pai" → 1; usa=[] → 0 → total 1
    p = {"quem": "Pai", "usa": []}
    assert contar_entidades(p) == 1

def test_quem_explicito_com_usa():
    # quem="Mãe" → 1; usa=["X","Y"] → 2 → total 3
    p = {"quem": "Mãe", "usa": ["X", "Y"]}
    assert contar_entidades(p) == 3


# ── lint_episodio ───────────────────────────────────────────────────────────

def _ep(*paginas):
    """Helper: _ep((n, [painel, ...]), ...) → dict de episódio."""
    return {"paginas": [{"n": n, "paineis": ps} for n, ps in paginas]}


def test_lint_sinaliza_painel_excedente():
    # painel sem quem + usa=["A","B","C"] → 4 entidades > max=2 → 1 erro
    ep = _ep((1, [{"usa": ["A", "B", "C"]}]))
    erros = lint_episodio(ep, max_entidades=2)
    assert len(erros) == 1
    e = erros[0]
    assert e["pagina"] == 1
    assert e["painel"] == 1
    assert e["n"] == 4
    assert "A" in e["entidades"]
    assert "B" in e["entidades"]
    assert "C" in e["entidades"]


def test_lint_narracao_nao_sinalizada():
    # painel sem quem, sem usa → 1 entidade → ok com max=2
    ep = _ep((1, [{}]))
    assert lint_episodio(ep, max_entidades=2) == []


def test_lint_quem_vazio_nao_sinalizado():
    # quem="" + usa=["A"] → 1 entidade → ok
    ep = _ep((1, [{"quem": "", "usa": ["A"]}]))
    assert lint_episodio(ep, max_entidades=2) == []


def test_lint_quem_pai_nao_sinalizado():
    # quem="Pai" + usa=[] → 1 entidade → ok
    ep = _ep((1, [{"quem": "Pai", "usa": []}]))
    assert lint_episodio(ep, max_entidades=2) == []


def test_lint_pagina_e_indice_corretos():
    # 2 páginas; página 2 tem 3 painéis, o terceiro estoura
    ep = _ep(
        (1, [{"quem": "A"}]),                          # pág 1, painel 1 → ok
        (2, [
            {"quem": "B"},                             # pág 2, painel 1 → ok
            {"quem": "C"},                             # pág 2, painel 2 → ok
            {"quem": "D", "usa": ["X", "Y", "Z"]},    # pág 2, painel 3 → 4 > 2
        ]),
    )
    erros = lint_episodio(ep, max_entidades=2)
    assert len(erros) == 1
    assert erros[0]["pagina"] == 2
    assert erros[0]["painel"] == 3


def test_lint_sem_erros_retorna_vazio():
    ep = _ep((1, [{"quem": "Ana"}, {"quem": "", "usa": ["prop"]}]))
    assert lint_episodio(ep) == []


if __name__ == "__main__":
    test_sem_quem_com_usa()
    test_sem_quem_sem_usa()
    test_quem_vazio_com_usa()
    test_quem_explicito_sem_usa()
    test_quem_explicito_com_usa()
    test_lint_sinaliza_painel_excedente()
    test_lint_narracao_nao_sinalizada()
    test_lint_quem_vazio_nao_sinalizado()
    test_lint_quem_pai_nao_sinalizado()
    test_lint_pagina_e_indice_corretos()
    test_lint_sem_erros_retorna_vazio()
    print("OK")
