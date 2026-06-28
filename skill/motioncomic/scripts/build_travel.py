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
TRANS_BUMP = 0.0   # troca DIRECIONAL: pan no zoom apertado, sem afastar (sbum)
HOLD_OUT = 1.06    # quadro comeca 6% mais aberto e empurra (push-in suave)
HOLD_FILL = 0.82   # MERGULHO MINIMO: todo hold ocupa no maximo 82% da pagina.
                   # Sem isso, quadro grande (ex.: p1/p2 2x2 do manga-dinamico)
                   # gera janela ~ pagina inteira -> o "mergulho" nele nao tem
                   # movimento e a navegacao "pula"/nao fica clara. O cap aperta
                   # no centro do quadro, garantindo um close legivel por quadro.
T_FULL = 1.7       # duracao do plano da PRANCHA INTEIRA (abre/fecha a pagina)
FULLPAGE_FILL = 0.88  # a prancha inteira ocupa 88% do quadro -> margem ao redor
                      # (sem a margem, a borda #111 da pagina some na tarja preta)
# --- viagem CONTINUA (sem cartao nem prancha-letterbox; tudo full-bleed) ---
HOLD_EASE = 0.55   # ASSENTAR: o hold chega ao quadro nestes ~0.55s e ENTAO PARA
                   # (camera estatica pelo resto da narracao). "chega e para".
OPEN_OUT = 1.55    # abertura/fechamento full-bleed: enquadramento do quadro ~55%
                   # mais aberto (estabelece o quadro sem sair pra pagina inteira).
T_OPEN_MIN = 0.9   # duracao minima do mergulho de abertura de cada pagina
T_TURN = 0.8       # VIRADA DE PAGINA: dissolve EM MOVIMENTO no enquadramento APERTADO
                   # (cada prancha segue derivando durante o cross-dissolve; nao congela)
