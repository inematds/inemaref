# Bloco Render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar a moldura escura da página por um layout "galeria" (mat branco + cabeçalho + gutters uniformes finos, variante dark/white), emitir uma cópia **textless** da página para o vídeo, abrir o vídeo com a narração-gancho em t=0, e padronizar o destino em `~/projetos/output/<id>`.

**Architecture:** Mudanças concentradas em 3 skills já existentes — `quadrinho` (CSS dos 2 templates + `fill_pagina`/`build_pagina`), `motioncomic` (`build_travel` usa textless + `build_motion._title_clip` ganha áudio), `serie` (`config` + `build_serie` repassam destino/moldura/kicker/accent). Reusa o motor textless+camada e o padrão de teste com Chromium real já presente em `quadrinho/tests`.

**Tech Stack:** Python 3 (stdlib), CSS, headless Chromium (screenshot), ffmpeg, inemavox TTS. Testes: scripts `test_*.py` rodáveis com `python3` (alguns renderizam com Chromium real, como os existentes).

---

## Estrutura de arquivos

- `skill/serie/scripts/config.py` — FALLBACK destino → `~/projetos/output`; novos defaults estilo `moldura`/`cor_destaque`.
- `skill/serie/config.yaml` — espelha os defaults acima.
- `skill/serie/scripts/build_serie.py` — expande destino; repassa `moldura`/`kicker`/`accent` ao montar páginas/vídeos.
- `skill/quadrinho/templates/{manga-dinamico,grade-uniforme}/style.css` — layout galeria com CSS vars.
- `skill/quadrinho/templates/{manga-dinamico,grade-uniforme}/template.html` — `{{kicker}}` no cabeçalho.
- `skill/quadrinho/scripts/fill_pagina.py` — `kicker` no repl.
- `skill/quadrinho/scripts/build_pagina.py` — params `moldura`/`kicker`/`accent`; injeta `:root`; emite `pagina-textless.png`.
- `skill/motioncomic/scripts/build_travel.py` — `_textless()`; câmera viaja sobre textless; repassa params; abertura em t=0.
- `skill/motioncomic/scripts/build_motion.py` — `_title_clip` aceita `audio`.
- `skill/{quadrinho,motioncomic,serie}/SKILL.md` — doc: A/B=formato, moldura, carrossel×vídeo, gancho.
- Testes novos: `skill/serie/tests/test_destino.py`, `skill/quadrinho/tests/test_moldura_textless.py`, `skill/motioncomic/tests/test_textless_path.py`.

---

### Task 1: Destino padrão `~/projetos/output` (R4)

**Files:**
- Modify: `skill/serie/scripts/config.py:12` (FALLBACK formato.destino)
- Modify: `skill/serie/config.yaml` (formato.destino)
- Modify: `skill/serie/scripts/build_serie.py:37,173-175`
- Test: `skill/serie/tests/test_destino.py`

- [ ] **Step 1: Write the failing test**

```python
# skill/serie/tests/test_destino.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import config

def test_fallback_destino_is_home_projetos_output():
    assert config.FALLBACK["formato"]["destino"] == "~/projetos/output"

def test_resolve_keeps_home_destino():
    flat = config.resolve({"id": "x"})
    assert flat["destino"] == "~/projetos/output"

def test_expanduser_resolves_outside_repo():
    p = os.path.expanduser(config.resolve({"id": "x"})["destino"])
    assert p == os.path.join(os.path.expanduser("~"), "projetos", "output")
    assert "~" not in p

if __name__ == "__main__":
    test_fallback_destino_is_home_projetos_output()
    test_resolve_keeps_home_destino()
    test_expanduser_resolves_outside_repo()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_destino.py`
Expected: AssertionError (destino ainda é `"output"`).

- [ ] **Step 3: Implement — config.py FALLBACK**

Em `skill/serie/scripts/config.py`, linha 12, troque `"destino": "output"` por:

```python
    "formato": {"tipo": "video-pagina", "n_episodios": 3, "n_paginas": 3, "destino": "~/projetos/output"},
```

- [ ] **Step 4: Implement — config.yaml**

Em `skill/serie/config.yaml`, na seção `formato`, troque a linha do destino por:

```yaml
  destino: ~/projetos/output    # pasta de saída -> <destino>/<serie-id>/ (+ manifesto.json)
```

- [ ] **Step 5: Implement — build_serie expande o destino**

Em `skill/serie/scripts/build_serie.py`, linha ~173, troque:

```python
    destino = out_dir or s["destino"] or "output"
```

por:

