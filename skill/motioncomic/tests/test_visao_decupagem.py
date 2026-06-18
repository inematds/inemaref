# skill/motioncomic/tests/test_visao_decupagem.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import visao_decupagem as vd

# --- helpers ---

def _ep_minimo():
    """Roteiro mínimo: 1 pagina, 3 paineis."""
    return {
        "paginas": [
            {
                "paineis": [
                    {"narracao": "Era uma vez.", "falas": [], "sfx": ""},
                    {"narracao": "O herói apareceu.", "falas": [{"texto": "Olá!"}], "sfx": "CRASH"},
                    {"narracao": "", "falas": [], "sfx": ""},
                ]
            }
        ]
    }

# --- validar_shots ---

def test_shots_clamp_at_e_zoom():
    shots = [{"tipo": "close", "at": [1.5, -0.2], "zoom": 5}]
    result = vd.validar_shots(shots)
    assert len(result) == 1
    s = result[0]
    assert s["at"] == [1.0, 0.0], f"at esperado [1.0, 0.0], got {s['at']}"
    assert s["zoom"] == 3.0, f"zoom esperado 3.0, got {s['zoom']}"
    assert s["peso"] == 1.0, f"peso ausente deve ser 1.0, got {s['peso']}"

def test_shots_tipo_invalido():
    try:
        vd.validar_shots([{"tipo": "xpto"}])
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass

def test_shots_lista_vazia():
    try:
        vd.validar_shots([])
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass

def test_shots_nao_lista():
    try:
        vd.validar_shots("nao-e-lista")
        assert False, "deveria ter levantado ValueError"
    except ValueError:
        pass

def test_shots_peso_negativo_vira_1():
    shots = [{"tipo": "wide", "peso": -1}]
    result = vd.validar_shots(shots)
    assert result[0]["peso"] == 1.0

def test_shots_peso_zero_vira_1():
    shots = [{"tipo": "pan", "peso": 0}]
    result = vd.validar_shots(shots)
    assert result[0]["peso"] == 1.0

def test_shots_defaults_ausentes():
    shots = [{"tipo": "insert"}]
    result = vd.validar_shots(shots)
    s = result[0]
    assert s["at"] == [0.5, 0.5]
    assert s["zoom"] == 1.0
    assert s["peso"] == 1.0
    assert "direction" not in s

def test_shots_direction_mantido():
    shots = [{"tipo": "pan", "direction": "left"}]
    result = vd.validar_shots(shots)
    assert result[0]["direction"] == "left"

def test_shots_direction_ausente_omitido():
    shots = [{"tipo": "tilt"}]
    result = vd.validar_shots(shots)
    assert "direction" not in result[0]

def test_shots_multiplos_em_ordem():
    shots = [
        {"tipo": "wide"},
        {"tipo": "close", "zoom": 2.0},
    ]
    result = vd.validar_shots(shots)
    assert result[0]["tipo"] == "wide"
    assert result[1]["tipo"] == "close"
    assert result[1]["zoom"] == 2.0

# --- contexto_do_painel ---

def test_contexto_painel_s01():
    ep = _ep_minimo()
    ctx = vd.contexto_do_painel(ep, "s01")
    assert "Era uma vez." in ctx

def test_contexto_painel_s02():
    ep = _ep_minimo()
    ctx = vd.contexto_do_painel(ep, "s02")
    assert "herói" in ctx or "heroi" in ctx.lower() or "O herói apareceu." in ctx
    assert "Olá!" in ctx
    # sfx também deve aparecer
    assert "CRASH" in ctx

def test_contexto_painel_fora_do_range():
    ep = _ep_minimo()
    ctx = vd.contexto_do_painel(ep, "s99")
    assert ctx == ""

def test_contexto_painel_s03_sem_conteudo():
    ep = _ep_minimo()
    ctx = vd.contexto_do_painel(ep, "s03")
    # painel 3 tem tudo vazio; retorna string (pode ser vazia)
    assert isinstance(ctx, str)

if __name__ == "__main__":
    test_shots_clamp_at_e_zoom()
    test_shots_tipo_invalido()
    test_shots_lista_vazia()
    test_shots_nao_lista()
    test_shots_peso_negativo_vira_1()
    test_shots_peso_zero_vira_1()
    test_shots_defaults_ausentes()
    test_shots_direction_mantido()
    test_shots_direction_ausente_omitido()
    test_shots_multiplos_em_ordem()
    test_contexto_painel_s01()
    test_contexto_painel_s02()
    test_contexto_painel_fora_do_range()
    test_contexto_painel_s03_sem_conteudo()
    print("OK")
