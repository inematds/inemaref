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
FICHA pronta pro `folder` — **`id`** (slug, obrigatorio), `nome`, `aparencia` reutilizavel,
`personalidade[]`, `caracteristicas[]`, `detalhes[]` com IDADE, `frase`, 5 `focos`, `kicker`,
`subtitulo`), `elenco[]` (cada um com
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
