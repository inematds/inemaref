---
name: quadrinho
description: Monta uma PAGINA de quadrinho/manga a partir de uma HISTORIA (e, opcionalmente, da referencia.json de um personagem do folder). Gera 6 quadros textless (estilo manga p&b) e poe narracao, baloes de fala e SFX como camada por cima, renderizando pra PNG. Use quando o usuario quiser "fazer quadrinho", "pagina de manga", "transformar a historia em HQ", "quadrinizar", "comic page". Dois modelos de pagina: grade-uniforme (todos os quadros iguais) e manga-dinamico (tamanhos diferentes).
---

# Skill: quadrinho — pagina de HQ/manga (passo 2 do inemaref)

Mesma arquitetura **textless + camada** do `folder`: o motor de imagem gera so os **quadros**
(textless); **narracao, baloes e SFX** sao camada HTML/CSS renderizada pra PNG. Reusa os helpers
testados do folder (`imgclient`, `render`, `png_size`, `artes`).

## Entrada
- **Historia** (texto). Obrigatorio.
- Opcional: `referencia.json` de um personagem (do `folder`) — usa o campo `aparencia` pra manter o
  personagem nos quadros.
- Opcional: **modelo de pagina** (`grade-uniforme` | `manga-dinamico`) e **arte** (default `manga`).

## Passos
1. **Monte o roteiro** — um `roteiro.json` no formato de
   `skill/quadrinho/tests/fixtures/roteiro-visionario.json`:
   `id` (slug), `titulo`, `personagem_aparencia` (descricao reutilizavel do personagem — copie do
   `aparencia` da `referencia.json` se houver), e **exatamente 6** `paineis`. Cada painel:
   `prompt` (cena textless, obrigatorio) + opcionais `narracao` (caixa de legenda), `fala` (balao) e
   `sfx` (onomatopeia).
2. **Rode o pipeline:**
   ```bash
   python3 - <<'PY'
   import sys, json
   sys.path.insert(0, "skill/quadrinho/scripts")
   from build_pagina import build_pagina
   rot = json.load(open("CAMINHO/roteiro.json"))
   build_pagina(rot,
       template_dir="skill/quadrinho/templates/<modelo>",  # grade-uniforme | manga-dinamico
       arte="manga")
       # out_dir default = "output" (raiz do repo, gitignorado)
   PY
   ```
   (Pre-requisito: servidor `inemaimg` em `http://localhost:8000`.)
3. **Mostre** o `pagina.png`. Saida em `output/<id>/`: `pagina.png`, `pagina.html` (editavel — texto
   e camada real), `assets/` (6 quadros crus), `roteiro.json`.

## Modelos de pagina
- **grade-uniforme** — 6 quadros iguais (2x3).
- **manga-dinamico** — 6 quadros de tamanhos diferentes (layout assimetrico, com splash).
- Ambos usam os mesmos 6 paineis; o CSS posiciona. Novo modelo = nova pasta em `templates/`
  (template.html + style.css + meta.json, mesmos placeholders `{{titulo}}` / `{{paineis_html}}`).

## Arte / motor
Estilo `manga` (p&b, screentone) em `skill/referencias/artes.json`. Motor padrao `flux2-klein`
(mesmo seam do folder; troca por `model=` em `build_pagina`).