```python
    destino = os.path.expanduser(out_dir or s["destino"] or "~/projetos/output")
```

E em `build_biblia` (linha ~37), troque:

```python
    base_out = os.path.join(out_dir or "output", biblia["id"], "biblia")
```

por:

```python
    base_out = os.path.join(os.path.expanduser(out_dir or "~/projetos/output"), biblia["id"], "biblia")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_destino.py`
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add skill/serie/scripts/config.py skill/serie/config.yaml skill/serie/scripts/build_serie.py skill/serie/tests/test_destino.py
git commit -m "feat(serie): destino padrao ~/projetos/output (R4)"
```

---

### Task 2: Cabeçalho galeria + CSS vars nos dois templates (R1, parte A)

**Files:**
- Modify: `skill/quadrinho/templates/manga-dinamico/style.css`
- Modify: `skill/quadrinho/templates/grade-uniforme/style.css`
- Modify: `skill/quadrinho/templates/manga-dinamico/template.html:6`
- Modify: `skill/quadrinho/templates/grade-uniforme/template.html:6`
- Modify: `skill/quadrinho/scripts/fill_pagina.py:128`
- Test: `skill/quadrinho/tests/test_fill_pagina.py` (acrescenta um teste)

- [ ] **Step 1: Write the failing test**

Acrescente ao final de `skill/quadrinho/tests/test_fill_pagina.py` (antes do bloco `if __name__`):

```python
def test_fill_emits_kicker_div():
    rot = dict(ROT); rot["kicker"] = "A ESCADA INVISIVEL DE LIA"
    html = fill(GRADE, rot)
    assert 'class="kicker"' in html
    assert "A ESCADA INVISIVEL DE LIA" in html

def test_fill_kicker_empty_when_absent():
    html = fill(DINAM, ROT)  # ROT sem kicker
    assert 'class="kicker"' in html  # div existe, vazia
    assert "{{" not in html
```

E garanta que o `if __name__ == "__main__"` chama os dois novos testes.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/quadrinho/tests/test_fill_pagina.py`
Expected: falha — `class="kicker"` ainda não existe / placeholder `{{kicker}}` sem valor.

- [ ] **Step 3: Implement — `{{kicker}}` nos dois template.html**

Em **ambos** `manga-dinamico/template.html` e `grade-uniforme/template.html`, troque a linha 6:

```html
    <header class="cabecalho"><span class="titulo">{{titulo}}</span></header>
```

por:

```html
    <header class="cabecalho"><div class="kicker">{{kicker}}</div><div class="titulo">{{titulo}}</div></header>
```

- [ ] **Step 4: Implement — `fill` fornece `kicker`**

Em `skill/quadrinho/scripts/fill_pagina.py`, linha ~128, troque:

```python
    repl = {"titulo": _esc(roteiro.get("titulo", "")), "paineis_html": "".join(frags)}
```

por:

```python
    repl = {"titulo": _esc(roteiro.get("titulo", "")),
            "kicker": _esc(roteiro.get("kicker", "")),
            "paineis_html": "".join(frags)}
```

- [ ] **Step 5: Implement — style.css `manga-dinamico`**

Substitua **todo** o conteúdo de `skill/quadrinho/templates/manga-dinamico/style.css` por:

