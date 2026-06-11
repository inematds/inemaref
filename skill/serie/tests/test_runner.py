import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from runner import is_video, escolher, mkivideos_disponivel


def test_is_video():
    assert is_video("video-pagina") and is_video("video-slideshow")
    assert not is_video("hq") and not is_video("texto")


def test_escolher_explicit_overrides():
    assert escolher("video-pagina", runner="inline", disponivel=True) == "inline"
    assert escolher("hq", runner="mkivideos", disponivel=False) == "mkivideos"


def test_escolher_auto():
    assert escolher("video-pagina", runner="auto", disponivel=True) == "mkivideos"
    assert escolher("video-pagina", runner="auto", disponivel=False) == "inline"
    assert escolher("hq", runner="auto", disponivel=True) == "inline"  # so video vai pra fila


def test_disponivel_uses_injected_check():
    assert mkivideos_disponivel(check_fn=lambda: True) is True
    assert mkivideos_disponivel(check_fn=lambda: False) is False


if __name__ == "__main__":
    test_is_video()
    test_escolher_explicit_overrides()
    test_escolher_auto()
    test_disponivel_uses_injected_check()
    print("OK")
