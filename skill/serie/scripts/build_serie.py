"""serie — orquestrador da V2: biblia (aprovacao) + lote de episodios.

build_biblia(): monta o pacote de aprovacao (folder do protagonista + biblia.md
+ pagina-piloto). build_serie(): apos aprovar, renderiza cada episodio por tipo,
nomeia descritivo, escreve manifesto.json e larga no destino. Idempotente.
Reusa folder/quadrinho/motioncomic; renderers injetaveis p/ teste sem daemon.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _deps  # noqa: E402
sys.path.insert(0, _deps.scripts("folder"))
sys.path.insert(0, _deps.scripts("quadrinho"))
sys.path.insert(0, _deps.scripts("motioncomic"))
sys.path.insert(0, os.path.dirname(__file__))
from config import resolve            # noqa: E402
from naming import slug, ep_base      # noqa: E402
import biblia as _biblia              # noqa: E402
import manifesto as _manifesto        # noqa: E402
import runner as _runner              # noqa: E402

_Q = _deps.templates("quadrinho")
_F = _deps.templates("folder")
_TEMPLATES = {"grade-uniforme": os.path.join(_Q, "grade-uniforme"),
              "manga-dinamico": os.path.join(_Q, "manga-dinamico")}


# ---------------------------------------------------------------- aprovacao
def build_biblia(biblia, piloto=None, out_dir=None, folder_fn=None, pagina_fn=None):
    """Pacote de aprovacao: biblia.md + folder do protagonista + pagina-piloto
    (se `piloto` — um roteiro de 1 pagina, 6 paineis). Retorna os caminhos."""
    _biblia.validate(biblia)
    s = resolve(biblia)
    base_out = os.path.join(os.path.expanduser(out_dir or s["destino"] or "~/projetos/output"),
                            biblia["id"], "biblia")
    os.makedirs(base_out, exist_ok=True)

    md_path = os.path.join(base_out, "biblia.md")
    with open(md_path, "w") as f:
        f.write(_biblia.to_markdown(biblia))
    result = {"biblia_md": md_path}

    if folder_fn is None:
        from build_folder import build_folder as folder_fn  # noqa: E402
    result["folder"] = folder_fn(
        biblia["protagonista"], template_dir=os.path.join(_F, "editorial-revista"),
        arte=s["arte"], modo="texto", out_dir=base_out)

    if piloto is not None:
        if pagina_fn is None:
            from build_pagina import build_pagina as pagina_fn  # noqa: E402
        ep0 = {"id": biblia["id"] + "-piloto",
               "personagem": biblia["protagonista"].get("aparencia", "")}
        result["piloto"] = pagina_fn(
            _page_to_quadrinho(ep0, piloto), _TEMPLATES[s["modelo_pagina"]],
            arte=s["arte"], out_dir=base_out)
    return result


# ---------------------------------------------------------------- helpers
def _page_to_quadrinho(ep, pg):
    """Roteiro de 1 pagina -> roteiro do quadrinho (fala dict->str; dobra o
    personagem no prompt). Mesma ponte do motioncomic build_travel."""
    personagem = ep.get("personagem", "")
    canon = {e["nome"].lower(): e["aparencia"] for e in ep.get("elementos", [])}
    paineis = []
    for panel in pg["paineis"]:
        who = panel.get("quem", personagem)
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
            fala = panel["fala"]
            qp["fala"] = fala["texto"] if isinstance(fala, dict) else fala
        paineis.append(qp)
    return {"id": f"{ep.get('id', 'ep')}-p{pg.get('n', 1):02d}", "titulo": pg.get("titulo", ""),
            "personagem_aparencia": "", "paineis": paineis}


def _ep_markdown(ep):
    out = [f"# {ep.get('titulo', '')}", "", ep.get("sinopse", ""), ""]
    for pg in ep.get("paginas", []):
        out.append(f"## Pagina {pg.get('n')} — {pg.get('titulo', '')}")
        for i, p in enumerate(pg.get("paineis", []), 1):
            out.append(f"{i}. {p.get('prompt', '')}")
            if p.get("narracao"):
                out.append(f"   narracao: {p['narracao']}")
            if p.get("fala"):
                fala = p["fala"]
                out.append(f"   fala: {fala['texto'] if isinstance(fala, dict) else fala}")
        out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- renderers
# assinatura uniforme: renderer(ep, settings, destdir, base) -> [paths]
def _render_texto(ep, settings, destdir, base):
    md = os.path.join(destdir, base + ".md")
    js = os.path.join(destdir, base + ".json")
    if not os.path.exists(md):
        with open(md, "w") as f:
            f.write(_ep_markdown(ep))
    if not os.path.exists(js):
        with open(js, "w") as f:
            json.dump(ep, f, ensure_ascii=False, indent=2)
    return [md, js]


def _render_hq(ep, settings, destdir, base):
    from build_pagina import build_pagina  # noqa: E402
    tdir = _TEMPLATES[settings["modelo_pagina"]]
    work = os.path.join(destdir, "_work")
    files = []
    for pg in ep["paginas"]:
        dst = os.path.join(destdir, f"{base}-p{int(pg['n']):02d}.png")
        if not os.path.exists(dst):
            png = build_pagina(_page_to_quadrinho(ep, pg), tdir, arte=settings["arte"], out_dir=work)
            os.replace(png, dst)
        files.append(dst)
    return files


def _render_video(ep, settings, destdir, base):
    dst = os.path.join(destdir, base + ".mp4")
    if os.path.exists(dst):
        return [dst]
    work = os.path.join(destdir, "_work")
    rot = dict(ep)
    rot["id"] = base
    if settings["tipo"] == "video-pagina":
        from build_travel import build_video_travel  # noqa: E402
        mp4 = build_video_travel(rot, out_dir=work, voice=settings["voz"], arte=settings["arte"],
                                 template_dir=_TEMPLATES[settings["modelo_pagina"]])
    else:
        from build_motion import build_video  # noqa: E402
        mp4 = build_video(rot, out_dir=work, voice=settings["voz"])
    os.replace(mp4, dst)
    return [dst]


_REGISTRY = {"texto": _render_texto, "hq": _render_hq,
             "video-slideshow": _render_video, "video-pagina": _render_video}


def _saidas(destdir, base):
    """Saidas ja no disco de um episodio: primarias (<base>.*: .md/.json/.mp4) +
    paginas de hq (<base>-pNN.*). Ordenado -> manifesto deterministico/idempotente."""
    return sorted(glob.glob(os.path.join(destdir, base + ".*"))
                  + glob.glob(os.path.join(destdir, base + "-p*.*")))


# ---------------------------------------------------------------- lote
def build_serie(biblia, episodios, out_dir=None, auto=False, runner="auto",
                renderers=None, gerado_em=None, notify_fn=None, mkivideos_check=None):
    """Renderiza todos os episodios por tipo e larga em <destino>/<id>/.
    Idempotente (pula arquivos existentes). `renderers` injetavel (teste);
    `notify_fn(msg)` p/ progresso. `auto` aqui e informativo (o portao e
    decidido por quem chama). Retorna {dest, manifesto, episodios}."""
    s = resolve(biblia)
    tipo = s["tipo"]
    destino = os.path.expanduser(out_dir or s["destino"] or "~/projetos/output")
    serie_slug = slug(biblia.get("assunto") or biblia["id"])
    destdir = os.path.join(destino, biblia["id"])
    os.makedirs(destdir, exist_ok=True)

    reg = dict(_REGISTRY)
    if renderers:
        reg.update(renderers)
    render = reg[tipo]
    modo = _runner.escolher(tipo, runner, _runner.mkivideos_disponivel(mkivideos_check))
    notify = notify_fn or (lambda msg: None)

    elementos = biblia.get("elementos", [])
    entregas = []
    for ep in episodios:
        ep.setdefault("elementos", elementos)   # canon visual disponivel p/ os renderers
        base = ep_base(serie_slug, ep["n"], ep.get("titulo", ""))
        # idempotente: so renderiza se ainda nao ha NENHUMA saida desse episodio.
        # `arquivos` vem sempre do estado final no disco -> identico entre rodadas
        # e por tipo (texto: .md/.json; video: .mp4; hq: -pNN.png).
        if not _saidas(destdir, base):
            render(ep, s, destdir, base)
        files = _saidas(destdir, base)
        entregas.append({"n": ep["n"], "arquivos": [os.path.basename(p) for p in files]})
        notify(f"[{biblia['id']}] episodio {ep['n']} ({modo}) ok")

    import datetime
    stamp = gerado_em or datetime.date.today().isoformat()
    man = _manifesto.build(biblia, entregas, stamp)
    man_path = os.path.join(destdir, "manifesto.json")
    with open(man_path, "w") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    notify(f"[{biblia['id']}] lote finalizado: {len(entregas)} episodios em {destdir}")
    return {"dest": destdir, "manifesto": man_path, "episodios": entregas}
