import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_travel

def test_textless_sibling_path():
    p = "/x/y/z/pagina.png"
    assert build_travel._textless(p) == "/x/y/z/pagina-textless.png"

if __name__ == "__main__":
    test_textless_sibling_path()
    print("OK textless path")
