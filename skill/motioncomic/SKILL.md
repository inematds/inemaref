---
name: inemaref-motioncomic
requires: [inemaref-folder, inemaref-quadrinho, inemaref-referencias]
description: Transforma uma HISTORIA em quadros num VIDEO de motion comic (16:9) — a camera da ZOOM em cada quadro durante a sua narracao (push-in), com voz (TTS inemavox) e balao/SFX como camada. Use quando o usuario quiser "video de quadrinhos", "motion comic", "quadrinho narrado em video", "dar zoom no quadro quando narra", "transformar a HQ em video", "camera viajando sobre a pagina". Arte cartoon/manga, narracao voz-off, balao so com fala/expressao.
---

# Skill: motioncomic — quadrinho em video com zoom (passo 3 do inemaref)

Implementa o `docs/02`: a camera **abre na prancha e viaja/zooma pelos quadros**, em sincronia com a
narracao. Mesma base **textless + camada**: a arte e gerada sem texto; **narracao** e voz e o **zoom**
acontece durante a fala.

## Duas formas
- **Forma A — slideshow (`build_motion.build_video`).** Uma imagem por vez (16:9, cartoon), com
  push-in durante a narracao e corte para a proxima. Simples; *nao parece uma pagina de quadrinho* —
  e uma sequencia de ilustracoes narradas. Na imagem ficam so balao/SFX (narracao e so voz).
- **Forma B — camera sobre a PAGINA DE PAPEL (`build_travel.build_video_travel`).** Monta a **pagina
  real de quadrinho** (grade 2x3 com sarjetas/baloes/legendas IMPRESSAS, via a skill `quadrinho`) e
  **move a camera sobre ela como quem filma uma pagina de papel**: mergulha (zoom-in) em cada quadro
  durante a sua narracao, **afasta um pouco e encaixa** no proximo, e na troca de pagina da
  **zoom-out total** e abre a seguinte. **Este e o modo "quadrinho de verdade" (padrao recomendado).**

> **A/B e FORMATO, nao narracao.** Forma A = `video-slideshow` (slideshow, paineis
> direto). Forma B = `video-pagina` (camera sobre a pagina). A narracao e uma faixa
> fluente UNICA que serve A e B — nunca gere "duas narracoes" para A/B.
>
> **Carrossel x video.** O carrossel sao as PAGINAS (`pagina.png`, com texto), lidas
> como quadrinho — nao e video. O video (A e B) usa a arte SEM texto: a Forma A pega os
> paineis direto; a Forma B viaja sobre `pagina-textless.png` (voz-off).
>
> **Gancho.** O video abre em t=0 com a narracao-gancho (`roteiro['abertura']`) sobre o
> card do assunto.
>
> **Moldura.** A pagina tem duas molduras (`moldura=dark|white`) escolhidas por geracao.

## Como funciona (pipeline)
**Forma B (padrao):** para cada pagina, gera os 6 quadros textless (flux2-klein) e monta a prancha com
a skill `quadrinho` (narracao/balao/SFX ja impressos). Re-renderiza a mesma pagina pintando cada
quadro de uma cor solida (mascara) para **medir os retangulos** dos quadros com precisao (vale pra
qualquer template). Narra cada quadro com `inemavox` -> mede a duracao -> a camera (crop animado do
ffmpeg) **viaja sobre a `pagina.png`**: abre na pagina inteira, mergulha no quadro pela duracao do
audio, afasta/encaixa no proximo, fecha na troca de pagina. Junta tudo num MP4 16:9.

**Forma A:** para cada quadro gera imagem cartoon -> sobrepoe so balao/SFX -> narra -> **ffmpeg
zoompan** faz o push-in pela duracao do audio -> junta (intro + titulo por pagina + quadros).

Ambas reusam `imgclient`/`render`/`artes` do `folder`; a Forma B reusa tambem `build_pagina`/
`fill_pagina` do `quadrinho`. Cada pagina precisa de **exatamente 6 paineis** (grade 2x3).

Pre-requisitos: `inemaimg` em `http://localhost:8000` e o daemon `inemavox` em `http://127.0.0.1:7860`.

## Entrada — o roteiro
Um dict (ver `tests/fixtures/roteiro-exemplo.json`):
```
{
  "id": "slug", "titulo": "...", "subtitulo": "...",
  "personagem": "descricao do protagonista (injetada nos quadros por padrao)",
  "paginas": [ { "n": 1, "titulo": "...", "paineis": [ <painel>, ... ] }, ... ]
}
```
Cada **painel**:
- `prompt` — cena textless (obrigatorio).
- `narracao` — voz-off (NAO aparece na imagem).
- `fala` — `{"quem": "...", "texto": "..."}` -> balao na imagem **e** falado.
- `sfx` — onomatopeia (so na imagem).
- `quem` — personagem do quadro: string descreve outro personagem; `""` = sem pessoa (so cena);
  ausente = usa o `personagem` protagonista. (Evita o protagonista "vazar" em quadros de outros.)
Texto narrado do quadro = `narracao` + `fala.texto`.

## Rodar
**Forma B — camera sobre a pagina (padrao):**
```bash
python3 - <<'PY'
import sys, json
sys.path.insert(0, "skill/motioncomic/scripts")
from build_travel import build_video_travel
rot = json.load(open("CAMINHO/roteiro.json"))
build_video_travel(rot, out_dir="output", voice="bella", arte="manga")  # voice: bella|rachel
PY
```
Saida em `output/<id>/`: `<id>-travel.mp4`, `pages/` (uma `pagina.png`+`mask.png` por pagina),
`voz/` (narracoes), `clips/`, `concat-travel.txt`.

