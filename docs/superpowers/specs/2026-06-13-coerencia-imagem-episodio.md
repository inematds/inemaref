# Coerência de imagem + referência de episódio (design — RASCUNHO p/ revisão)

Data: 2026-06-13
Status: **implementado** em `v1.04.001` (Pilar A on; Pilar B/C opt-in via `INEMAREF_QC=1`). Decisões resolvidas no fim.
Skills tocadas (previsto): `folder` (referência), `serie` (bíblia/episódio), `quadrinho`/`motioncomic` (geração dos painéis).

## Problema (do usuário)

Hoje a imagem é gerada por `flux2-klein` (T2I puro) a partir de um prompt = `aparencia` (string da referência) + cena + arte. **Não há nenhuma verificação** de que a imagem saiu coerente. Três exigências:

1. **Revisar a imagem ao ser criada** — conferir se está **adequada ao personagem** (bate com a referência/folder) **e à bíblia** (estilo, mundo, cenário corretos). Ex.: cenário pedido era **riacho**, não pode sair **praia**.
2. **Anatomia** — a verificação tem que pegar **erro de anatomia** (mãos/dedos errados, membros a mais, deformação, proporção).
3. **Referência de episódio** — quando um **episódio** muda algo de um personagem/objeto **canônico da bíblia** (ex.: outra roupa, um **uniforme**, um local específico), é preciso **criar a referência daquele episódio**: ela combina **o canon da bíblia + o delta do episódio**, e **todos os painéis do episódio** usam essa referência derivada — coerência interna ao episódio **sem perder** as características da bíblia.

## Contexto técnico (restrições reais)

- `imgclient.generate(prompt, out, model, width, height, images=None, negative_prompt, seed)` — `flux2-klein` **ignora `images`** (T2I; HTTP 500 se mandar). `qwen-edit-2511` aceita `images` (img2img/face-swap) mas é **instável** (OOM/500 na troca de modelo). Ver `docs/04-consistencia-pessoa-real.md`.
- Logo, **a coerência não vem de condicionar por imagem** (img2img) de forma confiável. Vem de **(a) texto de referência estruturado** no prompt + **(b) verificação por visão depois** + **(c) regerar quando reprovar**. `seed` permite variar/repetir geração.
- Material de referência já disponível: `folder/referencia.json` (`aparencia`, `retrato_ancora.png`, `ficha`); `serie/biblia.json` (`protagonista`, `elenco`, `elementos` = canon visual, `estilo.arte`). O episódio (`episodio.json`/roteiro) tem os painéis (`prompt`, `quem`).

## Abordagem proposta (3 pilares)

### Pilar A — Referência de episódio (derivação canon + delta) — *resolve a exigência 3*
- Estender o canon da bíblia (`protagonista`/`elenco`/`elementos`, cada um com `aparencia` base) com **overrides por episódio**.
- Ao montar um episódio, gerar uma **referência efetiva por entidade** = `aparencia_base` (bíblia) **+ delta do episódio** (ex.: `roupa: "uniforme escolar azul"`, `local_padrao: "riacho na mata"`, `estado_objeto: "…"`). Resultado = string/￼estrutura usada em **todos** os prompts daquele episódio.
- Persistir em algo como `referencia-ep.json` (ou bloco `referencias_efetivas` no `episodio.json`) p/ rastreabilidade e reuso (Forma A/B/C do mesmo ep).
- **Travar o que NÃO muda** (rosto, traços, paleta do personagem) e **aplicar só o delta** (roupa/local/objeto). O delta tem **precedência** sobre o canon só nos campos que ele declara.

### Pilar B — QC por visão após gerar (adequação) — *resolve a exigência 1*
- Depois de `generate`, **Claude VÊ a imagem** (mesmo padrão do `diretor-animacao`) e pontua contra: (1) **personagem** (bate com `aparencia` efetiva + `retrato_ancora`), (2) **bíblia/cenário** (estilo `arte` correto; **local certo** — riacho≠praia; objetos canônicos presentes/coerentes).
- Saída estruturada: `{adequado: bool, score, motivos:[...], dimensao_reprovada}`.
- **Regerar quando reprovar**: nova `seed` (e, se preciso, prompt reforçado com o ponto que falhou), até **N tentativas**; se ainda reprovar, **marcar/flag** p/ revisão humana (não travar a série toda).

