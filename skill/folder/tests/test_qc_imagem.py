import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import qc_imagem as Q


def _fake_generate():
    calls = []
    def gen(prompt, out_path, seed=None, **kw):
        calls.append({"prompt": prompt, "seed": seed, "kw": kw})
        with open(out_path, "wb") as f:
            f.write(b"\x89PNG\r\n")
    return gen, calls


def test_sem_judge_gera_uma_vez(tmp="/tmp/_qc_a"):
    os.makedirs(tmp, exist_ok=True)
    gen, calls = _fake_generate()
    out = os.path.join(tmp, "p.png")
    r = Q.gerar_revisado("cena", out, generate=gen)         # judge=None (default = QC off)
    assert r["ok"] and r["veredito"] is None and not r["flag"]
    assert len(calls) == 1
    assert not os.path.exists(out + ".qc.json")


def test_judge_aprova_na_segunda_reforca_anatomia(tmp="/tmp/_qc_b"):
    os.makedirs(tmp, exist_ok=True)
    gen, calls = _fake_generate()
    estados = [{"adequado": False, "dimensao": "anatomia"}, {"adequado": True, "dimensao": "ok"}]
    judge = lambda img, ref, esp: estados[len(calls) - 1]
    out = os.path.join(tmp, "p.png")
    r = Q.gerar_revisado("cena", out, judge=judge, generate=gen, tentativas=3)
    assert r["ok"] and r["tentativa"] == 2 and not r["flag"]
    assert "bad anatomy" in calls[1]["kw"].get("negative_prompt", "")  # reforco ao reprovar anatomia
    assert calls[0]["seed"] != calls[1]["seed"]                        # seed varia entre tentativas


def test_judge_reprova_tudo_flag_e_segue(tmp="/tmp/_qc_c"):
    os.makedirs(tmp, exist_ok=True)
    gen, calls = _fake_generate()
    judge = lambda img, ref, esp: {"adequado": False, "dimensao": "cenario", "motivos": ["praia != riacho"]}
    out = os.path.join(tmp, "p.png")
    r = Q.gerar_revisado("cena no riacho", out, ref="Lia", esperado="riacho",
                         judge=judge, generate=gen, tentativas=2)
    assert not r["ok"] and r["flag"] and r["tentativa"] == 2 and len(calls) == 2
    side = json.load(open(out + ".qc.json"))
    assert side["veredito"]["dimensao"] == "cenario"


def test_make_generate_fn_bate_assinatura_do_build_pagina(tmp="/tmp/_qc_d"):
    os.makedirs(tmp, exist_ok=True)
    gen, calls = _fake_generate()
    judge = lambda img, ref, esp: {"adequado": True, "dimensao": "ok"}
    fn = Q.make_generate_fn("Lia", tentativas=2, judge=judge, esperado=None, generate=gen)
    out = os.path.join(tmp, "p.png")
    # build_pagina chama: generate_fn(prompt, out, model=, width=, height=, negative_prompt=)
    fn("cena", out, model="flux2-klein", width=800, height=1000, negative_prompt="x")
    assert calls and calls[0]["kw"]["width"] == 800


if __name__ == "__main__":
    test_sem_judge_gera_uma_vez()
    test_judge_aprova_na_segunda_reforca_anatomia()
    test_judge_reprova_tudo_flag_e_segue()
    test_make_generate_fn_bate_assinatura_do_build_pagina()
    print("OK qc_imagem")
