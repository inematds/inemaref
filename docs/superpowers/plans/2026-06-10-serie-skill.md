# Skill `serie` (V2 inemaref) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `serie` skill: from a subject, the agent writes a series bible; after approval it autonomously renders every episode/page as `texto`/`hq`/`video`, reusing `folder`/`quadrinho`/`motioncomic`, dropping descriptively-named files + a `manifesto.json` into a destination folder.

**Architecture:** Same pattern as existing skills — `SKILL.md` is the LLM "brain" (writes `biblia.json` + episode roteiros); `scripts/` is the deterministic orchestrator. Pure, dependency-light modules (`config`, `naming`, `biblia`, `manifesto`, `runner`) are unit-tested without daemons; `build_serie.py` glues them and the real renderers (render functions are injectable so the orchestration is testable with fakes).

**Tech Stack:** Python 3.12 (stdlib + PyYAML 6 already installed), reuse of `folder`/`quadrinho`/`motioncomic` scripts, optional `mkivideos` queue. Tests follow the repo convention: plain scripts with `assert` + `if __name__ == "__main__": ...; print("OK")`, run via `python3 <test>.py`.

**Spec:** `docs/superpowers/specs/2026-06-10-serie-skill-design.md`

---

## File Structure

```
skill/serie/
  SKILL.md                 # brain: subject+config -> biblia.json; after approval -> episode roteiros
  config.yaml              # commented global defaults (single source)
  scripts/
    config.py              # load_config() + resolve(biblia): biblia > config.yaml > FALLBACK
    naming.py              # slug() + ep_base()/page_base() descriptive names
    biblia.py              # validate() + to_markdown()
    manifesto.py           # build() the manifesto.json dict
    runner.py              # is_video(), mkivideos_disponivel(), escolher()
    build_serie.py         # build_biblia() approval bundle + build_serie() batch + renderers
  tests/
    test_config.py  test_naming.py  test_biblia.py  test_manifesto.py
    test_runner.py  test_build_serie.py
```

Resolution order per field: `biblia.json` > `config.yaml` > `FALLBACK` (code). Renderers signature is uniform: `renderer(ep, settings, destdir, base) -> list[str]` (absolute paths written).

---

### Task 1: config — defaults file + loader/resolver

**Files:**
- Create: `skill/serie/config.yaml`
- Create: `skill/serie/scripts/config.py`
- Test: `skill/serie/tests/test_config.py`

- [ ] **Step 1: Write `config.yaml`**

```yaml
# serie — defaults da skill. Cada série sobrescreve na sua biblia.json.
estilo:
  arte: manga                   # manga | cartoon | foto
  modelo_pagina: grade-uniforme # grade-uniforme (2x3) | manga-dinamico (assimétrico)
  voz: bella                    # bella | rachel  (só tipos de vídeo)
  intro: true                   # cartão de abertura no vídeo: true | false
formato:
  tipo: video-pagina            # texto | hq | video-slideshow | video-pagina
  n_episodios: 3                # quantos episódios
  n_paginas: 3                  # páginas por episódio (cada página = 6 quadros)
  destino: output               # pasta de saída -> <destino>/<serie-id>/ (+ manifesto.json)
runtime:
  auto: false                   # true = pula o portão de aprovação
  runner: auto                  # auto (inline; mkivideos se de pé e tipo=vídeo) | inline | mkivideos
  notificar: true               # progresso no openpcbot: true | false
```

- [ ] **Step 2: Write the failing test** — `skill/serie/tests/test_config.py`

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from config import load_config, resolve, FALLBACK


def test_load_config_reads_yaml():
    cfg = load_config()
    assert cfg["estilo"]["arte"] == "manga"
    assert cfg["formato"]["tipo"] == "video-pagina"
    assert cfg["runtime"]["auto"] is False


def test_load_config_fallback_when_missing():
    cfg = load_config("/no/such/file.yaml")
    assert cfg == FALLBACK


def test_resolve_biblia_overrides_config():
    biblia = {"estilo": {"arte": "cartoon"}, "formato": {"tipo": "hq", "n_episodios": 5}}
    s = resolve(biblia)
    assert s["arte"] == "cartoon"        # biblia wins
    assert s["tipo"] == "hq"             # biblia wins
    assert s["n_episodios"] == 5         # biblia wins
    assert s["modelo_pagina"] == "grade-uniforme"  # falls to config default
    assert s["auto"] is False            # runtime default present in flat result


