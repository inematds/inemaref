"""Diretor DETERMINISTICO da Forma C — gera `decupagem.json` + `miolo.movie.yaml`
(spec pixflow.movie/v1) a partir do `forma-c.json`, sem IA generativa.

CALMO por padrao (conteudo infantil): look `cinema-dramatico` (natural, discreto),
movimento suave e VARIADO por cena, 1 tomada por painel (sem clone) salvo quando
a energia/cortes pedem mais. parallax=0 (desenho). As transicoes ficam em `cut`
(fadeIn 0) p/ a trilha de narracao casar sem dessincronizar. As paletas mais
energeticas ("alta"/"acao") seguem disponiveis, mas NAO sao o default.

Uso: dirigir(stage_dir, energia="media")  ->  escreve os 2 arquivos no stage_dir.
"""
import json
import os
import subprocess
import sys
import unicodedata

import yaml

# Importa validador do mesmo pacote (scripts/)
sys.path.insert(0, os.path.dirname(__file__))
from visao_decupagem import validar_shots


def _dur(wav):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", wav], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _framing(z_to, y_to=0.42):
    return {"type": "framing", "easing": "ease_out",
            "from": {"zoom": 1.0, "at": [0.5, 0.5]},
            "to": {"zoom": z_to, "at": [0.5, y_to]}}


# Look CALMO/natural aceito pelo motor pixflow (skill/src/looks.js): e o
# DEFAULT_LOOK do engine — grain/vignette/chroma/bloom baixos, sem o peso do
# `acao-epico`. Adequado a series infantis suaves.
LOOK_CALMO = "cinema-dramatico"


def _gentil(i):
    """UMA camera gentil por painel, variada por indice p/ paineis seguidos
    diferirem (sem clone). Sempre suave: intensity <= 0.6, framing zoom <= 1.18,
    easing lento. NUNCA crash_zoom/whip_pan, nunca push forte do zoom 1.0."""
    return [
        {"type": "push_in", "intensity": 0.45, "easing": "ease_in_out"},
        {"type": "pan", "direction": "right", "intensity": 0.4, "easing": "ease_in_out"},
        {"type": "pull_out", "intensity": 0.45, "easing": "ease_out"},
        _framing(1.12, 0.46),
        {"type": "pan", "direction": "left", "intensity": 0.4, "easing": "ease_in_out"},
        _framing(1.18, 0.40),
    ][i % 6]


