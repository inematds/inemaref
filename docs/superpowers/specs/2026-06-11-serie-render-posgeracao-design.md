# Série — Bloco Render + Bloco Pós-geração (design)

Data: 2026-06-11
Skills afetadas: `quadrinho`, `motioncomic`, `serie`
Status: design aprovado em conversa; pendente revisão do spec antes do plano.

## Objetivo

Dois blocos de melhoria na fábrica de séries do inemaref:

- **Bloco Render** — muda *o que sai* da geração: moldura nova da página, página
  textless dedicada ao vídeo, narração fluente única com gancho inicial, e o
  destino de saída padronizado.
- **Bloco Pós-geração** — opera *sobre o já gerado* (sem regenerar arte/voz):
  empacotar (zip), re-renderizar entre formatos A↔B, e gerar vídeo por página.

Princípio comum do Pós-geração: tudo lê os assets cacheados em
`<destino>/<id>/epNN/{pages,voz,clips}` e só monta/empacota. Nada regenera.

## Conceitos travados

- **Carrossel** = as **páginas** montadas em PNG (`pagina.png`), lidas como
  quadrinho. **Não é vídeo.** Mantém o texto impresso (narração/balão/SFX).
- **Forma A** (`video-slideshow` → `build_motion.build_video`) = slideshow:
  zoom quadro-a-quadro, voz-off. Consome os **painéis direto** (`assets/*.png`,
  já textless). **Não monta página.**
- **Forma B** (`video-pagina` → `build_travel.build_video_travel`, padrão) =
  câmera sobrevoa a **página de papel**. **Sempre monta a página** em quadrinho,
  mas na cópia **textless**. (No re-render pós-geração, reaproveita a página
  textless já em disco — não remonta.)
- **A/B é FORMATO**, não narração. A narração é uma **faixa fluente única**
  (campos `narracao` por quadro + `abertura`) que serve A e B igualmente. O
  formato muda só câmera/visual.

---

## Bloco Render

### R1 — Moldura V2 da página (skill `quadrinho`)

Substitui a moldura escura grossa atual (`.pagina { background:#111; padding:36px 40px 40px }`,
idêntica em `grade-uniforme` e `manga-dinamico`) por um layout "galeria":

- **Cabeçalho**: kicker com o nome da série (caixa-alta, espaçado, cor de
  destaque) + título do episódio serifado, com respiro generoso acima.
- **Mat branco** equalizado nos 4 lados ao redor do bloco de quadros.
- **Gutters uniformes finos** (~9px), com a **moldura externa = gutter interno**
  (mesmo tratamento), via `.quadros { background:<gutter>; padding:<gut>; gap:<gut> }`.
- **Duas variantes de moldura**, escolhidas por geração (como já há dois
  templates de layout):
  - `dark` — moldura/gutters escuros finos (quadros presos em frame preto fino);
  - `white` — moldura/gutters brancos (quadros flutuam no branco, look galeria).

Implementação: parametrizar `style.css` dos dois templates (ou variáveis CSS
injetadas no `fill_pagina`) com `moldura ∈ {dark, white}`. **Default: `dark`**
(frame visível, "quadrinho de verdade"); `white` é opção por geração.
Documentar ambas no `SKILL.md` do `quadrinho`.

Cor de destaque do kicker/título: configurável; default herda de um campo da
bíblia da série (ex.: `estilo.cor_destaque`) com fallback fixo.

Mockups de referência: `/tmp/mock_frames/{v2b-dark,v2c-white}.png` (efêmeros).

### R2 — Página textless para vídeo (skills `quadrinho` + `motioncomic`)

Hoje a Forma B viaja sobre `pagina.png` **com** texto impresso (decisão antiga,
`build_travel.py:12-13`). Inverter:

- `build_pagina` passa a emitir **dois** PNGs por página:
  - `pagina.png` — com texto (narração/balão/SFX). Vai pro **carrossel/HQ**.
  - `pagina-textless.png` — re-render do **mesmo HTML** escondendo
    `.narracao,.fala,.sfx` (mantendo `.panel-img` visível). Vai pro **vídeo**.
- O mecanismo já existe: `render_mask` (`build_travel.py:134`) já usa
  `display:none` nesses seletores — reaproveitar a técnica (sem esconder
  `.panel-img`).
- **Forma B** (`build_travel`) passa a viajar sobre `pagina-textless.png`.
- **Forma A** já consome painéis textless (`assets/*.png`) — sem mudança de
  fonte; só garantir que não imprime texto na imagem.
- **Carrossel** continua usando `pagina.png` (com texto).

Custo: um screenshot a mais por página (barato; sem geração de arte/voz).

### R3 — Narração fluente única + gancho inicial (skill `motioncomic` + modelo de conteúdo)

- **A/B = formato** documentado de forma inequívoca no `SKILL.md` do
  `motioncomic` e `serie`, pra não reincidir o equívoco de "duas narrações".
