# Consistência de Imagem — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Garantir que personagens/elementos do canon saiam visualmente consistentes em todas as cenas, criando e reusando fichas-âncora (imagem) por elemento, verificando cada imagem por visão contra a ficha, limitando elementos por painel, e gerando com prompt em inglês.

**Architecture:** Aproveita a infra existente — `build_pagina`/`build_motion` já consomem um dict `ancoras` ({nome→path}) e passam `images=[...]` (1-4) ao flux2-klein; `qc_imagem.judge_visao` já faz QC por Claude vision. Adicionamos: (1) um lint de elementos, (2) um "casting" que gera as fichas-âncora e popula `ancoras`, (3) auto-carregamento no build_serie, (4) QC comparativo imagem-vs-ficha, (5) pré-tradução PT→EN cacheada dos prompts.

**Tech Stack:** Python 3 (stdlib + urllib), flux2-klein via `imgclient`, testes estilo `skill/*/tests/test_*.py`. **Visão = o próprio agente (Claude Code via OAuth/assinatura, tool `Read`), NÃO API key** — o agente vê as imagens e grava os artefatos (veredito de QC, tradução EN); os scripts consomem. A chamada à API Anthropic (`qc_imagem.judge_visao`) fica só como fallback opcional p/ render 100% headless.

**Pontos de integração (da investigação):**
- prompt final: `skill/quadrinho/scripts/build_pagina.py:51-67`, `skill/motioncomic/scripts/build_motion.py:24-27,122-134`
- consumo de refs: `ancoras` dict → `images=imgs[:4]` (já existe)
- aparência efetiva: `referencia_ep.aplicar(ep, biblia)`
- QC: `skill/folder/scripts/qc_imagem.py:27-102`, ligado em `build_serie.py:131-146`
- estilo: `skill/referencias/artes.json` (`positivo`/`negativo`, já em EN)

---

### Task 1: Lint de elementos por painel

**Files:**
- Create: `skill/serie/scripts/lint_paineis.py`
- Test: `skill/serie/tests/test_lint_paineis.py`

- [ ] **Step 1 — Teste falhando.** `test_lint_paineis.py`: um painel com `quem` ausente (=protagonista) + `usa:["A","B","C"]` conta 4 entidades e é sinalizado quando `max=2`; um painel com só narração conta 1 (protagonista) e passa.
- [ ] **Step 2 — Implementar.** `contar_entidades(painel) -> int`: 1 se `quem` ausente OU `quem==""`-com-pessoa? (regra: protagonista conta quando `quem` ausente; `quem` não-vazio conta 1; cada item de `usa` conta 1; `quem==""` conta 0 pessoas mas os `usa` contam). `lint_episodio(ep, max_entidades=2) -> list[dict]` retorna `[{pagina,painel,n,entidades}]` dos que excedem.
- [ ] **Step 3 — Rodar teste** (`python3 skill/serie/tests/test_lint_paineis.py`) → PASS.
- [ ] **Step 4 — Integrar (warning não-bloqueante).** Em `build_serie.py`, antes do loop de render, chamar `lint_episodio` por ep e `notify`/print os excessos como AVISO (não aborta). Reusa o validador existente se houver.
- [ ] **Step 5 — Commit** `feat(serie): lint de elementos por painel (consistencia de imagem)`.

---

### Task 2: Casting — fichas-âncora por elenco e elementos

**Files:**
- Create: `skill/serie/scripts/casting.py`
- Test: `skill/serie/tests/test_casting.py`

- [ ] **Step 1 — Teste falhando.** Mock `generate_fn`; bíblia com 2 itens de elenco + 2 elementos → `gerar_fichas` chama o gerador 1x por entidade e devolve `ancoras` dict com 4 chaves lowercase apontando p/ os PNGs.
- [ ] **Step 2 — Implementar.**
```python
# casting.py
import os, json
from naming import slug
def _prompt_ficha(aparencia, arte_positivo):
    # ficha isolada: 1 entidade, fundo neutro, sem cena, p/ servir de ancora
    return f"{aparencia}, single subject isolated on a neutral plain background, full reference view, model sheet, {arte_positivo}, no text"
def gerar_fichas(biblia, out_dir, arte_positivo, generate_fn, width=1024, height=1024):
    casting_dir = os.path.join(out_dir, "casting"); os.makedirs(casting_dir, exist_ok=True)
    ancoras = {}
    entidades = [(e["nome"], e["aparencia"]) for e in biblia.get("elenco", [])] \
              + [(e["nome"], e["aparencia"]) for e in biblia.get("elementos", [])]
    for nome, ap in entidades:
        png = os.path.join(casting_dir, f"{slug(nome)}.png")
        if not os.path.exists(png):
            generate_fn(_prompt_ficha(ap, arte_positivo), png, width=width, height=height)
        ancoras[nome.lower()] = png
    # protagonista: reusa o retrato-ancora do folder se existir
    json.dump(ancoras, open(os.path.join(casting_dir, "ancoras.json"), "w"), ensure_ascii=False, indent=2)
    return ancoras
```
- [ ] **Step 3 — Rodar teste** → PASS.
- [ ] **Step 4 — Hook do protagonista.** Se `out_dir/biblia/<protag>/assets/retrato.png` (ou referencia.json `retrato_ancora`) existir, adicionar ao `ancoras` sob o id e o nome do protagonista. Teste cobre o caso.
- [ ] **Step 5 — Commit** `feat(serie): casting de fichas-ancora por elenco/elementos`.

