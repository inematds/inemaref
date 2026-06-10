"""Sobrepoe SO os 'textos de expressao' (balao de fala + SFX) num quadro.
A narracao NAO entra na imagem — ela e so voz. Renderiza 1280x720 via chromium."""
import html as _h
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
from render import render_html_to_png  # noqa: E402

_TPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: 1280px; height: 720px; overflow: hidden; font-family: Arial, sans-serif; }
.frame { position: relative; width: 1280px; height: 720px; background: #000; }
.bg { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.fala { position: absolute; left: 50%; bottom: 38px; transform: translateX(-50%); max-width: 76%; }
.fala span { display: inline-block; background: #fff; border: 3px solid #111; border-radius: 28px;
  padding: 14px 24px; font-size: 27px; font-weight: 600; color: #111; line-height: 1.25;
  box-shadow: 3px 4px 0 rgba(0,0,0,.35); }
.sfx { position: absolute; right: 30px; top: 26px; font-family: "Arial Black", sans-serif;
  font-weight: 900; font-size: 74px; color: #ffd23f; -webkit-text-stroke: 5px #111;
  transform: rotate(-8deg); }
</style></head><body><div class="frame">
<img class="bg" src="__IMG__">__FALA____SFX__
</div></body></html>"""

def render_panel(img_path, out_png, fala=None, sfx=None):
    fala_html = f'<div class="fala"><span>{_h.escape(fala)}</span></div>' if fala else ""
    sfx_html = f'<div class="sfx">{_h.escape(sfx)}</div>' if sfx else ""
    html = (_TPL.replace("__IMG__", "file://" + os.path.abspath(img_path))
                .replace("__FALA__", fala_html).replace("__SFX__", sfx_html))
    html_path = out_png + ".html"
    with open(html_path, "w") as f:
        f.write(html)
    render_html_to_png(html_path, out_png, 1280, 720)
    return out_png