- **Narração fluente única** serve A e B (já é a mesma fonte de roteiro).
- **Gancho inicial**: no t=0, mostrando o **card do assunto**, a narração abre
  com uma **chamada/gancho de atenção** clara — não só "dizer o assunto".
  - *Timing*: garantir áudio começando em t=0 sobre o card (`build_travel`
    abertura, ~`build_travel.py:336,361`; equivalente na Forma A).
  - *Conteúdo*: padronizar no modelo que `abertura` é um gancho (orientação no
    guia de narração do `SKILL.md` da série + validação leve na bíblia/roteiro).

### R4 — Destino padrão `~/projetos/output/<id>`

Hoje `formato.destino: "output"` (relativo ao cwd). Mudar o default para
`~/projetos/output` (absoluto, expanduser), fora do repo, uma pasta por série:
`~/projetos/output/<serie_id>/`. Continua sobrescritível por `out_dir`/config.

Pontos de mudança: `config.py` DEFAULTS (`formato.destino`) e o fallback em
`build_serie.py:173` (`destino = out_dir or s["destino"] or <novo default>`).

---

## Bloco Pós-geração

Novos comandos na skill `serie` (em `scripts/`), todos operando sobre
`<destino>/<id>/` já gerado, guiados pelo `manifesto.json`.

### P1 — Export / ZIP (`exportar_zip`)

`exportar_zip(serie_dir, tipo)` com `tipo ∈ {folders, paginas, imagens}`:

- `folders` — model sheets do(s) personagem(ns) (saída do `folder` no pacote da
  bíblia: `<id>/biblia/...`).
- `paginas` — todas as `pagina.png` (pranchas com texto) de
  `epNN/pages/*/pagina.png`.
- `imagens` — todos os painéis crus `epNN/pages/*/assets/*.png`.

Saída: `<serie_dir>/export/<id>-<tipo>.zip`. Só leitura + zip; sem regenerar.

### P2 — Re-render entre formatos A↔B (`re_render`)

`re_render(serie_dir, forma, ep=None)` com `forma ∈ {A, B}`:

- **→ B (travel)**: reaproveita `epNN/pages/*/pagina-textless.png` + `mask.png`
  (re-detecta rects sem re-renderizar) + `voz/*.wav`. Remonta só os clipes e o
  concat. Não regenera arte/voz; se faltar `pagina-textless.png` (séries
  antigas), re-renderiza a página textless a partir do `pagina.html` persistido.
- **→ A (slideshow)**: usa os painéis `epNN/pages/*/assets/*.png` + `voz/*.wav`;
  monta o slideshow. Sem regenerar.

Saída: novo `.mp4` por episódio na pasta, nomeado com o sufixo do formato.

### P3 — Vídeo por página (`videos_por_pagina`)

`videos_por_pagina(serie_dir, forma=B, ep=None)`: gera **1 clipe por prancha**
(cada `pagina(-textless).png` + os wavs daquela página: `p{nn}q*.wav` +
`chamada{nn}*.wav`), reusando o motor do `motioncomic`. Saída:
`epNN/paginas-video/epNN-pgMM.mp4`.

---

## Pré-requisito de persistência (já satisfeito)

Verificado em disco (`output/escada-invisivel-lia/`, série Maslow): cada página
persiste `pagina.png`, `assets/*.png`, `mask.png`, `pagina.html`, `roteiro.json`,
e a voz em `epNN/voz/*.wav`. O Pós-geração é viável sem mudança de pipeline,
**exceto** o novo `pagina-textless.png` (R2), que passa a ser emitido na geração
e re-derivado do `pagina.html` para séries antigas.

## Ordem de execução

1. **Bloco Render** primeiro (muda o que a fábrica produz), nesta ordem:
   R4 (destino) → R1 (moldura) → R2 (textless) → R3 (narração/gancho).
2. **Bloco Pós-geração** depois (P2 já nasce consumindo a página textless de R2):
   P1 (zip) → P3 (vídeo por página) → P2 (re-render A↔B).

## Testes

- `quadrinho`: build_pagina emite `pagina.png` **e** `pagina-textless.png`; o
  textless não contém `.narracao/.fala/.sfx` (checar via DOM/marcação no HTML de
  teste); as duas variantes de moldura renderizam sem erro. (`render_fn`
  injetável, sem Chromium real no teste unitário.)
- `motioncomic`: Forma B usa `pagina-textless.png`; abertura entra em t=0.
- `serie`: destino default resolve para `~/projetos/output/<id>`;
  `exportar_zip`/`re_render`/`videos_por_pagina` leem o manifesto e produzem
  saída a partir de uma pasta `<id>/` fixtura (sem daemons), com `renderers`
  injetáveis.

## Fora de escopo (YAGNI)

- Re-render retroativo automático das 20 páginas da série Maslow (decisão à
  parte; a infra de R2/P2 permite, mas não dispara sozinha).
- Formatos de export além de zip (tar, upload).
- UI/landing; só os scripts e SKILL.md.