if __name__ == "__main__":
    test_load_config_reads_yaml()
    test_load_config_fallback_when_missing()
    test_resolve_biblia_overrides_config()
    print("OK")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_config.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: Write `skill/serie/scripts/config.py`**

```python
import os
try:
    import yaml
except ImportError:
    yaml = None

_SERIE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # skill/serie
CONFIG_PATH = os.path.join(_SERIE_DIR, "config.yaml")

FALLBACK = {
    "estilo": {"arte": "manga", "modelo_pagina": "grade-uniforme", "voz": "bella", "intro": True},
    "formato": {"tipo": "video-pagina", "n_episodios": 3, "n_paginas": 3, "destino": "output"},
    "runtime": {"auto": False, "runner": "auto", "notificar": True},
}


def _merge(base, over):
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path=None):
    """Defaults globais: config.yaml mesclado sobre FALLBACK. Nunca crasha —
    se o arquivo sumir/quebrar (ou sem pyyaml), volta o FALLBACK."""
    path = path or CONFIG_PATH
    if yaml and os.path.exists(path):
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return _merge(FALLBACK, data)
        except Exception:
            return _merge(FALLBACK, {})
    return _merge(FALLBACK, {})


def resolve(biblia, config=None):
    """Achata estilo+formato+runtime aplicando biblia > config > fallback."""
    cfg = config or load_config()
    estilo = _merge(cfg["estilo"], biblia.get("estilo", {}))
    formato = _merge(cfg["formato"], biblia.get("formato", {}))
    flat = {}
    flat.update(estilo)
    flat.update(formato)
    flat.update(cfg["runtime"])
    return flat
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_config.py`
Expected: PASS — prints `OK`

- [ ] **Step 6: Commit**

```bash
git add skill/serie/config.yaml skill/serie/scripts/config.py skill/serie/tests/test_config.py
git commit -m "feat(serie): config.yaml + loader/resolver (biblia > config > fallback)"
```

---

### Task 2: naming — descriptive slugs/filenames

**Files:**
- Create: `skill/serie/scripts/naming.py`
- Test: `skill/serie/tests/test_naming.py`

- [ ] **Step 1: Write the failing test** — `skill/serie/tests/test_naming.py`

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from naming import slug, ep_base, page_base


def test_slug_strips_accents_and_spaces():
    assert slug("A Escada Invisível de Lia!") == "a-escada-invisivel-de-lia"
    assert slug("  ") == "x"          # nunca vazio
    assert slug("Café & Cia") == "cafe-cia"


def test_ep_base_is_descriptive():
    assert ep_base("piramide-maslow", 3, "O Confronto") == "piramide-maslow-ep03-o-confronto"


def test_page_base_adds_page_number():
    assert page_base("piramide-maslow", 3, 2, "O Confronto") == "piramide-maslow-ep03-o-confronto-p02"


if __name__ == "__main__":
    test_slug_strips_accents_and_spaces()
    test_ep_base_is_descriptive()
    test_page_base_adds_page_number()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_naming.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'naming'`

- [ ] **Step 3: Write `skill/serie/scripts/naming.py`**

```python
import re
import unicodedata


