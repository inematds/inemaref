import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_travel

def test_textless_sibling_path():
    p = "/x/y/z/pagina.png"
    assert build_travel._textless(p) == "/x/y/z/pagina-textless.png"

import inspect

def test_title_clip_accepts_audio():
    from build_motion import _title_clip
    assert "audio" in inspect.signature(_title_clip).parameters

if __name__ == "__main__":
    test_textless_sibling_path()
    test_title_clip_accepts_audio()
    print("OK textless path")