```css
:root { --gut: 9px; --gutter: #1b1b1b; --mat: 56px; --accent: #b08900; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: 1200px; height: 1600px; background: #fff; font-family: "Arial Black", Arial, sans-serif; color: #111; }
.pagina { width: 1200px; height: 1600px; display: flex; flex-direction: column; background: #fff; padding: var(--mat); }
.cabecalho { flex: 0 0 auto; padding: 0 0 28px; text-align: center; }
.kicker { font: 700 18px Arial, sans-serif; letter-spacing: .28em; color: var(--accent); text-transform: uppercase; margin-bottom: 10px; }
.kicker:empty { display: none; }
.titulo { font: 900 50px Georgia, "Times New Roman", serif; color: #111; }

/* dynamic manga layout — 6 panels, varied sizes */
.quadros { flex: 1; display: grid; gap: var(--gut); padding: var(--gut); background: var(--gutter);
  grid-template-columns: 1fr 1fr 1fr;
  grid-template-rows: 1.35fr 1fr 1fr 1fr;
  grid-template-areas:
    "p1 p1 p2"
    "p1 p1 p2"
    "p3 p4 p4"
    "p5 p5 p6"; }
.panel:nth-child(1) { grid-area: p1; }
.panel:nth-child(2) { grid-area: p2; }
.panel:nth-child(3) { grid-area: p3; }
.panel:nth-child(4) { grid-area: p4; }
.panel:nth-child(5) { grid-area: p5; }
.panel:nth-child(6) { grid-area: p6; }

.panel { position: relative; overflow: hidden; background: #000; }
.panel-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 28%; }

/* NARRACAO: default top-left, face_zones overrides via inline style */
.narracao { position: absolute; top: 0; left: 0; max-width: 70%; margin: 10px; padding: 8px 12px;
  background: rgba(255,255,255,.93); border: 2px solid #000; font-family: Georgia, "Times New Roman", serif;
  font-size: 17px; line-height: 1.28; color: #111; box-shadow: 3px 3px 0 rgba(0,0,0,.55); z-index: 2; }

/* FALA: default bottom-right, face_zones overrides via inline style */
.fala { position: absolute; right: 14px; bottom: 18px; max-width: 60%; margin: 12px; z-index: 2; }
.fala span { position: relative; display: inline-block; background: #fff; border: 2.5px solid #000;
  border-radius: 24px; padding: 10px 16px; font-family: Arial, sans-serif; font-weight: 700;
  font-size: 18px; color: #111; box-shadow: 2px 2px 0 rgba(0,0,0,.4); }
.fala span::after { content: ""; position: absolute; left: 26px; bottom: -15px;
  border: 10px solid transparent; border-top-color: #000; }

/* SFX: default top-right, face_zones overrides via inline style */
.sfx { position: absolute; right: 10px; top: 10px; margin: 10px; transform: rotate(-7deg);
  font-family: "Arial Black", sans-serif; font-weight: 900; font-size: 56px; color: #fff;
  -webkit-text-stroke: 3px #000; letter-spacing: .02em; text-shadow: 4px 4px 0 rgba(0,0,0,.6); z-index: 2; }
```

(Mudanças vs. original: `.pagina` fica branca com mat; cabeçalho galeria com `.kicker`+`.titulo`; `.quadros` ganha `padding`+`background` = gutter uniforme; `.panel` perde o `border: 3px solid #000` — a separação agora é o gutter. Grade e camadas de texto inalteradas.)

- [ ] **Step 6: Implement — style.css `grade-uniforme`**

Substitua **todo** o conteúdo de `skill/quadrinho/templates/grade-uniforme/style.css` pelo mesmo CSS do Step 5, **trocando apenas o bloco `.quadros`** por:

```css
.quadros { flex: 1; display: grid; gap: var(--gut); padding: var(--gut); background: var(--gutter);
  grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr 1fr; }
```

e **removendo** as 6 regras `.panel:nth-child(n) { grid-area: ... }` (a grade 2×3 não usa areas). Todo o resto (`:root`, `.pagina`, `.cabecalho`, `.kicker`, `.titulo`, `.panel`, `.panel-img`, `.narracao`, `.fala`, `.sfx`) é idêntico ao Step 5.

- [ ] **Step 7: Run tests to verify they pass**

Run: `python3 skill/quadrinho/tests/test_fill_pagina.py`
Expected: `OK`
Run: `python3 skill/quadrinho/tests/test_build_pagina.py`
Expected: `OK` (render real ainda produz `pagina.png` 1200×1600)

- [ ] **Step 8: Commit**

```bash
git add skill/quadrinho/templates skill/quadrinho/scripts/fill_pagina.py skill/quadrinho/tests/test_fill_pagina.py
git commit -m "feat(quadrinho): moldura galeria (mat branco + kicker + gutter uniforme) via CSS vars (R1)"
```

---

### Task 3: Param `moldura`/`kicker`/`accent` em `build_pagina` (R1, parte B)

**Files:**
- Modify: `skill/quadrinho/scripts/build_pagina.py:27-61`
- Test: `skill/quadrinho/tests/test_moldura_textless.py` (cria; parte moldura aqui)

- [ ] **Step 1: Write the failing test**

