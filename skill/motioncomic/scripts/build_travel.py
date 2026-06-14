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

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _deps  # noqa: E402
sys.path.insert(0, _deps.scripts("folder"))
sys.path.insert(0, _deps.scripts("quadrinho"))
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
HOLD_FILL = 0.82   # MERGULHO MINIMO: todo hold ocupa no maximo 82% da pagina.
                   # Sem isso, quadro grande (ex.: p1/p2 2x2 do manga-dinamico)
                   # gera janela ~ pagina inteira -> o "mergulho" nele nao tem
                   # movimento e a navegacao "pula"/nao fica clara. O cap aperta
                   # no centro do quadro, garantindo um close legivel por quadro.
T_FULL = 1.7       # duracao do plano da PRANCHA INTEIRA (abre/fecha a pagina)
FULLPAGE_FILL = 0.88  # a prancha inteira ocupa 88% do quadro -> margem ao redor
                      # (sem a margem, a borda #111 da pagina some na tarja preta)
CTA_NARR = "Aprenda mais em inema ponto clube."  # CTA padrao inema.club


# ---------------------------------------------------------------------------
# geometria da camera (puro)
# ---------------------------------------------------------------------------
def frame_window(rect, page_w, page_h, pad=0.0, ar=AR, max_w=None):
    """Janela 16:9 do MERGULHO num quadro — a MENOR que COBRE o quadro inteiro.
    LE A FORMA de cada quadro e se posiciona: quadro largo-e-baixo e enquadrado
    pela LARGURA (ganha contexto vertical); quadro estreito-e-alto, pela ALTURA
    (ganha contexto lateral); quadro quase-quadrado fica justo, com so slivers
    dos vizinhos. Isso torna a camera flexivel a layouts variaveis (ex.: a grade
    assimetrica do manga-dinamico) sem cortar quadros largos. Centrada no quadro
    e contida na pagina; quadro maior que a pagina e clampado (corte inevitavel).
    `max_w` (opcional) limita a largura da janela -> garante um MERGULHO MINIMO:
    quadros grandes (cuja janela cobriria ~ a pagina toda) sao apertados no
    centro, virando um close legivel em vez de um plano quase parado.
    Retorna (cx, cy, cw) — a altura e cw/ar."""
    x, y, w, h = rect
    cx, cy = x + w / 2, y + h / 2
    ew, eh = w * (1 + 2 * pad), h * (1 + 2 * pad)
    cw = min(max(ew, eh * ar), page_w)   # cobre largura E altura, em 16:9
    ch = cw / ar
    if ch > page_h:
        ch = page_h
        cw = min(ch * ar, page_w)
        ch = cw / ar
    if max_w is not None and cw > max_w:   # mergulho minimo: aperta no centro
        cw = max_w
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
    # u in [0,1]. NAO usar clip(): essa build do ffmpeg nao tem a funcao e o
    # crop silenciosamente abre pra in_w. min(max(...)) faz o mesmo papel.
    u = f"min(max(t/{T:.4f},0),1)"
    s = f"({u})*({u})*(3-2*({u}))"
    size = f"(({cw0:.2f})+(({cw1:.2f})-({cw0:.2f}))*{s})"
    if bump:
        size = f"({size}*(1+{bump:.3f}*sin(PI*({u}))))"
    cx = f"(({cx0:.2f})+(({cx1:.2f})-({cx0:.2f}))*{s})"
    cy = f"(({cy0:.2f})+(({cy1:.2f})-({cy0:.2f}))*{s})"
    # largura e altura auto-contidas (so iw/ih) — NAO usar ow/oh: dentro da
    # propria expressao o ffmpeg da o valor antigo (in_w) e o crop sai errado.
    # Virgulas ficam DENTRO de aspas simples -> nao escapar com backslash.
    w = f"min({size},in_w)"
    h = f"(({w})/{AR:.6f})"
    return (f"crop=w='{w}':h='{h}':"
            f"x='min(max({cx}-({w})/2,0),in_w-({w}))':"
            f"y='min(max({cy}-({h})/2,0),in_h-({h}))',"
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


def _fullpage_clip(page_png, dur, out_mp4, audio=None):
    """Plano da PRANCHA INTEIRA (letterbox) — abre e fecha a pagina mostrando-a
    por completo. Com `audio` (ex.: abertura narrada) usa a faixa."""
    bw, bh = int(W * FULLPAGE_FILL), int(H * FULLPAGE_FILL)
    vf = (f"scale={bw}:{bh}:force_original_aspect_ratio=decrease,"
          f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={FPS}")
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


def _cta_clip(out_mp4, voice="bella", narr=CTA_NARR):
    """Cartao final padrao INEMA.CLUB (dark premium ambar) + locucao."""
    png = out_mp4 + ".png"
    html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
            '*{margin:0;padding:0}body{width:1280px;height:720px;background:#0c0c10;'
            'display:flex;flex-direction:column;align-items:center;justify-content:center;'
            'font-family:"Arial Black",Arial,sans-serif}'
            '.k{color:#9a9aa6;font-size:24px;letter-spacing:.32em;margin-bottom:16px}'
            '.b{color:#E2A23B;font-size:96px;font-weight:900;letter-spacing:.01em}'
            '.t{color:#e9e9ee;font-size:28px;margin-top:22px;letter-spacing:.04em}'
            '</style></head><body>'
            '<div class="k">INEMA</div><div class="b">inema.club</div>'
            '<div class="t">aprenda &middot; crie &middot; compartilhe</div></body></html>')
    hp = out_mp4 + ".html"
    with open(hp, "w") as f:
        f.write(html)
    render_html_to_png(hp, png, W, H)
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-framerate", str(FPS), "-loop", "1"]
    if narr:
        wav = out_mp4 + ".wav"
        say(narr, wav, voice=voice)
        dur = duration(wav) + 0.8
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-i", wav,
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}", "-af", "apad"]
    else:
        dur = 3.0
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-f", "lavfi", "-t", f"{dur:.3f}",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-t", f"{dur:.3f}", out_mp4]
    subprocess.run(cmd, check=True)
    return out_mp4