def slug(text):
    """kebab-case ascii, sem acento; nunca vazio."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "x"


def ep_base(serie_slug, ep_n, ep_titulo):
    """Nome descritivo do episodio: <serie>-epNN-<titulo>."""
    return f"{serie_slug}-ep{int(ep_n):02d}-{slug(ep_titulo)}"


def page_base(serie_slug, ep_n, page_n, ep_titulo):
    """Nome de uma pagina: <serie>-epNN-<titulo>-pMM."""
    return f"{ep_base(serie_slug, ep_n, ep_titulo)}-p{int(page_n):02d}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_naming.py`
Expected: PASS — prints `OK`

- [ ] **Step 5: Commit**

```bash
git add skill/serie/scripts/naming.py skill/serie/tests/test_naming.py
git commit -m "feat(serie): naming — slug + nomes descritivos de episodio/pagina"
```

---

### Task 3: biblia — schema validation + readable markdown

**Files:**
- Create: `skill/serie/scripts/biblia.py`
- Test: `skill/serie/tests/test_biblia.py`

- [ ] **Step 1: Write the failing test** — `skill/serie/tests/test_biblia.py`

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import biblia as B

GOOD = {
    "id": "piramide-maslow", "assunto": "A piramide de Maslow",
    "premissa": {"logline": "Lia sobe a escada invisivel.", "sinopse": "Sinopse curta."},
    "formato": {"n_episodios": 2},
    "protagonista": {"nome": "Lia", "aparencia": "jovem, cardiga mostarda"},
    "elenco": [{"nome": "Teo", "aparencia": "oculos redondos"}],
    "episodios": [
        {"n": 1, "titulo": "O que e", "sinopse": "intro"},
        {"n": 2, "titulo": "Fisiologico", "sinopse": "base"},
    ],
}


def test_validate_accepts_good():
    assert B.validate(GOOD) is True


def test_validate_missing_field():
    bad = dict(GOOD); del bad["protagonista"]
    try:
        B.validate(bad); assert False, "deveria falhar"
    except ValueError as e:
        assert "protagonista" in str(e)


def test_validate_episode_count_mismatch():
    bad = dict(GOOD); bad["formato"] = {"n_episodios": 5}
    try:
        B.validate(bad); assert False, "deveria falhar"
    except ValueError as e:
        assert "n_episodios" in str(e)


def test_to_markdown_has_title_and_episodes():
    md = B.to_markdown(GOOD)
    assert "A piramide de Maslow" in md
    assert "Lia" in md and "Teo" in md
    assert "O que e" in md and "Fisiologico" in md


if __name__ == "__main__":
    test_validate_accepts_good()
    test_validate_missing_field()
    test_validate_episode_count_mismatch()
    test_to_markdown_has_title_and_episodes()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_biblia.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'biblia'`

- [ ] **Step 3: Write `skill/serie/scripts/biblia.py`**

```python
REQUIRED = ("id", "assunto", "premissa", "protagonista", "episodios")


def validate(biblia):
    """Valida a biblia. Levanta ValueError com mensagem acionavel."""
    miss = [k for k in REQUIRED if not biblia.get(k)]
    if miss:
        raise ValueError(f"biblia faltando campos: {miss}")
    eps = biblia["episodios"]
    if not isinstance(eps, list) or not eps:
        raise ValueError("episodios deve ser uma lista nao-vazia")
    for i, e in enumerate(eps, 1):
        if "n" not in e:
            raise ValueError(f"episodio {i} sem 'n'")
        if not e.get("titulo"):
            raise ValueError(f"episodio {i} sem 'titulo'")
    n = biblia.get("formato", {}).get("n_episodios")
    if n is not None and len(eps) != n:
        raise ValueError(f"n_episodios={n} mas o outline tem {len(eps)} episodios")
    return True


def to_markdown(biblia):
    """Biblia legivel para o portao de aprovacao."""
    p = biblia.get("premissa", {})
    prot = biblia.get("protagonista", {})
    out = [f"# {biblia.get('assunto', '')}", "",
           f"**Logline:** {p.get('logline', '')}", "",
           p.get("sinopse", ""), "",
           "## Protagonista", "",
           f"**{prot.get('nome', '')}** — {prot.get('aparencia', '')}"]
    elenco = biblia.get("elenco", [])
    if elenco:
        out += ["", "## Elenco", ""]
        out += [f"- **{c.get('nome', '')}** — {c.get('aparencia', '')}" for c in elenco]
    out += ["", "## Episodios", ""]
    out += [f"{e.get('n')}. **{e.get('titulo', '')}** — {e.get('sinopse', '')}"
            for e in biblia["episodios"]]
    return "\n".join(out) + "\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_biblia.py`
Expected: PASS — prints `OK`

- [ ] **Step 5: Commit**

```bash
git add skill/serie/scripts/biblia.py skill/serie/tests/test_biblia.py
git commit -m "feat(serie): biblia — validacao de schema + biblia.md legivel"
```

---

### Task 4: manifesto — the destination contract

**Files:**
- Create: `skill/serie/scripts/manifesto.py`
- Test: `skill/serie/tests/test_manifesto.py`

- [ ] **Step 1: Write the failing test** — `skill/serie/tests/test_manifesto.py`

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from manifesto import build

BIBLIA = {
    "id": "piramide-maslow", "assunto": "A piramide de Maslow",
    "premissa": {"logline": "Lia sobe a escada."},
    "formato": {"tipo": "video-pagina"},
    "episodios": [
        {"n": 1, "titulo": "O que e", "sinopse": "intro", "tags": ["maslow"]},
        {"n": 2, "titulo": "Fisiologico", "sinopse": "base"},
    ],
}


def test_build_manifesto_merges_biblia_and_files():
    entregas = [
        {"n": 1, "arquivos": ["piramide-maslow-ep01-o-que-e.mp4"], "thumb": "ep01.jpg"},
        {"n": 2, "arquivos": ["piramide-maslow-ep02-fisiologico.mp4"]},
    ]
    m = build(BIBLIA, entregas, gerado_em="2026-06-10")
    assert m["serie_id"] == "piramide-maslow"
    assert m["tipo"] == "video-pagina"
    assert m["gerado_em"] == "2026-06-10"
    assert len(m["episodios"]) == 2
    e1 = m["episodios"][0]
    assert e1["titulo"] == "O que e"          # do biblia
    assert e1["descricao"] == "intro"          # sinopse do biblia
    assert e1["tags"] == ["maslow"]
    assert e1["arquivos"] == ["piramide-maslow-ep01-o-que-e.mp4"]
    assert e1["thumb"] == "ep01.jpg"


if __name__ == "__main__":
    test_build_manifesto_merges_biblia_and_files()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_manifesto.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'manifesto'`

- [ ] **Step 3: Write `skill/serie/scripts/manifesto.py`**

```python
def build(biblia, entregas, gerado_em):
    """Monta o manifesto.json. `entregas` = [{n, arquivos:[...], thumb?}].
    Junta titulo/descricao/tags da biblia por numero de episodio."""
    by_n = {e["n"]: e for e in biblia.get("episodios", [])}
    episodios = []
    for d in entregas:
        e = by_n.get(d["n"], {})
        episodios.append({
            "n": d["n"],
            "titulo": e.get("titulo", ""),
            "descricao": e.get("sinopse", ""),
            "tags": e.get("tags", []),
            "arquivos": d.get("arquivos", []),
            "thumb": d.get("thumb"),
        })
    return {
        "serie": biblia.get("premissa", {}).get("logline", biblia.get("assunto", "")),
        "assunto": biblia.get("assunto", ""),
        "serie_id": biblia.get("id", ""),
        "tipo": biblia.get("formato", {}).get("tipo", ""),
        "gerado_em": gerado_em,
        "episodios": episodios,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_manifesto.py`
Expected: PASS — prints `OK`

- [ ] **Step 5: Commit**

```bash
git add skill/serie/scripts/manifesto.py skill/serie/tests/test_manifesto.py
git commit -m "feat(serie): manifesto — contrato com o uploader (serie + episodios + arquivos)"
```

---

### Task 5: runner — type/availability → execution choice

**Files:**
- Create: `skill/serie/scripts/runner.py`
- Test: `skill/serie/tests/test_runner.py`

- [ ] **Step 1: Write the failing test** — `skill/serie/tests/test_runner.py`

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from runner import is_video, escolher, mkivideos_disponivel


def test_is_video():
    assert is_video("video-pagina") and is_video("video-slideshow")
    assert not is_video("hq") and not is_video("texto")


def test_escolher_explicit_overrides():
    assert escolher("video-pagina", runner="inline", disponivel=True) == "inline"
    assert escolher("hq", runner="mkivideos", disponivel=False) == "mkivideos"


def test_escolher_auto():
    assert escolher("video-pagina", runner="auto", disponivel=True) == "mkivideos"
    assert escolher("video-pagina", runner="auto", disponivel=False) == "inline"
    assert escolher("hq", runner="auto", disponivel=True) == "inline"  # so video vai pra fila


def test_disponivel_uses_injected_check():
    assert mkivideos_disponivel(check_fn=lambda: True) is True
    assert mkivideos_disponivel(check_fn=lambda: False) is False


if __name__ == "__main__":
    test_is_video()
    test_escolher_explicit_overrides()
    test_escolher_auto()
    test_disponivel_uses_injected_check()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_runner.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'runner'`

- [ ] **Step 3: Write `skill/serie/scripts/runner.py`**

```python
import os

VIDEO_TIPOS = ("video-slideshow", "video-pagina")


def is_video(tipo):
    return tipo in VIDEO_TIPOS


def mkivideos_disponivel(check_fn=None):
    """True se a fila do mkivideos esta de pe. `check_fn` injetavel p/ teste;
    default tenta MKIVIDEOS_URL/health (sem a env -> False)."""
    if check_fn is not None:
        return bool(check_fn())
    url = os.environ.get("MKIVIDEOS_URL")
    if not url:
        return False
    try:
        import urllib.request
        urllib.request.urlopen(url.rstrip("/") + "/health", timeout=3)
        return True
    except Exception:
        return False


def escolher(tipo, runner="auto", disponivel=False):
    """Decide 'inline' ou 'mkivideos'. auto = mkivideos so se for video E a fila
    estiver disponivel; senao inline."""
    if runner in ("inline", "mkivideos"):
        return runner
    return "mkivideos" if (is_video(tipo) and disponivel) else "inline"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_runner.py`
Expected: PASS — prints `OK`

- [ ] **Step 5: Commit**

```bash
git add skill/serie/scripts/runner.py skill/serie/tests/test_runner.py
git commit -m "feat(serie): runner — escolha inline|mkivideos por tipo/disponibilidade"
```

---

### Task 6: build_serie — approval bundle + batch orchestrator

**Files:**
- Create: `skill/serie/scripts/build_serie.py`
- Test: `skill/serie/tests/test_build_serie.py`

This task wires the modules. Renderers are injectable so the orchestration is tested with fakes (no daemons). Real renderers reuse `quadrinho`/`motioncomic` and are used when no fake is passed.

- [ ] **Step 1: Write the failing test** — `skill/serie/tests/test_build_serie.py`

```python
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_serie as BS

BIBLIA = {
    "id": "demo-serie", "assunto": "Serie Demo",
    "premissa": {"logline": "logline", "sinopse": "sinopse"},
    "estilo": {"arte": "manga"},
    "formato": {"tipo": "texto", "n_episodios": 2, "destino": None},
    "protagonista": {"nome": "Lia", "aparencia": "jovem"},
    "episodios": [
        {"n": 1, "titulo": "Um", "sinopse": "s1"},
        {"n": 2, "titulo": "Dois", "sinopse": "s2"},
    ],
}


def _fake_ep(n, titulo):
    return {"id": f"demo-serie-ep{n:02d}", "n": n, "titulo": titulo, "personagem": "Lia",
            "paginas": [{"n": 1, "titulo": titulo, "paineis": [{"prompt": "cena"}]}]}


def test_build_biblia_bundle(tmp="/tmp/_serie_biblia"):
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    calls = {}
    def fake_folder(ficha, **kw):
        p = os.path.join(kw["out_dir"], "folder.png"); open(p, "w").close(); calls["folder"] = ficha; return p
    def fake_pagina(rot, tdir, **kw):
        p = os.path.join(kw["out_dir"], "pagina.png"); open(p, "w").close(); calls["piloto"] = rot; return p
    piloto = {"n": 1, "titulo": "Um", "paineis": [{"prompt": "cena"} for _ in range(6)]}
    res = BS.build_biblia(BIBLIA, piloto=piloto, out_dir=tmp,
                          folder_fn=fake_folder, pagina_fn=fake_pagina)
    assert os.path.exists(res["biblia_md"])
    assert os.path.exists(res["folder"])
    assert os.path.exists(res["piloto"])
    assert calls["folder"]["nome"] == "Lia"


def test_build_serie_batch_texto_and_manifest(tmp="/tmp/_serie_batch"):
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    episodios = [_fake_ep(1, "Um"), _fake_ep(2, "Dois")]
    rendered = []
    def fake_render(ep, settings, destdir, base):
        path = os.path.join(destdir, base + ".md")
        open(path, "w").write(ep["titulo"]); rendered.append(base); return [path]
    res = BS.build_serie(BIBLIA, episodios, out_dir=tmp, auto=True,
                         renderers={"texto": fake_render}, gerado_em="2026-06-10",
                         notify_fn=lambda msg: None)
    destdir = os.path.join(tmp, "demo-serie")
    assert os.path.exists(os.path.join(destdir, "manifesto.json"))
    m = json.load(open(os.path.join(destdir, "manifesto.json")))
    assert len(m["episodios"]) == 2
    assert m["episodios"][0]["arquivos"] == ["serie-demo-ep01-um.md"]
    # idempotente: re-rodar nao re-renderiza
    rendered.clear()
    BS.build_serie(BIBLIA, episodios, out_dir=tmp, auto=True,
                   renderers={"texto": fake_render}, gerado_em="2026-06-10", notify_fn=lambda m: None)
    assert rendered == [], "nao deveria re-renderizar arquivos existentes"


if __name__ == "__main__":
    test_build_biblia_bundle()
    test_build_serie_batch_texto_and_manifest()
    print("OK")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 skill/serie/tests/test_build_serie.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_serie'`

- [ ] **Step 3: Write `skill/serie/scripts/build_serie.py`**

```python
"""serie — orquestrador da V2: biblia (aprovacao) + lote de episodios.

