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


QUADRANTS = ("top-left", "top-right", "bottom-left", "bottom-right")
DEFAULT_POS = {"narracao": "top-left", "fala": "bottom-right", "sfx": "top-right"}

# limite duro por elemento — acima disso a caixa nao cabe nem no maior painel
MAX_CHARS = {"narracao": 220, "fala": 140, "sfx": 16}


def _assign_positions(present, occupied=frozenset()):
    """Atribui um quadrante distinto a cada elemento presente no painel.

    Alem de nunca repetir quadrante, narracao e sfx nao podem dividir a mesma
    metade vertical: a narracao e larga (max-width 70%) e o sfx e grande, na
    mesma faixa eles se sobrepoem em paineis estreitos. Quadrantes com rosto
    (occupied) sao evitados quando possivel."""
    result, used = {}, set()
    for elem in ("narracao", "fala", "sfx"):
        if elem not in present:
            continue
        if elem == "narracao":
            # narracao SEMPRE no topo: a faixa de cima e a zona segura (acima do
            # rosto, que o object-position empurra pra baixo). Nunca vai pro fundo
            # — embaixo a legenda cai no queixo/boca em closes.
            cands = ["top-left", "top-right"]
        else:
            cands = [DEFAULT_POS[elem]] + [q for q in QUADRANTS if q != DEFAULT_POS[elem]]

        def free(q, avoid_faces):
            if q in used or (avoid_faces and q in occupied):
                return False
            if elem == "sfx" and "narracao" in result and \
                    q.split("-")[0] == result["narracao"].split("-")[0]:
                return False
            return True

        pick = (next((q for q in cands if free(q, True)), None)
                or next((q for q in cands if free(q, False)), None)
                or DEFAULT_POS[elem])
        result[elem] = pick
        used.add(pick)
    return result


def _font_size(elem, text):
    """Fonte adaptativa: texto mais longo, fonte menor (evita estourar o painel)."""
    n = len(text)
    if elem == "narracao":
        return 17 if n <= 90 else 15 if n <= 150 else 13
    if elem == "fala":
        return 18 if n <= 60 else 16
    return 56 if n <= 7 else 40 if n <= 11 else 30  # sfx


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

    # valida comprimento dos textos antes de qualquer render
    for i, p in enumerate(paineis, start=1):
        for elem, limit in MAX_CHARS.items():
            text = p.get(elem)
            if text and len(str(text)) > limit:
                raise ValueError(
                    f"painel {i}: {elem} com {len(str(text))} chars "
                    f"(maximo {limit}) — encurte o texto")

    # face detection (optional, degrades gracefully)
    panel_faces = {}
    if assets_dir:
        try:
            from face_zones import face_quadrants
            for i in range(1, 7):
                img_path = os.path.join(assets_dir, f"panel{i}.png")
                if os.path.exists(img_path):
                    panel_faces[i] = face_quadrants(img_path)
        except ImportError:
            pass  # cv2 not installed, skip face detection

    with open(os.path.join(template_dir, "template.html")) as f:
        tpl = f.read()

    frags = []
    for i, p in enumerate(paineis, start=1):
        present = {k for k in ("narracao", "fala", "sfx") if p.get(k)}
        pos = _assign_positions(present, panel_faces.get(i, frozenset()))
        parts = [f'<img class="panel-img" src="assets/panel{i}.png" alt="">']
        if p.get("narracao"):
            style = f'{_pos_style(pos["narracao"])}; font-size:{_font_size("narracao", p["narracao"])}px'
            parts.append(f'<div class="narracao" style="{style}">{_esc(p["narracao"])}</div>')
        if p.get("sfx"):
            style = f'{_pos_style(pos["sfx"])}; font-size:{_font_size("sfx", p["sfx"])}px'
            parts.append(f'<div class="sfx" style="{style}">{_esc(p["sfx"])}</div>')
        if p.get("fala"):
            parts.append(f'<div class="fala" style="{_pos_style(pos["fala"])}">'
                         f'<span style="font-size:{_font_size("fala", p["fala"])}px">'
                         f'{_esc(p["fala"])}</span></div>')
        frags.append(f'<figure class="panel">{"".join(parts)}</figure>')

    repl = {"titulo": _esc(roteiro.get("titulo", "")),
            "kicker": _esc(roteiro.get("kicker", "")),
            "paineis_html": "".join(frags)}

    expected = set(re.findall(r"{{(\w+)}}", tpl))
    missing = expected - set(repl)
    if missing:
        raise ValueError(f"template has placeholders with no value: {sorted(missing)}")
    for key, val in repl.items():
        tpl = tpl.replace("{{" + key + "}}", str(val))
    return tpl
