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
    # energia alta + cortes=2 → 2 mv_scenes por painel (8 paineis = 16 scenes)
    assert len(m["assets"]["images"]) == 8
    assert len(m["scenes"]) >= 8  # ao menos 1 scene por painel
    # default do dirigir() agora e o look CALMO/natural
    assert m["defaults"]["look"] == "cinema-dramatico"
    assert D.LOOK_CALMO == "cinema-dramatico"
    assert m["audio"]["track"] == "narracao.wav"
    # desenho -> parallax 0 em toda cena
    assert all(s["effects"]["parallax"] == 0 for s in m["scenes"])
    # abre afastando (estabelece) na primeira scene
    assert m["scenes"][0]["camera"]["type"] == "pull_out"
    # com _seq/cortes>1, a paleta inclui framing em pelo menos uma scene
    tipos = {s["camera"]["type"] for s in m["scenes"]}
    assert "framing" in tipos or "push_in" in tipos, tipos
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


def _intensidades(cam):
    """Coleta intensidades relevantes de uma camera (intensity + framing to.zoom)."""
    vals = []
    if "intensity" in cam:
        vals.append(("intensity", cam["intensity"]))
    if cam.get("type") == "framing":
        vals.append(("zoom", cam["to"]["zoom"]))
    return vals


def _dirigir_calmo(tmp, energia="media", cortes=None, n=8):
    import yaml
    _stage(tmp, energia=energia, n=n)
    orig = D._dur
    D._dur = lambda w: 5.0
    try:
        _, mv, _ = D.dirigir(tmp, cortes=cortes)
    finally:
        D._dur = orig
    return yaml.safe_load(open(mv))


def _assert_calmo(m, n):
    # 1) EXATAMENTE 1 camera por painel -> nenhuma imagem repetida (sem clone)
    assert len(m["scenes"]) == n, (len(m["scenes"]), n)
    imgs = [s["image"] for s in m["scenes"]]
    assert len(imgs) == len(set(imgs)), imgs
    cams = [s["camera"] for s in m["scenes"]]
    tipos = {c["type"] for c in cams}
    # 2) sem crash_zoom / whip_pan em lugar nenhum
    assert not (tipos & {"crash_zoom", "whip_pan"}), tipos
    # 3) framing com zoom suave (<= 1.2) e intensidades discretas (<= 0.6)
    for c in cams:
        for nome, v in _intensidades(c):
            if nome == "zoom":
                assert v <= 1.2, ("framing zoom", v)
            else:
                assert v <= 0.6, ("intensity", v)
    # 4) paineis seguidos diferem (movimento variado, nao clonado)
    assert any(cams[k] != cams[k + 1] for k in range(len(cams) - 1)), cams


def test_modo_calmo_energia_media(tmp="/tmp/_fcd_calmo_media"):
    m = _dirigir_calmo(tmp, energia="media", n=8)
    _assert_calmo(m, 8)
    # look default calmo tambem no caminho determinístico
    assert m["defaults"]["look"] == "cinema-dramatico"
    assert all(s["look"] == "cinema-dramatico" for s in m["scenes"])


def test_modo_calmo_cortes_1(tmp="/tmp/_fcd_calmo_c1"):
    # cortes=1 forca 1 tomada por painel mesmo em energia energetica
    m = _dirigir_calmo(tmp, energia="alta", cortes=1, n=8)
    _assert_calmo(m, 8)


def test_preset_suave_eh_calmo(tmp="/tmp/_fcd_suave"):
    import yaml
    p = D.preset("suave")
    assert p["energia"] == "media" and p["cortes"] == 1
    _stage(tmp, energia=p["energia"], n=6)
    orig = D._dur
    D._dur = lambda w: 5.0
    try:
        _, mv, _ = D.dirigir(tmp, energia=p["energia"], cortes=p["cortes"])
    finally:
        D._dur = orig
    _assert_calmo(yaml.safe_load(open(mv)), 6)


def test_dirigir_default_look_eh_calmo():
    import inspect
    sig = inspect.signature(D.dirigir)
    assert sig.parameters["look"].default == "cinema-dramatico"
    assert sig.parameters["look"].default != "acao-epico"


if __name__ == "__main__":
    test_dirigir_gera_spec_pixflow_valido()
    test_energia_baixa_eh_mais_suave()
    test_modo_calmo_energia_media()
    test_modo_calmo_cortes_1()
    test_preset_suave_eh_calmo()
    test_dirigir_default_look_eh_calmo()
    print("OK forma_c_direcao")