build_biblia(): monta o pacote de aprovacao (folder do protagonista + biblia.md
+ pagina-piloto). build_serie(): apos aprovar, renderiza cada episodio por tipo,
nomeia descritivo, escreve manifesto.json e larga no destino. Idempotente.
Reusa folder/quadrinho/motioncomic; renderers injetaveis p/ teste sem daemon.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "folder", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "quadrinho", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "motioncomic", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))
from config import resolve            # noqa: E402
from naming import slug, ep_base      # noqa: E402
import biblia as _biblia              # noqa: E402
import manifesto as _manifesto        # noqa: E402
import runner as _runner              # noqa: E402

_Q = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "quadrinho", "templates"))
_F = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "folder", "templates"))
_TEMPLATES = {"grade-uniforme": os.path.join(_Q, "grade-uniforme"),
              "manga-dinamico": os.path.join(_Q, "manga-dinamico")}


# ---------------------------------------------------------------- aprovacao
def build_biblia(biblia, piloto=None, out_dir=None, folder_fn=None, pagina_fn=None):
    """Pacote de aprovacao: biblia.md + folder do protagonista + pagina-piloto
    (se `piloto` — um roteiro de 1 pagina, 6 paineis). Retorna os caminhos."""
    _biblia.validate(biblia)
    s = resolve(biblia)
    base_out = os.path.join(out_dir or "output", biblia["id"], "biblia")
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
    paineis = []
    for panel in pg["paineis"]:
        who = panel.get("quem", personagem)
        who = (who or "").strip().rstrip(".")
        scene = panel["prompt"].strip().rstrip(".")
        qp = {"prompt": f"{who}, {scene}" if who else scene}
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


