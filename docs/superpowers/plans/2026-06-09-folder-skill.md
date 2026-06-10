# Skill `folder` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `folder` skill — from a photo OR a text, produce a reference sheet (model sheet) as `folder.png` + editable `folder.html` + raw `assets/` + a locked `referencia.json`, using the **textless + layer** architecture (flux2-klein generates images, HTML/CSS carries layout+text, headless Chromium renders to PNG).

**Architecture:** A Python pipeline (`build_folder.py`) wires small single-responsibility helpers: an `inemaimg` HTTP client, a fixed-slot HTML template filler, a Chromium screenshotter, and a `referencia.json` builder. Two layout templates (`editorial-revista`, `dossie`) × two art styles (`foto`, `cartoon`) are combinable. The image engine is isolated to one client call so it can be swapped (flux2-klein default → qwen-edit-2511 fallback) without touching the pipeline.

**Tech Stack:** Python 3.12 (stdlib only: `urllib`, `base64`, `json`), headless Chromium (`~/.cache/ms-playwright/chromium-*/chrome-linux/chrome`), `inemaimg` local server at `http://localhost:8000`. Tests are dependency-free standalone scripts run with `python3`.

---

## File Structure

```
inemaref/skill/folder/
  SKILL.md                       # the skill: how Claude collects input + invokes the pipeline
  scripts/
    png_size.py                  # read PNG IHDR -> (width,height); no Pillow
    render.py                    # find_chromium() + render_html_to_png()
    imgclient.py                 # generate() -> POST inemaimg /generate, save PNG
    artes.py                     # load_arte() from referencias/artes.json + build_prompts()
    fill_template.py             # fill() ficha+images -> html string (fixed slots)
    referencia.py                # build_referencia() + validate_referencia()
    build_folder.py              # orchestrator (dependency-injectable generate_fn/render_fn)
  templates/
    editorial-revista/{template.html, style.css, meta.json}
    dossie/{template.html, style.css, meta.json}
  tests/
    test_png_size.py
    test_render.py
    test_fill_template.py
    test_referencia.py
    test_build_folder.py
    fixtures/ficha-exemplo.json
inemaref/skill/referencias/
  artes.json                     # machine source: prompt fragments per art style
  artes.md                       # human doc explaining the art styles
  consistencia.md                # identity-locking rule (aparencia field)
  referencia.schema.json         # contract for referencia.json
```

Each test file ends with `if __name__ == "__main__":` running every test fn and printing `OK`, so it runs with plain `python3` (no pytest needed). Tests add `scripts/` to `sys.path`.

---

## Task 0: Scaffolding

**Files:**
- Create: `inemaref/skill/folder/scripts/.keep`, `inemaref/skill/folder/tests/.keep`, `inemaref/skill/folder/templates/.keep`

- [ ] **Step 1: Create directories**

```bash
cd ~/projetos/inemaref
mkdir -p skill/folder/scripts skill/folder/tests/fixtures skill/folder/templates skill/referencias
touch skill/folder/scripts/.keep skill/folder/tests/.keep
```

- [ ] **Step 2: Commit**

```bash
git add skill/folder skill/referencias
git commit -m "chore: scaffold folder skill dirs"
```

---

## Task 1: PNG size helper (`png_size.py`)

Dependency-free PNG dimension reader (used by tests and render verification). PNG width/height are big-endian uint32 at byte offsets 16 and 20 (inside the IHDR chunk).

**Files:**
- Create: `skill/folder/scripts/png_size.py`
- Test: `skill/folder/tests/test_png_size.py`

- [ ] **Step 1: Write the failing test**

```python
# skill/folder/tests/test_png_size.py
import os, sys, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from png_size import png_size

# 2x1 red PNG, base64
PNG_2x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAEklEQVR4nGP8z8Dwn4EIwDiqEAARWAIBLb0nawAAAABJRU5ErkJggg=="
)

def test_reads_dimensions(tmp="/tmp/_pngsize_test.png"):
    with open(tmp, "wb") as f:
        f.write(PNG_2x1)
    assert png_size(tmp) == (2, 1)

if __name__ == "__main__":
    test_reads_dimensions()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/folder/tests/test_png_size.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'png_size'`

- [ ] **Step 3: Write minimal implementation**

```python
# skill/folder/scripts/png_size.py
import struct

def png_size(path):
    """Return (width, height) of a PNG by reading its IHDR chunk."""
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    width, height = struct.unpack(">II", head[16:24])
    return (width, height)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_png_size.py`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add skill/folder/scripts/png_size.py skill/folder/tests/test_png_size.py
git commit -m "feat(folder): png_size helper"
```

---

## Task 2: HTML→PNG renderer (`render.py`)

**Files:**
- Create: `skill/folder/scripts/render.py`
- Test: `skill/folder/tests/test_render.py`

- [ ] **Step 1: Write the failing test**

```python
# skill/folder/tests/test_render.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from render import render_html_to_png
from png_size import png_size

def test_renders_fixed_size(tmpdir="/tmp/_render_test"):
    os.makedirs(tmpdir, exist_ok=True)
    html = os.path.join(tmpdir, "p.html")
    png = os.path.join(tmpdir, "p.png")
    with open(html, "w") as f:
        f.write("<html><body style='margin:0;background:#c00'></body></html>")
    render_html_to_png(html, png, 400, 300)
    assert os.path.exists(png), "png not produced"
    assert png_size(png) == (400, 300), f"got {png_size(png)}"

if __name__ == "__main__":
    test_renders_fixed_size()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/folder/tests/test_render.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'render'`

- [ ] **Step 3: Write minimal implementation**

```python
# skill/folder/scripts/render.py
import glob, os, subprocess

