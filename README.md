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

**Versão atual: `v1.04.001`** — esquema e histórico no [Changelog](#changelog).

## Skills

- `skill/folder/` — ✅ **construída** — **cria a referência**: a ficha do personagem (retrato + bio + traços + grid), a partir de 1 foto ou texto. 2 layouts × 2 artes.
- `skill/quadrinho/` — ✅ **construída** — monta a **página de HQ/mangá** (6 quadros textless + balão/SFX/legenda em camada, colocação de texto consciente de rosto), 2 modelos de página.
- `skill/motioncomic/` — ✅ **construída** — quadrinho em **vídeo** (TTS), em **duas formas**:
  - **Forma A — slideshow** (`build_motion`): uma imagem por vez com zoom + narração voz-off.
  - **Forma B — câmera sobre a página de papel** (`build_travel`): monta a prancha real (grade 2×3) e a câmera viaja sobre ela, mergulhando em cada quadro durante a narração, afastando e encaixando no próximo (`docs/02`). É o modo "quadrinho de verdade".
- `skill/serie/` — ✅ **construída (V2)** — **criador de série ponta a ponta**: assunto → bíblia (folder + elenco + estilo + outline) → após aprovar, gera todos os episódios em texto/HQ/vídeo (reusa as skills acima) → arquivos nomeados + `manifesto.json` numa pasta de destino. Defaults em `config.yaml`; runner híbrido (inline | mkivideos).
- `skill/referencias/` — núcleo comum: estilos (foto/cartoon/mangá), regra de consistência, schema da referência.

## Formatos de vídeo e o ecossistema (A / B / C)

O `motioncomic` entrega vídeo em **formas**, nomeadas no arquivo como `<serie>-a/-b/-c-epNN-…mp4` (a letra vem antes do `epNN`; A e B convivem na mesma pasta da série):

- **Forma A — slideshow** (✅): uma imagem (textless) por vez, push-in + narração voz-off; balão/SFX opcionais na imagem.
- **Forma B — câmera sobre a página** (✅): monta a prancha real e a câmera viaja sobre a cópia **textless** (voz-off), mergulhando em cada quadro.
- **Forma C — filme cinematográfico** (🔜 planejada): a versão "filme" dos painéis. **Reusa o skill externo `diretor-animacao` como MOTOR** — não reinventamos a direção nem falamos com o pixflow na mão.

**Como a Forma C funciona (decisão registrada):** reaproveita os **painéis textless + as narrações** já gerados pela Forma A (sem regerar imagem nem voz) e os entrega ao `diretor-animacao`, que **VÊ** cada imagem, **DECIDE** a câmera por quadro seguindo gramática cinematográfica (18 movimentos + framing `from/to`, transições **não-uniformes**, curva de 3 atos, multi-shot em imagens ricas), aplica **look/grain/vinheta** e renderiza via **pixflow**. Para **desenho/ilustração** (nosso caso), **`parallax = 0`** (regra de ouro do diretor) — o "filme" vem da **câmera dirigida + transições + look**, não do 2.5D. Numa série, roda **direto** (sem portão de decupagem) episódio a episódio.

**Por que NÃO os outros skills de vídeo do ecossistema, aqui:**
- **`videoprodutor`** — orquestrador amplo (link/assunto → vídeo do zero: plano + imagem + voz + render). Redundante para a Forma C: já temos painéis textless e voz prontos; falta só a **direção** — papel do `diretor-animacao`.
- **`video-plan-editor`** (plano de cena) — plano de vídeo viral/estratégia (beat sheet, presets). Propósito diferente; não dirige imagens prontas.
- **`pixflow`** — é o **motor de render de baixo nível** (parallax/efeitos/câmera via spec YAML `pixflow.movie/v1`). A Forma C **não** fala com ele direto: fala com o `diretor-animacao`, que decide a decupagem e gera o spec.

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

As skills são **instaladas individualmente** em `~/.claude/skills/` por **symlink** apontando pro `skill/<nome>` do repo, com **nome prefixado `inemaref-<nome>`** (evita conflito com skills de nome genérico; o diretório no repo continua `skill/<nome>`).

### 1. Pré-requisitos
- **Python 3.10+** com `pyyaml`, `opencv-python`, `numpy` (`pip install pyyaml opencv-python numpy`).
- **ffmpeg** e **Chromium** (o render HTML→PNG acha o Chromium do Playwright/sistema; ou defina `CHROMIUM_BIN`).
- **Serviços locais** (conforme o que for usar): `inemaimg` (flux2-klein) em `http://localhost:8000` para imagem; `inemavox` em `http://127.0.0.1:7860` para voz (TTS) nos tipos de vídeo.
- O **repo clonado** em algum lugar — ex.: `~/projetos/inemaref`.

### 2. Instalar (symlinks)
```bash
REPO=~/projetos/inemaref            # caminho do repo clonado
for x in referencias folder quadrinho motioncomic serie; do
  ln -sfn "$REPO/skill/$x" ~/.claude/skills/inemaref-$x
done
# (opcional) atalho de descoberta — util se rodar fora da arvore do repo:
export INEMAREF_HOME="$REPO"        # ponha no seu ~/.bashrc para persistir
```
Instale **só as que quiser** — mas respeite as **dependências** (cada skill acha as irmãs em `~/.claude/skills/inemaref-<x>` por descoberta):

| skill | depende de |
|---|---|
| `inemaref-folder` | `inemaref-referencias` |
| `inemaref-quadrinho` | `inemaref-folder`, `inemaref-referencias` |
| `inemaref-motioncomic` | `inemaref-folder`, `inemaref-quadrinho`, `inemaref-referencias` |
| `inemaref-serie` | `inemaref-folder`, `inemaref-quadrinho`, `inemaref-motioncomic`, `inemaref-referencias` |

### 3. Verificar
```bash
ls -la ~/.claude/skills/inemaref-*          # devem ser symlinks pro repo
python3 -c "import sys; sys.path.insert(0,'$HOME/.claude/skills/inemaref-serie/scripts'); import build_serie; print('OK')"
```

Cada skill responde a **`/inemaref-<nome> help`** (folder, quadrinho, motioncomic, serie) com o resumo de uso e opções.

> **Erro de referência** ao usar uma skill sozinha = uma dependência não encontrada (ex.: `folder`/`referencias`). Solução: instale a skill irmã (tabela acima) **ou** `export INEMAREF_HOME=<caminho-do-repo>`.

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

## Versionamento

Esquema **`v1.<recurso>.<bug>`** — `major` fixo em **1** (linha V1 do produto); os outros dois são **contadores cumulativos**:

- **`<recurso>`** (2 dígitos) — **+1 a cada novo recurso/capacidade** entregue.
- **`<bug>`** (3 dígitos) — **+1 a cada correção de bug**.
- O número **só muda quando há mudança real** de código; **toda mudança entra no Changelog** abaixo (e vira uma tag git `vX.YY.ZZZ`). Doc/refactor sem efeito não bumpa.

## Changelog

- **`v1.04.001`** — 2026-06-13 — coerência de imagem (personagem/bíblia + anatomia) e referência por episódio.
  - `[recurso]` **Referência efetiva por episódio** — quando um episódio muda algo de um personagem/objeto canônico (outra roupa, **uniforme**, estado) ou define um cenário próprio (`cenario_padrao`: está no **riacho**, não na praia), o `serie` deriva `aparência efetiva = canon da bíblia + delta do episódio` (`variacoes`) e aplica em **todos** os painéis — mantendo o canon. Persistido em `<ep>-referencias.json`. Módulos: `folder/referencia.referencia_efetiva`, `serie/referencia_ep`.
  - `[recurso]` **QC da imagem por visão (DESATIVADO por padrão — custo)** — `folder/qc_imagem.gerar_revisado`: após gerar, **Claude vê** e checa **personagem/cenário/anatomia**; reprovou → regenera (nova seed, até N); reprovou tudo → `flag` + `<img>.qc.json` e segue. Ativar: `INEMAREF_QC=1` (+ `ANTHROPIC_API_KEY`). Default off = comportamento inalterado.
- **`v1.02.001`** — 2026-06-13 — revisão da `motioncomic` (Formas B/C + narração).
  - `[recurso]` **Narração revisada antes do TTS** — léxico de pronúncia editável (`skill/motioncomic/scripts/pronuncias.json`: termo em inglês/outra língua → fonética PT) + normalização (espaços/pontuação) dentro de `tts.say`; lint opcional `tts.revisar_ortografia` (sinaliza acentuação/pontuação, não corrige).
  - `[recurso]` **Forma C dirigida com ação** — `forma-c.json` passa a carregar `meta.direcao` (`energia` por gênero/tom + nota que instrui multi-shot 2–4 por painel, `crash_zoom`/`whip_pan`, closes diretos via `framing.at`, `parallax 0`).
  - `[bug]` **Forma B — navegação clara** — `HOLD_FILL` garante mergulho mínimo por quadro (quadro grande do `manga-dinamico` não fica mais ~ página inteira/parado) + guarda `quadros × painéis` antes de renderizar.
- **`v1.00.000`** — linha de base (início do versionamento): `folder`, `quadrinho`, `motioncomic` (Formas A/B) e `serie` (V2) construídas e testadas; Forma C (coletor + wrapper de cards).
