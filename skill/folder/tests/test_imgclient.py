# skill/folder/tests/test_imgclient.py
import os, sys, json, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import imgclient
from png_size import png_size

PNG_2x1_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAEklEQVR4nGP8z8Dwn4EIwDiqEAARWAIBLb0nawAAAABJRU5ErkJggg=="

class FakeResp:
    def __init__(self, body): self._b = body
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False

def test_builds_payload_and_saves(tmp="/tmp/_imgclient_out.png"):
    captured = {}
    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return FakeResp(json.dumps({"image": PNG_2x1_B64}).encode())
    imgclient._urlopen = fake_urlopen  # inject
    imgclient.generate("a cat", tmp, model="flux2-klein", width=2, height=1,
                       images=["/tmp/_imgclient_out_ref.png"] if False else None,
                       negative_prompt="text")
    assert captured["url"].endswith("/generate")
    assert captured["body"]["model"] == "flux2-klein"
    assert captured["body"]["prompt"] == "a cat"
    assert captured["body"]["width"] == 2 and captured["body"]["height"] == 1
    assert captured["body"]["negative_prompt"] == "text"
    assert png_size(tmp) == (2, 1)

if __name__ == "__main__":
    test_builds_payload_and_saves()
    print("OK")