```python
# skill/quadrinho/tests/test_moldura_textless.py
import os, sys, json, base64, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
from build_pagina import build_pagina
from png_size import png_size

GREY = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
ROT = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "roteiro-visionario.json")))
DINAM = os.path.join(os.path.dirname(__file__), "..", "templates", "manga-dinamico")

def fake_generate(prompt, out_path, **kw):
    with open(out_path, "wb") as f: f.write(GREY)
    return out_path

def test_moldura_dark_injects_root(out="/tmp/_moldura_dark"):
    if os.path.exists(out): shutil.rmtree(out)
    build_pagina(ROT, DINAM, out_dir=out, generate_fn=fake_generate,
                 moldura="dark", kicker="SERIE X", accent="#e2a23b")
    html = open(os.path.join(out, ROT["id"], "pagina.html")).read()
    assert "--gutter:#1b1b1b" in html.replace(" ", "")
    assert "--accent:#e2a23b" in html.replace(" ", "")
    assert "SERIE X" in html

def test_moldura_white_injects_root(out="/tmp/_moldura_white"):
    if os.path.exists(out): shutil.rmtree(out)
    build_pagina(ROT, DINAM, out_dir=out, generate_fn=fake_generate, moldura="white")
    html = open(os.path.join(out, ROT["id"], "pagina.html")).read()
    assert "--gutter:#ffffff" in html.replace(" ", "")

if __name__ == "__main__":
    test_moldura_dark_injects_root()
    test_moldura_white_injects_root()
    print("OK moldura")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/quadrinho/tests/test_moldura_textless.py`
Expected: TypeError (build_pagina não aceita `moldura`).

- [ ] **Step 3: Implement — assinatura + injeção do `:root`**

Em `skill/quadrinho/scripts/build_pagina.py`, troque a assinatura (linha 27-28):

```python
def build_pagina(roteiro, template_dir, arte="manga", out_dir="output",
                 model="flux2-klein", generate_fn=None, render_fn=None):
```

por:

```python
_GUTTER = {"dark": "#1b1b1b", "white": "#ffffff"}

def build_pagina(roteiro, template_dir, arte="manga", out_dir="output",
                 model="flux2-klein", generate_fn=None, render_fn=None,
                 moldura="dark", kicker=None, accent="#b08900"):
```

Logo após a linha `html = fill(template_dir, roteiro, assets_dir=assets)` (linha ~54), insira a passagem do kicker e a injeção do `:root`:

```python
    html = fill(template_dir, roteiro, assets_dir=assets,
                kicker=(kicker if kicker is not None else roteiro.get("kicker")))
    root = (f"<style>:root{{--gutter:{_GUTTER.get(moldura, '#1b1b1b')};"
            f"--accent:{accent}}}</style>")
    html = html.replace("</head>", root + "</head>")
```

(Remova a linha original `html = fill(template_dir, roteiro, assets_dir=assets)` — foi substituída acima.)

- [ ] **Step 4: Implement — `fill` aceita `kicker`**

Em `skill/quadrinho/scripts/fill_pagina.py`, troque a assinatura (linha 71):

```python
def fill(template_dir, roteiro, assets_dir=None):
```

por:

```python
def fill(template_dir, roteiro, assets_dir=None, kicker=None):
```

E no `repl` (Task 2, Step 4), troque a linha do kicker por:

```python
            "kicker": _esc(kicker if kicker is not None else roteiro.get("kicker", "")),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 skill/quadrinho/tests/test_moldura_textless.py`
Expected: `OK moldura`
Run: `python3 skill/quadrinho/tests/test_fill_pagina.py`
Expected: `OK` (assinatura nova é retrocompatível — `kicker` default None)

- [ ] **Step 6: Commit**

```bash
git add skill/quadrinho/scripts/build_pagina.py skill/quadrinho/scripts/fill_pagina.py skill/quadrinho/tests/test_moldura_textless.py
git commit -m "feat(quadrinho): build_pagina aceita moldura/kicker/accent e injeta :root (R1)"
```

---

### Task 4: `pagina-textless.png` em `build_pagina` (R2, parte A)

**Files:**
- Modify: `skill/quadrinho/scripts/build_pagina.py:57-65`
- Test: `skill/quadrinho/tests/test_moldura_textless.py` (acrescenta)

- [ ] **Step 1: Write the failing test**

Acrescente a `skill/quadrinho/tests/test_moldura_textless.py` (antes do `if __name__`):

```python
def test_emits_textless_png(out="/tmp/_textless"):
    if os.path.exists(out): shutil.rmtree(out)
    png = build_pagina(ROT, DINAM, out_dir=out, generate_fn=fake_generate)
    base = os.path.dirname(png)
    tl_png = os.path.join(base, "pagina-textless.png")
    tl_html = os.path.join(base, "pagina-textless.html")
    assert os.path.exists(tl_png) and png_size(tl_png) == (1200, 1600)
    h = open(tl_html).read().replace(" ", "")
    assert ".narracao,.fala,.sfx{display:none" in h
```

E acrescente `test_emits_textless_png()` ao `if __name__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/quadrinho/tests/test_moldura_textless.py`
Expected: falha — `pagina-textless.png` não existe.

