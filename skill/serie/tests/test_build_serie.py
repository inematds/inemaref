import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_serie as BS

BIBLIA = {
    "id": "demo-serie", "assunto": "Serie Demo",
    "objetivo": "Demonstrar a serie de ponta a ponta.",
    "premissa": {"logline": "logline", "sinopse": "sinopse"},
    "estilo": {"arte": "manga"},
    "formato": {"tipo": "texto", "n_episodios": 2, "destino": None},
    "protagonista": {"nome": "Lia", "aparencia": "jovem"},
    "episodios": [
        {"n": 1, "titulo": "Um", "sinopse": "s1", "contribuicao": "abre a serie"},
        {"n": 2, "titulo": "Dois", "sinopse": "s2", "contribuicao": "fecha a serie"},
    ],
}


def _fake_ep(n, titulo):
    return {"id": f"demo-serie-ep{n:02d}", "n": n, "titulo": titulo, "personagem": "Lia",
            "paginas": [{"n": 1, "titulo": titulo, "paineis": [{"prompt": "cena"}]}]}


def test_build_biblia_bundle(tmp="/tmp/_serie_biblia"):
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    calls = {}
    def fake_folder(ficha, **kw):
        p = os.path.join(kw["out_dir"], "folder.png"); open(p, "w").close(); calls["folder"] = ficha; return p
    def fake_pagina(rot, tdir, **kw):
        p = os.path.join(kw["out_dir"], "pagina.png"); open(p, "w").close(); calls["piloto"] = rot; return p
    piloto = {"n": 1, "titulo": "Um", "paineis": [{"prompt": "cena"} for _ in range(6)]}
    res = BS.build_biblia(BIBLIA, piloto=piloto, out_dir=tmp,
                          folder_fn=fake_folder, pagina_fn=fake_pagina)
    assert os.path.exists(res["biblia_md"])
    assert os.path.exists(res["folder"])
    assert os.path.exists(res["piloto"])
    assert calls["folder"]["nome"] == "Lia"


def test_build_serie_batch_texto_and_manifest(tmp="/tmp/_serie_batch"):
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    episodios = [_fake_ep(1, "Um"), _fake_ep(2, "Dois")]
    rendered = []
    def fake_render(ep, settings, destdir, base):
        path = os.path.join(destdir, base + ".md")
        open(path, "w").write(ep["titulo"]); rendered.append(base); return [path]
    res = BS.build_serie(BIBLIA, episodios, out_dir=tmp, auto=True,
                         renderers={"texto": fake_render}, gerado_em="2026-06-10",
                         notify_fn=lambda msg: None)
    destdir = os.path.join(tmp, "demo-serie")
    assert os.path.exists(os.path.join(destdir, "manifesto.json"))
    m = json.load(open(os.path.join(destdir, "manifesto.json")))
    assert len(m["episodios"]) == 2
    assert m["episodios"][0]["arquivos"] == ["serie-demo-ep01-um.md"]
    # idempotente: re-rodar nao re-renderiza
    rendered.clear()
    BS.build_serie(BIBLIA, episodios, out_dir=tmp, auto=True,
                   renderers={"texto": fake_render}, gerado_em="2026-06-10", notify_fn=lambda m: None)
    assert rendered == [], "nao deveria re-renderizar arquivos existentes"


def test_texto_manifest_idempotent(tmp="/tmp/_serie_texto_idem"):
    """Regressao: o tipo texto usa o renderer real (.md + .json, sem daemon).
    O manifesto deve ser IDENTICO entre rodadas e listar os dois arquivos."""
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    episodios = [_fake_ep(1, "Um"), _fake_ep(2, "Dois")]
    r1 = BS.build_serie(BIBLIA, episodios, out_dir=tmp, auto=True,
                        gerado_em="2026-06-10", notify_fn=lambda m: None)
    m1 = json.load(open(r1["manifesto"]))
    arq1 = m1["episodios"][0]["arquivos"]
    assert "serie-demo-ep01-um.md" in arq1
    assert "serie-demo-ep01-um.json" in arq1
    r2 = BS.build_serie(BIBLIA, episodios, out_dir=tmp, auto=True,
                        gerado_em="2026-06-10", notify_fn=lambda m: None)
    m2 = json.load(open(r2["manifesto"]))
    assert m1["episodios"] == m2["episodios"], "manifesto deve ser identico entre rodadas"


