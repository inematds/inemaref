import html as _html
import os, re

def _esc(s):
    return _html.escape(str(s))

def fill(template_dir, roteiro):
    """Build a comic page HTML from a roteiro. Panel art is textless; the
    narration boxes, speech balloons and SFX are this HTML layer on top.

    The panel markup is generic (numbered .panel figures) — each template's CSS
    positions them (uniform grid vs varied manga grid). Requires exactly 6
    paineis (both templates are laid out for 6). Raises ValueError on a leftover
    template placeholder."""
    paineis = roteiro["paineis"]
    if len(paineis) != 6:
        raise ValueError(f"exactly 6 paineis required, got {len(paineis)}")

    with open(os.path.join(template_dir, "template.html")) as f:
        tpl = f.read()

    frags = []
    for i, p in enumerate(paineis, start=1):
        parts = [f'<img class="panel-img" src="assets/panel{i}.png" alt="">']
        if p.get("narracao"):
            parts.append(f'<div class="narracao">{_esc(p["narracao"])}</div>')
        if p.get("sfx"):
            parts.append(f'<div class="sfx">{_esc(p["sfx"])}</div>')
        if p.get("fala"):
            parts.append(f'<div class="fala"><span>{_esc(p["fala"])}</span></div>')
        frags.append(f'<figure class="panel">{"".join(parts)}</figure>')

    repl = {"titulo": _esc(roteiro.get("titulo", "")), "paineis_html": "".join(frags)}

    expected = set(re.findall(r"{{(\w+)}}", tpl))
    missing = expected - set(repl)
    if missing:
        raise ValueError(f"template has placeholders with no value: {sorted(missing)}")
    for key, val in repl.items():
        tpl = tpl.replace("{{" + key + "}}", str(val))
    return tpl
