import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import config

def test_fallback_destino_is_home_projetos_output():
    assert config.FALLBACK["formato"]["destino"] == "~/projetos/output"

def test_resolve_keeps_home_destino():
    flat = config.resolve({"id": "x"})
    assert flat["destino"] == "~/projetos/output"

def test_expanduser_resolves_outside_repo():
    p = os.path.expanduser(config.resolve({"id": "x"})["destino"])
    assert p == os.path.join(os.path.expanduser("~"), "projetos", "output")
    assert "~" not in p

def test_build_serie_expands_destino():
    import build_serie
    biblia = {"id": "demo-x", "assunto": "demo", "formato": {"tipo": "texto"}}

    def noop(ep, settings, destdir, base):
        return []

    res = build_serie.build_serie(
        biblia,
        [{"n": 1, "titulo": "t", "paginas": []}],
        renderers={"texto": noop},
        auto=True,
    )
    dest = res["dest"]
    assert "~" not in str(dest)
    assert os.path.expanduser("~/projetos/output") in str(dest)


def test_estilo_defaults_moldura_accent():
    assert config.FALLBACK["estilo"]["moldura"] == "dark"
    assert config.FALLBACK["estilo"]["cor_destaque"] == "#b08900"
    flat = config.resolve({"id": "x"})
    assert flat["moldura"] == "dark" and flat["cor_destaque"] == "#b08900"


if __name__ == "__main__":
    test_fallback_destino_is_home_projetos_output()
    test_resolve_keeps_home_destino()
    test_expanduser_resolves_outside_repo()
    test_build_serie_expands_destino()
    test_estilo_defaults_moldura_accent()
    print("OK")
