"""Testa _merge_ancoras: autoload de casting/ancoras.json + merge com explicitas."""
import json
import os
import sys
import tempfile

# path para importar build_serie a partir do dir scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from build_serie import _merge_ancoras  # noqa: E402


def test_merge_com_arquivo():
    """Arquivo existe: auto carregado, explicito vence conflito."""
    with tempfile.TemporaryDirectory() as tmp:
        casting_dir = os.path.join(tmp, "casting")
        os.makedirs(casting_dir)
        ancoras_json = {"nuvem": "/x/nuvem.png", "matriarca": "/x/m.png"}
        with open(os.path.join(casting_dir, "ancoras.json"), "w") as f:
            json.dump(ancoras_json, f)

        result = _merge_ancoras(tmp, {"nuvem": "/y/over.png"})

        assert result == {"nuvem": "/y/over.png", "matriarca": "/x/m.png"}, (
            f"esperado {{'nuvem': '/y/over.png', 'matriarca': '/x/m.png'}}, obtido {result}"
        )


def test_merge_sem_arquivo():
    """Sem arquivo casting/ancoras.json: retorna so as explicitas."""
    with tempfile.TemporaryDirectory() as tmp:
        result = _merge_ancoras(tmp, {"hero": "/h/hero.png"})
        assert result == {"hero": "/h/hero.png"}, (
            f"esperado {{'hero': '/h/hero.png'}}, obtido {result}"
        )


def test_merge_sem_arquivo_sem_explicitas():
    """Sem arquivo e sem explicitas: retorna dict vazio."""
    with tempfile.TemporaryDirectory() as tmp:
        result = _merge_ancoras(tmp, None)
        assert result == {}, f"esperado {{}}, obtido {result}"


def test_merge_explicitas_none_com_arquivo():
    """Arquivo existe, explicitas=None: retorna so o auto."""
    with tempfile.TemporaryDirectory() as tmp:
        casting_dir = os.path.join(tmp, "casting")
        os.makedirs(casting_dir)
        with open(os.path.join(casting_dir, "ancoras.json"), "w") as f:
            json.dump({"x": "/a/x.png"}, f)

        result = _merge_ancoras(tmp, None)
        assert result == {"x": "/a/x.png"}, f"esperado {{'x': '/a/x.png'}}, obtido {result}"


if __name__ == "__main__":
    test_merge_com_arquivo()
    print("test_merge_com_arquivo OK")
    test_merge_sem_arquivo()
    print("test_merge_sem_arquivo OK")
    test_merge_sem_arquivo_sem_explicitas()
    print("test_merge_sem_arquivo_sem_explicitas OK")
    test_merge_explicitas_none_com_arquivo()
    print("test_merge_explicitas_none_com_arquivo OK")
    print("OK")