def _split_wav(wav, t, out_a, out_b):
    """Corta `wav` em [0,t] (out_a) e [t,fim] (out_b) — p/ a narracao atravessar
    o cartao da pagina e a prancha inteira (formato C)."""
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", wav, "-t", f"{t:.3f}",
                    "-ar", "44100", "-ac", "2", out_a], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", wav,
                    "-ar", "44100", "-ac", "2", out_b], check=True)
    return out_a, out_b


def _page_card_clip(pn, titulo, out_mp4, audio=None, secs=T_FULL):
    """Cartao de entrada da pagina ('PAGINA n / titulo'), mesmo estilo do cartao
    de episodio. Com `audio` toca a 1a parte da chamada narrada."""
    import html as _h
    png = out_mp4 + ".png"
    html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
            '*{margin:0;padding:0}body{width:1280px;height:720px;background:#10141c;'
            'display:flex;align-items:center;justify-content:center;'
            'font-family:"Arial Black",Arial,sans-serif}'
            '.t{color:#fff;font-size:56px;font-weight:900;text-align:center;max-width:84%;line-height:1.18}'
            '.t small{display:block;color:#ffd23f;font-size:24px;letter-spacing:.2em;margin-bottom:18px}'
            '</style></head><body><div class="t"><small>PAGINA __N__</small>__T__</div></body></html>'
            ).replace("__N__", str(pn)).replace("__T__", _h.escape(titulo or ""))
    hp = out_mp4 + ".html"
    with open(hp, "w") as f:
        f.write(html)
    render_html_to_png(hp, png, W, H)
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-framerate", str(FPS), "-loop", "1"]
    if audio:
        dur = duration(audio)
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-i", audio,
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}", "-af", "apad"]
    else:
        dur = secs
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-f", "lavfi", "-t", f"{dur:.3f}",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-t", f"{dur:.3f}", out_mp4]
    subprocess.run(cmd, check=True)
    return out_mp4


# ---------------------------------------------------------------------------
# montagem da pagina de quadrinho (reusa a skill `quadrinho`)
# ---------------------------------------------------------------------------
_TEMPLATE_DIR = os.path.join(_deps.templates("quadrinho"), "manga-dinamico")


