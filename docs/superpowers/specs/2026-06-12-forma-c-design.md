# Forma C — filme cinematográfico dos painéis (design)

Data: 2026-06-12
Skills envolvidas: `motioncomic` (helper coletor + wrapper de cards) · `diretor-animacao` (MOTOR, externo) · `pixflow` (render, externo)
Status: design aprovado em conversa; pendente revisão do spec antes do plano.

## Objetivo

Adicionar um 3º formato de vídeo à fábrica — **Forma C = a versão "filme" dos painéis**: câmera dirigida por quadro + transições + look/grain, em vez do push-in uniforme da Forma A. Reusa os assets já gerados (textless + narração), sem regerar imagem nem voz. Resultado nomeado `<serie>-c-epNN-<titulo>.mp4`, na mesma pasta da série, ao lado de `-a-`/`-b-`.

## Decisões travadas

- **Motor = `diretor-animacao`** (skill externo em `~/projetos/diretor-animacao`). É **dirigido por Claude** (VÊ cada imagem, decide câmera por beat com gramática cinematográfica, gera o spec do pixflow). **Não reinventar a direção** nem falar com o pixflow na mão.
- **Render = `pixflow`** (`~/projetos/pixflow`, motor v2.3, spec `pixflow.movie/v1`).
- **Entrada = assets da Forma A, reusados:** painéis **textless** (`assets/pNNqN.png`) + **narrações** (`assets/pNNqN.wav`). Narração fluida (a locução por quadro que já existe). Sem regerar.
- **Desenho → `parallax = 0`** (regra de ouro do diretor). O "filme" vem de **câmera dirigida + transições não-uniformes + look/grain/vinheta**, não do 2.5D.
- **Roda DIRETO** (sem portão de decupagem), episódio a episódio.
- **Mantém gancho de abertura (t=0) + CTA inema.club**, igual A/B (mesma identidade).
- **16:9.**
- Forma C **não** é um `tipo` do lote determinístico do `build_serie` (A/B são Python puro). É um **fluxo dirigido** (Claude + diretor-animacao) por cima dos assets.

## Por que `diretor-animacao` (e não os outros)

- **`videoprodutor`** — orquestrador amplo (link/assunto → vídeo do zero, gera plano+imagem+voz+render). Redundante: já temos painéis textless + voz; falta só a **direção**.
- **`video-plan-editor`** — plano de vídeo viral/estratégia; propósito diferente, não dirige imagens prontas.
- **`pixflow` direto** — é o motor de baixo nível; a direção (qual câmera por quadro) é justamente o valor do `diretor-animacao`.

(Registrado também no README, seção "Formatos de vídeo e o ecossistema".)

## Arquitetura

Forma C é um **fluxo por episódio**, com pouco código novo no inemaref (o grosso é o `diretor-animacao`):

1. **Garantir assets da Forma A** do episódio (painéis textless + narrações). Se não existirem, gerar primeiro (a etapa de assets da Forma A — `_gen_image`/`say` — já produz `assets/pNNqN.png` + `pNNqN.wav`). Para o Teo, já existem em disco.
2. **Coletor (novo, `skill/motioncomic/scripts/forma_c.py`):** dado o roteiro do episódio + a pasta de assets, monta o material que o `diretor-animacao` consome:
   - lista **ordenada** de imagens textless (ordem de leitura: páginas em ordem, painéis 1→6);
   - as **narrações por trecho** (`pNNqN.wav`) na mesma ordem;
   - metadados: `titulo`, `abertura` (gancho), nome de saída.
   Função pura/testável: `coletar_forma_c(roteiro, assets_dir) -> {imagens:[...], wavs:[...], meta:{...}}`.
3. **Direção + render do MIOLO:** o `diretor-animacao` recebe imagens + narrações, dirige (decupagem) e renderiza via pixflow o **filme dos painéis** (`miolo.mp4`), direto.
4. **Cards (wrapper):** renderizar o **card de abertura narrando o gancho em t=0** (reusa `motioncomic.build_motion._title_clip(..., audio=abertura, voice=...)`) e o **CTA inema.club** (reusa `build_travel._cta_clip`). 16:9, mesmo encode dos outros clipes.
5. **Concat:** `[intro] + [miolo dirigido] + [cta]` via `ffmpeg -f concat` → `<serie>-c-epNN-<titulo>.mp4` na pasta da série. (Cuidado: o `miolo` do pixflow precisa sair com o **mesmo encode** dos cards — libx264/yuv420p/30fps/aac/44100/2 — pra o concat `-c copy`; se divergir, re-encode o miolo uma vez no padrão.)
6. **Verificar:** frames por cena + brilho nas fronteiras (anti-pisca; receita em `~/projetos/diretor-animacao/DICAS-CORRECOES.md`).

### Componentes (isolados)

| Unidade | O que faz | Depende de | Testável |
|---|---|---|---|
| `coletar_forma_c` (novo, `motioncomic/scripts/forma_c.py`) | roteiro+assets_dir → lista ordenada de imagens+wavs+meta | nada externo | ✅ unit (assets fake) |
| naming `<serie>-c-ep…` | nome de saída consistente com A/B | `serie/naming.ep_base` | ✅ unit |
| wrapper de cards | intro(gancho) + CTA + concat | reusa `_title_clip`/`_cta_clip` (motioncomic) + ffmpeg | parcial (encode-match) |
| `diretor-animacao` | direção + spec + render | pixflow, GPU, remotion | externo (validação manual) |
| `pixflow` | render parallax/câmera/efeitos | node/remotion/chromium/GPU | externo |

## Pré-requisitos / viabilidade

- `pixflow` operacional: node v24 ✓, remotion instalado ✓, CLI ✓, GPU NVIDIA GB10 ✓ (modelo de profundidade baixa no 1º uso). **VALIDAR com um render real** (um shot ou o ep1) **ANTES** de fazer o resto — é o maior risco.
- `diretor-animacao` em `~/projetos/diretor-animacao`; `pixflow` em `~/projetos/pixflow`.
- `inemaimg`/`inemavox` só se precisar (re)gerar assets da Forma A; para reusar os do Teo, não.

## Testes

- `coletar_forma_c`: com um roteiro fixtura (2 páginas × 6) e uma pasta de assets fake (PNGs/WAVs vazios nomeados `pNNqN.*`), retorna a lista **na ordem de leitura** e os meta (titulo, abertura). Cobre painel sem wav (erro claro).
- naming: `<serie>-c-ep01-<titulo>` bate o padrão de A/B (letra antes do `ep`).
- O render do `diretor-animacao`/pixflow é **validação manual** (precisa GPU/remotion) — fora do unit; provado no Teo ep1.

## Escopo / YAGNI

- **Não** automatizar a direção em Python (o valor é a direção vision-based do diretor).
- **Não** mexer nas Formas A/B.
- **Não** fazer 9:16 agora (16:9).
- Forma C roda como **fluxo dirigido** (Claude + diretor), **não** como tipo do lote automático — documentado.
- O parallax fica em 0 (desenho); se um dia houver série de fotos, reavaliar.

## Ordem de execução

1. **Validar render** ponta a ponta (pixflow/diretor) num shot OU direto no Teo ep1 — confirma o motor neste ambiente.
2. **Coletor + naming + wrapper de cards** (com testes).
3. **Teo ep1 Forma C** ponta a ponta — conferir o filme (direção, cards, concat, anti-pisca).
4. **Teo eps 2–5** Forma C, direto.
