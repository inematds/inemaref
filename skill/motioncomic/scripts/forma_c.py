"""Forma C — cola entre os assets do motioncomic (Forma A) e o skill
`diretor-animacao` (que dirige + renderiza via pixflow). NAO dirige nada aqui:
so encena os paineis textless + narracoes no layout que o diretor consome,
nomeia a saida, e envolve o filme dirigido com o card de gancho + o CTA.
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from build_motion import _title_clip, FPS, W, H   # noqa: E402  (card de abertura)
from build_travel import _cta_clip                # noqa: E402  (CTA inema.club)
import _deps  # noqa: E402
sys.path.insert(0, _deps.scripts("serie"))
from naming import ep_base   # noqa: E402  (mesmo gerador de nome das Formas A/B)


def forma_c_out_name(serie_slug, n, titulo):
    """Nome do arquivo Forma C, no MESMO padrao das Formas A/B: a letra do
    formato (c) vem ANTES do epNN -> <serie>-c-ep01-<titulo>.mp4."""
    return ep_base(f"{serie_slug}-c", n, titulo) + ".mp4"


def _paineis_em_ordem(roteiro):
    """Lista [tag] na ordem de leitura: paginas em ordem, paineis 1..6.
    tag = pNNqI (o nome do asset da Forma A)."""
    out = []
    for pg in roteiro["paginas"]:
        pn = pg["n"]
        for idx in range(1, len(pg["paineis"]) + 1):
            tag = f"p{pn:02d}q{idx}"
            out.append(tag)
    return out


def coletar_forma_c(roteiro, assets_dir, stage_dir):
    """Encena os paineis textless (assets/pNNqN.png) + narracoes (pNNqN.wav) da
    Forma A em `stage_dir/assets/{img,audio}/sNN.*` (na ORDEM de leitura), e
    escreve `stage_dir/forma-c.json` (cenas + meta). Retorna o manifesto dict.
    Levanta FileNotFoundError se faltar imagem ou narracao de algum painel."""
    img_dir = os.path.join(stage_dir, "assets", "img")
    aud_dir = os.path.join(stage_dir, "assets", "audio")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(aud_dir, exist_ok=True)

    tags = _paineis_em_ordem(roteiro)
    cenas, imagens, narracoes = [], [], []
    # mapa origem -> prompt (dica de cena p/ o diretor VER)
    prompt_de = {}
    for pg in roteiro["paginas"]:
        for idx, p in enumerate(pg["paineis"], start=1):
            prompt_de[f"p{pg['n']:02d}q{idx}"] = p.get("prompt", "")

    for i, tag in enumerate(tags, start=1):
        src_png = os.path.join(assets_dir, f"{tag}.png")
        src_wav = os.path.join(assets_dir, f"{tag}.wav")
        if not os.path.exists(src_png):
            raise FileNotFoundError(f"painel sem imagem: {tag}.png em {assets_dir}")
        if not os.path.exists(src_wav):
            raise FileNotFoundError(f"painel sem narracao: {tag}.wav em {assets_dir}")
        sid = f"s{i:02d}"
        dst_png = os.path.join(img_dir, f"{sid}.png")
        dst_wav = os.path.join(aud_dir, f"{sid}.wav")
        shutil.copyfile(src_png, dst_png)
        shutil.copyfile(src_wav, dst_wav)
        imagens.append(dst_png)
        narracoes.append(dst_wav)
        cenas.append({"sid": sid, "origem": tag, "img": f"assets/img/{sid}.png",
                      "narr": f"assets/audio/{sid}.wav", "cena": prompt_de.get(tag, "")})

    meta = {"id": roteiro.get("id", ""), "n": roteiro.get("n"),
            "titulo": roteiro.get("titulo", ""), "subtitulo": roteiro.get("subtitulo", ""),
            "abertura": (roteiro.get("abertura") or "").strip()}
    manifesto = {"meta": meta, "cenas": cenas, "imagens": imagens, "narracoes": narracoes}
    with open(os.path.join(stage_dir, "forma-c.json"), "w") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)
    return manifesto
