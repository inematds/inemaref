import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from manifesto import build

BIBLIA = {
    "id": "piramide-maslow", "assunto": "A piramide de Maslow",
    "premissa": {"logline": "Lia sobe a escada."},
    "formato": {"tipo": "video-pagina"},
    "episodios": [
        {"n": 1, "titulo": "O que e", "sinopse": "intro", "tags": ["maslow"]},
        {"n": 2, "titulo": "Fisiologico", "sinopse": "base"},
    ],
}


def test_build_manifesto_merges_biblia_and_files():
    entregas = [
        {"n": 1, "arquivos": ["piramide-maslow-ep01-o-que-e.mp4"], "thumb": "ep01.jpg"},
        {"n": 2, "arquivos": ["piramide-maslow-ep02-fisiologico.mp4"]},
    ]
    m = build(BIBLIA, entregas, gerado_em="2026-06-10")
    assert m["serie_id"] == "piramide-maslow"
    assert m["tipo"] == "video-pagina"
    assert m["gerado_em"] == "2026-06-10"
    assert len(m["episodios"]) == 2
    e1 = m["episodios"][0]
    assert e1["titulo"] == "O que e"          # do biblia
    assert e1["descricao"] == "intro"          # sinopse do biblia
    assert e1["tags"] == ["maslow"]
    assert e1["arquivos"] == ["piramide-maslow-ep01-o-que-e.mp4"]
    assert e1["thumb"] == "ep01.jpg"


if __name__ == "__main__":
    test_build_manifesto_merges_biblia_and_files()
    print("OK")
