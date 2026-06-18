"""Testes unitarios para _camera_do_shot e _seq_visao (forma_c_direcao.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import forma_c_direcao as D


# ---------------------------------------------------------------------------
# _camera_do_shot
# ---------------------------------------------------------------------------

def test_close_retorna_framing():
    shot = {"tipo": "close", "at": [0.4, 0.3], "zoom": 2.5, "peso": 1}
    cam = D._camera_do_shot(shot)
    assert cam["type"] == "framing", cam
    assert cam["to"]["at"] == [0.4, 0.3], cam
    assert cam["to"]["zoom"] == 2.5, cam
    assert cam["from"]["zoom"] == 1.0, cam


def test_insert_retorna_framing():
    shot = {"tipo": "insert", "at": [0.45, 0.28], "zoom": 3.0, "peso": 2}
    cam = D._camera_do_shot(shot)
    assert cam["type"] == "framing", cam
    assert cam["to"]["at"] == [0.45, 0.28], cam


def test_wide_retorna_pull_out():
    shot = {"tipo": "wide", "at": [0.5, 0.5], "zoom": 1.0, "peso": 1}
    cam = D._camera_do_shot(shot)
    assert cam["type"] == "pull_out", cam


def test_pan_retorna_pan():
    shot = {"tipo": "pan", "at": [0.5, 0.5], "zoom": 1.0, "peso": 1, "direction": "left"}
    cam = D._camera_do_shot(shot)
    assert cam["type"] == "pan", cam
    assert cam["direction"] == "left", cam


def test_pan_default_direction():
    shot = {"tipo": "pan", "at": [0.5, 0.5], "zoom": 1.0, "peso": 1}
    cam = D._camera_do_shot(shot)
    assert cam["type"] == "pan", cam
    assert cam["direction"] == "right", cam


def test_tilt_retorna_pan():
    shot = {"tipo": "tilt", "at": [0.5, 0.5], "zoom": 1.0, "peso": 1}
    cam = D._camera_do_shot(shot)
    assert cam["type"] == "pan", cam  # pan vertical
    assert cam["direction"] == "up", cam


# ---------------------------------------------------------------------------
# _seq_visao
# ---------------------------------------------------------------------------

SHOTS_3 = [
    {"tipo": "wide",   "peso": 1, "at": [0.5, 0.5],  "zoom": 1.0},
    {"tipo": "close",  "peso": 1, "at": [0.4, 0.3],  "zoom": 2.5},
    {"tipo": "insert", "peso": 2, "at": [0.45, 0.28], "zoom": 3.0},
]


def test_seq_visao_tres_itens():
    result = D._seq_visao(SHOTS_3, 8.0)
    assert len(result) == 3, result


def test_seq_visao_soma_total():
    result = D._seq_visao(SHOTS_3, 8.0)
    soma = sum(item["dur"] for item in result)
    assert abs(soma - 8.0) <= 0.01, f"soma={soma}"


def test_seq_visao_pesos_refletidos():
    result = D._seq_visao(SHOTS_3, 8.0)
    # pesos [1,1,2] -> proporcoes ~[2,2,4] de 8.0
    assert abs(result[0]["dur"] - 2.0) <= 0.05, result[0]["dur"]
    assert abs(result[1]["dur"] - 2.0) <= 0.05, result[1]["dur"]
    assert abs(result[2]["dur"] - 4.0) <= 0.05, result[2]["dur"]


def test_seq_visao_cameras_corretas():
    result = D._seq_visao(SHOTS_3, 8.0)
    assert result[0]["camera"]["type"] == "pull_out"
    assert result[1]["camera"]["type"] == "framing"
    assert result[2]["camera"]["type"] == "framing"


def test_seq_visao_um_shot():
    shots = [{"tipo": "wide", "peso": 1, "at": [0.5, 0.5], "zoom": 1.0}]
    result = D._seq_visao(shots, 5.0)
    assert len(result) == 1
    assert abs(result[0]["dur"] - 5.0) <= 0.01


def test_seq_visao_shots_invalido():
    try:
        D._seq_visao([], 5.0)
        assert False, "deveria levantar ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# dirigir com visao= (integracao basica sem ffprobe)
# ---------------------------------------------------------------------------

def test_dirigir_com_visao(tmp="/tmp/_fcd_visao"):
    import json, shutil, yaml
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "assets", "audio"), exist_ok=True)
    cenas = [{"sid": f"s{i:02d}", "origem": f"p01q{i}",
              "img": f"assets/img/s{i:02d}.png", "narr": f"assets/audio/s{i:02d}.wav",
              "cena": ""} for i in range(1, 4)]
    json.dump({"meta": {"id": "x", "direcao": {"energia": "alta"}}, "cenas": cenas},
              open(os.path.join(tmp, "forma-c.json"), "w"))

    visao = {
        "s01": [
            {"tipo": "wide",  "peso": 1, "at": [0.5, 0.5], "zoom": 1.0},
            {"tipo": "close", "peso": 1, "at": [0.4, 0.3], "zoom": 2.0},
        ]
    }
    orig = D._dur
    D._dur = lambda w: 3.0
    try:
        dec, mv, total = D.dirigir(tmp, visao=visao)
    finally:
        D._dur = orig

    m = yaml.safe_load(open(mv))
    scenes = m["scenes"]

    # s01 deve ter 2 mv_scenes (visao), s02/s03 seguem cortes normais
    ids_s01 = [s for s in scenes if s["id"].startswith("s01")]
    assert len(ids_s01) == 2, f"esperado 2 scenes para s01, got {len(ids_s01)}"

    # soma durations de s01 == d total do painel
    d_s01 = round(0.6 + 3.0 + 0.7, 2)
    soma_s01 = sum(s["duration"] for s in ids_s01)
    assert abs(soma_s01 - d_s01) <= 0.01, f"soma_s01={soma_s01} != {d_s01}"

    # dec_scenes: 1 por painel (3 total)
    d = json.load(open(dec))
    assert len(d["scenes"]) == 3


if __name__ == "__main__":
    test_close_retorna_framing()
    test_insert_retorna_framing()
    test_wide_retorna_pull_out()
    test_pan_retorna_pan()
    test_pan_default_direction()
    test_tilt_retorna_pan()
    test_seq_visao_tres_itens()
    test_seq_visao_soma_total()
    test_seq_visao_pesos_refletidos()
    test_seq_visao_cameras_corretas()
    test_seq_visao_um_shot()
    test_seq_visao_shots_invalido()
    test_dirigir_com_visao()
    print("OK")