# --- camera por CONTEUDO (gramatica do pixflow-trailer/inteligencia-direcao) ---
def _norm(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


_KW_CLOSE = ("close", "rosto", "olho", "expressa", "sorriso", "lagrim", "bochech",
             "primeiro plano", "detalhe", "perto do rosto")
_KW_WIDE = ("amplo", "plano geral", "panorama", "ao longe", "paisagem", "vista",
            "horizonte", "tudo branco", "sitio coberto", "ao redor", "estabelec", "campo nevado")
_KW_ACAO = ("corre", "salta", "pula", "vento", "tempestade", "nevasca", "foge",
            "dispara", "uiva", "rajada", "girando", "atira")
_KW_MED = ("de corpo inteiro", "de pe", "os dois", "ao lado", "plano medio", "juntos")


def _classificar(cena):
    """Enquadramento do painel a partir do PROMPT (deterministico, sem IA):
    close | wide | acao | medio — base da escolha de camera por CONTEUDO."""
    t = _norm(cena)
    if any(k in t for k in _KW_CLOSE):
        return "close"
    if any(k in t for k in _KW_WIDE):
        return "wide"
    if any(k in t for k in _KW_ACAO):
        return "acao"
    if any(k in t for k in _KW_MED):
        return "medio"
    return "medio"


def _framing_at(z, pt):
    """Recorte (framing) da MESMA imagem ate o ponto de interesse `pt`=(x,y) em 0..1."""
    return {"type": "framing", "easing": "ease_out",
            "from": {"zoom": 1.0, "at": [0.5, 0.5]},
            "to": {"zoom": z, "at": [round(pt[0], 3), round(pt[1], 3)]}}


# BEATS narrativos — lidos do PROMPT (visual) + NARRACAO (o que e dito). Cada beat
# tem movimento, ritmo, look e efeito proprios (gramatica do pixflow-trailer).
_BT_TENSAO = ("tremen", "frio", "gelad", "congel", "perigo", "sofre", "apert", "medo",
              "escur", "ameac", "susto", "preocup", "aguenta", "nao aguenta", "doeu", "serio")
_BT_MARAVILHA = ("encant", "lind", "brilhant", "sorri", "maravilh", "magic", "feliz",
                 "gargalh", "riu", "deslumbr", "tapete branco", "bonequinho", "pra cima")
_BT_ACAO = ("corre", "correndo", "girando", "salta", "pula", " vento", "nevasca", "foge",
            "dispara", "atira", "rajada", "uiva", "batia as patas")
_BT_DECISAO = ("decid", "vou dar um jeito", "determinad", "certeza", "promet", "ia inventar",
               "vou esquentar", "rabisc", "ideia")
# pontos de interesse alternados -> RECORTES variados (nao mira sempre o centro)
_PONTOS = [(0.5, 0.40), (0.42, 0.46), (0.58, 0.43), (0.5, 0.50)]


def _beat(prompt, narr):
    """Beat narrativo do painel (le visual + narrativa). Prioriza o PROBLEMA
    (tensao) — e nele que entra o close rapido — depois maravilha/acao/decisao."""
    t = _norm((prompt or "") + " || " + (narr or ""))
    if any(k in t for k in _BT_TENSAO):
        return "tensao"
    if any(k in t for k in _BT_MARAVILHA):
        return "maravilha"
    if any(k in t for k in _BT_ACAO):
        return "acao"
    if any(k in t for k in _BT_DECISAO):
        return "decisao"
    return "calmo"


def _montagem(prompt, narr, dur, i):
    """Mini-montagem DIRIGIDA pela narrativa (visual + o que e dito): cada BEAT tem
    seu movimento, RITMO, look e EFEITO (gramatica do pixflow-trailer). Retorna uma
    lista de shots {camera, look, effects} — recortes da MESMA imagem. So 2D.
    - PROBLEMA/tensao: estabelece rapido -> CLOSE RAPIDO (crash/push forte) no detalhe,
      cortes curtos, look tenso (vinheta/chroma/grain sobem).
    - MARAVILHA: lento e etereo (sonho-etereo, bloom), poucos cortes longos.
    - ACAO: pan acompanha + mergulho.
    - DECISAO: push que cresce -> close firme.  - CALMO: estabelece -> recorte suave."""
    beat = _beat(prompt, narr)
    pt = _PONTOS[i % len(_PONTOS)]
    pt2 = _PONTOS[(i + 2) % len(_PONTOS)]
    d = "right" if i % 2 == 0 else "left"

    def shots(seq, look, fx):
        return [{"camera": c, "look": look, "effects": fx} for c in seq]

    if beat == "tensao":
        fx = {"vignette": 0.6, "chroma": 0.8, "grain": 0.13, "bloom": 0.1, "saturation": 0.85}
        # alterna o "soco" (crash <-> push forte) e o estabelece -> sem repetir
        punch = ({"type": "crash_zoom", "intensity": 0.95, "easing": "ease_in"} if i % 2 == 0
                 else {"type": "push_in", "intensity": 1.05, "easing": "ease_in"})
        estab = ({"type": "pull_out", "intensity": 0.85, "easing": "ease_out"} if i % 2 == 0
                 else {"type": "pan", "direction": d, "intensity": 0.8, "easing": "ease_in_out"})
        if dur >= 5.5:   # estabelece -> CLOSE RAPIDO no problema -> segura no detalhe
            return shots([estab, punch, _framing_at(1.5, pt)], "cinema-dramatico", fx)
        return shots([punch, _framing_at(1.5, pt)], "cinema-dramatico", fx)
    if beat == "maravilha":
        fx = {"bloom": 0.42, "exposure": 1.08, "grain": 0.04, "saturation": 0.95}
        seq = [{"type": "push_in", "intensity": 0.5, "easing": "ease_in_out"}]
        if dur >= 6:
            seq.append(_framing_at(1.3, pt))
        return shots(seq, "sonho-etereo", fx)
    if beat == "acao":
        fx = {"chroma": 0.6, "grain": 0.1}
        seq = [{"type": "pan", "direction": d, "intensity": 1.0, "easing": "ease_in_out"},
               {"type": "push_in", "intensity": 0.9, "easing": "ease_in"}]
        if dur >= 7:
            seq.append(_framing_at(1.45, pt2))
        return shots(seq, "cinema-dramatico", fx)
    if beat == "decisao":
        fx = {"vignette": 0.55, "bloom": 0.16}
        seq = [{"type": "push_in", "intensity": 0.85, "easing": "ease_in"}]
        if dur >= 5:
            seq.append(_framing_at(1.42, (0.5, 0.4)))
        return shots(seq, "cinema-dramatico", fx)
    # calmo: estabelece (variado) -> recorte suave
    estab = ({"type": "pull_out", "intensity": 0.8, "easing": "ease_out"} if i % 2
             else {"type": "pan", "direction": d, "intensity": 0.7, "easing": "ease_in_out"})
    seq = [estab] + ([_framing_at(1.32, pt)] if dur >= 6 else [])
    return shots(seq, "cinema-dramatico", {})


def _paleta(energia):
    """Lista de cameras que se alternam por cena (proven no pixflow)."""
    if energia == "alta":
        return [
            {"type": "pull_out", "intensity": 1.0, "easing": "ease_out"},
            {"type": "push_in", "intensity": 1.1, "easing": "ease_in"},
            {"type": "pan", "direction": "right", "intensity": 0.9, "easing": "ease_in_out"},
            _framing(1.40),
            {"type": "crash_zoom", "intensity": 1.2, "easing": "ease_in"},
            {"type": "pan", "direction": "left", "intensity": 0.9, "easing": "ease_in_out"},
            {"type": "push_in", "intensity": 1.0, "easing": "ease_out"},
            {"type": "whip_pan", "direction": "right", "intensity": 1.0, "easing": "ease_in_out"},
        ]
    if energia == "acao":
        return [
            {"type": "pull_out", "intensity": 0.9, "easing": "ease_out"},
            {"type": "push_in", "intensity": 1.2, "easing": "ease_in"},
            {"type": "crash_zoom", "intensity": 1.3, "easing": "ease_in"},
            {"type": "whip_pan", "direction": "right", "intensity": 1.1, "easing": "ease_in_out"},
            _framing(1.50, 0.40),
            {"type": "whip_pan", "direction": "left", "intensity": 1.1, "easing": "ease_in_out"},
            {"type": "push_in", "intensity": 1.3, "easing": "ease_in"},
            {"type": "pan", "direction": "right", "intensity": 1.0, "easing": "ease_in_out"},
        ]
    if energia == "baixa":
        return [
            {"type": "push_in", "intensity": 0.5, "easing": "ease_in_out"},
            {"type": "pull_out", "intensity": 0.5, "easing": "ease_out"},
            _framing(1.18),
            {"type": "pan", "direction": "right", "intensity": 0.4, "easing": "ease_in_out"},
        ]
    return [  # media
        {"type": "push_in", "intensity": 0.8, "easing": "ease_in"},
        {"type": "pull_out", "intensity": 0.8, "easing": "ease_out"},
        {"type": "pan", "direction": "right", "intensity": 0.7, "easing": "ease_in_out"},
        _framing(1.28),
        {"type": "pan", "direction": "left", "intensity": 0.7, "easing": "ease_in_out"},
        {"type": "push_in", "intensity": 0.9, "easing": "ease_out"},
    ]


def _camera(i, n, energia):
    """Camera da cena i (de n). CALMO ("media"/"baixa"): 1 tomada gentil, variada
    por indice (sem clone, sem zoom forte). ENERGETICO ("alta"/"acao"): abre
    afastando (estabelece), fecha em close, e no meio alterna a paleta."""
    if energia in ("media", "baixa"):
        return _gentil(i)
    if i == 0:
        return {"type": "pull_out", "intensity": 1.0, "easing": "ease_out"}
    if i == n - 1:
        return _framing(1.30, 0.4)            # fecha em close no ponto de interesse
    pal = _paleta(energia)
    return pal[i % len(pal)]


# Presets padrao da Forma C. A biblia referencia pelo nome em estilo.acao_c (serie/
# temporada) e o episodio pode sobrescrever em ep.acao_c. Cada preset combina:
#   energia = paleta de camera (baixa|media|alta|acao)
#   cortes  = multi-shot por painel (1 = 1 tomada; 2-3 = ritmo de filme de acao)
#   slides  = "reusar" (so mais cortes na MESMA imagem, sem custo) |
#             "expandir" (mais paineis — exige re-gerar imagens; roadmap)
PRESETS = {
    "suave":    {"energia": "media", "cortes": 1, "slides": "reusar",   "visao": False},
    "dinamico": {"energia": "alta",  "cortes": 2, "slides": "reusar",   "visao": False},
    "acao":     {"energia": "acao",  "cortes": 3, "slides": "reusar",   "visao": True},
    "epico":    {"energia": "acao",  "cortes": 3, "slides": "expandir", "visao": True},
}


def preset(nome):
    """Resolve um preset padrao por nome (fallback: suave)."""
    return dict(PRESETS.get(nome or "suave", PRESETS["suave"]))


def _cortes_de(energia):
    return {"baixa": 1, "media": 1, "alta": 2, "acao": 3}.get(energia, 1)


def _camera_do_shot(shot):
    """Mapeia um shot normalizado {tipo, at, zoom, peso, direction?} → camera pixflow."""
    tipo = shot["tipo"]
    if tipo in ("close", "insert"):
        return {
            "type": "framing",
            "easing": "ease_out",
            "from": {"zoom": 1.0, "at": [0.5, 0.5]},
            "to": {"zoom": shot["zoom"], "at": shot["at"]},
        }
    if tipo == "wide":
        return {"type": "pull_out", "intensity": 0.9, "easing": "ease_out"}
    if tipo == "pan":
        return {"type": "pan", "direction": shot.get("direction", "right"),
                "intensity": 1.0, "easing": "ease_in_out"}
    if tipo == "tilt":
        # pan vertical; se o pixflow não aceitar 'up'/'down', cai p/ 'right'
        return {"type": "pan", "direction": shot.get("direction", "up"),
                "intensity": 1.0, "easing": "ease_in_out"}
    raise ValueError(f"tipo de shot desconhecido: {tipo!r}")


def _seq_visao(shots, d):
    """Gera lista de {camera, dur} a partir dos shots validados, duracao total = d."""
    shots = validar_shots(shots)
    soma_pesos = sum(s["peso"] for s in shots)
    result = []
    acum = 0.0
    for k, s in enumerate(shots):
        if k == len(shots) - 1:
            # última fatia fecha exatamente o total
            dur = round(d - acum, 2)
        else:
            dur = round(d * s["peso"] / soma_pesos, 2)
        acum += dur
        result.append({"camera": _camera_do_shot(s), "dur": dur})
    return result


def _seq(i, n, energia, cortes, prompt="", narr="", dur=4.0):
    """SHOTS do painel {camera, look, effects}. CALMO/MEDIO: mini-montagem DIRIGIDA
    pela narrativa (_montagem: beat -> movimento/ritmo/look/efeito). ENERGETICO
    (alta/acao): corte seco estabelece -> aproxima -> impacto (crash/whip). As
    duracoes (no dirigir) somam a do painel — a narracao nao desce."""
    if cortes <= 1 or energia in ("media", "baixa"):
        return _montagem(prompt, narr, dur, i)
    estabelece = [
        {"type": "pull_out", "intensity": 0.9, "easing": "ease_out"},
        {"type": "whip_pan", "direction": "right" if i % 2 else "left", "intensity": 1.1, "easing": "ease_in_out"},
        {"type": "pan", "direction": "left" if i % 2 else "right", "intensity": 1.0, "easing": "ease_in_out"},
    ][i % 3]
    aproxima = {"type": "push_in", "intensity": 1.2, "easing": "ease_in"}
    impacto = _framing(1.5, 0.4) if i % 2 else {"type": "crash_zoom", "intensity": 1.3, "easing": "ease_in"}
    cams = [estabelece, aproxima, impacto]
    cams = cams[:cortes] if cortes <= 3 else cams + [aproxima] * (cortes - 3)
    look = "acao-epico" if energia == "acao" else LOOK_CALMO
    return [{"camera": c, "look": look, "effects": {}} for c in cams]


def dirigir(stage_dir, energia=None, look=LOOK_CALMO, lead=0.6, tail=0.7, cortes=None,
            visao=None, visao_path=None, parallax=0.0):
    """Le `stage_dir/forma-c.json`, escreve `decupagem.json` + `miolo.movie.yaml`.
    `energia` = paleta de camera; `cortes` = multi-shot por painel (None -> deriva
    da energia). `visao_path` = caminho para JSON de cobertura; carregado se `visao`
    for None. `parallax` (0 = arte chapada; >0 = profundidade 2.5D via Depth-Anything
    no pixflow). Retorna (decupagem_path, movie_path, total_segundos)."""
    man = json.load(open(os.path.join(stage_dir, "forma-c.json")))
    if visao is None and visao_path and os.path.exists(visao_path):
        visao = json.load(open(visao_path))
    cenas = man["cenas"]
    direc = (man.get("meta", {}).get("direcao", {}) or {})
    energia = energia or direc.get("energia") or "alta"
    if cortes is None:
        cortes = direc.get("cortes") or _cortes_de(energia)
    n = len(cenas)

    dec_scenes, mv_scenes, images = [], [], []
    total = 0.0
    for i, c in enumerate(cenas):
        sid = c["sid"]
        wav = os.path.join(stage_dir, c["narr"])
        d = round(lead + _dur(wav) + tail, 2)
        total += d
        dec_scenes.append({"id": sid, "dur": d, "fadeIn": 0.0, "narr": c["narr"]})
        images.append({"id": sid, "file": c["img"]})
        if visao and sid in visao:
            # cobertura guiada por visão: uma mv_scene por shot
            itens = _seq_visao(visao[sid], d)
            kk = len(itens)
            for k, item in enumerate(itens):
                scene_id = sid if kk == 1 else f"{sid}_{k}"
                mv_scenes.append({"id": scene_id, "image": sid,
                                  "duration": item["dur"], "camera": item["camera"],
                                  "effects": {"parallax": parallax},
                                  "look": look, "transition_out": {"type": "cut"}})
        else:
            shots = _seq(i, n, energia, cortes,
                         prompt=c.get("cena", ""), narr=c.get("narr_txt", ""), dur=d)
            kk = len(shots)
            base = round(d / kk, 2)
            durs = [base] * (kk - 1) + [round(d - base * (kk - 1), 2)]
            for j, sh in enumerate(shots):
                eff = {"parallax": parallax, **(sh.get("effects") or {})}
                mv_scenes.append({"id": sid if kk == 1 else f"{sid}_{j+1}", "image": sid,
                                  "duration": durs[j], "camera": sh["camera"], "effects": eff,
                                  "look": sh.get("look", look), "transition_out": {"type": "cut"}})

    decupagem = {"lead": lead, "scenes": dec_scenes}
    movie = {"schema": "pixflow.movie/v1",
             "meta": {"title": f"{man.get('meta', {}).get('id', 'forma-c')} miolo"},
             "output": {"resolution": "1280x720", "fps": 30, "filename": "miolo.mp4"},
             "defaults": {"look": look},
             "assets": {"images": images},
             "scenes": mv_scenes,
             "audio": {"track": "narracao.wav", "volume": 1.0}}

    dec_path = os.path.join(stage_dir, "decupagem.json")
    mv_path = os.path.join(stage_dir, "miolo.movie.yaml")
    with open(dec_path, "w") as f:
        json.dump(decupagem, f, ensure_ascii=False, indent=2)
    with open(mv_path, "w") as f:
        yaml.safe_dump(movie, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return dec_path, mv_path, round(total, 2)