# --- pagina inteira na "mesa" + ENQUADRAMENTO POR LINHA (camera de leitura) ---
DESK_FILL = 0.9    # a folha ocupa 90% da altura do quadro 16:9; resto = mesa (margem)
CLOSE_CAP = 0.62   # zoom da linha: largura <= 62% da pagina (close legivel por linha)
ROW_PULL = 1.7     # recuo (zoom-out) na troca de LINHA: largura no meio do trajeto
T_ROW = 1.0        # duracao da troca de linha (recuo + diagonal + mergulho, 1 clipe)
T_DIVE = 2.4       # mergulho suave da PAGINA INTEIRA ate o 1o quadro (sem 'pulo')
T_PAGE_END = 1.0   # segura na PAGINA INTEIRA no fim (titulo) antes de virar a pagina
# --- MODELO ZOOM-LENTO-CONTINUO (v2) — substitui o "rajada + congela + dissolve parado" ---
# A camera NUNCA vai a pagina inteira nem recua: ENTRA ~ENTRY_OUT mais aberta que o 1o quadro
# e assenta; em cada quadro da um push-in MUITO lento durante TODA a narracao (jamais congela);
# entre quadros faz um GLIDE lento e plano (pan na linha; diagonal SEM recuo na troca de linha).
# As juncoes ficam em velocidade ~0 (eased) dos dois lados -> continuo, sem pulo e sem freeze.
ENTRY_OUT = 1.16    # cada pagina ENTRA este tanto mais aberta que o 1o quadro e assenta nele
DWELL_PUSH = 1.06   # push-in lento por quadro: comeca DWELL_PUSH x e fecha em 1.0x na narracao
T_GLIDE = 1.4       # glide lento entre quadros da MESMA linha (pan puro, suavizado)
T_GLIDE_ROW = 2.2   # glide da TROCA de linha (diagonal maior) — mais longo p/ manter calmo, SEM recuo
TURN_DRIFT = 0.06   # deriva que cada prancha mantem DURANTE o dissolve da troca (nao congela)
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
    Troca DIRECIONAL: cx,cy fazem o pan; a LARGURA nunca afasta. No meio do
    trajeto a janela fica no zoom MAIS apertado (min das larguras) e relaxa pros
    endpoints exatos -> pan no close, sem o 'sbum' de voltar pra pagina. cw nunca
    passa de max(a_w, b_w). `bump` mantido por compat (default 0, sem efeito)."""
    s = u * u * (3 - 2 * u)
    cx = a[0] + (b[0] - a[0]) * s
    cy = a[1] + (b[1] - a[1]) * s
    lin = a[2] + (b[2] - a[2]) * s          # largura linear (endpoints exatos)
    cw = min(a[2], b[2]) + (lin - min(a[2], b[2])) * (1 - math.sin(math.pi * u))
    return (cx, cy, cw)


def _filter(a, b, dur, ease=None, straight=False, pull_cw=None):
    """String -vf: crop animado (a->b) + scale para 16:9. Espelha window_at em
    sintaxe de expressao do ffmpeg (variavel de tempo `t`). `ease` (s) conclui o
    movimento ANTES do fim do clipe; para t>ease a janela fica PARADA em b (a
    camera assenta no quadro). Default ease=dur -> move o clipe inteiro.
    Largura: `pull_cw` = ABRE no meio ate `pull_cw` e fecha (recuo da troca de
    linha, num movimento so); `straight` = MONOTONICA (abrir/fechar); default =
    aperta no meio (pan colado, sem afastar)."""
    cx0, cy0, cw0 = a
    cx1, cy1, cw1 = b
    T = max(float(ease if ease else dur), 1e-3)
    # u in [0,1] em [0,T]; para t>T, u=1 -> janela ESTATICA em b (assenta).
    # NAO usar clip(): essa build do ffmpeg nao tem a funcao e o crop
    # silenciosamente abre pra in_w. min(max(...)) faz o mesmo papel.
    u = f"min(max(t/{T:.4f},0),1)"
    s = f"({u})*({u})*(3-2*({u}))"
    # espelha window_at: largura linear, mas apertada pro min no meio do trajeto
    # (pan no close, sem afastar). min(a_w,b_w) e constante.
    wmin = min(cw0, cw1)
    lin = f"(({cw0:.2f})+(({cw1:.2f})-({cw0:.2f}))*{s})"
    if pull_cw is not None:                       # recuo: abre no meio (pico=pull_cw) e fecha
        mid = (cw0 + cw1) / 2.0
        size = f"({lin}+({float(pull_cw) - mid:.2f})*sin(PI*({u})))"
    elif straight:
        size = lin                                # zoom monotonico (abrir/fechar)
    else:                                         # pan colado: aperta no meio, sem afastar
        size = f"(({wmin:.2f})+({lin}-({wmin:.2f}))*(1-sin(PI*({u}))))"
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
    # esconde overlays E o cabecalho (kicker/titulo). O cabecalho via
    # `visibility:hidden` (NAO display:none) p/ NAO tirar o espaco dele e deslocar
    # os quadros — so impede o kicker (cor do accent) de poluir a deteccao de cor.
    rules = [".panel-img,.narracao,.fala,.sfx{display:none!important}",
             ".cabecalho{visibility:hidden!important}",
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
def _seg_clip(page_png, a, b, dur, out_mp4, ease=None, straight=False, pull_cw=None, audio=None):
    """Um segmento de camera sobre a pagina: anima a janela a->b por `dur` s.
    `ease` (s) faz a camera ASSENTAR (move ate `ease` e para parada). `straight`
    = zoom monotonico; `pull_cw` = recuo que abre no meio (troca de linha, 1 clipe).
    Com `audio` (wav) usa a faixa; senao silencio. Encode identico (concat -c copy)."""
    vf = _filter(a, b, dur, ease=ease, straight=straight, pull_cw=pull_cw)
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


def _pageturn_clip(plate_a, win_a, plate_b, win_b, dur, out_mp4, drift=TURN_DRIFT, page_w=None):
    """VIRADA DE PAGINA: cross-dissolve EM MOVIMENTO no enquadramento APERTADO. `win_a`
    e a janela final (ultimo quadro) da pagina i; `win_b` a janela de ENTRADA da i+1.
    Cada prancha CONTINUA derivando durante o dissolve (a i fechando um tico, a i+1
    assentando) -> a troca nunca 'congela'. Apertado (nao a pagina inteira) -> troca pouca
    area de uma vez, le como fluido. Silenciosa. Encode identico aos demais (concat -c copy)."""
    pw = page_w or max(win_a[2], win_b[2])
    a0, a1 = win_a, zoom_window(win_a, 1 - drift, pw)     # i segue fechando um tico
    b0, b1 = zoom_window(win_b, 1 + drift, pw), win_b     # i+1 segue assentando
    va = _filter(a0, a1, dur, straight=True)              # prancha i deriva (nao estatica)
    vb = _filter(b0, b1, dur, straight=True)              # prancha i+1 deriva
    fc = (f"[0:v]{va}[a];[1:v]{vb}[b];"
          f"[a][b]xfade=transition=fade:duration={dur:.3f}:offset=0,"
          f"format=yuv420p[v]")
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error",
           "-framerate", str(FPS), "-loop", "1", "-t", f"{dur:.3f}", "-i", plate_a,
           "-framerate", str(FPS), "-loop", "1", "-t", f"{dur:.3f}", "-i", plate_b,
           "-f", "lavfi", "-t", f"{dur:.3f}",
           "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
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


def _desk(plate_png, out_png, fill=DESK_FILL):
    """Compoe a prancha numa 'mesa' (fundo escuro com brilho/sombra + margem) num
    quadro 16:9, para a camera poder ABRIR na PAGINA INTEIRA e mergulhar nela com
    zoom continuo — um crop nao mostra uma pagina retrato inteira em 16:9 sem isso.
    Retorna (out_png, ox, oy, CW, CH): offset da pagina no composto e o tamanho."""
    from PIL import Image, ImageDraw, ImageFilter
    page = Image.open(plate_png).convert("RGB")
    pw, ph = page.size
    CH = int(round(ph / fill))
    CW = int(round(CH * AR))
    if CW < pw:                              # pagina larga demais: ajusta pela largura
        CW = int(round(pw / fill)); CH = int(round(CW / AR))
    ox, oy = (CW - pw) // 2, (CH - ph) // 2
    canvas = Image.new("RGB", (CW, CH), (12, 12, 16))
    glow = Image.new("L", (CW, CH), 0)       # brilho radial suave atras da pagina
    ImageDraw.Draw(glow).ellipse(
        [ox - pw * 0.12, oy - ph * 0.10, ox + pw * 1.12, oy + ph * 1.10], fill=80)
    glow = glow.filter(ImageFilter.GaussianBlur(max(CW, CH) // 16))
    canvas = Image.composite(Image.new("RGB", (CW, CH), (38, 38, 50)), canvas, glow)
    sh = Image.new("L", (CW, CH), 0)         # sombra projetada da pagina
    dy = int(ph * 0.012); m = int(ph * 0.02)
    ImageDraw.Draw(sh).rectangle([ox - m, oy - m + dy, ox + pw + m, oy + ph + m + dy], fill=170)
    sh = sh.filter(ImageFilter.GaussianBlur(int(ph * 0.022)))
    canvas = Image.composite(Image.new("RGB", (CW, CH), (0, 0, 0)), canvas, sh)
    canvas.paste(page, (ox, oy))             # cola a pagina + borda fina
    ImageDraw.Draw(canvas).rectangle([ox, oy, ox + pw - 1, oy + ph - 1],
                                     outline=(64, 64, 78), width=2)
    canvas.save(out_png)
    return out_png, ox, oy, CW, CH


def _rows_of(rects):
    """Indice de LINHA de cada quadro (agrupa pelos y dos centros): permite afastar
    a camera SO na troca de linha (pulo vertical), mantendo pan colado na linha."""
    avg_h = sum(h for _, _, _, h in rects) / max(len(rects), 1)
    order = sorted(range(len(rects)), key=lambda i: rects[i][1] + rects[i][3] / 2)
    row, r, last = {}, 0, None
    for i in order:
        yc = rects[i][1] + rects[i][3] / 2
        if last is not None and yc - last > 0.4 * avg_h:
            r += 1
        row[i] = r; last = yc
    return row


def _row_windows(rects0, ox, oy, CW, CH, page_w, page_h):
    """Enquadramento POR LINHA (camera de leitura): cada quadro vira uma janela na
    MESMA altura/zoom da sua linha (cy e largura constantes na linha) -> deslize
    lateral vira PAN PURO; o zoom so muda na TROCA de linha. As janelas de quadro
    ficam CONTIDAS na pagina (nao na mesa) -> nunca mostram a margem preta no hold.
    Retorna (hwin, rows)."""
    rows = _rows_of(rects0)
    cen = [(x + ox + w / 2, y + oy + h / 2) for (x, y, w, h) in rects0]
    # area de ARTE (uniao dos quadros) no composto -> as janelas ficam contidas
    # AQUI, nunca na borda/gutter da pagina nem na mesa preta.
    ax0 = ox + min(x for x, y, w, h in rects0); ax1 = ox + max(x + w for x, y, w, h in rects0)
    ay0 = oy + min(y for x, y, w, h in rects0); ay1 = oy + max(y + h for x, y, w, h in rects0)
    row_cw, row_cy = {}, {}
    for rid in sorted(set(rows.values())):
        idxs = [i for i in range(len(rects0)) if rows[i] == rid]
        rh = max(rects0[i][3] for i in idxs)                       # altura dos quadros da linha
        row_cw[rid] = min(rh * AR, CLOSE_CAP * page_w, ax1 - ax0)  # zoom (largura) da linha
        row_cy[rid] = sum(cen[i][1] for i in idxs) / len(idxs)     # cy CONSTANTE na linha

    def clamp(cx, cy, cw):                       # contido na AREA DE ARTE
        cw = min(cw, ax1 - ax0); ch = min(cw / AR, ay1 - ay0); cw = ch * AR
        return (min(max(cx, ax0 + cw / 2), ax1 - cw / 2),
                min(max(cy, ay0 + ch / 2), ay1 - ch / 2), cw)
    hwin = [clamp(cen[i][0], row_cy[rows[i]], row_cw[rows[i]]) for i in range(len(rects0))]
    return hwin, rows, (ax0, ay0, ax1, ay1)


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


def _page_clips(desk_png, hwin, rows, durs, wavs, chamada_wav, clips_dir, pn, CW):
    """Camera de UMA pagina no modelo ZOOM-LENTO-CONTINUO. Retorna a lista de clipes:
      - ENTRADA: assenta de ENTRY_OUT ate ~o 1o quadro, narrando a chamada (sem full-page);
      - por quadro: push-in lento (DWELL_PUSH x -> 1.0x) durante TODA a narracao (sem freeze);
      - entre quadros: GLIDE lento e plano (pan na mesma linha; diagonal SEM recuo na troca
        de linha). As juncoes ficam em velocidade ~0 (eased) -> continuo, sem pulo."""
    clips = []
    n = len(hwin)
    entry_a = zoom_window(hwin[0], ENTRY_OUT, CW)              # entra um tico mais aberta
    entry_b = zoom_window(hwin[0], DWELL_PUSH, CW)             # e assenta no 1o quadro
    entry_dur = max(T_GLIDE, duration(chamada_wav)) if chamada_wav else T_GLIDE
    entry = os.path.join(clips_dir, f"{pn:02d}0-entra.mp4")
    _seg_clip(desk_png, entry_a, entry_b, entry_dur, entry, straight=True, audio=chamada_wav)
    clips.append(entry)
    for i in range(n):
        dwell = os.path.join(clips_dir, f"{pn:02d}q{i+1}-dwell.mp4")    # push-in lento na fala
        _seg_clip(desk_png, zoom_window(hwin[i], DWELL_PUSH, CW), hwin[i],
                  durs[i], dwell, straight=True, audio=wavs[i])         # ease=dur: move o clipe todo
        clips.append(dwell)
        if i < n - 1:
            glide = os.path.join(clips_dir, f"{pn:02d}q{i+1}-glide.mp4")
            tg = T_GLIDE if rows[i] == rows[i + 1] else T_GLIDE_ROW     # troca de linha = mais calma
            _seg_clip(desk_png, hwin[i], zoom_window(hwin[i + 1], DWELL_PUSH, CW),
                      tg, glide, straight=True)                         # pan/diagonal plana, SEM recuo
            clips.append(glide)
    return clips


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
    prev_desk, prev_last = None, None    # virada: dissolve EM MOVIMENTO, apertado
    for pgi, pg in enumerate(pages):
        pn = pg["n"]
        # 1) monta a pagina e compoe na 'mesa' (folha + margem) p/ a camera viajar nela.
        page_png = build_pagina(_page_roteiro(roteiro, pg), tdir,
                                arte=arte, out_dir=pages_dir, model=model,
                                moldura=moldura, kicker=kicker, accent=accent,
                                generate_fn=generate_fn,
                                ancoras=ancoras, protagonista_id=protagonista_id)
        plate = _textless(page_png)
        page_html = os.path.join(os.path.dirname(page_png), "pagina.html")
        mask_png = os.path.join(os.path.dirname(page_png), "mask.png")
        render_mask(page_html, mask_png, PW, PH)
        rects0 = detect_rects(mask_png)
        # cada quadro detectado casa 1:1 com um painel do roteiro (mesma ordem).
        if len(rects0) != len(pg["paineis"]):
            raise ValueError(
                f"pagina {pn}: {len(rects0)} quadros detectados != "
                f"{len(pg['paineis'])} paineis no roteiro — layout incompativel")
        desk_png = os.path.join(os.path.dirname(plate), "desk.png")
        desk_png, ox, oy, CW, CH = _desk(plate, desk_png)
        # ENQUADRAMENTO POR LINHA: zoom/altura constantes na linha (deslize vira pan puro).
        hwin, rows, _ = _row_windows(rects0, ox, oy, CW, CH, PW, PH)

        # 2) narracao por quadro + chamada da pagina
        wavs, durs = [], []
        for idx, panel in enumerate(pg["paineis"], start=1):
            wav = os.path.join(voz_dir, f"p{pn:02d}q{idx}.wav")
            if not os.path.exists(wav):
                say(_spoken(panel), wav, voice=voice)
            wavs.append(wav)
            durs.append(duration(wav))
        chamada = (pg.get("chamada") or "").strip()
        cwav = None
        if chamada:
            cwav = os.path.join(voz_dir, f"chamada{pn:02d}.wav")
            if not os.path.exists(cwav):
                say(chamada, cwav, voice=voice)

        # 3) VIRADA EM MOVIMENTO (apertada): ultimo quadro da pagina anterior -> a
        #    ENTRADA desta, com as duas pranchas derivando durante o dissolve.
        if prev_desk is not None:
            turn = os.path.join(clips_dir, f"{pn:02d}t-turn.mp4")
            _pageturn_clip(prev_desk, prev_last, desk_png,
                           zoom_window(hwin[0], ENTRY_OUT, CW), T_TURN, turn, page_w=CW)
            clips.append(turn)

        # 4) CAMINHO CONTINUO da pagina (entrada que assenta + push-in lento por quadro
        #    + glide lento ao proximo; sem full-page, sem freeze, sem recuo).
        clips += _page_clips(desk_png, hwin, rows, durs, wavs, cwav, clips_dir, pn, CW)
        prev_desk, prev_last = desk_png, hwin[-1]

    # 7) CTA inema.club (o hold na pagina grande da ultima pagina ja fechou o video)
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
