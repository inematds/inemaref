# Formato C — Direção por Recorte Guiado por Visão — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Substituir o multi-shot genérico (zoom repetido, reprovado) por uma decupagem que, olhando CADA imagem por visão, escolhe recortes significativos — close no rosto, insert no olho, tilt, pan por um detalhe — com velocidades variadas, como um filme real, reusando a mesma imagem (sem gerar quadros novos).

**Architecture:** A camada de visão é feita pelo PRÓPRIO AGENTE (Claude Code, tool `Read`, via OAuth/assinatura — SEM API key): o agente vê cada imagem + contexto e grava um "plano de cobertura" em `visao.json` (lista de shots `{tipo, at:[x,y], zoom, peso}`). O `forma_c_direcao.dirigir` (determinístico) consome esse JSON e converte os shots em câmeras pixflow via `_framing(zoom, at)`, durações proporcionais ao `peso` (velocidades variadas). Cacheado por episódio. Fallback determinístico (`_seq` atual) quando não há `visao.json`. Preset/bíblia liga. (Mesmo modelo do diretor-animacao: VER[agente]→DECIDIR→script monta.)

**Tech Stack:** Python 3, pixflow.movie/v1, ffprobe. **Visão = o agente (Claude Code via OAuth/assinatura, tool `Read`)** produz `visao.json`; o script só monta o `movie.yaml`. API Anthropic apenas como fallback headless opcional.

**Pontos de integração (da investigação):**
- `skill/folder/scripts/qc_imagem.py:77-102` — padrão de chamada de visão (base64 image → JSON) a reusar.
- `skill/motioncomic/scripts/forma_c_direcao.py` — `_framing(z_to, y_to)` (:24-27) já parametriza recorte por `at`; `dirigir` (:71+) e `_seq` (multi-shot atual) a estender.
- referência de gramática: `~/projetos/diretor-animacao/skill/diretor-animacao` (VER→OUVIR→DECIDIR; spec pixflow.movie/v1).

---

### Task 1: Módulo de visão — plano de cobertura por imagem

**Files:**
- Create: `skill/motioncomic/scripts/visao_decupagem.py`
- Test: `skill/motioncomic/tests/test_visao_decupagem.py`

- [ ] **Step 1 — Teste falhando.** Com urlopen mockado retornando JSON de shots, `planos_da_imagem(img, contexto, energia="acao")` devolve lista normalizada de `{tipo, at:[x,y], zoom, peso}`, com `at` em 0..1 e `zoom>=1`. Sem API/erro → retorna `None` (fallback).
- [ ] **Step 2 — Implementar.** Reusa o POST de `qc_imagem` (base64 PNG + instrução). A instrução pede: identifique regiões de interesse (rosto/olhos/sujeito/detalhe da ação) e proponha N planos cobrindo a cena como um filme — `wide` (estabelece), `close` (rosto), `insert` (olho/detalhe), `pan`/`tilt` (varredura) — variando o tipo; devolva JSON `{"shots":[{"tipo","at":[x,y],"zoom","peso"}]}`. `energia` controla N (suave≈1, dinamico≈2, acao≈3) e agressividade. Normaliza/valida a saída; clampa `at`∈[0,1], `zoom`∈[1,3].
- [ ] **Step 3 — Rodar teste** (`python3 skill/motioncomic/tests/test_visao_decupagem.py`) → PASS.
- [ ] **Step 4 — Commit** `feat(formaC): visao_decupagem — plano de cobertura por imagem`.

---

### Task 2: `dirigir` converte shots de visão em câmeras pixflow

**Files:**
- Modify: `skill/motioncomic/scripts/forma_c_direcao.py` (`dirigir`, novo `_seq_visao`)
- Test: `skill/motioncomic/tests/test_seq_visao.py`

- [ ] **Step 1 — Teste falhando.** `_seq_visao(shots, d)` para um painel de duração `d` com 3 shots devolve 3 cenas pixflow cujas durações somam `d` (proporcionais ao `peso`), cada uma com câmera coerente: `close`/`insert` → `_framing(zoom, at_y)` no `at`; `pan`/`tilt` → movimento na direção; `wide` → `pull_out`.
- [ ] **Step 2 — Implementar.** `_camera_do_shot(shot)`: mapeia `tipo`→câmera pixflow usando `at`/`zoom` (close/insert via `_framing` com `at`; pan/tilt via `{type:"pan"/"... ", direction, intensity}`; wide via `pull_out`). `_seq_visao(shots,d)`: durações = `d * peso/Σpeso` (arredonda, ajusta a última p/ somar `d`). `dirigir(..., visao=None)`: se `visao` (dict `{sid: [shots]}`) tem o painel, usa `_seq_visao`; senão cai no `_seq` determinístico atual. `decupagem.json` continua 1 entrada de áudio por painel (dur=d) → sincronia preservada.
- [ ] **Step 3 — Rodar teste** → PASS (inclui asserção `abs(Σdur - d) < 0.05`).
- [ ] **Step 4 — Commit** `feat(formaC): dirigir com recorte guiado por visao (_seq_visao)`.