**Forma A — slideshow:**
```python
from build_motion import build_video
build_video(rot, out_dir="output", voice="bella")
```
Saida: `<id>.mp4`, `assets/`, `clips/`, `concat.txt`.

## Ajustes (Forma B)
- Voz: `voice="rachel"`. Arte da pagina: `arte="cartoon"` (default `manga`).
- Ritmo da camera: `T_OPEN`/`T_TRANS`/`T_CLOSE` (duracao dos movimentos), `TRANS_BUMP` (quanto a
  camera afasta na troca de quadro), `HOLD_OUT` (push-in durante a narracao) em `build_travel.py`.
- **Mergulho minimo (navegacao clara):** `HOLD_FILL` (default 0.82) limita a janela de cada hold a
  82% da pagina. Sem isso, quadro grande (ex.: p1/p2 2x2 do `manga-dinamico`) gera janela ~ pagina
  inteira e o mergulho nele "nao anda" — a navegacao pula/embaralha. O cap aperta no centro do
  quadro -> close legivel por quadro. O build ainda **valida quadros×paineis** (mesma contagem/ordem)
  antes de renderizar, falhando claro em layout incompativel.
- **Layout flexivel:** passe `template_dir=` p/ escolher a grade — default
  `quadrinho/templates/grade-uniforme` (2x3); use `.../manga-dinamico` p/ quadros de tamanhos e
  posicoes variaveis. A camera **le o layout real** (`render_mask` pinta cada quadro de uma cor e
  `detect_rects` mede a bounding box) e o `frame_window` **se posiciona por quadro**, cobrindo cada
  um conforme a forma (largo → enquadra pela largura; alto → pela altura). Qualquer grade de 6
  funciona sem mudar a camera.

## Narracao — revisao de escrita + pronuncia (antes do TTS)
Vale para A, B e C (todas narram pelo `tts.say`). Antes de gerar a voz:
- **Revise o roteiro ACENTUADO e PONTUADO.** Texto sem acento faz o `inemavox` pronunciar errado; a
  raiz e o roteiro estar correto. Lint opcional `tts.revisar_ortografia(texto)` lista pontuacao
  final ausente, espacos duplos e (se `pyspellchecker` pt instalado) palavras suspeitas de estar sem
  acento — **nao corrige**, so sinaliza; rode antes de narrar.
- **Termos em ingles/outra lingua:** `tts.say()` aplica automaticamente o lexico de pronuncia
  `scripts/pronuncias.json` (`{termo: regravacao_fonetica_pt}`, ex.: `Maslow→Maslou`,
  `design→dizain`) — palavra inteira, ignora caixa. **Edite o JSON** acrescentando os nomes proprios
  e jargoes da sua serie. Override do caminho via `INEMAVOX_LEXICO`.
- `tts.revisar_narracao` (chamada dentro do `say`) ainda colapsa espacos e garante pontuacao final
  (entonacao). Funcoes puras testadas em `tests/test_tts_revisao.py`.

## Forma C — filme dirigido dos paineis (acao)
3º formato: a versao "filme" dos paineis, dirigida pelo skill `diretor-animacao` (que VE cada imagem
e decide camera/cortes) + render `pixflow`, reusando os assets da Forma A (textless + narracao). Cola
em `scripts/forma_c.py`: `coletar_forma_c(roteiro, assets_dir, stage_dir, energia=None)` encena os
paineis em ordem e escreve `forma-c.json`; `wrap_forma_c` poe gancho (t=0) + CTA. Saida
`<serie>-c-epNN-<titulo>.mp4`. Detalhe em `docs/superpowers/specs/2026-06-12-forma-c-design.md`.

**Mais acao (evitar o "sutil"):** o `forma-c.json` carrega um bloco `meta.direcao` com `energia`
(`alta|media|baixa`, derivada do `genero`/`tom` do roteiro — aventura/acao→`alta`) e uma `nota` que
instrui o diretor. Em energia **alta**, dirija com:
- **multi-shot 2–4 por painel** (a mesma imagem reusada): wide estabelece → `cut`/`whip` → **CLOSE
  direto e preciso** no ponto de interesse (`framing.at`). A MESMA narracao atravessa os cortes.
- **`crash_zoom`/`whip_pan`** nos beats de tensao; amplitude maior (o motor ja suporta tudo isso).
- **imagens intermediarias** opcionais entre momentos quando a narracao pede mais beats.
- desenho → `parallax 0` (a vida vem de camera/corte, nao do 2.5D).

## Help
Se o usuario digitar `/inemaref-motioncomic help`, responda com este resumo:
- **O que faz:** transforma uma historia em quadros num video motion comic (16:9) — a camera zooma/viaja por cada quadro durante sua narracao (voz TTS), com balao/SFX como camada.
- **Entrada:** um roteiro (dict com `id`, `titulo`, `personagem`, `paginas[]` de 6 paineis cada; ver `tests/fixtures/roteiro-exemplo.json`).
- **Uso:** Forma B (padrao) `build_video_travel(rot, out_dir=..., voice="bella", arte="manga")`; Forma A `build_video(rot, ...)` — em `skill/motioncomic/scripts`.
- **Depende de:** inemaref-folder, inemaref-quadrinho, inemaref-referencias.
- **Pre-requisitos:** `inemaimg` em `http://localhost:8000`, daemon `inemavox` em `http://127.0.0.1:7860` e ffmpeg.