- [ ] **Step 3: Implement — render da cópia textless**

Em `skill/quadrinho/scripts/build_pagina.py`, logo após a linha que renderiza a página com texto:

```python
    render_fn(html_path, os.path.join(base, "pagina.png"), meta["width"], meta["height"])
```

insira:

```python
    # cópia TEXTLESS p/ o vídeo (carrossel usa pagina.png COM texto; o vídeo
    # viaja sobre esta, só a arte dos painéis). Reusa o display:none do mask.
    textless_html = html.replace(
        "</head>", "<style>.narracao,.fala,.sfx{display:none!important}</style></head>")
    textless_path = os.path.join(base, "pagina-textless.html")
    with open(textless_path, "w") as f:
        f.write(textless_html)
    render_fn(textless_path, os.path.join(base, "pagina-textless.png"),
              meta["width"], meta["height"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/quadrinho/tests/test_moldura_textless.py`
Expected: `OK moldura` + textless test passa.

- [ ] **Step 5: Commit**

```bash
git add skill/quadrinho/scripts/build_pagina.py skill/quadrinho/tests/test_moldura_textless.py
git commit -m "feat(quadrinho): emite pagina-textless.png p/ video (R2)"
```

---

### Task 5: `build_travel` viaja sobre a página textless + repassa params (R2, parte B)

**Files:**
- Modify: `skill/motioncomic/scripts/build_travel.py:329-432`
- Test: `skill/motioncomic/tests/test_textless_path.py`

- [ ] **Step 1: Write the failing test**

```python
# skill/motioncomic/tests/test_textless_path.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_travel

def test_textless_sibling_path():
    p = "/x/y/z/pagina.png"
    assert build_travel._textless(p) == "/x/y/z/pagina-textless.png"

if __name__ == "__main__":
    test_textless_sibling_path()
    print("OK textless path")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/motioncomic/tests/test_textless_path.py`
Expected: AttributeError (`_textless` não existe).

- [ ] **Step 3: Implement — helper `_textless`**

Em `skill/motioncomic/scripts/build_travel.py`, logo antes de `def _page_roteiro` (linha ~300), adicione:

```python
def _textless(page_png):
    """A cópia SEM texto, irmã do pagina.png (emitida pelo build_pagina)."""
    return os.path.join(os.path.dirname(page_png), "pagina-textless.png")
```

- [ ] **Step 4: Implement — assinatura repassa moldura/kicker/accent**

Troque a assinatura de `build_video_travel` (linha ~329-330):

```python
def build_video_travel(roteiro, out_dir="output", voice="bella", model="flux2-klein",
                       arte="manga", intro=True, template_dir=None):
```

por:

```python
def build_video_travel(roteiro, out_dir="output", voice="bella", model="flux2-klein",
                       arte="manga", intro=True, template_dir=None,
                       moldura="dark", kicker=None, accent="#b08900"):
```

- [ ] **Step 5: Implement — monta a página com params e viaja sobre a textless**

No corpo, troque o bloco (linhas ~368-374):

```python
        # 1) monta a pagina de papel (narracao/balao/sfx impressos)
        page_png = build_pagina(_page_roteiro(roteiro, pg), tdir,
                                arte=arte, out_dir=pages_dir, model=model)
        last_page_png = page_png
        page_html = os.path.join(os.path.dirname(page_png), "pagina.html")
        mask_png = os.path.join(os.path.dirname(page_png), "mask.png")
        render_mask(page_html, mask_png, PW, PH)
```

por:

```python
        # 1) monta a pagina de papel; pagina.png (COM texto) = carrossel,
        #    pagina-textless.png = sobre a qual a CAMERA viaja (voz-off).
        page_png = build_pagina(_page_roteiro(roteiro, pg), tdir,
                                arte=arte, out_dir=pages_dir, model=model,
                                moldura=moldura, kicker=kicker, accent=accent)
        travel_png = _textless(page_png)
        last_page_png = travel_png
        page_html = os.path.join(os.path.dirname(page_png), "pagina.html")
        mask_png = os.path.join(os.path.dirname(page_png), "mask.png")
        render_mask(page_html, mask_png, PW, PH)
```

