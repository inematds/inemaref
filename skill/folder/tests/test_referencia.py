import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from referencia import build_referencia, validate_referencia

FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))

def test_build_and_validate_ok():
    ref = build_referencia(FICHA, modo="texto", arte="foto",
                           retrato_ancora="assets/retrato.png", foto_origem=None)
    assert ref["id"] == "ideni-maldaner"
    assert ref["modo"] == "texto" and ref["arte"] == "foto"
    assert ref["aparencia"].startswith("an 84-year-old")
    assert ref["ficha"]["nome"] == "IDENI MALDANER"
    validate_referencia(ref)  # must not raise

def test_validate_rejects_bad_modo():
    ref = build_referencia(FICHA, modo="texto", arte="foto",
                           retrato_ancora="x.png", foto_origem=None)
    ref["modo"] = "video"
    try:
        validate_referencia(ref); assert False, "should reject bad modo"
    except ValueError:
        pass

if __name__ == "__main__":
    test_build_and_validate_ok(); test_validate_rejects_bad_modo(); print("OK")