def _textless(page_png):
    """A cópia SEM texto, irmã do pagina.png (emitida pelo build_pagina)."""
    return os.path.join(os.path.dirname(page_png), "pagina-textless.png")


def _page_roteiro(roteiro, pg):
    """Converte uma pagina do roteiro de motioncomic no roteiro que a skill
    `quadrinho` espera. O personagem (`quem`/protagonista) e dobrado no prompt
    de cada quadro; a fala-dict vira string (so o texto vai pro balao)."""
    personagem = roteiro.get("personagem", "")
    canon = {e["nome"].lower(): e["aparencia"] for e in roteiro.get("elementos", [])}
    paineis = []
    for panel in pg["paineis"]:
        who = panel["quem"] if "quem" in panel else personagem
        who = (who or "").strip().rstrip(".")
        scene = panel["prompt"].strip().rstrip(".")
        prompt = f"{who}, {scene}" if who else scene
        # canon visual: dobra a aparencia travada dos elementos que o quadro USA
        for u in (panel.get("usa") or []):
            ap = canon.get(str(u).lower())
            if ap:
                prompt = f"{prompt}, {ap}"
        qp = {"prompt": prompt}
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
                       arte="manga", intro=True, template_dir=None,
                       moldura="dark", kicker=None, accent="#b08900", generate_fn=None,
                       ancoras=None, protagonista_id=None):
    """Forma B: pagina de papel + camera viajando. Cada pagina precisa de 6
    paineis. `template_dir` escolhe o layout da prancha (default **manga-dinamico**
    — quadros de tamanhos/posicoes variaveis; passe .../grade-uniforme p/ a 2x3).
    A camera LE o layout real (mascara) e se posiciona por quadro, entao qualquer
    grade de 6 funciona. Cada pagina ABRE mostrando a prancha inteira; na 1a, a
    narracao comeca dizendo o assunto (`roteiro['abertura']`); o video FECHA na
    prancha inteira e num CTA inema.club. Saida em <out_dir>/<id>/<id>-travel.mp4."""
    import html as _h
    import json
    from build_pagina import build_pagina

    tdir = template_dir or _TEMPLATE_DIR
    with open(os.path.join(tdir, "meta.json")) as f:
        meta = json.load(f)
    PW, PH = meta["width"], meta["height"]

    base = os.path.join(out_dir, roteiro["id"])
    clips_dir = os.path.join(base, "clips")
    pages_dir = os.path.join(base, "pages")
    voz_dir = os.path.join(base, "voz")
    for d in (clips_dir, pages_dir, voz_dir):
        os.makedirs(d, exist_ok=True)
    clips = []

    abertura = (roteiro.get("abertura") or "").strip()
    if intro:
        tc = os.path.join(clips_dir, "000-intro.mp4")
        # o card do assunto JA narra o gancho em t=0 (abertura). Sem abertura,
        # fica o card silencioso de 2.2s como antes.
        _title_clip(f'<small>{_h.escape(roteiro.get("subtitulo", "MOTION COMIC"))}</small>'
                    + _h.escape(roteiro["titulo"]), tc, secs=2.2,
                    audio=(abertura or None), voice=voice)
        clips.append(tc)

    pages = roteiro["paginas"]
    last_page_png = None
    for pgi, pg in enumerate(pages):
        pn = pg["n"]
        # 1) monta a pagina de papel; pagina.png (COM texto) = carrossel,
        #    pagina-textless.png = sobre a qual a CAMERA viaja (voz-off).
        page_png = build_pagina(_page_roteiro(roteiro, pg), tdir,
                                arte=arte, out_dir=pages_dir, model=model,
                                moldura=moldura, kicker=kicker, accent=accent,
                                generate_fn=generate_fn,
                                ancoras=ancoras, protagonista_id=protagonista_id)
        travel_png = _textless(page_png)
        last_page_png = travel_png
        page_html = os.path.join(os.path.dirname(page_png), "pagina.html")
        mask_png = os.path.join(os.path.dirname(page_png), "mask.png")
        render_mask(page_html, mask_png, PW, PH)
        rects = detect_rects(mask_png)
        frames = [frame_window(r, PW, PH, max_w=HOLD_FILL * PW) for r in rects]
        # mapeamento claro: cada quadro detectado casa 1:1 com um painel do
        # roteiro (mesma ordem). Se divergir, a camera mergulharia no quadro
        # errado durante a narracao errada -> falha antes de renderizar.
        if len(frames) != len(pg["paineis"]):
            raise ValueError(
                f"pagina {pn}: {len(frames)} quadros detectados != "
                f"{len(pg['paineis'])} paineis no roteiro — layout incompativel")

        # 2) narracao por quadro
        wavs, durs = [], []
        for idx, panel in enumerate(pg["paineis"], start=1):
            wav = os.path.join(voz_dir, f"p{pn:02d}q{idx}.wav")
            if not os.path.exists(wav):
                say(_spoken(panel), wav, voice=voice)
            wavs.append(wav)
            durs.append(duration(wav))

        # 3) FORMATO C: a CHAMADA narrada COMECA no cartao "PAGINA n / titulo" e
        #    TERMINA na PRANCHA INTEIRA — a mesma fala atravessa cartao -> prancha.
        #    (abertura ja foi narrada no card de intro em t=0; aqui so a chamada da pagina)
        chamada = (pg.get("chamada") or "").strip()
        intro_txt = chamada
        card = os.path.join(clips_dir, f"{pn:02d}0-cartao.mp4")
        est = os.path.join(clips_dir, f"{pn:02d}1-prancha.mp4")
        if intro_txt:
            cwav = os.path.join(voz_dir, f"chamada{pn:02d}.wav")
            if not os.path.exists(cwav):
                say(intro_txt, cwav, voice=voice)
            dtot = duration(cwav)
            card_dur = min(2.2, dtot)
            if dtot - card_dur > 0.2:          # divide a fala: cartao -> prancha
                pa = os.path.join(voz_dir, f"chamada{pn:02d}a.wav")
                pb = os.path.join(voz_dir, f"chamada{pn:02d}b.wav")
                _split_wav(cwav, card_dur, pa, pb)
                _page_card_clip(pn, pg.get("titulo", ""), card, audio=pa)
                _fullpage_clip(travel_png, duration(pb) + 0.4, est, audio=pb)
            else:                               # fala curta: tudo no cartao
                _page_card_clip(pn, pg.get("titulo", ""), card, audio=cwav)
                _fullpage_clip(travel_png, T_FULL, est)
        else:
            _page_card_clip(pn, pg.get("titulo", ""), card)
            _fullpage_clip(travel_png, T_FULL, est)
        clips.append(card)
        clips.append(est)

        # 4) mergulha em cada quadro; afasta e encaixa no proximo.
        #    a transicao termina JA no ponto onde o proximo hold comeca
        #    (zoom_window do proximo quadro) -> sem pulo entre trans e hold.
        for i in range(len(frames)):
            hold = os.path.join(clips_dir, f"{pn:02d}q{i+1}-hold.mp4")
            _seg_clip(travel_png, zoom_window(frames[i], HOLD_OUT, PW), frames[i],
                      durs[i], hold, audio=wavs[i])
            clips.append(hold)
            if i < len(frames) - 1:
                tr = os.path.join(clips_dir, f"{pn:02d}q{i+1}-trans.mp4")
                _seg_clip(travel_png, frames[i], zoom_window(frames[i + 1], HOLD_OUT, PW),
                          T_TRANS, tr, bump=TRANS_BUMP)
                clips.append(tr)

    # 5) FECHA mostrando a PRANCHA INTEIRA da ultima pagina
    if last_page_png:
        fim = os.path.join(clips_dir, "zz8-prancha-fim.mp4")
        _fullpage_clip(last_page_png, T_FULL, fim)
        clips.append(fim)
    # 6) CTA padrao inema.club (todos os nossos videos)
    cta = os.path.join(clips_dir, "zz9-cta.mp4")
    _cta_clip(cta, voice=voice)
    clips.append(cta)

    listfile = os.path.join(base, "concat-travel.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    out_mp4 = os.path.join(base, f"{roteiro['id']}-travel.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", listfile, "-c", "copy", out_mp4], check=True)
    return out_mp4