### Pilar C — Anatomia/artefatos — *resolve a exigência 2*
- Parte da mesma passada de visão (Pilar B) **ou** um checador dedicado: detectar **mãos/dedos errados, membros extras, rostos duplicados, deformação, proporção**.
- Mesma política de **regerar-ao-reprovar**. (Detector offline dedicado de anatomia é difícil; a via prática é o **check por visão**, talvez reforçado no `negative_prompt` que já tem `bad anatomy`/`extra fingers`.)

## Onde encaixa (pontos de integração)
- `skill/folder/scripts/` — função de **derivação** `referencia_efetiva(canon, delta_ep)`.
- `skill/serie/scripts/build_serie.py` — montar as referências efetivas do episódio antes de `_render_hq`/assets e passá-las aos prompts.
- `skill/folder/scripts/imgclient.py` ou um wrapper `gerar_revisado(...)` — laço **gerar → QC(visão) → regerar/flag**.
- `skill/motioncomic`/`quadrinho` — consumir a referência efetiva (em vez da `aparencia` crua da bíblia).

## Escopo / YAGNI
- **Não** depender de img2img (`qwen-edit`) p/ travar rosto enquanto for instável — coerência por **texto + QC**.
- **Não** bloquear a série inteira por 1 painel reprovado — **flag + segue**, com relatório.
- Começar pelo **Pilar A** (determinístico, testável sem rede) e pelo **QC textualmente especificado**; a chamada de visão é o passo dirigido (Claude).

## Decisões (resolvidas 2026-06-13)
1. **Quem julga** → **Claude vê** (`qc_imagem.judge_visao`, modelo de visão barato via `INEMAREF_QC_MODEL`, default `claude-haiku-4-5`).
2. **Regeneração** → até `qc_tentativas` (default 3), varia `seed` a cada tentativa e **reforça o negativo de anatomia** quando a dimensão reprovada é anatomia; reprovou tudo → **flag** (`<img>.qc.json`) e segue.
3. **Onde guardar** → **delta autoral no episódio** (`variacoes` + `cenario_padrao`); **efetivo derivado** persistido em `<ep>-referencias.json` (saída). Delta = clausula livre por entidade (não campos rígidos) — mais flexível.
4. **Bíblia** → **sem novos campos** no canon; o delta e o cenário vivem no episódio. Inferência fica a cargo do prompt do painel + `cenario_padrao`.
5. **Custo** → QC **desativado por padrão**; quando ligado (`INEMAREF_QC=1`), roda em **todas** as imagens do caminho HQ. (Amostragem/cobertura de vídeo: follow-up, se o custo pesar.)

## Implementado (v1.04.001) — o que ficou
- `folder/scripts/referencia.py::referencia_efetiva` (merge canon+delta, puro).
- `serie/scripts/referencia_ep.py::resolver_referencias`/`aplicar` (efetivo por ep + dobra de cenário + resolve `quem`).
- `folder/scripts/qc_imagem.py::gerar_revisado`/`make_generate_fn`/`judge_visao` (loop gerar→revisar→regerar/flag; backend de visão opt-in).
- `serie/scripts/build_serie.py`: aplica refs efetivas no lote, persiste `<ep>-referencias.json`, e injeta o QC no `generate_fn` do `build_pagina` quando ligado.
- Testes: `serie/tests/test_referencia_ep.py`, `folder/tests/test_qc_imagem.py` (85/85 verdes).

## Pendências / follow-up
- ✅ **(feito, v1.05.001)** QC nos caminhos de **vídeo**: `build_video_travel`/`build_video`/`_gen_image` aceitam `generate_fn`; o `serie._render_video` injeta o QC (Formas A/B), igual à HQ.
- `judge_visao` (chamada real à API) é **opt-in e não testado ao vivo** — validar custo/latência num episódio quando o usuário ativar.
