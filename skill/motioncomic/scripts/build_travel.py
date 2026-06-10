"""Motion comic — modo CAMERA-SOBRE-A-PAGINA-DE-PAPEL (Forma B, docs/02).

Monta a PAGINA REAL de quadrinho (grade 2x3 com sarjetas / baloes / legendas
impressas, via a skill `quadrinho`) e move a camera sobre ela como quem filma
uma pagina de papel:

  - mergulha (zoom-in) em cada quadro durante a sua narracao;
  - na troca de quadro, AFASTA um pouco (mostra o contexto da pagina) e volta,
    encaixando no proximo quadro;
  - na troca de PAGINA, da zoom-out total ate a pagina inteira e ABRE a proxima.

A narracao e so voz (TTS inemavox). Balao / SFX / legenda ja estao IMPRESSOS na
pagina (e a "pagina de papel"), entao sao reaproveitados do `pagina.png`.

Diferente do `build_motion` (Forma A — slideshow: uma imagem por vez, com corte),
aqui a camera nunca sai da pagina: ela viaja sobre uma unica prancha por pagina.

Funcoes puras (detect_rects / frame_window / window_at / _filter) sao testaveis
sem daemon; build_video_travel precisa de imgclient + inemavox.
"""
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "quadrinho", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))
from render import render_html_to_png  # noqa: E402
from tts import say, duration          # noqa: E402
from build_motion import _title_clip, _spoken, FPS, W, H  # noqa: E402

AR = W / H  # 16/9

# cor solida unica por quadro na "mascara" — usada so para medir os retangulos
PANEL_COLORS = [
    (230, 30, 30), (30, 170, 40), (40, 80, 230),
    (235, 185, 20), (180, 40, 200), (20, 200, 200),
]

# duracoes (s) dos movimentos de camera
T_OPEN = 0.9   # abre a pagina: pagina inteira -> 1o quadro
T_TRANS = 0.7  # troca de quadro: afasta e encaixa no proximo
T_CLOSE = 0.9  # fecha a pagina: ultimo quadro -> pagina inteira
TRANS_BUMP = 0.22  # quanto a camera "afasta" no meio da troca de quadro
HOLD_OUT = 1.06    # quadro comeca 6% mais aberto e empurra (push-in suave)


# ---------------------------------------------------------------------------
# geometria da camera (puro)
# ---------------------------------------------------------------------------
def frame_window(rect, page_w, page_h, pad=0.06, ar=AR):
    """Menor janela 16:9 que cobre o quadro `rect` (com folga `pad`), centrada
    no quadro e contida na pagina. Retorna (cx, cy, cw) — a altura e cw/ar."""
    x, y, w, h = rect
    cx, cy = x + w / 2, y + h / 2
    ew, eh = w * (1 + 2 * pad), h * (1 + 2 * pad)
    cw = max(ew, eh * ar)
    cw = min(cw, page_w)
    ch = cw / ar
    if ch > page_h:
        ch = page_h
        cw = min(ch * ar, page_w)
        ch = cw / ar
    cx = min(max(cx, cw / 2), page_w - cw / 2)
    cy = min(max(cy, ch / 2), page_h - ch / 2)
    return (cx, cy, cw)


def wide_window(page_w, page_h, ar=AR):
    """Janela 'pagina inteira' — a mais aberta possivel (largura cheia)."""
    cw = page_w
    cy = min(max(page_h / 2, (cw / ar) / 2), page_h - (cw / ar) / 2)
    return (page_w / 2, cy, cw)


def zoom_window(win, k, page_w):
    """Mesma janela, `k`x mais aberta (k>1) ou fechada (k<1)."""
    cx, cy, cw = win
    return (cx, cy, min(cw * k, page_w))


def window_at(a, b, u, bump=0.0):
    """Interpola a janela de `a`->`b` no instante u in [0,1] com smoothstep.
    `bump` afasta a camera no meio do trajeto (sin) e volta — endpoints exatos."""
    s = u * u * (3 - 2 * u)
    cx = a[0] + (b[0] - a[0]) * s
    cy = a[1] + (b[1] - a[1]) * s
    cw = (a[2] + (b[2] - a[2]) * s) * (1 + bump * math.sin(math.pi * u))
    return (cx, cy, cw)


