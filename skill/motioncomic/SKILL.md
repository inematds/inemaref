---
name: motioncomic
description: Transforma uma HISTORIA em quadros num VIDEO de motion comic (16:9) — a camera da ZOOM em cada quadro durante a sua narracao (push-in), com voz (TTS inemavox) e balao/SFX como camada. Use quando o usuario quiser "video de quadrinhos", "motion comic", "quadrinho narrado em video", "dar zoom no quadro quando narra", "transformar a HQ em video". Arte cartoon/manga, narracao voz-off, balao so com fala/expressao.
---

# Skill: motioncomic — quadrinho em video com zoom (passo 3 do inemaref)

Implementa o `docs/02`: a camera **abre na prancha e viaja/zooma pelos quadros**, em sincronia com a
narracao. Mesma base **textless + camada**: o quadro e gerado sem texto; **narracao** e so voz e o
**zoom** acontece durante a fala; na imagem ficam so os **textos de expressao** (balao + SFX).

## Como funciona (pipeline)
Para cada quadro: gera imagem cartoon (flux2-klein) -> sobrepoe so balao/SFX (sem caixa de narracao)
-> narra com `inemavox` (TTS, voz `bella`/`rachel`) -> mede a duracao -> **ffmpeg zoompan** faz o
push-in no quadro pela duracao do audio -> junta tudo (intro + titulo por pagina + quadros) num MP4
16:9. Reusa `imgclient`/`render`/`artes` do `folder`.

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
```bash
python3 - <<'PY'
import sys, json
sys.path.insert(0, "skill/motioncomic/scripts")
from build_motion import build_video
rot = json.load(open("CAMINHO/roteiro.json"))
build_video(rot, out_dir="output", voice="bella")   # voice: bella | rachel
PY
```
Saida em `output/<id>/`: `<id>.mp4`, `assets/` (quadros + narracoes), `clips/`, `concat.txt`.

## Ajustes
- Voz: `voice="rachel"`. Ritmo do zoom: `0.13` em `_panel_clip` (build_motion).
- Formato/arte: hoje 16:9 cartoon; trocar `arte` em `_gen_image` (manga/foto) e `W/H`.
