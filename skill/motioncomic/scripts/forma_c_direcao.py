"""Diretor DETERMINISTICO da Forma C — gera `decupagem.json` + `miolo.movie.yaml`
(spec pixflow.movie/v1) a partir do `forma-c.json`, sem IA generativa.

Implementa a "mais acao" pedida: look `acao-epico`, intensidade alta, framing
fechado e crash_zoom/whip_pan nos beats, com camera VARIADA por cena (ritmo
cinematografico por indice + energia). parallax=0 (desenho). As transicoes ficam
em `cut` (fadeIn 0) p/ a trilha de narracao casar sem dessincronizar.

Uso: dirigir(stage_dir, energia="alta")  ->  escreve os 2 arquivos no stage_dir.
"""
import json
import os
import subprocess

import yaml


def _dur(wav):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", wav], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _framing(z_to, y_to=0.42):
    return {"type": "framing", "easing": "ease_out",
            "from": {"zoom": 1.0, "at": [0.5, 0.5]},
            "to": {"zoom": z_to, "at": [0.5, y_to]}}


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
    """Camera da cena i (de n): abre afastando (estabelece), fecha em close, e
    no meio alterna a paleta — non-uniforme, com mais punch na energia alta."""
    if i == 0:
        return {"type": "pull_out", "intensity": 1.0, "easing": "ease_out"}
    if i == n - 1:
        return _framing(1.30, 0.4)            # fecha em close no ponto de interesse
    pal = _paleta(energia)
    return pal[i % len(pal)]


def dirigir(stage_dir, energia="alta", look="acao-epico", lead=0.6, tail=0.7):
    """Le `stage_dir/forma-c.json`, escreve `decupagem.json` + `miolo.movie.yaml`.
    Retorna (decupagem_path, movie_path, total_segundos)."""
    man = json.load(open(os.path.join(stage_dir, "forma-c.json")))
    cenas = man["cenas"]
    energia = (man.get("meta", {}).get("direcao", {}) or {}).get("energia") or energia
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
        mv_scenes.append({"id": sid, "image": sid, "duration": d,
                          "camera": _camera(i, n, energia), "effects": {"parallax": 0},
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
