import json, os
from artes import build_prompts
from fill_template import fill
from referencia import build_referencia, validate_referencia
import imgclient
import render as _render

def _meta(template_dir):
    with open(os.path.join(template_dir, "meta.json")) as f:
        return json.load(f)

def build_folder(ficha, template_dir, arte, out_dir, modo, foto_origem=None,
                 model="flux2-klein", generate_fn=None, render_fn=None):
    """Run the full pipeline. Returns the referencia dict (also written to disk).

    generate_fn(prompt, out_path, model, width, height, images, negative_prompt)
    render_fn(html_path, png_path, width, height)
    Both default to the real imgclient / chromium implementations."""
    generate_fn = generate_fn or imgclient.generate
    render_fn = render_fn or _render.render_html_to_png

    meta = _meta(template_dir)
    base = os.path.join(out_dir, ficha["id"])
    assets = os.path.join(base, "assets")
    os.makedirs(assets, exist_ok=True)

    prompts = build_prompts(ficha, arte)
    neg = prompts["negativo"]
    rslot, fslot = meta["slots"]["retrato"], meta["slots"]["foco"]
    ref_imgs = [foto_origem] if (modo == "foto" and foto_origem) else None

    # 1 portrait
    retrato_path = os.path.join(assets, "retrato.png")
    generate_fn(prompts["retrato"], retrato_path, model=model,
                width=rslot["width"], height=rslot["height"],
                images=ref_imgs, negative_prompt=neg)
    # 5 focos
    foco_paths = []
    for i, fp in enumerate(prompts["focos"], start=1):
        p = os.path.join(assets, f"foco{i}.png")
        generate_fn(fp, p, model=model, width=fslot["width"], height=fslot["height"],
                    images=ref_imgs, negative_prompt=neg)
        foco_paths.append(p)

    # fill html (image src relative to the html file)
    images_rel = {"retrato": "assets/retrato.png",
                  "focos": [f"assets/foco{i}.png" for i in range(1, 6)]}
    html = fill(template_dir, ficha, images_rel)
    # rewrite css href to absolute so chromium finds it from the out dir
    html = html.replace('href="style.css"', f'href="file://{os.path.join(template_dir, "style.css")}"')
    html_path = os.path.join(base, "folder.html")
    with open(html_path, "w") as f:
        f.write(html)

    # render
    render_fn(html_path, os.path.join(base, "folder.png"), meta["width"], meta["height"])

    # referencia
    ref = build_referencia(ficha, modo=modo, arte=arte,
                           retrato_ancora="assets/retrato.png", foto_origem=foto_origem)
    validate_referencia(ref)
    with open(os.path.join(base, "referencia.json"), "w") as f:
        json.dump(ref, f, ensure_ascii=False, indent=2)
    return ref
