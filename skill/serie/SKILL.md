---
name: inemaref-serie
requires: [inemaref-folder, inemaref-quadrinho, inemaref-motioncomic, inemaref-referencias]
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
**`objetivo`** (obrigatorio), `premissa{logline,sinopse}`, `estilo`/`formato` (so o que difere do
default), `protagonista` (uma FICHA pronta pro `folder` — **`id`** (slug, obrigatorio), `nome`,
`aparencia` reutilizavel, `personalidade[]`, `caracteristicas[]`, `detalhes[]` com IDADE, `frase`,
5 `focos`, `kicker`, `subtitulo`), `elenco[]` (cada um com `aparencia` travada), **`elementos[]`**
(canon visual) e `episodios[]` (exatamente `n_episodios`).

**Tres regras de conteudo (o que torna a serie boa):**
1. **Objetivo + contribuicao.** A serie tem um **`objetivo`** declarado (o que quer alcancar e PRA QUEM
   — ensinar/convencer/emocionar/vender). E **cada episodio** tem **`contribuicao`** (1 frase: o que
   ELE entrega rumo ao objetivo). Nenhum episodio e so cena solta — todo `{n,titulo,sinopse,contribuicao}`.
2. **Canon visual (`elementos`).** Conceitos/objetos/cenarios recorrentes (ex.: a "Piramide de Maslow"
   com 5 camadas) sao **definidos UMA vez** em `elementos[] = [{nome, aparencia travada}]` e
   **referenciados** nos quadros que os usam, via `usa: ["Piramide"]` no painel — o motor **dobra** a
   `aparencia` no prompt (como faz com o protagonista). Assim a piramide sai IGUAL em todo quadro/episodio.
3. **Narracao fluente.** NAO escreva uma frase solta por quadro. Escreva a **locucao da pagina como um
   texto corrido** (gancho -> desenvolvimento -> virada -> fecho, com conectivos "entao/mas/foi ai que")
   e **segmente** esse texto nos 6 quadros — cada `narracao` e um pedaco de um todo coerente, nao uma
   legenda isolada.
4. **Acentuacao correta (a narracao e FALADA por TTS).** Escreva todo texto narrado/exibido — `abertura`,
   `titulo`, `chamada`, `narracao` e `fala.texto` — **JA com a acentuacao do portugues** (nao, voce, ceu,
   agua, tambem, vulcao, manha...). Sem acento o inemavox pronuncia errado. **O `build_serie` ja roda uma
   checagem automatica** (`revisar_acentos`) que corrige o que e seguro antes do TTS e avisa formas
   ambiguas (esta/esta) — mas o acerto na fonte e o que garante a voz certa; os campos de imagem
   (`prompt`/`quem`/`usa`/`sfx`) NAO sao tocados.

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
Apos aprovar, escreva os roteiros de TODOS os episodios (guiado pela biblia, **servindo a
`contribuicao` de cada um**). Cada episodio = roteiro no formato do `motioncomic`:
`{id, n, titulo, sinopse, personagem:<aparencia do protagonista>,
paginas:[{n,titulo,paineis:[6x {prompt, narracao?, fala?{quem,texto}, sfx?, quem?, usa?:["Elemento"]}]}]}`.
- **Consistencia:** use a `aparencia` do protagonista/elenco em todo quadro; e marque `usa:["Nome"]` nos
  quadros que mostram um **elemento** do canon — o motor dobra a aparencia travada (piramide igual sempre).
- **Narracao fluente:** escreva a locucao da pagina como texto corrido e **segmente** nos 6 quadros (ver
  Passo 1, regra 3). `n_paginas` paginas por episodio.

