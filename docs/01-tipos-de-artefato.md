# 01 — Tipos de artefato

Originados das 7 imagens de referência (ChatGPT) em `assets/exemplos/`. Três tipos distintos.

## Tipo 1 — Folder / ficha de personagem (o *model sheet*)

Exemplos: `folder-menino-nerd.png`, `folder-menina-amigas.png`, `folder-ideni-skate.png`.

Layout editorial/revista: **retrato grande** + **PERSONALIDADE** + **CARACTERÍSTICAS PRINCIPAIS** (ícones) +
**DETALHES** (nome, idade, estilo, frase) + tira **"DETALHES EM FOCO"** (5 mini-retratos). Fotorrealista.

**Papel:** é a **referência travada** da pessoa. Gera 1 vez por personagem e vira a fonte de verdade para
todas as páginas/episódios. → produzido pela skill `folder`.

## Tipo 2 — Página de HQ fotorrealista

Exemplo: `pagina-foto-age-is-power.png` (a senhora — "AGE IS EXPERIENCE. EXPERIENCE IS POWER").

Foto-realismo em painéis, paleta sépia/âmbar, **SFX em bold** (RACKLE, FLIP, CLACK, WHOOSH), caixas de
narração, "TO BE CONTINUED". Pessoa real como protagonista.

## Tipo 3 — Página de HQ ilustrada/cartoon

Exemplos: `pagina-cartoon-guardia-natureza.png`, `pagina-cartoon-menino-descobertas.png`,
`pagina-cartoon-amigas-aventuras.png`.

Mesma gramática de HQ (painéis, balões, SFX, título), mas **desenho/pintura** (aquarela, cores vivas) em vez
de foto. "PLIM!", "FSSS!", splashes de cor.

## Implicações de projeto

- **Dois estilos coexistem** (foto e cartoon) → tratar como **presets de estilo** na skill `quadrinho`, não
  escolher um só.
- **O folder (tipo 1) precede as páginas (tipo 2/3)** → confirma a referência como passo 0.
- Nos exemplos do ChatGPT o **texto vem grudado (baked)**. O `inemaref` vai pelo caminho **textless +
  camada** (ver `docs/03`), mantendo o look mas ganhando controle.