def _filter(a, b, dur, bump=0.0):
    """String -vf: crop animado (a->b) + scale para 16:9. Espelha window_at em
    sintaxe de expressao do ffmpeg (variavel de tempo `t`)."""
    cx0, cy0, cw0 = a
    cx1, cy1, cw1 = b
    T = max(float(dur), 1e-3)
    u = f"clip(t/{T:.4f},0,1)"
    s = f"({u})*({u})*(3-2*({u}))"
    size = f"(({cw0:.2f})+(({cw1:.2f})-({cw0:.2f}))*{s})"
    if bump:
        size = f"({size}*(1+{bump:.3f}*sin(PI*({u}))))"
    cx = f"(({cx0:.2f})+(({cx1:.2f})-({cx0:.2f}))*{s})"
    cy = f"(({cy0:.2f})+(({cy1:.2f})-({cy0:.2f}))*{s})"
    return (f"crop=w='min({size}\\,in_w)':h='ow/{AR:.6f}':"
            f"x='clip({cx}-ow/2\\,0\\,in_w-ow)':y='clip({cy}-oh/2\\,0\\,in_h-oh)',"
            f"scale={W}:{H},setsar=1,fps={FPS}")


# ---------------------------------------------------------------------------
# medicao dos quadros na pagina (mascara de cores)
# ---------------------------------------------------------------------------
def _mask_style():
    rules = [".panel-img,.narracao,.fala,.sfx{display:none!important}",
             ".panel{border:0!important}"]
    for i, (r, g, b) in enumerate(PANEL_COLORS, start=1):
        rules.append(f".quadros .panel:nth-child({i}){{background:rgb({r},{g},{b})!important}}")
    return "<style>" + "".join(rules) + "</style>"


def render_mask(page_html, out_png, w, h):
    """Re-renderiza a MESMA pagina pintando cada quadro de uma cor solida
    (mesmo CSS/grade), para medir os retangulos com precisao."""
    with open(page_html) as f:
        html = f.read()
    html = html.replace("</head>", _mask_style() + "</head>")
    mask_html = out_png + ".html"
    with open(mask_html, "w") as f:
        f.write(html)
    render_html_to_png(mask_html, out_png, w, h)
    return out_png


def detect_rects(mask_png):
    """Retorna [(x,y,w,h), ...] na ordem de leitura (PANEL_COLORS) lendo a
    bounding box de cada cor solida na mascara."""
    import cv2
    import numpy as np
    img = cv2.imread(mask_png)
    if img is None:
        raise ValueError(f"mascara nao carregou: {mask_png}")
    rgb = img[:, :, ::-1].astype(int)
    rects = []
    for (r, g, b) in PANEL_COLORS:
        diff = np.abs(rgb - np.array([r, g, b])).sum(axis=2)
        ys, xs = np.where(diff < 60)
        if len(xs) == 0:
            raise ValueError("cor de quadro ausente na mascara — layout incompativel")
        rects.append((int(xs.min()), int(ys.min()),
                      int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)))
    return rects


# ---------------------------------------------------------------------------
# renderizacao dos segmentos (ffmpeg)
# ---------------------------------------------------------------------------
def _seg_clip(page_png, a, b, dur, out_mp4, bump=0.0, audio=None):
    """Um segmento de camera sobre a pagina: anima a janela a->b por `dur` s.
    Com `audio` (wav) usa a faixa; senao gera silencio. Encode identico ao
    _title_clip para permitir concat -c copy."""
    vf = _filter(a, b, dur, bump)
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error",
           "-framerate", str(FPS), "-loop", "1", "-t", f"{dur:.3f}", "-i", page_png]
    if audio:
        cmd += ["-i", audio]
    else:
        cmd += ["-f", "lavfi", "-t", f"{dur:.3f}",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += ["-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out_mp4]
    subprocess.run(cmd, check=True)
    return out_mp4


# ---------------------------------------------------------------------------
# montagem da pagina de quadrinho (reusa a skill `quadrinho`)
# ---------------------------------------------------------------------------
_TEMPLATE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "quadrinho", "templates", "grade-uniforme"))


def _page_roteiro(roteiro, pg):
    """Converte uma pagina do roteiro de motioncomic no roteiro que a skill
    `quadrinho` espera. O personagem (`quem`/protagonista) e dobrado no prompt
    de cada quadro; a fala-dict vira string (so o texto vai pro balao)."""
    personagem = roteiro.get("personagem", "")
    paineis = []
    for panel in pg["paineis"]:
        who = panel["quem"] if "quem" in panel else personagem
        who = (who or "").strip().rstrip(".")
        scene = panel["prompt"].strip().rstrip(".")
        qp = {"prompt": f"{who}, {scene}" if who else scene}
        if panel.get("narracao"):
            qp["narracao"] = panel["narracao"]
        if panel.get("sfx"):
            qp["sfx"] = panel["sfx"]
        if panel.get("fala"):
            qp["fala"] = panel["fala"]["texto"]
        paineis.append(qp)
    return {"id": f"{roteiro['id']}-pg{pg['n']:02d}", "titulo": pg.get("titulo", ""),
            "personagem_aparencia": "", "paineis": paineis}


