# inemaref — fábrica de conteúdo a partir de referência

> **Escopo (lê isto primeiro):** `inemaref` é uma **fábrica de conteúdo a partir de uma referência de pessoa real**.
> Entro com **uma foto + uma história** → saem artefatos com a **mesma pessoa consistente**:
> **ficha de personagem (folder) → página de quadrinho → série/episódios → filme.**
> O **ativo central é a referência** (a pessoa real travada) — ela atravessa todos os artefatos. Por isso
> "ref" no nome: tudo aqui *cria* ou *consome* essa referência. **Não é gaveta genérica** — se não envolve
> referência de pessoa → personagem → história, não entra aqui.

## Por que existe

Fazer **histórias em quadrinhos com pessoas reais** esbarra sempre no mesmo nó: **manter o personagem igual**
entre quadros, páginas e episódios. A solução é tratar a **referência** (o *model sheet* da pessoa) como o
passo 0 que trava tudo. A partir dela, montar páginas, séries e — reusando o ecossistema de vídeo que já
existe — motion comics narrados e filmes.

## O fluxo

```
1 FOTO (pessoa real) + HISTÓRIA
  → FOLDER       (skill: ficha de referência — o model sheet que trava a pessoa)
  → QUADRINHO    (skill: monta a página — quadros sem texto + texto/balões em camada)
  → [estático]   página pronta (texto baked OU camada) — 2 estilos: foto e cartoon
  → [dinâmico]   motion comic: câmera abre na prancha → viaja pelos quadros + narração
  → SÉRIE        (V2: várias páginas, carrossel, episódios de um canal)
  → FILME        (V3: vira vídeo — reusa o videoprodutor)
```

## Estado

**V1 + V2 construídas; primeira série completa produzida.** As skills `folder`, `quadrinho`, `motioncomic` (V1) e `serie` (V2 — criador de série) estão **construídas e testadas** (suíte verde). A V2 já gerou uma **série inteira de exemplo** — *A Escada Invisível de Lia* (a Pirâmide de Maslow), 20 episódios × 10 páginas em vídeo (bíblia + roteiros versionados em [`conteudo/`](conteudo/)). Filme (V3) permanece à frente. Página do projeto (landing + guia): [`index.html`](index.html).

## Skills

- `skill/folder/` — ✅ **construída** — **cria a referência**: a ficha do personagem (retrato + bio + traços + grid), a partir de 1 foto ou texto. 2 layouts × 2 artes.
- `skill/quadrinho/` — ✅ **construída** — monta a **página de HQ/mangá** (6 quadros textless + balão/SFX/legenda em camada, colocação de texto consciente de rosto), 2 modelos de página.
- `skill/motioncomic/` — ✅ **construída** — quadrinho em **vídeo** (TTS), em **duas formas**:
  - **Forma A — slideshow** (`build_motion`): uma imagem por vez com zoom + narração voz-off.
  - **Forma B — câmera sobre a página de papel** (`build_travel`): monta a prancha real (grade 2×3) e a câmera viaja sobre ela, mergulhando em cada quadro durante a narração, afastando e encaixando no próximo (`docs/02`). É o modo "quadrinho de verdade".
- `skill/serie/` — ✅ **construída (V2)** — **criador de série ponta a ponta**: assunto → bíblia (folder + elenco + estilo + outline) → após aprovar, gera todos os episódios em texto/HQ/vídeo (reusa as skills acima) → arquivos nomeados + `manifesto.json` numa pasta de destino. Defaults em `config.yaml`; runner híbrido (inline | mkivideos).
- `skill/referencias/` — núcleo comum: estilos (foto/cartoon/mangá), regra de consistência, schema da referência.

## Como usar

Cada skill é um pipeline Python rodado da raiz do repo; a saída cai em `output/<id>/` (gitignorado).
Pré-requisitos: `inemaimg` (flux2-klein) em `localhost:8000`; para vídeo, `inemavox` em `127.0.0.1:7860`; e `ffmpeg`/Chromium.

```python
# 1) referência (folder)
import sys, json; sys.path.insert(0, "skill/folder/scripts")
from build_folder import build_folder
build_folder(json.load(open("ficha.json")),
             template_dir="skill/folder/templates/editorial-revista", arte="cartoon", modo="texto")

# 2) página de HQ (quadrinho) — roteiro com exatamente 6 painéis
sys.path.insert(0, "skill/quadrinho/scripts")
from build_pagina import build_pagina
build_pagina(json.load(open("roteiro.json")),
             template_dir="skill/quadrinho/templates/grade-uniforme", arte="manga")

# 3) vídeo — câmera sobre a página (motioncomic, Forma B); páginas de 6 quadros
sys.path.insert(0, "skill/motioncomic/scripts")
from build_travel import build_video_travel
build_video_travel(json.load(open("roteiro.json")), voice="bella", arte="manga")
```

Guia completo, com exemplos e pré-requisitos: abra [`index.html`](index.html) (também publicável no GitHub Pages).
Cada `skill/<nome>/SKILL.md` traz a entrada esperada (schema do JSON) e os detalhes.

## Instalar como skills (Claude Code)

As skills podem ser **instaladas individualmente** em `~/.claude/skills/` (symlink apontando pro `skill/<nome>` do repo). Duas regras:

- **Nomes prefixados `inemaref-<nome>`** (`inemaref-folder`, `inemaref-quadrinho`, `inemaref-motioncomic`, `inemaref-serie`, `inemaref-referencias`) — evita **conflito** com outras skills de nome genérico. (O diretório no repo continua `skill/<nome>`; só o nome instalado é prefixado.)
- **Independência + dependências:** cada skill **localiza as irmãs por descoberta** (`$INEMAREF_HOME/skill/<x>` → `~/.claude/skills/inemaref-<x>` → repo via realpath), então instalar uma sozinha funciona desde que suas **dependências** estejam disponíveis. As dependências são declaradas no `SKILL.md` (ex.: `serie` requer `folder`/`quadrinho`/`motioncomic`; `quadrinho`/`motioncomic` requerem `folder` + `referencias`). Atalho: `export INEMAREF_HOME=<caminho-do-repo>`.

Cada skill responde a **`/inemaref-<nome> help`** com o resumo de uso e opções.

> Se aparecer **erro de referência** ao instalar/usar uma skill sozinha, é uma dependência não encontrada (ex.: `folder`/`referencias`): instale a skill irmã ou defina `INEMAREF_HOME`.

## Documentos

- [`docs/00-escopo-e-visao.md`](docs/00-escopo-e-visao.md) — o que é, e a visão V1 / V2 / V3.
- [`docs/01-tipos-de-artefato.md`](docs/01-tipos-de-artefato.md) — folder, página foto, página cartoon (com exemplos em `assets/exemplos/`).
- [`docs/02-motion-comic.md`](docs/02-motion-comic.md) — a câmera que abre na prancha e viaja pelos quadros + narração.
- [`docs/03-decisao-painel-a-painel.md`](docs/03-decisao-painel-a-painel.md) — por que gerar quadro-a-quadro (caminho B), não a página num shot.
- [`docs/04-consistencia-pessoa-real.md`](docs/04-consistencia-pessoa-real.md) — o nó técnico; Nano Banana × flux2-klein; o experimento a rodar.
- [`docs/05-reuso-ecossistema.md`](docs/05-reuso-ecossistema.md) — pixflow / videoprodutor / mdd / inemavox / inemaimg já fazem ~80%.

## Exemplos

`assets/exemplos/` — as 7 imagens de referência feitas no ChatGPT que originaram este projeto
(3 folders, 1 página foto, 3 páginas cartoon).
