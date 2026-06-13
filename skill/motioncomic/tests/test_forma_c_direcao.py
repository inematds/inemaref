import os, sys, json, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import forma_c_direcao as D


def _stage(tmp, energia="alta", n=8):
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(os.path.join(tmp, "assets", "audio"), exist_ok=True)
    cenas = [{"sid": f"s{i:02d}", "origem": f"p01q{i}",
              "img": f"assets/img/s{i:02d}.png", "narr": f"assets/audio/s{i:02d}.wav",
              "cena": ""} for i in range(1, n + 1)]
    json.dump({"meta": {"id": "x", "direcao": {"energia": energia}}, "cenas": cenas},
              open(os.path.join(tmp, "forma-c.json"), "w"))
    return tmp


def test_dirigir_gera_spec_pixflow_valido(tmp="/tmp/_fcd"):
    import yaml
    _stage(tmp, energia="alta", n=8)
    orig = D._dur
    D._dur = lambda w: 5.0          # sem ffprobe
    try:
        dec, mv, total = D.dirigir(tmp)
    finally:
        D._dur = orig
    m = yaml.safe_load(open(mv))
    assert m["schema"] == "pixflow.movie/v1"
    assert len(m["scenes"]) == 8 and len(m["assets"]["images"]) == 8
    assert m["defaults"]["look"] == "acao-epico"
    assert m["audio"]["track"] == "narracao.wav"
    # desenho -> parallax 0 em toda cena
    assert all(s["effects"]["parallax"] == 0 for s in m["scenes"])
    # abre afastando (estabelece), fecha em close (framing)
    assert m["scenes"][0]["camera"]["type"] == "pull_out"
    assert m["scenes"][-1]["camera"]["type"] == "framing"
    # energia alta usa cameras de ACAO
    tipos = {s["camera"]["type"] for s in m["scenes"]}
    assert tipos & {"crash_zoom", "whip_pan"}, tipos
    # duracao da cena = lead + narr + tail
    d = json.load(open(dec))
    assert abs(d["scenes"][0]["dur"] - (0.6 + 5.0 + 0.7)) < 0.01
    assert d["lead"] == 0.6


def test_energia_baixa_eh_mais_suave(tmp="/tmp/_fcd_b"):
    import yaml
    _stage(tmp, energia="baixa", n=6)
    orig = D._dur
    D._dur = lambda w: 4.0
    try:
        _, mv, _ = D.dirigir(tmp)
    finally:
        D._dur = orig
    m = yaml.safe_load(open(mv))
    tipos = {s["camera"]["type"] for s in m["scenes"]}
    # energia baixa NAO usa crash/whip
    assert not (tipos & {"crash_zoom", "whip_pan"}), tipos


if __name__ == "__main__":
    test_dirigir_gera_spec_pixflow_valido()
    test_energia_baixa_eh_mais_suave()
    print("OK forma_c_direcao")
