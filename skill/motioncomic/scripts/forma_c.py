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


# genero do episodio -> energia de direcao sugerida ao diretor-animacao.
# Generos de ACAO pedem amplitude/cortes; contemplativos pedem respiro.
GENERO_ENERGIA = {
    "aventura": "alta", "acao": "alta", "ação": "alta", "terror": "alta",
    "suspense": "alta", "thriller": "alta", "comedia": "media", "comédia": "media",
    "drama": "media", "educativo": "media", "infantil": "media",
    "contemplativo": "baixa", "poetico": "baixa", "poético": "baixa",
}
# Nota de direcao gravada no manifesto p/ o diretor-animacao NAO cair no default
# sutil. O motor ja suporta tudo isto (multi-shot, crash_zoom, whip); aqui so
# instruimos o uso conforme a energia do episodio.
DIRECAO_NOTA = (
    "Filme dos paineis: priorize ACAO e leitura clara. Energia ALTA "
    "(aventura/acao/suspense): use multi-shot 2-4 por painel — wide estabelece "
    "-> cut/whip -> CLOSE direto e preciso no ponto de interesse (framing.at); "
    "crash_zoom/whip_pan nos beats de tensao; amplitude maior. A MESMA narracao "
    "pode atravessar os cortes (montagem sobre fala continua). Reuse a mesma "
    "imagem com enquadramentos/cortes diferentes; gere imagens intermediarias se "
    "a narracao pede mais momentos. Energia BAIXA: push-in/parallax suave, planos "
    "longos. Desenho -> parallax 0."
)


def _energia_do_roteiro(roteiro, energia=None):
    """Energia de direcao: override explicito > campo do roteiro (genero/tom) >
    'media' (default neutro)."""
    if energia:
        return energia
    g = (roteiro.get("genero") or roteiro.get("tom") or "").strip().lower()
    return GENERO_ENERGIA.get(g, "media")


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


def coletar_forma_c(roteiro, assets_dir, stage_dir, energia=None):
    """Encena os paineis textless (assets/pNNqN.png) + narracoes (pNNqN.wav) da
    Forma A em `stage_dir/assets/{img,audio}/sNN.*` (na ORDEM de leitura), e
    escreve `stage_dir/forma-c.json` (cenas + meta + direcao). Retorna o
    manifesto dict. `energia` (alta|media|baixa) ajusta a intensidade sugerida
    ao diretor; default vem do genero/tom do roteiro. Levanta FileNotFoundError
    se faltar imagem ou narracao de algum painel."""
    img_dir = os.path.join(stage_dir, "assets", "img")
    aud_dir = os.path.join(stage_dir, "assets", "audio")
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(aud_dir, exist_ok=True)

    tags = _paineis_em_ordem(roteiro)
    cenas, imagens, narracoes = [], [], []
    # mapas origem -> prompt (o que o diretor VE) e -> narracao (o que ele OUVE):
    # o diretor da Forma C dirige a camera pelos DOIS (visual + narrativa).
    prompt_de, narr_de = {}, {}
    for pg in roteiro["paginas"]:
        for idx, p in enumerate(pg["paineis"], start=1):
            tag = f"p{pg['n']:02d}q{idx}"
            prompt_de[tag] = p.get("prompt", "")
            fala = p.get("fala") or ""
            if isinstance(fala, dict):
                fala = fala.get("texto", "")
            narr_de[tag] = " ".join(x for x in (p.get("narracao", ""), fala) if x).strip()

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
                      "narr": f"assets/audio/{sid}.wav", "cena": prompt_de.get(tag, ""),
                      "narr_txt": narr_de.get(tag, "")})

    meta = {"id": roteiro.get("id", ""), "n": roteiro.get("n"),
            "titulo": roteiro.get("titulo", ""), "subtitulo": roteiro.get("subtitulo", ""),
            "abertura": (roteiro.get("abertura") or "").strip(),
            "direcao": {"energia": _energia_do_roteiro(roteiro, energia),
                        "nota": DIRECAO_NOTA}}
    manifesto = {"meta": meta, "cenas": cenas, "imagens": imagens, "narracoes": narracoes}
    with open(os.path.join(stage_dir, "forma-c.json"), "w") as f:
        json.dump(manifesto, f, ensure_ascii=False, indent=2)
    return manifesto


def wrap_forma_c(miolo_mp4, out_mp4, *, abertura, titulo, subtitulo="MOTION COMIC",
                 voice="bella"):
    """Envolve o filme dirigido (miolo) com o card de abertura narrando o gancho
    (t=0) e o CTA inema.club — mesma identidade das Formas A/B. Concatena via
    filtro `concat` (re-encoda), tolerante a diferenca de encode entre o pixflow
    e os cards. Retorna out_mp4."""
    import html as _h
    base = os.path.dirname(os.path.abspath(out_mp4))
    work = os.path.join(base, "_forma_c_cards")
    os.makedirs(work, exist_ok=True)
    abertura = (abertura or "").strip()

    intro = os.path.join(work, "000-intro.mp4")
    _title_clip(f'<small>{_h.escape(subtitulo or "MOTION COMIC")}</small>'
                + _h.escape(titulo), intro, secs=2.2,
                audio=(abertura or None), voice=voice)
    cta = os.path.join(work, "zz9-cta.mp4")
    _cta_clip(cta, voice=voice)

    parts = [intro, miolo_mp4, cta]
    # concat por FILTRO (re-encoda) -> tolera params diferentes entre pixflow e cards
    inputs = []
    for p in parts:
        inputs += ["-i", p]
    n = len(parts)
    fc = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", *inputs,
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-ar", "44100", "-ac", "2", out_mp4]
    subprocess.run(cmd, check=True)
    return out_mp4
