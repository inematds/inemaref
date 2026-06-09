import html as _html
import json, os

def _esc(s):
    return _html.escape(str(s))

def fill(template_dir, ficha, images):
    """Fill a fixed-slot template. images = {'retrato': path, 'focos': [5 paths]}.
    Returns HTML string. Raises ValueError if focos count != 5 or a placeholder
    is left unreplaced."""
    if len(ficha.get("focos", [])) != 5 or len(images.get("focos", [])) != 5:
        raise ValueError("exactly 5 focos (and 5 foco images) are required")

    with open(os.path.join(template_dir, "template.html")) as f:
        tpl = f.read()

    personalidade_html = "".join(f"<p>{_esc(x)}</p>" for x in ficha["personalidade"])
    caracteristicas_html = "".join(
        f'<div class="row"><span class="icone">{_esc(c["icone"])}</span>'
        f'<span>{_esc(c["label"])}</span></div>' for c in ficha["caracteristicas"])
    detalhes_html = "".join(
        f'<div class="row"><span class="k">{_esc(d["k"])}</span>'
        f'<span class="v">{_esc(d["v"])}</span></div>' for d in ficha["detalhes"])

    repl = {
        "kicker": _esc(ficha.get("kicker", "")),
        "nome": _esc(ficha["nome"]),
        "subtitulo": _esc(ficha.get("subtitulo", "")),
        "frase": _esc(ficha.get("frase", "")),
        "img_retrato": images["retrato"],
        "personalidade_html": personalidade_html,
        "caracteristicas_html": caracteristicas_html,
        "detalhes_html": detalhes_html,
    }
    for i, (img, foco) in enumerate(zip(images["focos"], ficha["focos"]), start=1):
        repl[f"foco{i}_img"] = img
        repl[f"foco{i}_legenda"] = _esc(foco["legenda"])

    for key, val in repl.items():
        tpl = tpl.replace("{{" + key + "}}", str(val))

    if "{{" in tpl:
        leftover = tpl[tpl.index("{{"): tpl.index("{{") + 40]
        raise ValueError(f"unreplaced placeholder near: {leftover!r}")
    return tpl
