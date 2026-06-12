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

if __name__ == "__main__":
    test_fallback_destino_is_home_projetos_output()
    test_resolve_keeps_home_destino()
    test_expanduser_resolves_outside_repo()
    print("OK")
