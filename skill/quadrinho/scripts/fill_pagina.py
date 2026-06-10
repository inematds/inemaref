import html as _html
import os, re

def _esc(s):
    return _html.escape(str(s))


def _pos_style(quadrant):
    """CSS inline para posicionar um elemento num quadrante especifico."""
    MAP = {
        "top-left":     "top:0; left:0; bottom:auto; right:auto",
        "top-right":    "top:0; right:0; bottom:auto; left:auto",
        "bottom-left":  "bottom:0; left:0; top:auto; right:auto",
        "bottom-right": "bottom:0; right:0; top:auto; left:auto",
    }
    return MAP.get(quadrant, "")


def fill(template_dir, roteiro, assets_dir=None):
    """Build a comic page HTML from a roteiro. Panel art is textless; the
    narration boxes, speech balloons and SFX are this HTML layer on top.

    If assets_dir is provided, runs face detection on each panel image
    and positions text elements away from detected faces. Otherwise uses
    CSS defaults from the stylesheet.

    The panel markup is generic (numbered .panel figures) -- each template's CSS
    positions them (uniform grid vs varied manga grid). Requires exactly 6
    paineis (both templates are laid out for 6). Raises ValueError on a leftover
    template placeholder."""
    paineis = roteiro["paineis"]
    if len(paineis) != 6:
        raise ValueError(f"exactly 6 paineis required, got {len(paineis)}")

    # face detection (optional, degrades gracefully)
    panel_zones = {}
    if assets_dir:
        try:
            from face_zones import safe_positions
            for i in range(1, 7):
                img_path = os.path.join(assets_dir, f"panel{i}.png")
                if os.path.exists(img_path):
                    panel_zones[i] = safe_positions(img_path)
        except ImportError:
            pass  # cv2 not installed, skip face detection

    with open(os.path.join(template_dir, "template.html")) as f:
        tpl = f.read()

    frags = []
    for i, p in enumerate(paineis, start=1):
        zones = panel_zones.get(i, {})
        parts = [f'<img class="panel-img" src="assets/panel{i}.png" alt="">']
        if p.get("narracao"):
            style = _pos_style(zones.get("narracao", "")) if zones else ""
            style_attr = f' style="{style}"' if style else ""
            parts.append(f'<div class="narracao"{style_attr}>{_esc(p["narracao"])}</div>')
        if p.get("sfx"):
            style = _pos_style(zones.get("sfx", "")) if zones else ""
            style_attr = f' style="{style}"' if style else ""
            parts.append(f'<div class="sfx"{style_attr}>{_esc(p["sfx"])}</div>')
        if p.get("fala"):
            style = _pos_style(zones.get("fala", "")) if zones else ""
            style_attr = f' style="{style}"' if style else ""
            parts.append(f'<div class="fala"{style_attr}><span>{_esc(p["fala"])}</span></div>')
        frags.append(f'<figure class="panel">{"".join(parts)}</figure>')

    repl = {"titulo": _esc(roteiro.get("titulo", "")), "paineis_html": "".join(frags)}

    expected = set(re.findall(r"{{(\w+)}}", tpl))
    missing = expected - set(repl)
    if missing:
        raise ValueError(f"template has placeholders with no value: {sorted(missing)}")
    for key, val in repl.items():
        tpl = tpl.replace("{{" + key + "}}", str(val))
    return tpl
