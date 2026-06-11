import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from naming import slug, ep_base, page_base


def test_slug_strips_accents_and_spaces():
    assert slug("A Escada Invisível de Lia!") == "a-escada-invisivel-de-lia"
    assert slug("  ") == "x"          # nunca vazio
    assert slug("Café & Cia") == "cafe-cia"


def test_ep_base_is_descriptive():
    assert ep_base("piramide-maslow", 3, "O Confronto") == "piramide-maslow-ep03-o-confronto"


def test_page_base_adds_page_number():
    assert page_base("piramide-maslow", 3, 2, "O Confronto") == "piramide-maslow-ep03-o-confronto-p02"


if __name__ == "__main__":
    test_slug_strips_accents_and_spaces()
    test_ep_base_is_descriptive()
    test_page_base_adds_page_number()
    print("OK")