Depois, em **todas** as chamadas de clipe que usam `page_png` para a câmera, troque `page_png` por `travel_png`:
- linha ~405: `_fullpage_clip(travel_png, duration(pb) + 0.4, est, audio=pb)`
- linha ~408: `_fullpage_clip(travel_png, T_FULL, est)`
- linha ~411: `_fullpage_clip(travel_png, T_FULL, est)`
- linha ~420: `_seg_clip(travel_png, zoom_window(frames[i], HOLD_OUT, PW), frames[i], durs[i], hold, audio=wavs[i])`
- linha ~425: `_seg_clip(travel_png, frames[i], zoom_window(frames[i + 1], HOLD_OUT, PW), T_TRANS, tr, bump=TRANS_BUMP)`

(O fechamento usa `last_page_png`, que já é `travel_png`. O `_page_card_clip` NÃO usa page_png — fica intacto.)

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 skill/motioncomic/tests/test_textless_path.py`
Expected: `OK textless path`
Run: `python3 -c "import sys,os; sys.path.insert(0,'skill/motioncomic/scripts'); import build_travel; print('import ok')"`
Expected: `import ok`

- [ ] **Step 7: Commit**

```bash
git add skill/motioncomic/scripts/build_travel.py skill/motioncomic/tests/test_textless_path.py
git commit -m "feat(motioncomic): Forma B viaja sobre pagina-textless + repassa moldura/kicker/accent (R2)"
```

---

### Task 6: Abertura-gancho em t=0 sobre o card (R3, parte A)

**Files:**
- Modify: `skill/motioncomic/scripts/build_motion.py:49-67` (`_title_clip` aceita `audio`)
- Modify: `skill/motioncomic/scripts/build_travel.py:355-411` (abertura no intro, não no chamada da pág 0)
- Test: `skill/motioncomic/tests/test_textless_path.py` (acrescenta um teste de assinatura)

- [ ] **Step 1: Write the failing test**

Acrescente a `skill/motioncomic/tests/test_textless_path.py` (antes do `if __name__`):

```python
import inspect

def test_title_clip_accepts_audio():
    from build_motion import _title_clip
    assert "audio" in inspect.signature(_title_clip).parameters
```

E acrescente `test_title_clip_accepts_audio()` ao `if __name__`.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/motioncomic/tests/test_textless_path.py`
Expected: falha — `_title_clip` não tem param `audio`.

- [ ] **Step 3: Implement — `_title_clip` aceita `audio`**

Em `skill/motioncomic/scripts/build_motion.py`, na função `_title_clip` (linha ~49), troque a assinatura `def _title_clip(text, out_mp4, secs=1.8):` por:

```python
def _title_clip(text, out_mp4, secs=1.8, audio=None, voice="bella"):
```

E troque a invocação do ffmpeg (linha ~62-67, a que usa `-f lavfi ... anullsrc`) por uma versão que, havendo `audio`, narra e ajusta a duração ao áudio:

```python
    from tts import say, duration
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-loop", "1"]
    if audio:
        wav = audio if os.path.exists(str(audio)) else out_mp4 + ".wav"
        if not os.path.exists(wav):
            say(audio, wav, voice=voice)
        dur = duration(wav) + 0.4
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-i", wav,
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}", "-af", "apad"]
    else:
        dur = secs
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-f", "lavfi", "-t", f"{dur:.3f}",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-t", f"{dur:.3f}", out_mp4]
    subprocess.run(cmd, check=True)
    return out_mp4
```

(Se o `_title_clip` atual já tiver `import` próprios de `tts`/`os`, não duplique — reuse os do topo do módulo. `W`, `H`, `FPS` já estão no escopo do módulo.)

- [ ] **Step 4: Implement — build_travel: gancho no intro, não na chamada da pág 0**

Em `skill/motioncomic/scripts/build_travel.py`, o bloco do intro (linhas ~355-359) e a abertura (linha ~361-362). Troque:

```python
    if intro:
        tc = os.path.join(clips_dir, "000-intro.mp4")
        _title_clip(f'<small>{_h.escape(roteiro.get("subtitulo", "MOTION COMIC"))}</small>'
                    + _h.escape(roteiro["titulo"]), tc, secs=2.2)
        clips.append(tc)

    # abertura narrada — a narracao COMECA dizendo o assunto (entra na 1a chamada)
    abertura = (roteiro.get("abertura") or "").strip()
```

por:

```python
    abertura = (roteiro.get("abertura") or "").strip()
    if intro:
        tc = os.path.join(clips_dir, "000-intro.mp4")
        # o card do assunto JÁ narra o gancho em t=0 (abertura). Sem abertura,
        # fica o card silencioso de 2.2s como antes.
        _title_clip(f'<small>{_h.escape(roteiro.get("subtitulo", "MOTION COMIC"))}</small>'
                    + _h.escape(roteiro["titulo"]), tc, secs=2.2,
                    audio=(abertura or None), voice=voice)
        clips.append(tc)
```

