import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from config import load_config, resolve, FALLBACK


def test_load_config_reads_yaml():
    cfg = load_config()
    assert cfg["estilo"]["arte"] == "manga"
    assert cfg["formato"]["tipo"] == "video-pagina"
    assert cfg["runtime"]["auto"] is False


def test_load_config_fallback_when_missing():
    cfg = load_config("/no/such/file.yaml")
    assert cfg == FALLBACK


def test_resolve_biblia_overrides_config():
    biblia = {"estilo": {"arte": "cartoon"}, "formato": {"tipo": "hq", "n_episodios": 5}}
    s = resolve(biblia)
    assert s["arte"] == "cartoon"        # biblia wins
    assert s["tipo"] == "hq"             # biblia wins
    assert s["n_episodios"] == 5         # biblia wins
    assert s["modelo_pagina"] == "manga-dinamico"  # falls to config default
    assert s["auto"] is False            # runtime default present in flat result


if __name__ == "__main__":
    test_load_config_reads_yaml()
    test_load_config_fallback_when_missing()
    test_resolve_biblia_overrides_config()
    print("OK")
