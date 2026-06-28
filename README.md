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

**Versão atual: `v1.09.002`** — esquema e histórico no [Changelog](#changelog).

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

- **`v1.09.002`** — 2026-06-28 — Forma B com **câmera de zoom lento contínuo**; Forma C dirigida também pela **narração**; **checagem de acentuação** sempre antes do TTS.
  - `[recurso]` **Forma B — zoom lento contínuo** (`build_travel.py`) — novo modelo de câmera que **elimina os "pulos"**: por quadro um **push-in lento** durante toda a narração (sem congelar); entre quadros um **glide plano lento** (pan na linha / diagonal na troca de linha) **sem recuo**; a câmera **nunca vai à página inteira** (entra `ENTRY_OUT` mais aberta e assenta); **virada de página = dissolve em movimento, apertado** (`_pageturn_clip` reescrito + `_page_clips`). Removidos `estab`/`open-4×`/`close-5.8×`/`pend` (as fontes do salto). Knobs de ritmo no topo do arquivo. 59 testes verdes.
  - `[recurso]` **Forma C — direção também pela narração** (`forma_c.py`, `forma_c_direcao.py`) — além do visual, o diretor passa a receber o **texto narrado** por painel (`narr_txt`); novas heurísticas (`_classificar`/`_beat`/`_montagem`, `_seq(prompt, narr, dur)`) usam visual **+** narrativa pra decidir os cortes.
  - `[recurso]` **Checagem de acentuação sempre** (`serie/revisar_acentos.py`) — o `build_serie` **corrige a acentuação PT-BR do texto narrado** (`abertura`/`titulo`/`chamada`/`narracao`/`fala.texto`) **antes do TTS**, pois sem acento a voz pronuncia errado: auto-corrige o que é seguro (palavra inválida sem acento — preserva caixa, idempotente) e **avisa** formas ambíguas (`esta`/`está`); nunca toca em `prompt`/`quem`/`usa`/`sfx`. Determinístico, sem rede; integrado como o `lint_paineis`. `SKILL.md` instrui autoria já acentuada.
- **`v1.08.002`** — 2026-06-18 — Forma C **calma** + cobertura por **visão**; **casting** de fichas-âncora; **lint** de painéis; Forma B com pan **direcional**.
  - `[recurso]` **Forma C calma por padrão** (`forma_c_direcao.py`) — conteúdo infantil pede suavidade: look `cinema-dramatico` (natural), **1 toma gentil por painel** (sem clone, `intensity ≤ 0.6`, framing `zoom ≤ 1.18`, nunca `crash_zoom`/`whip_pan`), variada por índice. As paletas energéticas (`alta`/`acao`) seguem disponíveis, mas deixaram de ser o default.
  - `[recurso]` **Presets da Forma C** — `suave`/`dinamico`/`acao`/`epico` combinam energia (paleta de câmera), `cortes` (multi-shot por painel) e `slides`. A bíblia referencia por nome em `estilo.acao_c`; o episódio sobrescreve em `ep.acao_c`.
  - `[recurso]` **Cobertura guiada por visão** (`visao_decupagem.py`) — schema/validador de *shots* (`wide`/`close`/`insert`/`pan`/`tilt`, `at`/`zoom`/`peso` clampados) + `contexto_do_painel`. `dirigir(..., visao_path=)` carrega o JSON de cobertura e gera **uma `mv_scene` por shot** (cortes = sequência de imagens/recortes da MESMA imagem guiados por visão), com as durações somando a do painel (narração não dessincroniza).
  - `[recurso]` **Casting de fichas-âncora** (`serie/casting.py`) — gera **uma ficha-referência por elenco/elemento** do canon (subject isolado, model sheet) e persiste `casting/ancoras.json` (`nome→caminho`); reaproveita o retrato do protagonista sem regenerar.
  - `[recurso]` **Autoload de âncoras no `serie`** — `build_serie` funde `casting/ancoras.json` com as âncoras explícitas (explícito vence) antes de gerar — o mapa de referências deixa de depender só do chamador (fecha o pendente do `v1.07.001`).
  - `[recurso]` **Lint de painéis** (`serie/lint_paineis.py`) — aviso **não-bloqueante** por episódio quando um painel passa de **2 entidades** (protagonista/`quem` + `usa[]`), reduzindo *drift* de imagens superlotadas. Integrado ao `build_serie` (`notify`).
  - `[bug]` **Forma B — transição direcional** (`build_travel.py`) — a troca de quadro afastava pra página no meio do trajeto (o "sbum"). Agora `TRANS_BUMP 0.22→0.0` e nova lei de largura (`window_at`/`_filter`): o `cx,cy` faz o **pan** no zoom apertado (largura aperta pro `min` no meio, endpoints exatos), sem voltar pra prancha.
- **`v1.07.001`** — 2026-06-14 — geração **ancorada em imagem** (flux2-klein aceita 1–4 referências).
  - `[recurso]` **Âncora de imagem no gerador** — validado que o `flux2-klein` **usa** `images=` (1–4 refs; acima de 4 dá erro): a referência carrega **identidade E estilo** do personagem, resolvendo o *drift* da geração só-texto. Removido o guard errado do `build_folder` (`model != "flux2-klein"`) — `modo="foto"` agora manda a imagem ao klein.
  - `[recurso]` **Anchoring por quadro nos vídeos (opt-in)** — `build_motion.build_video`, `build_travel.build_video_travel` e `quadrinho.build_pagina` aceitam `ancoras={entidade(lower)->caminho}` + `protagonista_id`; por quadro, juntam as refs do `quem`/`usa` (teto 4) e mandam `images=` ao gerador. `serie.build_serie` recebe `ancoras=` e repassa às Formas A/B. Default `None` = comportamento inalterado (texto puro).
  - `[nota]` `negative_prompt` é **ignorado** pelo flux2-klein (FLUX.2 não suporta); docstring do `imgclient` corrigida. *(Pendente p/ depois: derivar `ancoras` automaticamente da bíblia/folders no `serie` — hoje o mapa vem do chamador.)*
- **`v1.06.002`** — 2026-06-13 — Forma C dirigida (ação) + correção do canon na Forma A.
  - `[recurso]` **Diretor determinístico da Forma C** (`skill/motioncomic/scripts/forma_c_direcao.py`) — gera `decupagem.json` + `miolo.movie.yaml` (spec pixflow) a partir do `forma-c.json`, **sem IA**: câmera variada por energia (look `acao-epico`, `crash_zoom`/`whip_pan`/`framing`, intensidade alta), `parallax 0`. Automatiza a Forma C com mais **ação** (atende o pedido de "menos sutil").
  - `[bug]` **Canon na Forma A** — `build_motion.build_video` não dobrava a aparência travada dos elementos `usa:[...]` (só a Forma B dobrava), fazendo personagens/objetos canônicos (ex.: um cão são-bernardo) sofrerem *drift* (virar golden/urso). Agora dobra igual à Forma B → personagem recorrente consistente em A e C.
- **`v1.05.001`** — 2026-06-13 — QC de imagem também no caminho de **vídeo**.
  - `[recurso]` `build_video_travel`/`build_video`/`_gen_image` passam a aceitar `generate_fn`; o `serie` injeta o QC (opt-in) também nos vídeos (Formas A/B), não só na HQ — fecha o follow-up de `v1.04.001`. Default off = inalterado.
- **`v1.04.001`** — 2026-06-13 — coerência de imagem (personagem/bíblia + anatomia) e referência por episódio.
  - `[recurso]` **Referência efetiva por episódio** — quando um episódio muda algo de um personagem/objeto canônico (outra roupa, **uniforme**, estado) ou define um cenário próprio (`cenario_padrao`: está no **riacho**, não na praia), o `serie` deriva `aparência efetiva = canon da bíblia + delta do episódio` (`variacoes`) e aplica em **todos** os painéis — mantendo o canon. Persistido em `<ep>-referencias.json`. Módulos: `folder/referencia.referencia_efetiva`, `serie/referencia_ep`.
  - `[recurso]` **QC da imagem por visão (DESATIVADO por padrão — custo)** — `folder/qc_imagem.gerar_revisado`: após gerar, **Claude vê** e checa **personagem/cenário/anatomia**; reprovou → regenera (nova seed, até N); reprovou tudo → `flag` + `<img>.qc.json` e segue. Ativar: `INEMAREF_QC=1` (+ `ANTHROPIC_API_KEY`). Default off = comportamento inalterado.
- **`v1.02.001`** — 2026-06-13 — revisão da `motioncomic` (Formas B/C + narração).
  - `[recurso]` **Narração revisada antes do TTS** — léxico de pronúncia editável (`skill/motioncomic/scripts/pronuncias.json`: termo em inglês/outra língua → fonética PT) + normalização (espaços/pontuação) dentro de `tts.say`; lint opcional `tts.revisar_ortografia` (sinaliza acentuação/pontuação, não corrige).
  - `[recurso]` **Forma C dirigida com ação** — `forma-c.json` passa a carregar `meta.direcao` (`energia` por gênero/tom + nota que instrui multi-shot 2–4 por painel, `crash_zoom`/`whip_pan`, closes diretos via `framing.at`, `parallax 0`).
  - `[bug]` **Forma B — navegação clara** — `HOLD_FILL` garante mergulho mínimo por quadro (quadro grande do `manga-dinamico` não fica mais ~ página inteira/parado) + guarda `quadros × painéis` antes de renderizar.
- **`v1.00.000`** — linha de base (início do versionamento): `folder`, `quadrinho`, `motioncomic` (Formas A/B) e `serie` (V2) construídas e testadas; Forma C (coletor + wrapper de cards).
