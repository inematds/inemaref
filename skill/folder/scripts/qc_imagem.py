"""QC da imagem gerada (Pilar B/C da coerencia) — DESATIVADO por padrao (custo).

`gerar_revisado()` gera a imagem e, SE houver um `judge`, REVISA por VISAO (Claude
ve) se ela bate com o personagem/biblia e se a ANATOMIA esta correta; reprovou ->
regenera com outra seed (ate `tentativas`); reprovou tudo -> grava `<out>.qc.json`
e SEGUE (flag, nao trava a serie). Sem `judge` -> comporta-se EXATAMENTE como
antes (uma geracao, sem revisao) = o default.

Ativar (opt-in): `INEMAREF_QC=1` + `ANTHROPIC_API_KEY` (o backend `judge_visao`
usa um modelo de visao barato; veja `INEMAREF_QC_MODEL`).
"""
import base64
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import imgclient  # noqa: E402

QC_MODEL = os.environ.get("INEMAREF_QC_MODEL", "claude-haiku-4-5")
QC_URL = os.environ.get("INEMAREF_QC_URL", "https://api.anthropic.com/v1/messages")

_NEG_ANATOMIA = "bad anatomy, extra fingers, deformed hands, extra limbs, fused fingers"


def gerar_revisado(prompt, out_path, *, ref=None, esperado=None, tentativas=3,
                   judge=None, generate=None, seed=None, **gen_kwargs):
    """Gera + (opcional) revisa por visao, regenerando ate `tentativas`. Retorna
    {ok, tentativa, veredito|None, flag}. `judge(out_path, ref, esperado)` ->
    {adequado, score, dimensao, motivos}. `judge=None` -> 1 geracao, sem QC."""
    generate = generate or imgclient.generate
    if judge is None:                       # QC desligado: comportamento original
        generate(prompt, out_path, seed=seed, **gen_kwargs)
        return {"ok": True, "tentativa": 1, "veredito": None, "flag": False}

    base_seed = seed if seed is not None else 0
    ultimo = None
    for i in range(1, max(1, tentativas) + 1):
        kw = dict(gen_kwargs)
        if ultimo and ultimo.get("dimensao") == "anatomia":   # reforca negativo
            neg = kw.get("negative_prompt")
            kw["negative_prompt"] = (neg + ", " + _NEG_ANATOMIA) if neg else _NEG_ANATOMIA
        generate(prompt, out_path, seed=base_seed + i, **kw)
        ultimo = judge(out_path, ref, esperado) or {}
        if ultimo.get("adequado"):
            return {"ok": True, "tentativa": i, "veredito": ultimo, "flag": False}

    with open(out_path + ".qc.json", "w") as f:                # reprovou tudo: flag + segue
        json.dump({"prompt": prompt, "esperado": esperado, "ref": ref,
                   "tentativas": tentativas, "veredito": ultimo}, f,
                  ensure_ascii=False, indent=2)
    return {"ok": False, "tentativa": tentativas, "veredito": ultimo, "flag": True}


def make_generate_fn(ref, *, esperado=None, tentativas=3, judge=None, generate=None):
    """Adapta `gerar_revisado` a assinatura `generate_fn(prompt, out, **kw)` que o
    build_pagina injeta. `esperado` default = o proprio prompt do painel.
    `generate` injetavel (teste); None -> imgclient.generate."""
    def _gen(prompt, out_path, **kw):
        return gerar_revisado(prompt, out_path, ref=ref, esperado=esperado or prompt,
                              tentativas=tentativas, judge=judge, generate=generate, **kw)
    return _gen


_INSTRU = (
    "Voce e um revisor de arte. Analise a IMAGEM e responda SO um JSON (sem "
    "markdown, sem texto fora do JSON) com as chaves: adequado (bool), score "
    "(0..1), dimensao (uma de: personagem|cenario|anatomia|ok), motivos (lista "
    "curta de strings em PT). Reprove (adequado=false) se: NAO bate com a "
    "REFERENCIA do personagem; o cenario/mundo diverge do ESPERADO (ex.: pediram "
    "riacho e veio praia); ou ha ERRO DE ANATOMIA (maos/dedos errados, membros a "
    "mais, deformacao, proporcao). Caso contrario adequado=true, dimensao=ok."
)


def judge_visao(img_path, ref, esperado, *, model=None, url=None, api_key=None):
    """Backend REAL (opt-in): Claude VE a imagem e devolve o veredito estruturado.
    Requer ANTHROPIC_API_KEY (sem chave -> erro claro). Custa -> use so com
    INEMAREF_QC=1."""
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("judge_visao requer ANTHROPIC_API_KEY (QC por visao nao configurado)")
    with open(img_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    texto = (f"{_INSTRU}\n\nREFERENCIA do personagem: {ref or '(nao informada)'}\n"
             f"ESPERADO (cena pedida): {esperado or '(nao informado)'}")
    body = json.dumps({
        "model": model or QC_MODEL, "max_tokens": 400,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                          "media_type": "image/png", "data": data}},
            {"type": "text", "text": texto}]}]}).encode()
    req = urllib.request.Request(url or QC_URL, data=body, method="POST", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    txt = "".join(b.get("text", "") for b in resp.get("content", [])
                  if b.get("type") == "text").strip()
    if txt.startswith("```"):                       # tolera cerca de codigo
        txt = txt.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(txt)
