import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_serie as BS

BIBLIA = {
    "id": "demo-serie", "assunto": "Serie Demo",
    "premissa": {"logline": "logline", "sinopse": "sinopse"},
    "estilo": {"arte": "manga"},
    "formato": {"tipo": "texto", "n_episodios": 2, "destino": None},
    "protagonista": {"nome": "Lia", "aparencia": "jovem"},
    "episodios": [
        {"n": 1, "titulo": "Um", "sinopse": "s1"},
        {"n": 2, "titulo": "Dois", "sinopse": "s2"},
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


if __name__ == "__main__":
    test_build_biblia_bundle()
    test_build_serie_batch_texto_and_manifest()
    test_texto_manifest_idempotent()
    print("OK")