def find_chromium():
    """Locate a Chromium binary: env override, ms-playwright cache, then PATH."""
    env = os.environ.get("CHROMIUM_BIN")
    if env and os.path.exists(env):
        return env
    cache = os.path.expanduser("~/.cache/ms-playwright")
    hits = sorted(glob.glob(os.path.join(cache, "chromium-*/chrome-linux/chrome")))
    if hits:
        return hits[-1]  # highest version
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        from shutil import which
        p = which(name)
        if p:
            return p
    raise RuntimeError("no Chromium binary found (set CHROMIUM_BIN)")

def render_html_to_png(html_path, png_path, width, height):
    """Screenshot a local HTML file to PNG at an exact pixel size."""
    chrome = find_chromium()
    url = "file://" + os.path.abspath(html_path)
    cmd = [
        chrome, "--headless=new", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--screenshot={os.path.abspath(png_path)}",
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    if not os.path.exists(png_path):
        raise RuntimeError("chromium produced no screenshot")
    return png_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_render.py`
Expected: `OK`
(If FAIL on chromium discovery, run `ls ~/.cache/ms-playwright/chromium-*/chrome-linux/chrome` to confirm a binary exists; set `CHROMIUM_BIN` if needed.)

- [ ] **Step 5: Commit**

```bash
git add skill/folder/scripts/render.py skill/folder/tests/test_render.py
git commit -m "feat(folder): chromium html->png renderer"
```

---

## Task 3: inemaimg client (`imgclient.py`)

Isolated engine call — the **single swap point** (flux2-klein → qwen-edit-2511). Uses stdlib `urllib`.

**Files:**
- Create: `skill/folder/scripts/imgclient.py`
- Test: `skill/folder/tests/test_imgclient.py`

- [ ] **Step 1: Write the failing test** (tests payload construction + PNG decode via an injected opener; no live server)

```python
# skill/folder/tests/test_imgclient.py
import os, sys, json, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import imgclient
from png_size import png_size

PNG_2x1_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAABCAYAAAD0In+KAAAAEklEQVR4nGP8z8Dwn4EIwDiqEAARWAIBLb0nawAAAABJRU5ErkJggg=="

class FakeResp:
    def __init__(self, body): self._b = body
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False

def test_builds_payload_and_saves(tmp="/tmp/_imgclient_out.png"):
    captured = {}
    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return FakeResp(json.dumps({"image": PNG_2x1_B64}).encode())
    imgclient._urlopen = fake_urlopen  # inject
    imgclient.generate("a cat", tmp, model="flux2-klein", width=2, height=1,
                       images=["/tmp/_imgclient_out_ref.png"] if False else None,
                       negative_prompt="text")
    assert captured["url"].endswith("/generate")
    assert captured["body"]["model"] == "flux2-klein"
    assert captured["body"]["prompt"] == "a cat"
    assert captured["body"]["width"] == 2 and captured["body"]["height"] == 1
    assert captured["body"]["negative_prompt"] == "text"
    assert png_size(tmp) == (2, 1)

if __name__ == "__main__":
    test_builds_payload_and_saves()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/folder/tests/test_imgclient.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'imgclient'`

- [ ] **Step 3: Write minimal implementation**

```python
# skill/folder/scripts/imgclient.py
import base64, json, urllib.request

BASE_URL = "http://localhost:8000"
_urlopen = urllib.request.urlopen  # seam for tests

def _b64_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def generate(prompt, out_path, model="flux2-klein", width=None, height=None,
             images=None, negative_prompt=None, seed=None, base_url=BASE_URL):
    """POST inemaimg /generate and save the returned PNG to out_path.

    images: optional list of reference image file paths (used by edit models
    like qwen-edit-2511; flux2-klein may ignore them — that is the documented
    fallback seam, see referencias/consistencia.md)."""
    payload = {"model": model, "prompt": prompt}
    if width:  payload["width"] = width
    if height: payload["height"] = height
    if negative_prompt: payload["negative_prompt"] = negative_prompt
    if seed is not None: payload["seed"] = seed
    if images: payload["images"] = [_b64_file(p) for p in images]
    req = urllib.request.Request(
        base_url + "/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data["image"]))
    return out_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_imgclient.py`
Expected: `OK`

- [ ] **Step 5: Live smoke (manual, skippable)**

Run (only if inemaimg is up): `curl -s http://localhost:8000/health`
Expected: JSON with `"status"`/`loaded_model`. If down, the live e2e in Task 9 is what exercises the real call.

- [ ] **Step 6: Commit**

```bash
git add skill/folder/scripts/imgclient.py skill/folder/tests/test_imgclient.py
git commit -m "feat(folder): inemaimg generate client (engine swap seam)"
```

---

## Task 4: Art-style fragments + prompt builder (`artes.json`, `artes.py`)

**Files:**
- Create: `skill/referencias/artes.json`
- Create: `skill/folder/scripts/artes.py`
- Test: `skill/folder/tests/test_artes.py`

- [ ] **Step 1: Create the art fragments file**

```json
// skill/referencias/artes.json
{
  "foto": {
    "positivo": "photorealistic, editorial magazine photography, natural soft lighting, sharp focus, shallow depth of field, high detail skin texture",
    "negativo": "text, letters, words, watermark, logo, caption, signature, lowres, blurry, deformed, extra fingers"
  },
  "cartoon": {
    "positivo": "illustrated cartoon style, watercolor and gouache, clean confident lineart, vivid saturated colors, soft cel shading, storybook illustration",
    "negativo": "text, letters, words, watermark, logo, caption, signature, photorealistic, 3d render, lowres, deformed"
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# skill/folder/tests/test_artes.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from artes import load_arte, build_prompts

def test_load_arte():
    a = load_arte("foto")
    assert "photorealistic" in a["positivo"]
    assert "text" in a["negativo"]

def test_build_prompts_shape():
    ficha = {"aparencia": "an 84yo woman with short white hair",
             "focos": [{"legenda": "Setup de confianca"}, {"legenda": "Pe firme"},
                       {"legenda": "Atitude"}, {"legenda": "Movimento"}, {"legenda": "Aventura"}]}
    p = build_prompts(ficha, "foto")
    assert "an 84yo woman" in p["retrato"]
    assert "photorealistic" in p["retrato"]
    assert "no text" in p["retrato"]
    assert len(p["focos"]) == 5
    assert "setup de confianca" in p["focos"][0].lower()

if __name__ == "__main__":
    test_load_arte(); test_build_prompts_shape(); print("OK")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 skill/folder/tests/test_artes.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'artes'`

- [ ] **Step 4: Write minimal implementation**

```python
# skill/folder/scripts/artes.py
import json, os

_ARTES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "referencias", "artes.json")

def load_arte(arte):
    with open(_ARTES_PATH) as f:
        data = json.load(f)
    if arte not in data:
        raise ValueError(f"unknown art style: {arte} (have {list(data)})")
    return data[arte]

def build_prompts(ficha, arte):
    """Build textless prompts: 1 big portrait + 5 'detalhes em foco' shots."""
    a = load_arte(arte)
    aparencia = ficha["aparencia"].strip().rstrip(".")
    base = f"{aparencia}, {a['positivo']}, plain neutral background, no text"
    retrato = f"{base}, head-and-shoulders portrait, looking at camera"
    focos = []
    for foco in ficha["focos"][:5]:
        scene = foco["legenda"].strip().lower()
        focos.append(f"{base}, {scene}, candid close detail")
    return {"retrato": retrato, "focos": focos, "negativo": a["negativo"]}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_artes.py`
Expected: `OK`

- [ ] **Step 6: Create the human doc**

```markdown
<!-- skill/referencias/artes.md -->
# Estilos de arte

Fragmentos de prompt em `artes.json` (fonte de verdade do código). Dois estilos:

- **foto** — foto-realista, fotografia editorial de revista. Para fichas de pessoas reais.
- **cartoon** — ilustração aquarela/gouache, lineart, cores vivas. Para personagens ilustrados.

Cada estilo tem `positivo` (injetado no prompt) e `negativo` (negative prompt — sempre proíbe
texto/letras, porque a arquitetura é *textless*: o texto é a camada HTML).

Adicionar um estilo = adicionar uma chave em `artes.json`.
```

- [ ] **Step 7: Commit**

```bash
git add skill/referencias/artes.json skill/referencias/artes.md skill/folder/scripts/artes.py skill/folder/tests/test_artes.py
git commit -m "feat(folder): art-style fragments + prompt builder"
```

---

## Task 5: Template filler (`fill_template.py`) + `editorial-revista` template

Fixed-slot templating: scalar `{{key}}` placeholders + pre-built HTML fragments for the repeated regions (`{{personalidade_html}}`, `{{caracteristicas_html}}`, `{{detalhes_html}}`) + 5 fixed foco slots. The filler asserts **no `{{` remains** after substitution.

**Files:**
- Create: `skill/folder/templates/editorial-revista/template.html`
- Create: `skill/folder/templates/editorial-revista/style.css`
- Create: `skill/folder/templates/editorial-revista/meta.json`
- Create: `skill/folder/scripts/fill_template.py`
- Create: `skill/folder/tests/fixtures/ficha-exemplo.json`
- Test: `skill/folder/tests/test_fill_template.py`

- [ ] **Step 1: Create the example ficha fixture**

```json
// skill/folder/tests/fixtures/ficha-exemplo.json
{
  "id": "ideni-maldaner",
  "kicker": "PERFIL DO PERSONAGEM",
  "nome": "IDENI MALDANER",
  "subtitulo": "RADICAL ATE NA ALMA",
  "aparencia": "an 84-year-old woman, short white hair, warm smile, beige winter jacket",
  "personalidade": ["Corajosa sob pressao.", "Energia que surpreende.", "Atitude com humor."],
  "caracteristicas": [
    {"icone": "⚡", "label": "Coragem radical"},
    {"icone": "💎", "label": "Estilo atemporal"},
    {"icone": "🌟", "label": "Energia contagiante"}
  ],
  "detalhes": [
    {"k": "NOME", "v": "Ideni Maldaner"},
    {"k": "IDADE", "v": "84"},
    {"k": "ESTILO", "v": "Radical chique"}
  ],
  "frase": "Vamos sem feले?",
  "focos": [
    {"legenda": "SETUP DE CONFIANCA"},
    {"legenda": "PE FIRME"},
    {"legenda": "ATITUDE ASSINATURA"},
    {"legenda": "ESTILO EM MOVIMENTO"},
    {"legenda": "MARCAS DE AVENTURA"}
  ]
}
```

- [ ] **Step 2: Create the template HTML**

```html
<!-- skill/folder/templates/editorial-revista/template.html -->
<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"><link rel="stylesheet" href="style.css"></head>
<body>
  <main class="folder">
    <header class="kicker">{{kicker}}</header>
    <section class="hero">
      <div class="hero-text">
        <h1 class="nome">{{nome}}</h1>
        <p class="subtitulo">{{subtitulo}}</p>
        <div class="frase">{{frase}}</div>
      </div>
      <img class="retrato" src="{{img_retrato}}" alt="">
    </section>
    <aside class="col-direita">
      <h2>PERSONALIDADE</h2>
      <div class="personalidade">{{personalidade_html}}</div>
      <h2>CARACTERISTICAS PRINCIPAIS</h2>
      <div class="caracteristicas">{{caracteristicas_html}}</div>
      <h2>DETALHES</h2>
      <div class="detalhes">{{detalhes_html}}</div>
    </aside>
    <section class="focos">
      <h2>DETALHES EM FOCO</h2>
      <div class="focos-grid">
        <figure><img src="{{foco1_img}}" alt=""><figcaption>{{foco1_legenda}}</figcaption></figure>
        <figure><img src="{{foco2_img}}" alt=""><figcaption>{{foco2_legenda}}</figcaption></figure>
        <figure><img src="{{foco3_img}}" alt=""><figcaption>{{foco3_legenda}}</figcaption></figure>
        <figure><img src="{{foco4_img}}" alt=""><figcaption>{{foco4_legenda}}</figcaption></figure>
        <figure><img src="{{foco5_img}}" alt=""><figcaption>{{foco5_legenda}}</figcaption></figure>
      </div>
    </section>
  </main>
</body>
</html>
```

- [ ] **Step 3: Create the template CSS** (editorial look; fixed 1200×1600 canvas)

```css
/* skill/folder/templates/editorial-revista/style.css */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: 1200px; height: 1600px; background: #f4f1ec; font-family: Georgia, "Times New Roman", serif; color: #1a1a1a; }
.folder { width: 1200px; height: 1600px; padding: 56px 56px 40px; display: grid;
  grid-template-columns: 1fr 320px; grid-template-rows: auto 1fr auto; gap: 28px 40px; }
.kicker { grid-column: 1 / -1; letter-spacing: .28em; font-size: 13px; text-transform: uppercase; border-bottom: 2px solid #1a1a1a; padding-bottom: 10px; }
.hero { position: relative; display: flex; align-items: flex-end; }
.hero-text { position: absolute; left: 0; bottom: 0; z-index: 2; max-width: 70%; }
.nome { font-family: "Arial Black", Helvetica, sans-serif; font-weight: 900; font-size: 92px; line-height: .92; letter-spacing: -.02em; text-transform: uppercase; }
.subtitulo { margin-top: 14px; letter-spacing: .22em; font-size: 14px; text-transform: uppercase; }
.frase { margin-top: 18px; font-style: italic; font-size: 17px; max-width: 320px; color: #333; }
.retrato { width: 100%; height: 100%; object-fit: cover; filter: saturate(1.02); }
.col-direita h2 { font-family: Helvetica, sans-serif; font-size: 15px; letter-spacing: .12em; margin: 22px 0 10px; border-bottom: 1px solid #1a1a1a; padding-bottom: 6px; }
.col-direita h2:first-child { margin-top: 0; }
.personalidade p { font-size: 15px; line-height: 1.55; }
.caracteristicas .row { display: flex; align-items: center; gap: 12px; font-size: 15px; padding: 7px 0; }
.caracteristicas .icone { width: 26px; text-align: center; font-size: 18px; }
.detalhes .row { display: flex; justify-content: space-between; font-size: 13px; padding: 5px 0; border-bottom: 1px dotted #bbb; }
.detalhes .k { letter-spacing: .08em; color: #666; }
.focos { grid-column: 1 / -1; }
.focos h2 { font-family: Helvetica, sans-serif; font-size: 15px; letter-spacing: .12em; border-bottom: 1px solid #1a1a1a; padding-bottom: 6px; margin-bottom: 14px; }
.focos-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.focos-grid figure { display: flex; flex-direction: column; gap: 8px; }
.focos-grid img { width: 100%; aspect-ratio: 1/1; object-fit: cover; }
.focos-grid figcaption { font-family: Helvetica, sans-serif; font-size: 10px; letter-spacing: .1em; text-align: center; color: #444; }
```

- [ ] **Step 4: Create the template meta**

```json
// skill/folder/templates/editorial-revista/meta.json
{ "nome": "Editorial Revista", "descricao": "Layout de perfil estilo revista (look dos exemplos).",
  "width": 1200, "height": 1600,
  "slots": { "retrato": {"width": 832, "height": 1216}, "foco": {"width": 768, "height": 768} } }
```

- [ ] **Step 5: Write the failing test**

```python
# skill/folder/tests/test_fill_template.py
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fill_template import fill

TPL = os.path.join(os.path.dirname(__file__), "..", "templates", "editorial-revista")
FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))
IMAGES = {"retrato": "assets/retrato.png",
          "focos": [f"assets/foco{i}.png" for i in range(1, 6)]}

def test_fill_replaces_all_placeholders():
    html = fill(TPL, FICHA, IMAGES)
    assert "{{" not in html, "unreplaced placeholder remains"
    assert "IDENI MALDANER" in html
    assert "assets/retrato.png" in html
    assert "assets/foco5.png" in html
    assert "SETUP DE CONFIANCA" in html
    assert "Coragem radical" in html
    assert "Corajosa sob pressao." in html

def test_fill_rejects_wrong_foco_count():
    bad = dict(FICHA); bad["focos"] = FICHA["focos"][:3]
    try:
        fill(TPL, bad, IMAGES); assert False, "should have raised"
    except ValueError:
        pass

if __name__ == "__main__":
    test_fill_replaces_all_placeholders(); test_fill_rejects_wrong_foco_count(); print("OK")
```

- [ ] **Step 6: Run test to verify it fails**

Run: `python3 skill/folder/tests/test_fill_template.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'fill_template'`

- [ ] **Step 7: Write minimal implementation**

```python
# skill/folder/scripts/fill_template.py
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
```

- [ ] **Step 8: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_fill_template.py`
Expected: `OK`

- [ ] **Step 9: Visual sanity render (manual)** — fill with placeholder grey images and eyeball the layout.

```bash
python3 - <<'PY'
import os, sys, json
sys.path.insert(0, "skill/folder/scripts")
from fill_template import fill
from render import render_html_to_png
tpl = "skill/folder/templates/editorial-revista"
ficha = json.load(open("skill/folder/tests/fixtures/ficha-exemplo.json"))
out = "/tmp/_folder_preview"; os.makedirs(out+"/assets", exist_ok=True)
# 1x1 grey png placeholder copied to each slot
import base64
GREY = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
for n in ["retrato"]+[f"foco{i}" for i in range(1,6)]:
    open(f"{out}/assets/{n}.png","wb").write(GREY)
html = fill(tpl, ficha, {"retrato":"assets/retrato.png","focos":[f"assets/foco{i}.png" for i in range(1,6)]})
open(f"{out}/folder.html","w").write(html)
render_html_to_png(f"{out}/folder.html", f"{out}/folder.png", 1200, 1600)
print("preview:", f"{out}/folder.png")
PY
```
Open `/tmp/_folder_preview/folder.png` with the Read tool and confirm: no overflow, all sections present, text legible.

- [ ] **Step 10: Commit**

```bash
git add skill/folder/templates/editorial-revista skill/folder/scripts/fill_template.py skill/folder/tests/test_fill_template.py skill/folder/tests/fixtures/ficha-exemplo.json
git commit -m "feat(folder): editorial-revista template + fill_template"
```

---

## Task 6: Second layout template (`dossie`)

A distinct layout that reuses the **same placeholders** as `editorial-revista`, proving the template system is swappable with no code change.

**Files:**
- Create: `skill/folder/templates/dossie/template.html`
- Create: `skill/folder/templates/dossie/style.css`
- Create: `skill/folder/templates/dossie/meta.json`
- Test: `skill/folder/tests/test_dossie_fill.py`

- [ ] **Step 1: Create `dossie` template.html** (same placeholders, dossier/file framing — retrato left, data right, focos as a bottom evidence strip)

```html
<!-- skill/folder/templates/dossie/template.html -->
<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"><link rel="stylesheet" href="style.css"></head>
<body>
  <main class="dossie">
    <header class="topbar"><span class="kicker">{{kicker}}</span><span class="tag">DOSSIE</span></header>
    <section class="body">
      <div class="left"><img class="retrato" src="{{img_retrato}}" alt="">
        <div class="frase">{{frase}}</div></div>
      <div class="right">
        <h1 class="nome">{{nome}}</h1>
        <p class="subtitulo">{{subtitulo}}</p>
        <h2>PERSONALIDADE</h2><div class="personalidade">{{personalidade_html}}</div>
        <h2>CARACTERISTICAS</h2><div class="caracteristicas">{{caracteristicas_html}}</div>
        <h2>DETALHES</h2><div class="detalhes">{{detalhes_html}}</div>
      </div>
    </section>
    <section class="focos">
      <div class="focos-grid">
        <figure><img src="{{foco1_img}}" alt=""><figcaption>{{foco1_legenda}}</figcaption></figure>
        <figure><img src="{{foco2_img}}" alt=""><figcaption>{{foco2_legenda}}</figcaption></figure>
        <figure><img src="{{foco3_img}}" alt=""><figcaption>{{foco3_legenda}}</figcaption></figure>
        <figure><img src="{{foco4_img}}" alt=""><figcaption>{{foco4_legenda}}</figcaption></figure>
        <figure><img src="{{foco5_img}}" alt=""><figcaption>{{foco5_legenda}}</figcaption></figure>
      </div>
    </section>
  </main>
</body>
</html>
```

- [ ] **Step 2: Create `dossie` style.css** (1200×1600, darker dossier aesthetic)

```css
/* skill/folder/templates/dossie/style.css */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: 1200px; height: 1600px; background: #14161a; color: #e8e6e1; font-family: "Courier New", monospace; }
.dossie { width: 1200px; height: 1600px; padding: 48px; display: flex; flex-direction: column; gap: 24px; }
.topbar { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #c9a24b; padding-bottom: 12px; }
.kicker { letter-spacing: .28em; font-size: 13px; color: #c9a24b; }
.tag { font-weight: bold; letter-spacing: .2em; color: #c9a24b; border: 1px solid #c9a24b; padding: 4px 12px; }
.body { display: grid; grid-template-columns: 480px 1fr; gap: 36px; flex: 1; }
.left { display: flex; flex-direction: column; gap: 16px; }
.retrato { width: 100%; height: 980px; object-fit: cover; border: 3px solid #c9a24b; }
.frase { font-style: italic; font-size: 16px; color: #c9a24b; }
.nome { font-family: Arial, sans-serif; font-weight: 900; font-size: 64px; line-height: .95; letter-spacing: -.01em; }
.subtitulo { margin: 10px 0 18px; letter-spacing: .22em; font-size: 13px; color: #9aa0a6; }
.right h2 { font-size: 14px; letter-spacing: .14em; color: #c9a24b; margin: 20px 0 8px; border-bottom: 1px solid #3a3f46; padding-bottom: 5px; }
.personalidade p { font-size: 14px; line-height: 1.6; }
.caracteristicas .row { display: flex; gap: 12px; align-items: center; padding: 6px 0; font-size: 14px; }
.caracteristicas .icone { width: 24px; text-align: center; }
.detalhes .row { display: flex; justify-content: space-between; font-size: 12px; padding: 5px 0; border-bottom: 1px dotted #3a3f46; }
.detalhes .k { color: #9aa0a6; }
.focos-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.focos-grid figure { display: flex; flex-direction: column; gap: 6px; }
.focos-grid img { width: 100%; aspect-ratio: 1/1; object-fit: cover; border: 2px solid #3a3f46; }
.focos-grid figcaption { font-size: 9px; letter-spacing: .1em; text-align: center; color: #9aa0a6; }
```

- [ ] **Step 3: Create `dossie` meta.json**

```json
// skill/folder/templates/dossie/meta.json
{ "nome": "Dossie", "descricao": "Layout de dossie/ficha tecnica, fundo escuro e dourado.",
  "width": 1200, "height": 1600,
  "slots": { "retrato": {"width": 832, "height": 1216}, "foco": {"width": 768, "height": 768} } }
```

- [ ] **Step 4: Write the test** (same fill, different template, all placeholders replaced)

```python
# skill/folder/tests/test_dossie_fill.py
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from fill_template import fill

TPL = os.path.join(os.path.dirname(__file__), "..", "templates", "dossie")
FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))
IMAGES = {"retrato": "assets/retrato.png", "focos": [f"assets/foco{i}.png" for i in range(1, 6)]}

def test_dossie_fills_clean():
    html = fill(TPL, FICHA, IMAGES)
    assert "{{" not in html
    assert "IDENI MALDANER" in html and "DOSSIE" in html

if __name__ == "__main__":
    test_dossie_fills_clean(); print("OK")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_dossie_fill.py`
Expected: `OK` (it passes immediately — `fill` already exists; this guards the template's placeholder set)

- [ ] **Step 6: Commit**

```bash
git add skill/folder/templates/dossie skill/folder/tests/test_dossie_fill.py
git commit -m "feat(folder): dossie layout template"
```

---

## Task 7: `referencia.json` builder + schema (`referencia.py`, `referencia.schema.json`)

**Files:**
- Create: `skill/referencias/referencia.schema.json`
- Create: `skill/folder/scripts/referencia.py`
- Test: `skill/folder/tests/test_referencia.py`

- [ ] **Step 1: Create the schema (contract/doc)**

```json
// skill/referencias/referencia.schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "referencia",
  "type": "object",
  "required": ["id", "modo", "nome", "arte", "aparencia", "retrato_ancora", "ficha"],
  "properties": {
    "id": {"type": "string"},
    "modo": {"enum": ["foto", "texto"]},
    "nome": {"type": "string"},
    "idade": {"type": ["integer", "null"]},
    "arte": {"enum": ["foto", "cartoon"]},
    "aparencia": {"type": "string", "minLength": 1},
    "retrato_ancora": {"type": "string"},
    "foto_origem": {"type": ["string", "null"]},
    "ficha": {"type": "object"}
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# skill/folder/tests/test_referencia.py
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from referencia import build_referencia, validate_referencia

FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))

def test_build_and_validate_ok():
    ref = build_referencia(FICHA, modo="texto", arte="foto",
                           retrato_ancora="assets/retrato.png", foto_origem=None)
    assert ref["id"] == "ideni-maldaner"
    assert ref["modo"] == "texto" and ref["arte"] == "foto"
    assert ref["aparencia"].startswith("an 84-year-old")
    assert ref["ficha"]["nome"] == "IDENI MALDANER"
    validate_referencia(ref)  # must not raise

def test_validate_rejects_bad_modo():
    ref = build_referencia(FICHA, modo="texto", arte="foto",
                           retrato_ancora="x.png", foto_origem=None)
    ref["modo"] = "video"
    try:
        validate_referencia(ref); assert False, "should reject bad modo"
    except ValueError:
        pass

if __name__ == "__main__":
    test_build_and_validate_ok(); test_validate_rejects_bad_modo(); print("OK")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 skill/folder/tests/test_referencia.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'referencia'`

- [ ] **Step 4: Write minimal implementation** (dependency-free validator — no `jsonschema` install)

```python
# skill/folder/scripts/referencia.py
def build_referencia(ficha, modo, arte, retrato_ancora, foto_origem):
    idade = None
    for d in ficha.get("detalhes", []):
        if d.get("k", "").upper() == "IDADE":
            try: idade = int(d["v"])
            except (ValueError, TypeError): idade = None
    return {
        "id": ficha["id"],
        "modo": modo,
        "nome": ficha["nome"],
        "idade": idade,
        "arte": arte,
        "aparencia": ficha["aparencia"],
        "retrato_ancora": retrato_ancora,
        "foto_origem": foto_origem,
        "ficha": ficha,
    }

def validate_referencia(ref):
    """Minimal validator matching referencia.schema.json. Raises ValueError."""
    required = ["id", "modo", "nome", "arte", "aparencia", "retrato_ancora", "ficha"]
    for k in required:
        if k not in ref:
            raise ValueError(f"missing required field: {k}")
    if ref["modo"] not in ("foto", "texto"):
        raise ValueError(f"invalid modo: {ref['modo']}")
    if ref["arte"] not in ("foto", "cartoon"):
        raise ValueError(f"invalid arte: {ref['arte']}")
    if not isinstance(ref["aparencia"], str) or not ref["aparencia"].strip():
        raise ValueError("aparencia must be a non-empty string")
    if not isinstance(ref["ficha"], dict):
        raise ValueError("ficha must be an object")
    return True
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_referencia.py`
Expected: `OK`

- [ ] **Step 6: Create the identity-locking doc**

```markdown
<!-- skill/referencias/consistencia.md -->
# Consistencia da pessoa (campo `aparencia`)

`aparencia` (em `referencia.json`) e o "prompt de identidade" reutilizavel: uma descricao textual
estavel da pessoa/personagem (idade, cabelo, rosto, marca registrada), injetada em TODO prompt de
imagem — no folder e, depois, nos quadros do `quadrinho`. E o que mantem a pessoa igual.

## Modo foto vs modo texto
- **texto** — personagem inventado; `aparencia` e escrita pelo Claude a partir da historia.
- **foto** — pessoa real; `aparencia` descreve a foto, e a foto e passada como `images=[...]` ao
  motor (`imgclient.generate`).

## Seam de troca de motor (a decisao do brainstorming)
Padrao: `flux2-klein` (T2I). Como flux ignora `images`, o rosto pode nao fixar no modo foto. Se o
teste de aceitacao (Task 9) mostrar deriva de rosto, trocar `model="flux2-klein"` por
`model="qwen-edit-2511"` em `build_folder.py` (tarefas face-swap/multiple-angles, que usam `images`).
E uma troca de uma linha — nenhuma outra parte muda.
```

- [ ] **Step 7: Commit**

```bash
git add skill/referencias/referencia.schema.json skill/referencias/consistencia.md skill/folder/scripts/referencia.py skill/folder/tests/test_referencia.py
git commit -m "feat(folder): referencia.json builder + schema + consistencia doc"
```

---

## Task 8: Orchestrator (`build_folder.py`)

Wires everything. **Dependency-injectable** `generate_fn`/`render_fn` so the integration test runs with fake image generation (no live server).

**Files:**
- Create: `skill/folder/scripts/build_folder.py`
- Test: `skill/folder/tests/test_build_folder.py`

- [ ] **Step 1: Write the failing integration test** (fake generate_fn writes a real grey PNG to each slot; uses the real fill + real render)

```python
# skill/folder/tests/test_build_folder.py
import os, sys, json, base64, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from build_folder import build_folder
from referencia import validate_referencia
from png_size import png_size

GREY = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
FICHA = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "ficha-exemplo.json")))
TPL = os.path.join(os.path.dirname(__file__), "..", "templates", "editorial-revista")

def fake_generate(prompt, out_path, **kw):
    with open(out_path, "wb") as f: f.write(GREY)
    return out_path

def test_build_produces_all_artifacts(out="/tmp/_build_folder_test"):
    if os.path.exists(out): shutil.rmtree(out)
    ref = build_folder(FICHA, template_dir=TPL, arte="foto", out_dir=out,
                       modo="texto", foto_origem=None, generate_fn=fake_generate)
    base = os.path.join(out, FICHA["id"])
    assert os.path.exists(os.path.join(base, "folder.html"))
    assert os.path.exists(os.path.join(base, "folder.png"))
    assert png_size(os.path.join(base, "folder.png")) == (1200, 1600)
    assert os.path.exists(os.path.join(base, "assets", "retrato.png"))
    for i in range(1, 6):
        assert os.path.exists(os.path.join(base, "assets", f"foco{i}.png"))
    saved = json.load(open(os.path.join(base, "referencia.json")))
    validate_referencia(saved)
    assert saved == ref

if __name__ == "__main__":
    test_build_produces_all_artifacts(); print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/folder/tests/test_build_folder.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_folder'`

- [ ] **Step 3: Write minimal implementation**

```python
# skill/folder/scripts/build_folder.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/folder/tests/test_build_folder.py`
Expected: `OK`

- [ ] **Step 5: Run the whole suite**

```bash
for t in skill/folder/tests/test_*.py; do echo "== $t"; python3 "$t" || break; done
```
Expected: every file prints `OK`.

- [ ] **Step 6: Commit**

```bash
git add skill/folder/scripts/build_folder.py skill/folder/tests/test_build_folder.py
git commit -m "feat(folder): pipeline orchestrator (build_folder)"
```

---

## Task 9: Live end-to-end acceptance (real flux2-klein)

The real generative run — exercises `inemaimg`. **Requires the inemaimg server up.** This is the minimal consistency experiment from `docs/04`, scoped to the folder.

**Files:** none (verification run; outputs land in `/tmp/folder-e2e/`)

- [ ] **Step 1: Confirm the server is up**

Run: `curl -s http://localhost:8000/health`
Expected: JSON including `loaded_model`. If down, start inemaimg (`cd ~/projetos/inemaimg && docker compose up -d`) and wait for health.

- [ ] **Step 2: Run modo texto, editorial-revista, foto** (invented character)

```bash
python3 - <<'PY'
import sys, json
sys.path.insert(0, "skill/folder/scripts")
from build_folder import build_folder
ficha = json.load(open("skill/folder/tests/fixtures/ficha-exemplo.json"))
ref = build_folder(ficha, "skill/folder/templates/editorial-revista", arte="foto",
                   out_dir="/tmp/folder-e2e/texto-editorial", modo="texto")
print("done:", ref["id"])
PY
```
Open `/tmp/folder-e2e/texto-editorial/ideni-maldaner/folder.png` with the Read tool. Verify: 6 real images present, text legible, no overflow.

- [ ] **Step 3: Run the other 3 combos** (texto×dossie×cartoon, and a photo run if a real photo is available)

```bash
python3 - <<'PY'
import sys, json
sys.path.insert(0, "skill/folder/scripts")
from build_folder import build_folder
ficha = json.load(open("skill/folder/tests/fixtures/ficha-exemplo.json"))
combos = [
  ("skill/folder/templates/dossie", "cartoon", "/tmp/folder-e2e/texto-dossie-cartoon"),
  ("skill/folder/templates/editorial-revista", "cartoon", "/tmp/folder-e2e/texto-editorial-cartoon"),
]
for tpl, arte, out in combos:
    build_folder(ficha, tpl, arte=arte, out_dir=out, modo="texto")
    print("done:", out)
PY
```
For the **photo mode** check, place a real portrait at `/tmp/ref.jpg` and run with `modo="foto", foto_origem="/tmp/ref.jpg"`. Inspect whether the face holds across the 6 shots.

- [ ] **Step 4: Record the consistency verdict**

In `docs/04-consistencia-pessoa-real.md`, append a short note under a new `## Resultado (folder)` heading: did flux2-klein hold the face in photo mode? If not, follow `referencias/consistencia.md` to swap `model="qwen-edit-2511"` and re-run Step 3's photo case.

- [ ] **Step 5: Commit the verdict**

```bash
git add docs/04-consistencia-pessoa-real.md
git commit -m "docs: folder consistency verdict (flux2-klein e2e)"
```

---

## Task 10: `SKILL.md` (the skill entry point)

The prose the agent reads when the skill triggers: how to collect input, write the ficha, and invoke the pipeline.

**Files:**
- Create: `skill/folder/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

````markdown
---
name: folder
description: Cria a FICHA DE REFERENCIA (model sheet) de um personagem a partir de uma FOTO (pessoa real) ou de um TEXTO (descricao/historia). Saida = pagina editorial (folder.png) + folder.html editavel + assets/ (imagens cruas) + referencia.json travado. Use quando o usuario quiser "criar referencia", "ficha de personagem", "model sheet", "folder do personagem", ou der uma foto/historia e pedir a pagina de referencia do inemaref. Dois layouts (editorial-revista, dossie) x duas artes (foto, cartoon), combinaveis.
---

# Skill: folder — ficha de referencia (passo 0 do inemaref)

Arquitetura **textless + camada**: o flux2-klein gera so as imagens; o texto e o layout sao camada
HTML/CSS renderizada pra PNG. Detalhes em `docs/superpowers/specs/2026-06-09-folder-skill-design.md`.

## Entrada
- **Foto** (pessoa real) **ou** **texto** (descricao/historia). Um dos dois e obrigatorio.
- Opcionais: nome, idade, **arte** (`foto`|`cartoon`, default `foto`), **layout**
  (`editorial-revista`|`dossie`, default `editorial-revista`).

## Passos
1. **Monte a ficha** — produza um `ficha.json` no formato de
   `skill/folder/tests/fixtures/ficha-exemplo.json`:
   `id` (slug do nome), `kicker`, `nome`, `subtitulo`, `aparencia` (descricao reutilizavel da
   pessoa — ver `skill/referencias/consistencia.md`), `personalidade[]`, `caracteristicas[{icone,label}]`,
   `detalhes[{k,v}]` (inclua IDADE), `frase`, e **exatamente 5** `focos[{legenda}]`.
   - Modo texto: escreva os campos a partir da historia.
   - Modo foto: descreva a pessoa em `aparencia` e guarde o caminho da foto.
2. **Rode o pipeline:**
   ```bash
   python3 - <<'PY'
   import sys, json
   sys.path.insert(0, "skill/folder/scripts")
   from build_folder import build_folder
   ficha = json.load(open("CAMINHO/ficha.json"))
   build_folder(ficha,
       template_dir="skill/folder/templates/<layout>",
       arte="<foto|cartoon>",
       out_dir="<pasta de saida>",
       modo="<texto|foto>",
       foto_origem="<caminho da foto ou None>")
   PY
   ```
   (Pre-requisito: servidor `inemaimg` em `http://localhost:8000`.)
3. **Mostre** o `folder.png` ao usuario. Para ajustes de texto, edite `folder.html` e re-renderize
   com `skill/folder/scripts/render.py`. As imagens ficam em `assets/`; a referencia travada em
   `referencia.json` (consumida depois pela skill `quadrinho`).

## Estilos
- **Layout:** adicione uma pasta em `skill/folder/templates/` (template.html + style.css + meta.json,
  mesmos placeholders).
- **Arte:** adicione uma chave em `skill/referencias/artes.json`.

## Motor de imagem
Padrao `flux2-klein`. Se o rosto nao fixar no modo foto, troque para `qwen-edit-2511` (parametro
`model=` em `build_folder`) — ver `skill/referencias/consistencia.md`.
````

- [ ] **Step 2: Sanity-check the description triggers** — confirm the `description` names the verbs the user used ("criar referencia", "ficha de personagem", "model sheet", "folder").

- [ ] **Step 3: Commit**

```bash
git add skill/folder/SKILL.md
git commit -m "feat(folder): SKILL.md entry point"
```

---

## Task 11: Wire up the skill READMEs

Update the placeholder READMEs so the repo reflects the built skill.

**Files:**
- Modify: `skill/folder/README.md`
- Modify: `README.md` (root — "Estado" / "Skills" sections)

- [ ] **Step 1: Update `skill/folder/README.md`** — replace "Ainda não construída" with a one-paragraph pointer to `SKILL.md` and the spec/plan.

- [ ] **Step 2: Update root `README.md`** — in "Estado", note the `folder` skill is built (V1 começou); in "Skills (futuras)", drop `folder` from "futuras".

- [ ] **Step 3: Commit**

```bash
git add skill/folder/README.md README.md
git commit -m "docs: mark folder skill as built"
```

---

## Self-Review (done while writing)

- **Spec coverage:** §2 architecture B → Tasks 5/8; §2 two style axes → Tasks 5/6 (layout) + Task 4 (arte); §3 inputs/auto-fill → Task 10 SKILL.md; §4 pipeline → Task 8; §5 file structure → all; §6 referencia.json → Task 7; §7 outputs → Task 8 integration test asserts all 4; §8 sizing → meta.json (Tasks 5/6) consumed in Task 8; §9 inemaimg + render → Tasks 2/3; §10 verification 2×2×2 → Task 9; §3 engine-swap seam → Task 3 + consistencia.md (Task 7). Covered.
- **Placeholder scan:** every code step has full code; no TBD/TODO. The only deferred item (real qwen-edit swap) is explicitly out of scope per spec §11 and documented as a one-line change.
- **Type consistency:** `build_folder(ficha, template_dir, arte, out_dir, modo, foto_origem, model, generate_fn, render_fn)` consistent across Task 8 def and Task 9/10 calls; `fill(template_dir, ficha, images)` consistent Tasks 5/6/8; `generate(prompt, out_path, model, width, height, images, negative_prompt, seed, base_url)` consistent Tasks 3/8; `build_prompts(ficha, arte)` Tasks 4/8; `build_referencia(ficha, modo, arte, retrato_ancora, foto_origem)` + `validate_referencia(ref)` Tasks 7/8. Image src is relative in `fill`; `build_folder` rewrites the CSS href to absolute `file://` so Chromium resolves it from the output dir while keeping `assets/` paths relative (co-located with folder.html). Consistent.