---

### Task 3: build_serie auto-carrega `ancoras` do casting

**Files:**
- Modify: `skill/serie/scripts/build_serie.py` (resolução de settings, ~:217)
- Test: `skill/serie/tests/test_ancoras_autoload.py`

- [ ] **Step 1 — Teste falhando.** Com um `out_dir/casting/ancoras.json` em disco, `build_serie` (com generate mockado) injeta essas âncoras em `settings["ancoras"]`, sem sobrescrever chaves passadas explicitamente.
- [ ] **Step 2 — Implementar.** Em build_serie, após montar `settings`: `auto = _load_json(os.path.join(destdir,"casting","ancoras.json"))`; `settings["ancoras"] = {**auto, **(settings.get("ancoras") or {})}`.
- [ ] **Step 3 — Rodar teste** → PASS.
- [ ] **Step 4 — Commit** `feat(serie): render usa fichas-ancora do casting automaticamente`.

---

### Task 4: QC comparativo (imagem gerada × ficha-âncora)

**Files:**
- Modify: `skill/folder/scripts/qc_imagem.py` (`judge_visao` :77-102, `make_generate_fn` :56-63)
- Modify: `skill/serie/scripts/build_serie.py` (`_qc_generate_fn` :131-146)
- Test: `skill/folder/tests/test_qc_comparativo.py`

- [ ] **Step 1 — Teste falhando.** `judge_visao(img, ref, esperado, ref_img=<path>)` com urlopen mockado: o payload deve conter **2 imagens** (a ficha-âncora + a gerada) e a instrução de "mesma identidade?".
- [ ] **Step 2 — Implementar.** `judge_visao` aceita `ref_img=None`; se dado, inclui 2 blocos `image` no content e amplia `_INSTRU` ("a 1a imagem e a FICHA de referencia; a 2a foi gerada; e o MESMO personagem/objeto? mesma cor/forma/marcas?"). `make_generate_fn`/`_qc_generate_fn` passam a ficha do elemento principal do painel (de `settings["ancoras"]` pelo `quem`/`usa`).
- [ ] **Step 3 — Rodar teste** → PASS.
- [ ] **Step 4 — Commit** `feat(qc): QC comparativo imagem-vs-ficha por visao`.

---

### Task 5: Idioma EN — pré-tradução PT→EN cacheada

**Files:**
- Create: `skill/serie/scripts/traduzir.py`
- Modify: `build_pagina.py:51-53`, `build_motion.py:24-25` (usar `*_en` quando presente)
- Test: `skill/serie/tests/test_traduzir.py`

- [ ] **Step 1 — Teste falhando.** `traduzir_episodio(ep, glossario, traduz_fn)` grava `prompt_en` em cada painel reusando o cache (não re-chama `traduz_fn` se `prompt_en` já existe).
- [ ] **Step 2 — Implementar.** `to_en(texto, glossario, api_key=...)` via Anthropic `/v1/messages` (mesmo padrão de `qc_imagem`), com o glossário do canon embutido pra termos consistentes. `traduzir_episodio` percorre painéis e canon, preenche `prompt_en`/`aparencia_en` (idempotente).
- [ ] **Step 3 — Rodar teste** (mock `traduz_fn`) → PASS.
- [ ] **Step 4 — Consumir.** Em build_pagina/build_motion, montar o `full` com `painel.get("prompt_en") or painel["prompt"]` e `aparencia_en or aparencia`. Flag `estilo.prompt_idioma == "en"` ou `INEMAREF_PROMPT_EN=1` ativa.
- [ ] **Step 5 — Commit** `feat(serie): geracao com prompt EN (autoria PT, validado por A/B)`.

---

## Self-Review
- Cobre: lint (T1), fixar/usar elemento (T2+T3), verificar pós-criação (T4), inglês (T5) — os 4 pontos pedidos pelo usuário. ✅
- Sem placeholders: assinaturas e código-chave presentes; cada task tem teste e ponto de integração exato.
- Consistência de nomes: `ancoras` dict {nome.lower(): path} usado igual em casting/build_serie/build_pagina.
- Custos (fase produção): T2 gera N imagens extras (fichas); T4/T5 usam API Anthropic. Tudo opt-in/idempotente.
