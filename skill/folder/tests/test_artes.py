import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from artes import load_arte, build_prompts

def test_load_arte():
    a = load_arte("foto")
    assert "photorealistic" in a["positivo"]
    assert "text" in a["negativo"]

def test_build_prompts_shape():
    ficha = {"aparencia": "an 84yo woman with short white hair",
             "focos": [{"legenda": "Setup de confianca"}, {"legenda": "Pe firme"},
                       {"legenda": "Atitude"}, {"legenda": "Movimento"}, {"legenda": "Aventura"}]}
    p = build_prompts(ficha, "foto")
    assert "an 84yo woman" in p["retrato"]
    assert "photorealistic" in p["retrato"]
    assert "no text" in p["retrato"]
    assert len(p["focos"]) == 5
    assert "setup de confianca" in p["focos"][0].lower()

if __name__ == "__main__":
    test_load_arte(); test_build_prompts_shape(); print("OK")