E, na linha ~391, troque:

```python
        intro_txt = (f"{abertura} {chamada}".strip() if pgi == 0 else chamada)
```

por:

```python
        # abertura já foi narrada no card de intro (t=0); aqui só a chamada da página
        intro_txt = chamada
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 skill/motioncomic/tests/test_textless_path.py`
Expected: `OK textless path` + os 2 testes novos.
Run: `python3 -c "import sys; sys.path.insert(0,'skill/motioncomic/scripts'); import build_travel, build_motion; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add skill/motioncomic/scripts/build_motion.py skill/motioncomic/scripts/build_travel.py skill/motioncomic/tests/test_textless_path.py
git commit -m "feat(motioncomic): gancho narrado em t=0 sobre o card de abertura (R3)"
```

---

### Task 7: Wiring na serie + documentação (R1/R2/R3, parte final)

**Files:**
- Modify: `skill/serie/scripts/config.py:11` (estilo: `moldura`, `cor_destaque`)
- Modify: `skill/serie/config.yaml` (estilo)
- Modify: `skill/serie/scripts/build_serie.py:120-148`
- Modify: `skill/quadrinho/SKILL.md`, `skill/motioncomic/SKILL.md`, `skill/serie/SKILL.md`
- Test: `skill/serie/tests/test_destino.py` (acrescenta estilo defaults)

- [ ] **Step 1: Write the failing test**

Acrescente a `skill/serie/tests/test_destino.py` (antes do `if __name__`, e registre as chamadas nele):

```python
def test_estilo_defaults_moldura_accent():
    assert config.FALLBACK["estilo"]["moldura"] == "dark"
    assert config.FALLBACK["estilo"]["cor_destaque"] == "#b08900"
    flat = config.resolve({"id": "x"})
    assert flat["moldura"] == "dark" and flat["cor_destaque"] == "#b08900"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_destino.py`
Expected: KeyError/AssertionError — `moldura`/`cor_destaque` não existem.

- [ ] **Step 3: Implement — defaults de estilo em config.py**

Em `skill/serie/scripts/config.py`, linha 11, troque o dict `estilo` por:

```python
    "estilo": {"arte": "manga", "modelo_pagina": "manga-dinamico", "voz": "bella",
               "intro": True, "moldura": "dark", "cor_destaque": "#b08900"},
```

- [ ] **Step 4: Implement — config.yaml estilo**

Em `skill/serie/config.yaml`, na seção `estilo`, acrescente:

```yaml
  moldura: dark                 # dark (frame fino escuro) | white (gutters brancos, look galeria)
  cor_destaque: "#b08900"       # cor do kicker/realce no cabeçalho da página
```

- [ ] **Step 5: Implement — build_serie repassa kicker/moldura/accent**

Os renderers têm assinatura `(ep, settings, destdir, base)` — **não** recebem `biblia`. Em vez de mudar assinaturas, injete o `kicker` no `settings` resolvido uma vez, e leia `moldura`/`cor_destaque` (que já vêm no resolve via estilo, Steps 3-4) dentro dos renderers.

Em `skill/serie/scripts/build_serie.py`, logo após `s = resolve(biblia)` (linha ~171), insira:

```python
    s["kicker"] = biblia.get("kicker") or biblia.get("assunto", "")
```

No `_render_hq` (linha ~129), troque:

```python
            png = build_pagina(_page_to_quadrinho(ep, pg), tdir, arte=settings["arte"], out_dir=work)
```

por:

```python
            png = build_pagina(_page_to_quadrinho(ep, pg), tdir, arte=settings["arte"], out_dir=work,
                               moldura=settings.get("moldura", "dark"),
                               kicker=settings.get("kicker", ""),
                               accent=settings.get("cor_destaque", "#b08900"))
```

No `_render_video` (linha ~142-145), troque o ramo `video-pagina`:

```python
        from build_travel import build_video_travel  # noqa: E402
        mp4 = build_video_travel(rot, out_dir=work, voice=settings["voz"], arte=settings["arte"],
                                 template_dir=_TEMPLATES[settings["modelo_pagina"]])
```

por (acrescenta os três kwargs, mantendo `template_dir`):

```python
        from build_travel import build_video_travel  # noqa: E402
        mp4 = build_video_travel(rot, out_dir=work, voice=settings["voz"], arte=settings["arte"],
                                 template_dir=_TEMPLATES[settings["modelo_pagina"]],
                                 moldura=settings.get("moldura", "dark"),
                                 kicker=settings.get("kicker", ""),
                                 accent=settings.get("cor_destaque", "#b08900"))
```