# ---------------------------------------------------------------- lote
def build_serie(biblia, episodios, out_dir=None, auto=False, runner="auto",
                renderers=None, gerado_em=None, notify_fn=None, mkivideos_check=None):
    """Renderiza todos os episodios por tipo e larga em <destino>/<id>/.
    Idempotente (pula arquivos existentes). `renderers` injetavel (teste);
    `notify_fn(msg)` p/ progresso. `auto` aqui e informativo (o portao e
    decidido por quem chama). Retorna {dest, manifesto, episodios}."""
    s = resolve(biblia)
    tipo = s["tipo"]
    destino = out_dir or s["destino"] or "output"
    serie_slug = slug(biblia.get("assunto") or biblia["id"])
    destdir = os.path.join(destino, biblia["id"])
    os.makedirs(destdir, exist_ok=True)

    reg = dict(_REGISTRY)
    if renderers:
        reg.update(renderers)
    render = reg[tipo]
    modo = _runner.escolher(tipo, runner, _runner.mkivideos_disponivel(mkivideos_check))
    notify = notify_fn or (lambda msg: None)

    entregas = []
    for ep in episodios:
        base = ep_base(serie_slug, ep["n"], ep.get("titulo", ""))
        files = render(ep, s, destdir, base)   # modo mkivideos: enfileira; default inline
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 skill/serie/tests/test_build_serie.py`
Expected: PASS — prints `OK`

- [ ] **Step 5: Run the whole suite to verify no regressions**

Run: `for t in skill/*/tests/test_*.py; do printf "%s: " "$t"; python3 "$t" >/dev/null 2>&1 && echo OK || echo FAIL; done`
Expected: every line `OK` (folder, quadrinho, motioncomic, serie)

- [ ] **Step 6: Commit**

```bash
git add skill/serie/scripts/build_serie.py skill/serie/tests/test_build_serie.py
git commit -m "feat(serie): orquestrador — build_biblia (aprovacao) + build_serie (lote idempotente)"
```

---

### Task 7: SKILL.md — the brain (LLM guidance)

**Files:**
- Create: `skill/serie/SKILL.md`

No automated test (it is LLM-facing prose). Verification is the manual walkthrough in Step 2.

- [ ] **Step 1: Write `skill/serie/SKILL.md`**

````markdown
---
name: serie
description: Cria uma SERIE completa a partir de um ASSUNTO — escreve a BIBLIA (premissa, protagonista com folder, elenco, estilo, outline de episodios), e apos aprovacao gera todos os EPISODIOS e suas paginas em texto / HQ / video, reusando folder, quadrinho e motioncomic, largando os arquivos nomeados + manifesto.json numa pasta de destino. Use quando o usuario quiser "criar uma serie", "transformar um assunto numa serie", "episodios de um canal", "biblia da serie", "serie de quadrinhos/HQ/video sobre X". Portao de aprovacao na biblia (flag auto pula). V2 do inemaref.
---

# Skill: serie — criador de serie ponta a ponta (passo 4 do inemaref)

O Claude e o CEREBRO (escreve a biblia e os roteiros); o Python (`scripts/build_serie.py`) e o
ORQUESTRADOR determinista que renderiza reusando `folder`/`quadrinho`/`motioncomic`. Defaults em
`config.yaml` (ordem: biblia.json > config.yaml > fallback). Spec: `docs/superpowers/specs/2026-06-10-serie-skill-design.md`.

## Entrada
- **assunto** (obrigatorio) + config opcional: `tipo` (texto|hq|video-slideshow|video-pagina),
  `arte`, `modelo_pagina`, `n_episodios`, `n_paginas`, `destino`, `auto`. O que faltar cai no `config.yaml`.

## Passo 1 — escreva a biblia
Produza `biblia.json` (ver schema no spec, secao 4.2). Campos: `id` (slug do assunto), `assunto`,
`premissa{logline,sinopse}`, `estilo`/`formato` (so o que difere do default), `protagonista` (uma
FICHA pronta pro `folder` — `nome`, `aparencia` reutilizavel, `personalidade[]`, `caracteristicas[]`,
`detalhes[]` com IDADE, `frase`, 5 `focos`, `kicker`, `subtitulo`), `elenco[]` (cada um com
`aparencia` travada), e `episodios[]` (exatamente `n_episodios`, cada um `{n,titulo,sinopse}`).
Escreva tambem o roteiro da **pagina-piloto** (ep1/pag1, 6 paineis) p/ a aprovacao.

## Passo 2 — pacote de aprovacao
```bash
python3 - <<'PY'
import sys, json; sys.path.insert(0, "skill/serie/scripts")
from build_serie import build_biblia
b = json.load(open("CAMINHO/biblia.json")); piloto = json.load(open("CAMINHO/piloto.json"))
print(build_biblia(b, piloto=piloto))   # output/<id>/biblia/: biblia.md, folder.png, pagina-piloto
PY
```
Mostre `biblia.md` + `folder.png` + a pagina-piloto. **Espere o "aprovado".** Se o usuario ajustar,
edite a `biblia.json` e re-rode. (`auto=True` no Passo 4 pula este portao.)

## Passo 3 — roteiros dos episodios
Apos aprovar, escreva os roteiros de TODOS os episodios (guiado pela biblia). Cada episodio = roteiro
no formato do `motioncomic`: `{id, n, titulo, sinopse, personagem:<aparencia do protagonista>,
paginas:[{n,titulo,paineis:[6x {prompt, narracao?, fala?{quem,texto}, sfx?, quem?}]}]}`.
Use a `aparencia` do protagonista/elenco em todo quadro (consistencia). `n_paginas` paginas por episodio.

## Passo 4 — rode o lote
```bash
python3 - <<'PY'
import sys, json; sys.path.insert(0, "skill/serie/scripts")
from build_serie import build_serie
b = json.load(open("CAMINHO/biblia.json"))
eps = [json.load(open(f"CAMINHO/ep{n:02d}.json")) for n in range(1, b["formato"]["n_episodios"]+1)]
print(build_serie(b, eps, auto=True))   # default destino=output/<id>/; passe out_dir= p/ outra pasta
PY
```
Saida em `<destino>/<id>/`: arquivos nomeados (`<assunto>-epNN-<titulo>.*`) + `manifesto.json`.
Idempotente (re-rodar continua de onde parou). Progresso no openpcbot quando `notificar: true`.

## Pre-requisitos
`inemaimg` em `localhost:8000` (imagem). Para `video-*`: `inemavox` em `127.0.0.1:7860` (TTS) + ffmpeg.
`config.yaml` traz os defaults; edite-o p/ mudar arte/tipo/numeros/destino globais.

## Tipos -> entrega
`texto` -> `.md`/`.json` por episodio · `hq` -> PNGs por pagina · `video-slideshow`/`video-pagina`
-> 1 MP4 por episodio. (pixflow/animabook: adiados — ver spec secao 10.)
````

- [ ] **Step 2: Verify the SKILL.md self-consistency**

Run: `python3 -c "import sys; sys.path.insert(0,'skill/serie/scripts'); import build_serie, biblia, manifesto, naming, runner, config; print('imports OK')"`
Expected: prints `imports OK` (confirms every script the SKILL.md references imports cleanly).

- [ ] **Step 3: Commit**

```bash
git add skill/serie/SKILL.md
git commit -m "docs(serie): SKILL.md — guia do cerebro (biblia -> aprovacao -> roteiros -> lote)"
```

---

### Task 8: README — list `serie` as built (V2)

**Files:**
- Modify: `README.md` (the `## Skills` list and the `## Estado` line)

- [ ] **Step 1: Add the `serie` bullet under `## Skills`**

In `README.md`, after the `skill/motioncomic/` bullet block (before the `skill/referencias/` line), add:

```markdown
- `skill/serie/` — ✅ **construída (V2)** — **criador de série ponta a ponta**: assunto → bíblia (folder + elenco + estilo + outline) → após aprovar, gera todos os episódios em texto/HQ/vídeo (reusa as skills acima) → arquivos nomeados + `manifesto.json` numa pasta de destino. Defaults em `config.yaml`; runner híbrido (inline | mkivideos).
```

- [ ] **Step 2: Update the `## Estado` line** to mention V2

Replace the first sentence of `## Estado` with:

```markdown
**V1 + V2 construídas.** As skills `folder`, `quadrinho`, `motioncomic` (V1) e `serie` (V2 — criador de série) estão **construídas e testadas** (suíte verde). Filme (V3) permanece à frente. Página do projeto (landing + guia): [`index.html`](index.html).
```

- [ ] **Step 3: Verify the suite still passes**

Run: `for t in skill/*/tests/test_*.py; do printf "%s: " "$t"; python3 "$t" >/dev/null 2>&1 && echo OK || echo FAIL; done`
Expected: every line `OK`

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README lista a skill serie (V2) como construida"
```