---

### Task 3: Cache do plano de visão por episódio

**Files:**
- Modify: `skill/motioncomic/scripts/forma_c_direcao.py` (`dirigir`)
- Create: `skill/motioncomic/scripts/coletar_visao.py` (helper)
- Test: `skill/motioncomic/tests/test_visao_cache.py`

- [ ] **Step 1 — Teste falhando.** `montar_visao(stage_dir, energia, analisar_fn)` gera `<stage>/visao.json` `{sid:[shots]}` chamando `analisar_fn` 1x por imagem; se `visao.json` já existe, **não** re-chama (idempotente).
- [ ] **Step 2 — Implementar.** `montar_visao` percorre `forma-c.json` cenas, para cada `img` chama `analisar_fn(img, contexto, energia)` (default = `visao_decupagem.planos_da_imagem`), grava cache. `dirigir` aceita `visao_path` e carrega o cache.
- [ ] **Step 3 — Rodar teste** → PASS.
- [ ] **Step 4 — Commit** `feat(formaC): cache de visao por episodio (visao.json)`.

---

### Task 4: Preset/bíblia liga a visão + orquestrador

**Files:**
- Modify: `skill/motioncomic/scripts/forma_c_direcao.py` (`PRESETS`: campo `visao: bool`)
- Modify: `output/teo-guardiao-da-noite/fonte/_render_all.py` (`forma_C`)
- Test: `skill/motioncomic/tests/test_preset_visao.py`

- [ ] **Step 1 — Teste falhando.** `preset("acao")` traz `visao: True`; `preset("suave")` traz `visao: False`.
- [ ] **Step 2 — Implementar.** Adicionar `"visao"` aos PRESETS (acao/epico=True; suave/dinamico=False). No `_render_all.forma_C`: se `pr["visao"]` e há `ANTHROPIC_API_KEY`, `montar_visao(stage, pr["energia"], ...)` antes de `dirigir(stage, energia=pr["energia"], cortes=pr["cortes"], visao_path=...)`. Sem key → log AVISO e segue determinístico.
- [ ] **Step 3 — Rodar teste** → PASS.
- [ ] **Step 4 — Commit** `feat(formaC): preset liga direcao por visao + orquestrador`.

---

### Task 5: Piloto ep26 com visão (verificação real)

- [ ] **Step 1.** `export ANTHROPIC_API_KEY=...`; `rm -f output/teo-guardiao-da-noite/teo-e-o-guardiao-da-noite-c-ep26-*.mp4`; `rm -f output/teo-guardiao-da-noite/_formaC/ep26/visao.json`.
- [ ] **Step 2.** `python3 output/teo-guardiao-da-noite/fonte/_render_all.py c 26` (bg + waiter).
- [ ] **Step 3 — Verificar.** Conferir `visao.json` (shots por painel variados: close/insert/pan/tilt, não repetidos), `miolo.movie.yaml` (câmeras com `at` deslocados, durações variadas), e o MP4 final íntegro. Mostrar ao usuário p/ veredito.
- [ ] **Step 4 — Commit** `test(formaC): piloto ep26 dirigido por visao`.

---

## Self-Review
- Cobre o pedido: recorte por conteúdo (T1+T2), velocidades variadas (T2 pesos), "como filme real" via visão (T1), reuso da imagem (sem gerar quadros), liga na bíblia (T4). ✅
- Fallback determinístico preserva as outras séries (visao off → `_seq` atual). Retrocompat ok.
- Sincronia áudio/vídeo mantida (decupagem = 1 áudio/painel; soma das durações = d) — mesmo princípio já validado.
- Resolução/"mais slides" ficam p/ produção (não dependem deste plano).
- Custo: 1 chamada de visão por imagem por episódio (cacheada). Opt-in via preset + ANTHROPIC_API_KEY.