(Forma A — `video-slideshow` via `build_video` — não monta página, então não recebe `moldura`/`kicker`; o gancho da Forma A vem do `_title_clip` com áudio, Task 6.)

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_destino.py`
Expected: `OK`
Run: `for t in skill/*/tests/test_*.py; do printf "%s " "$t"; python3 "$t"; done`
Expected: todos `OK` (suíte verde, agora ≥21 testes).

- [ ] **Step 7: Implement — documentação (A/B=formato, moldura, carrossel, gancho)**

Em `skill/motioncomic/SKILL.md`, acrescente perto do topo da seção das duas formas:

```markdown
> **A/B é FORMATO, não narração.** Forma A = `video-slideshow` (slideshow, painéis
> direto). Forma B = `video-pagina` (câmera sobre a página). A narração é uma faixa
> fluente ÚNICA que serve A e B — nunca gere "duas narrações" para A/B.
>
> **Carrossel × vídeo.** O carrossel são as PÁGINAS (`pagina.png`, com texto), lidas
> como quadrinho — não é vídeo. O vídeo (A e B) usa a arte SEM texto: a Forma A pega os
> painéis direto; a Forma B viaja sobre `pagina-textless.png` (voz-off).
>
> **Gancho.** O vídeo abre em t=0 com a narração-gancho (`roteiro['abertura']`) sobre o
> card do assunto.
>
> **Moldura.** A página tem duas molduras (`moldura=dark|white`) escolhidas por geração.
```

Em `skill/quadrinho/SKILL.md`, documente o param `moldura` (dark|white), o `kicker`/`accent` no cabeçalho, e que `build_pagina` emite `pagina.png` (com texto, p/ carrossel) **e** `pagina-textless.png` (p/ vídeo).

Em `skill/serie/SKILL.md`, na seção de estilo/config, documente `moldura` e `cor_destaque`, e reforce A/B=formato (não confundir com voz).

- [ ] **Step 8: Commit**

```bash
git add skill/serie/scripts/config.py skill/serie/config.yaml skill/serie/scripts/build_serie.py skill/serie/tests/test_destino.py skill/*/SKILL.md
git commit -m "feat(serie): repassa moldura/kicker/accent + docs A/B=formato/carrossel/gancho (R1/R2/R3)"
```

---

## Self-Review

**Spec coverage:**
- R1 (moldura V2 + dark/white) → Tasks 2, 3, 7. ✓
- R2 (página textless; A=painéis, B=textless, carrossel=com texto) → Tasks 4, 5; doc Task 7. ✓
- R3 (A/B=formato doc; narração fluente única; gancho t=0) → Task 6 (timing) + Task 7 (docs). ✓
- R4 (destino `~/projetos/output`) → Task 1. ✓
- Pós-geração (P1-P3) — **fora deste plano** por decisão (plano separado). ✓

**Placeholder scan:** sem TBD/TODO; todo passo tem código ou comando concreto. Pontos de "confirme lendo" (Task 7 Step 5) são verificações de escopo local, não placeholders de implementação — a edição alvo está dada.

**Type consistency:** `moldura`/`kicker`/`accent` têm os mesmos nomes e defaults (`"dark"`, `None`, `"#b08900"`) em `build_pagina`, `build_video_travel` e nas chamadas do `build_serie`. `_textless(page_png)` definido na Task 5 e usado lá mesmo. `fill(..., kicker=None)` casa com a chamada em `build_pagina`. CSS var `--gutter`/`--accent` injetada na Task 3 casa com o uso no CSS das Tasks 2.

**Observação de interação (não bloqueia):** `FULLPAGE_FILL=0.88` (`build_travel.py:50`) existia para a borda `#111` não sumir na tarja preta; com o mat branco (R1) a prancha já tem margem clara — manter 0.88 é seguro; revisar para 1.0 fica como ajuste fino opcional pós-render, não tarefa.

---

## Pré-requisitos de execução

- `inemaimg` em `localhost:8000` (Tasks 2-4 renderizam páginas com Chromium; a geração real de imagem usa o daemon, mas os testes injetam `fake_generate`/usam Chromium local — não precisam do flux).
- `ffmpeg` no PATH (Tasks 5-6 montam clipes; os testes dessas tasks são de assinatura/caminho, não rodam ffmpeg).
- Chromium (ms-playwright) para os testes de render do `quadrinho`.
