import json, os, sys

# reuse the folder skill's tested helpers (shared image engine + renderer).
# resolve by DISCOVERY so quadrinho works even when symlinked ALONE into
# ~/.claude/skills/ (never depend on the repo tree being alongside):
#   1) $INEMAREF_HOME/skill/folder/scripts
#   2) the installed sister skill  ~/.claude/skills/folder/scripts
#   3) repo-relative fallback via realpath (resolves through the symlink back
#      into the real repo, so a lone install still finds folder/ in the repo)
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _deps  # noqa: E402
_FOLDER_SCRIPTS = _deps.scripts("folder")
sys.path.insert(0, _FOLDER_SCRIPTS)
import imgclient            # noqa: E402
import render as _render    # noqa: E402
from artes import load_arte  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from fill_pagina import fill  # noqa: E402


def _meta(template_dir):
    with open(os.path.join(template_dir, "meta.json")) as f:
        return json.load(f)


def build_pagina(roteiro, template_dir, arte="manga", out_dir="output",
                 model="flux2-klein", generate_fn=None, render_fn=None):
    """Render one comic page: generate 6 textless panels, fill the page template
    (narration/balloons/SFX as an HTML layer), screenshot to PNG.

    Artifacts land in `<out_dir>/<id>/`: pagina.png, pagina.html, assets/ (6
    panels), roteiro.json. generate_fn/render_fn are injectable for testing."""
    generate_fn = generate_fn or imgclient.generate
    render_fn = render_fn or _render.render_html_to_png

    meta = _meta(template_dir)
    a = load_arte(arte)
    base = os.path.join(out_dir, roteiro["id"])
    assets = os.path.join(base, "assets")
    os.makedirs(assets, exist_ok=True)

    aparencia = (roteiro.get("personagem_aparencia") or "").strip().rstrip(".")
    slot = meta["slots"]["painel"]

    for i, p in enumerate(roteiro["paineis"], start=1):
        scene = p["prompt"].strip().rstrip(".")
        prompt = (f"{aparencia}, {scene}, {a['positivo']}, no text" if aparencia
                  else f"{scene}, {a['positivo']}, no text")
        generate_fn(prompt, os.path.join(assets, f"panel{i}.png"), model=model,
                    width=slot["width"], height=slot["height"],
                    negative_prompt=a["negativo"])

    html = fill(template_dir, roteiro, assets_dir=assets)
    css_abs = os.path.abspath(os.path.join(template_dir, "style.css"))
    html = html.replace('href="style.css"', f'href="file://{css_abs}"')
    html_path = os.path.join(base, "pagina.html")
    with open(html_path, "w") as f:
        f.write(html)

    render_fn(html_path, os.path.join(base, "pagina.png"), meta["width"], meta["height"])

    with open(os.path.join(base, "roteiro.json"), "w") as f:
        json.dump(roteiro, f, ensure_ascii=False, indent=2)
    return os.path.join(base, "pagina.png")
