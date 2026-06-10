import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import biblia as B

GOOD = {
    "id": "piramide-maslow", "assunto": "A piramide de Maslow",
    "premissa": {"logline": "Lia sobe a escada invisivel.", "sinopse": "Sinopse curta."},
    "formato": {"n_episodios": 2},
    "protagonista": {"nome": "Lia", "aparencia": "jovem, cardiga mostarda"},
    "elenco": [{"nome": "Teo", "aparencia": "oculos redondos"}],
    "episodios": [
        {"n": 1, "titulo": "O que e", "sinopse": "intro"},
        {"n": 2, "titulo": "Fisiologico", "sinopse": "base"},
    ],
}


def test_validate_accepts_good():
    assert B.validate(GOOD) is True


def test_validate_missing_field():
    bad = dict(GOOD); del bad["protagonista"]
    try:
        B.validate(bad); assert False, "deveria falhar"
    except ValueError as e:
        assert "protagonista" in str(e)


def test_validate_episode_count_mismatch():
    bad = dict(GOOD); bad["formato"] = {"n_episodios": 5}
    try:
        B.validate(bad); assert False, "deveria falhar"
    except ValueError as e:
        assert "n_episodios" in str(e)


def test_to_markdown_has_title_and_episodes():
    md = B.to_markdown(GOOD)
    assert "A piramide de Maslow" in md
    assert "Lia" in md and "Teo" in md
    assert "O que e" in md and "Fisiologico" in md


if __name__ == "__main__":
    test_validate_accepts_good()
    test_validate_missing_field()
    test_validate_episode_count_mismatch()
    test_to_markdown_has_title_and_episodes()
    print("OK")
