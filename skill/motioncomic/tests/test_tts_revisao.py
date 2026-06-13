import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from tts import (aplicar_pronuncias, revisar_narracao, revisar_ortografia,
                 carregar_lexico)

LEX = {"design": "dizain", "designer": "dizainer", "app": "epe"}


def test_pronuncia_palavra_inteira_ignora_caixa():
    assert aplicar_pronuncias("O Design e o DESIGN.", LEX) == "O dizain e o dizain."
    # nao casa prefixo dentro de outra palavra: 'designar' fica intacto
    assert aplicar_pronuncias("vou designar alguem", LEX) == "vou designar alguem"
    # termo mais longo primeiro: 'designer' nao vira 'dizain'+er
    assert aplicar_pronuncias("um designer", LEX) == "um dizainer"


def test_revisar_narracao_normaliza_e_pontua():
    # colapsa espacos, aplica lexico e garante ponto final
    out = revisar_narracao("  abra   o   app  ", lexico=LEX)
    assert out == "abra o epe."
    # ja pontuado: nao duplica
    assert revisar_narracao("Pronto!", lexico=LEX) == "Pronto!"
    assert revisar_narracao("Fim...", lexico=LEX) == "Fim..."


def test_revisar_narracao_vazio():
    assert revisar_narracao("", lexico=LEX) == ""
    assert revisar_narracao(None, lexico=LEX) is None


def test_revisar_ortografia_lint():
    assert "sem pontuacao final" in revisar_ortografia("texto sem ponto")
    assert "espacos duplos" in revisar_ortografia("dois  espacos.")
    assert revisar_ortografia("Tudo certo aqui.") == []
    assert revisar_ortografia("   ") == ["texto vazio"]


def test_lexico_padrao_carrega_do_json():
    # o pronuncias.json do skill carrega e ignora chaves _meta
    lex = carregar_lexico()
    assert isinstance(lex, dict)
    assert all(not k.startswith("_") for k in lex)
    assert "design" in lex  # termo semente


if __name__ == "__main__":
    test_pronuncia_palavra_inteira_ignora_caixa()
    test_revisar_narracao_normaliza_e_pontua()
    test_revisar_narracao_vazio()
    test_revisar_ortografia_lint()
    test_lexico_padrao_carrega_do_json()
    print("OK tts revisao")
