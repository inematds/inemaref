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


def _seq(i, n, energia, cortes):
    """Sequencia de cameras pro MESMO painel. CALMO (energia "media"/"baixa" OU
    cortes<=1): EXATAMENTE 1 tomada gentil por painel — uma imagem, uma camera,
    sem clone e sem zoom forte. ENERGETICO (cortes>1): corte seco entre tomadas
    (estabelece -> aproxima -> impacto), variando por indice. As duracoes somam a
    duracao do painel, entao a narracao (faixa unica) nao desce."""
    if cortes <= 1:
        # 1 tomada por painel = SEMPRE gentil (mesmo em energia energetica): sem
        # clone, sem zoom forte. Energia so volta a "pesar" com cortes>1.
        return [_gentil(i)]
    if energia in ("media", "baixa"):
        return [_camera(i, n, energia)]
    estabelece = [
        {"type": "pull_out", "intensity": 0.9, "easing": "ease_out"},
        {"type": "whip_pan", "direction": "right" if i % 2 else "left", "intensity": 1.1, "easing": "ease_in_out"},
        {"type": "pan", "direction": "left" if i % 2 else "right", "intensity": 1.0, "easing": "ease_in_out"},
    ][i % 3]
    aproxima = {"type": "push_in", "intensity": 1.2, "easing": "ease_in"}
    impacto = _framing(1.5, 0.4) if i % 2 else {"type": "crash_zoom", "intensity": 1.3, "easing": "ease_in"}
    seq = [estabelece, aproxima, impacto]
    if cortes <= 3:
        return seq[:cortes]
    return seq + [aproxima] * (cortes - 3)


def dirigir(stage_dir, energia=None, look=LOOK_CALMO, lead=0.6, tail=0.7, cortes=None, visao=None, visao_path=None):
    """Le `stage_dir/forma-c.json`, escreve `decupagem.json` + `miolo.movie.yaml`.
    `energia` = paleta de camera; `cortes` = multi-shot por painel (None -> deriva
    da energia). `visao_path` = caminho para JSON de cobertura; carregado se `visao`
    for None. Retorna (decupagem_path, movie_path, total_segundos)."""
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
                                  "effects": {"parallax": 0},
                                  "look": look, "transition_out": {"type": "cut"}})
        else:
            cams = _seq(i, n, energia, cortes)
            kk = len(cams)
            base = round(d / kk, 2)
            durs = [base] * (kk - 1) + [round(d - base * (kk - 1), 2)]
            for j, cam in enumerate(cams):
                mv_scenes.append({"id": sid if kk == 1 else f"{sid}_{j+1}", "image": sid,
                                  "duration": durs[j], "camera": cam, "effects": {"parallax": 0},
                                  "look": look, "transition_out": {"type": "cut"}})

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