def build_video_travel(roteiro, out_dir="output", voice="bella", model="flux2-klein",
                       arte="manga", intro=True):
    """Forma B: pagina de papel + camera viajando. Cada pagina precisa de 6
    paineis (grade 2x3). Saida em <out_dir>/<id>/<id>-travel.mp4."""
    import html as _h
    import json
    from build_pagina import build_pagina

    with open(os.path.join(_TEMPLATE_DIR, "meta.json")) as f:
        meta = json.load(f)
    PW, PH = meta["width"], meta["height"]

    base = os.path.join(out_dir, roteiro["id"])
    clips_dir = os.path.join(base, "clips")
    pages_dir = os.path.join(base, "pages")
    voz_dir = os.path.join(base, "voz")
    for d in (clips_dir, pages_dir, voz_dir):
        os.makedirs(d, exist_ok=True)
    clips = []

    if intro:
        tc = os.path.join(clips_dir, "000-intro.mp4")
        _title_clip(f'<small>{_h.escape(roteiro.get("subtitulo", "MOTION COMIC"))}</small>'
                    + _h.escape(roteiro["titulo"]), tc, secs=2.2)
        clips.append(tc)

    pages = roteiro["paginas"]
    for pgi, pg in enumerate(pages):
        pn = pg["n"]
        # 1) monta a pagina de papel (grade 2x3, narracao/balao/sfx impressos)
        page_png = build_pagina(_page_roteiro(roteiro, pg), _TEMPLATE_DIR,
                                arte=arte, out_dir=pages_dir, model=model)
        page_html = os.path.join(os.path.dirname(page_png), "pagina.html")
        mask_png = os.path.join(os.path.dirname(page_png), "mask.png")
        render_mask(page_html, mask_png, PW, PH)
        rects = detect_rects(mask_png)
        frames = [frame_window(r, PW, PH) for r in rects]
        wide = wide_window(PW, PH)

        # 2) narracao por quadro
        wavs, durs = [], []
        for idx, panel in enumerate(pg["paineis"], start=1):
            wav = os.path.join(voz_dir, f"p{pn:02d}q{idx}.wav")
            if not os.path.exists(wav):
                say(_spoken(panel), wav, voice=voice)
            wavs.append(wav)
            durs.append(duration(wav))

        # 3) titulo + abertura da pagina
        tc = os.path.join(clips_dir, f"{pn:02d}0-titulo.mp4")
        _title_clip(f'<small>PAGINA {pn}</small>{_h.escape(pg.get("titulo", ""))}', tc, secs=1.6)
        clips.append(tc)
        opn = os.path.join(clips_dir, f"{pn:02d}1-abre.mp4")
        _seg_clip(page_png, wide, frames[0], T_OPEN, opn)
        clips.append(opn)

        # 4) mergulha em cada quadro; afasta e encaixa no proximo
        for i in range(len(frames)):
            hold = os.path.join(clips_dir, f"{pn:02d}q{i+1}-hold.mp4")
            _seg_clip(page_png, zoom_window(frames[i], HOLD_OUT, PW), frames[i],
                      durs[i], hold, audio=wavs[i])
            clips.append(hold)
            if i < len(frames) - 1:
                tr = os.path.join(clips_dir, f"{pn:02d}q{i+1}-trans.mp4")
                _seg_clip(page_png, frames[i], frames[i + 1], T_TRANS, tr, bump=TRANS_BUMP)
                clips.append(tr)

        # 5) fecha a pagina (zoom-out total) se houver proxima
        if pgi < len(pages) - 1:
            cl = os.path.join(clips_dir, f"{pn:02d}9-fecha.mp4")
            _seg_clip(page_png, frames[-1], wide, T_CLOSE, cl)
            clips.append(cl)

    listfile = os.path.join(base, "concat-travel.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    out_mp4 = os.path.join(base, f"{roteiro['id']}-travel.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", listfile, "-c", "copy", out_mp4], check=True)
    return out_mp4