---

## Self-Review (done while writing — recorded here)

- **Spec coverage:** config.yaml + resolution order (Task 1) · descriptive naming (Task 2) · biblia schema + biblia.md (Task 3) · manifesto contract (Task 4) · runner hybrid/mkivideos detection (Task 5) · build_biblia approval bundle with pilot + auto + idempotent batch + types→delivery + reuse + notify (Task 6) · SKILL.md brain + approval gate + end-to-end flow (Task 7) · README (Task 8). Out-of-scope items (upload, pixflow/animabook, foto-fiel, ≠6 quadros) intentionally not implemented.
- **Placeholder scan:** no TBD/TODO; every code step shows full code; commands have expected output.
- **Type consistency:** renderer signature `renderer(ep, settings, destdir, base) -> [paths]` is uniform across `_render_texto/_render_hq/_render_video`, `_REGISTRY`, and the injected fakes in the test. `resolve()` returns the flat settings dict consumed by `build_biblia`/`build_serie`/renderers. `_page_to_quadrinho(ep, pg)` and `_ep_markdown(ep)` are defined in Task 6 before use. `ep_base(serie_slug, n, titulo)` matches between Task 2 and its call in `build_serie`.

## Open notes for the implementer

- The repo's tests are plain scripts (not pytest); run any single test with `python3 skill/serie/tests/test_X.py` (prints `OK`).
- `_render_hq`/`_render_video` need the `inemaimg`/`inemavox` daemons and are exercised only via real runs (the unit tests inject fakes). After Task 6, optionally smoke-test one real `texto` série end-to-end (no daemons needed) to confirm the destination/manifesto layout.
- mkivideos submission is selected by `runner.escolher` but the default `_render_video` still renders inline; wiring an actual queue submit is a small follow-up (V2.1) — keep the `escolher` seam.