def test_canon_visual_fold():
    """Canon visual: um quadro que USA um elemento recebe a aparencia travada
    dobrada no prompt (piramide igual em todo quadro)."""
    ep = {"id": "e1", "n": 1, "titulo": "T", "personagem": "Lia",
          "elementos": [{"nome": "Piramide", "aparencia": "pedra, 5 camadas, luz dourada"}]}
    pg = {"n": 1, "titulo": "T", "paineis": [
        {"prompt": "Lia diante da piramide", "usa": ["Piramide"]},
        {"prompt": "Lia andando"},
    ]}
    q = BS._page_to_quadrinho(ep, pg)
    assert "pedra, 5 camadas, luz dourada" in q["paineis"][0]["prompt"]
    assert "pedra, 5 camadas" not in q["paineis"][1]["prompt"]   # quadro sem `usa` nao dobra


def test_video_format_letter(tmp="/tmp/_serie_forma"):
    """Forma A (slideshow) e B (pagina) convivem na MESMA pasta: a LETRA do
    formato vem ANTES do epNN no nome (<serie>-a-ep01 / <serie>-b-ep01); texto
    NAO leva letra de formato."""
    import shutil
    for tipo, mark in [("video-pagina", "-b-ep"), ("video-slideshow", "-a-ep")]:
        shutil.rmtree(tmp, ignore_errors=True)
        b = json.loads(json.dumps(BIBLIA)); b["formato"] = {"tipo": tipo, "destino": None}
        seen = []
        def fake(ep, settings, destdir, base):
            seen.append(base); p = os.path.join(destdir, base + ".mp4"); open(p, "w").close(); return [p]
        BS.build_serie(b, [_fake_ep(1, "Um")], out_dir=tmp, auto=True,
                       renderers={tipo: fake}, gerado_em="2026-06-10", notify_fn=lambda m: None)
        assert seen and all(mark in x for x in seen), (tipo, seen)
    # texto: sem letra de formato
    shutil.rmtree(tmp, ignore_errors=True)
    seen = []
    def faketxt(ep, settings, destdir, base):
        seen.append(base); p = os.path.join(destdir, base + ".md"); open(p, "w").close(); return [p]
    BS.build_serie(BIBLIA, [_fake_ep(1, "Um")], out_dir=tmp, auto=True,
                   renderers={"texto": faketxt}, gerado_em="2026-06-10", notify_fn=lambda m: None)
    assert seen and all("-a-ep" not in x and "-b-ep" not in x for x in seen), seen


def test_qc_generate_fn_gating():
    """QC e opt-in: _qc_generate_fn devolve None por padrao (comportamento
    inalterado) e um callable quando ligado (env INEMAREF_QC ou settings.qc_imagem)."""
    os.environ.pop("INEMAREF_QC", None)
    ep = {"referencias_efetivas": {"protagonista": "Lia efetiva"}}
    assert BS._qc_generate_fn(ep, {}) is None
    assert callable(BS._qc_generate_fn(ep, {"qc_imagem": True}))
    os.environ["INEMAREF_QC"] = "1"
    try:
        assert callable(BS._qc_generate_fn(ep, {}))
    finally:
        os.environ.pop("INEMAREF_QC", None)


if __name__ == "__main__":
    test_build_biblia_bundle()
    test_qc_generate_fn_gating()
    test_build_serie_batch_texto_and_manifest()
    test_texto_manifest_idempotent()
    test_canon_visual_fold()
    test_video_format_letter()
    print("OK")
