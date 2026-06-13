# Coerência de imagem + referência de episódio (design — RASCUNHO p/ revisão)

Data: 2026-06-13
Status: **rascunho** — captura os requisitos do usuário e propõe abordagem; decisões em aberto no fim.
Skills tocadas (previsto): `folder` (referência), `serie` (bíblia/episódio), `quadrinho`/`motioncomic` (geração dos painéis).

## Problema (do usuário)

Hoje a imagem é gerada por `flux2-klein` (T2I puro) a partir de um prompt = `aparencia` (string da referência) + cena + arte. **Não há nenhuma verificação** de que a imagem saiu coerente. Três exigências:

1. **Revisar a imagem ao ser criada** — conferir se está **adequada ao personagem** (bate com a referência/folder) **e à bíblia** (estilo, mundo, cenário corretos). Ex.: cenário pedido era **riacho**, não pode sair **praia**.
2. **Anatomia** — a verificação tem que pegar **erro de anatomia** (mãos/dedos errados, membros a mais, deformação, proporção).
3. **Referência de episódio** — quando um **episódio** muda algo de um personagem/objeto **canônico da bíblia** (ex.: outra roupa, um **uniforme**, um local específico), é preciso **criar a referência daquele episódio**: ela combina **o canon da bíblia + o delta do episódio**, e **todos os painéis do episódio** usam essa referência derivada — coerência interna ao episódio **sem perder** as características da bíblia.

## Contexto técnico (restrições reais)

- `imgclient.generate(prompt, out, model, width, height, images=None, negative_prompt, seed)` — `flux2-klein` **ignora `images`** (T2I; HTTP 500 se mandar). `qwen-edit-2511` aceita `images` (img2img/face-swap) mas é **instável** (OOM/500 na troca de modelo). Ver `docs/04-consistencia-pessoa-real.md`.
- Logo, **a coerência não vem de condicionar por imagem** (img2img) de forma confiável. Vem de **(a) texto de referência estruturado** no prompt + **(b) verificação por visão depois** + **(c) regerar quando reprovar**. `seed` permite variar/repetir geração.
- Material de referência já disponível: `folder/referencia.json` (`aparencia`, `retrato_ancora.png`, `ficha`); `serie/biblia.json` (`protagonista`, `elenco`, `elementos` = canon visual, `estilo.arte`). O episódio (`episodio.json`/roteiro) tem os painéis (`prompt`, `quem`).

## Abordagem proposta (3 pilares)

### Pilar A — Referência de episódio (derivação canon + delta) — *resolve a exigência 3*
- Estender o canon da bíblia (`protagonista`/`elenco`/`elementos`, cada um com `aparencia` base) com **overrides por episódio**.
- Ao montar um episódio, gerar uma **referência efetiva por entidade** = `aparencia_base` (bíblia) **+ delta do episódio** (ex.: `roupa: "uniforme escolar azul"`, `local_padrao: "riacho na mata"`, `estado_objeto: "…"`). Resultado = string/￼estrutura usada em **todos** os prompts daquele episódio.
- Persistir em algo como `referencia-ep.json` (ou bloco `referencias_efetivas` no `episodio.json`) p/ rastreabilidade e reuso (Forma A/B/C do mesmo ep).
- **Travar o que NÃO muda** (rosto, traços, paleta do personagem) e **aplicar só o delta** (roupa/local/objeto). O delta tem **precedência** sobre o canon só nos campos que ele declara.

### Pilar B — QC por visão após gerar (adequação) — *resolve a exigência 1*
- Depois de `generate`, **Claude VÊ a imagem** (mesmo padrão do `diretor-animacao`) e pontua contra: (1) **personagem** (bate com `aparencia` efetiva + `retrato_ancora`), (2) **bíblia/cenário** (estilo `arte` correto; **local certo** — riacho≠praia; objetos canônicos presentes/coerentes).
- Saída estruturada: `{adequado: bool, score, motivos:[...], dimensao_reprovada}`.
- **Regerar quando reprovar**: nova `seed` (e, se preciso, prompt reforçado com o ponto que falhou), até **N tentativas**; se ainda reprovar, **marcar/flag** p/ revisão humana (não travar a série toda).

### Pilar C — Anatomia/artefatos — *resolve a exigência 2*
- Parte da mesma passada de visão (Pilar B) **ou** um checador dedicado: detectar **mãos/dedos errados, membros extras, rostos duplicados, deformação, proporção**.
- Mesma política de **regerar-ao-reprovar**. (Detector offline dedicado de anatomia é difícil; a via prática é o **check por visão**, talvez reforçado no `negative_prompt` que já tem `bad anatomy`/`extra fingers`.)

## Onde encaixa (pontos de integração)
- `skill/folder/scripts/` — função de **derivação** `referencia_efetiva(canon, delta_ep)`.
- `skill/serie/scripts/build_serie.py` — montar as referências efetivas do episódio antes de `_render_hq`/assets e passá-las aos prompts.
- `skill/folder/scripts/imgclient.py` ou um wrapper `gerar_revisado(...)` — laço **gerar → QC(visão) → regerar/flag**.
- `skill/motioncomic`/`quadrinho` — consumir a referência efetiva (em vez da `aparencia` crua da bíblia).

## Escopo / YAGNI
- **Não** depender de img2img (`qwen-edit`) p/ travar rosto enquanto for instável — coerência por **texto + QC**.
- **Não** bloquear a série inteira por 1 painel reprovado — **flag + segue**, com relatório.
- Começar pelo **Pilar A** (determinístico, testável sem rede) e pelo **QC textualmente especificado**; a chamada de visão é o passo dirigido (Claude).

## Decisões em aberto (preciso confirmar com o usuário)
1. **Quem julga a adequação/anatomia?** Proposta: **Claude vê** (já fazemos no `diretor-animacao`). Alternativa: modelo local de embedding/anatomia (mais infra). → confirmar.
2. **Política de regeneração:** quantas tentativas (proposta: 2–3), varia só `seed` ou também reforça o prompt? Reprovou tudo → flag e segue, certo?
3. **Onde guardar a referência de episódio:** arquivo `referencia-ep.json` por episódio, ou um bloco dentro do `episodio.json`? Formato do **delta** (campos: `roupa`, `local`, `estado`, …)?
4. **Bíblia precisa de novos campos?** (ex.: `local_canonico` por cena, lista de `objetos` com estado) — ou inferimos do `prompt` do painel?
5. **Custo/tempo:** QC por visão em toda imagem (séries têm centenas de painéis) — rodar em todas, ou amostral/somente nas que “mais importam”?