## Coerencia por episodio (variacoes + QC)
Quando um episodio **muda algo** de um personagem/objeto canonico, ou tem um cenario proprio, declare no
**proprio episodio** (o lote deriva a `aparencia efetiva = canon da biblia + delta` e aplica em TODOS os
paineis, sem perder o canon; o derivado fica em `<ep>-referencias.json`):
- **`variacoes`**: `{ "<id|nome da entidade>": "<clausula da mudanca>" }` — ex.:
  `{"lia": "vestindo uniforme escolar azul-marinho", "piramide de maslow": "parcialmente submersa"}`.
  Casa por nome/id (ignora caixa) com protagonista, `elenco[]` e `elementos[]`. O `quem` de painel que
  bate um nome vira a aparencia efetiva.
- **`cenario_padrao`**: ancora de mundo do episodio (ex.: `"riacho na mata, luz dourada"`) — dobrada no
  fim de cada `prompt` p/ travar o lugar (**riacho != praia**).
- **QC da imagem (opcional, custo):** ligando **`INEMAREF_QC=1`** (+ `ANTHROPIC_API_KEY`), cada painel
  e revisado por **visao** (bate personagem? cenario certo? anatomia ok?) e **regerado** ao reprovar
  (ate `qc_tentativas`, default 3); reprovou tudo -> `flag` em `<img>.qc.json` e segue. **Desativado por
  padrao** (sem custo, comportamento inalterado).

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

**Os dois formatos narrados (= "Forma A / Forma B" do motioncomic docs/02).** Quando o usuario
pedir "versao narrada A e B", "as duas formas", "slideshow e pagina" — ele quer ESTES dois `tipo`s,
NAO duas vozes:
- **`video-slideshow` (Forma A)** — `build_motion`: cada quadro vira imagem textless, balao/SFX
  sobrepostos, narra e da ZOOM no quadro durante a fala; a camera viaja **quadro a quadro**.
- **`video-pagina` (Forma B)** — `build_travel`: monta a PAGINA real de quadrinho (grade, sarjetas,
  baloes impressos) e a camera **sobrevoa a folha** como quem filma um papel.
Voz (`bella`/`rachel`) e um eixo SEPARADO de A/B — nao confunda formato com voz.

**A/B e FORMATO, nao narracao.** A narracao e uma faixa fluente UNICA, compartilhada por A e B.
Nunca gere "duas narracoes" ou "duas vozes" por causa do formato.

## Estilo — moldura e cor_destaque
Dois campos de estilo novos (em `config.yaml` e `FALLBACK`):
- **`moldura`** (`dark` | `white`) — frame da pagina HQ: `dark` = borda fina escura (padrao);
  `white` = gutters brancos, look galeria.
- **`cor_destaque`** (hex, default `"#b08900"`) — cor do kicker/realce no cabecalho de cada pagina.

O campo **`kicker`** da biblia (string; se ausente, usa `assunto`) aparece acima do titulo em cada
pagina — identifica a serie visualmente. O `build_serie` injeta `kicker` no `settings` resolvido
e repassa `moldura`/`kicker`/`accent` para `build_pagina` (HQ) e `build_video_travel` (Forma B).
Para sobrescrever numa biblia especifica: adicione `"estilo": {"moldura": "white", "cor_destaque": "#c04000"}` na `biblia.json`.

## Help
Se o usuario digitar `/inemaref-serie help`, responda com este resumo:
- **O que faz:** cria uma serie completa a partir de um assunto — escreve a biblia (premissa, protagonista, elenco, estilo, outline), e apos aprovacao gera todos os episodios em texto/HQ/video + manifesto.json.
- **Entrada:** um assunto (obrigatorio) + config opcional (`tipo`, `arte`, `modelo_pagina`, `n_episodios`, `n_paginas`, `destino`, `auto`); o que faltar cai no `config.yaml`.
- **Uso:** monte `biblia.json` (+ piloto), rode `build_biblia(b, piloto=...)` para aprovacao, depois `build_serie(b, eps, auto=True)` em `skill/serie/scripts`.
- **Depende de:** inemaref-folder, inemaref-quadrinho, inemaref-motioncomic, inemaref-referencias.
- **Pre-requisitos:** `inemaimg` em `localhost:8000`; para `video-*` tambem `inemavox` em `127.0.0.1:7860` (TTS) + ffmpeg.
