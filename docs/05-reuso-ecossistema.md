# 05 — O que já temos no ecossistema (inventário para reuso)

`inemaref` **não refaz** render, geração nem direção — agrega só a frente específica: **referência de pessoa
real → folder → página de HQ → carrossel/série**. O resto já existe. Inventário do que reusar.

## ⚠️ Sobreposição crítica: `fontefilm`

`~/projetos/fontefilm` — repo `inematds/fontefilm`.
**"Um diretor de cinema de IA que transforma texto em filme de quadrinhos — rodando na sua máquina."**

É **quase a mesma visão do `inemaref`**, do lado do *filme*. Caminho dele:
```
texto + estilo → roteiro (3 atos) → bíblia (personagens/locações/paleta) → decupagem (plano+câmera por painel)
  → painéis (imagem) → movimento (parallax 2.5D / Ken Burns) → narração+som → montagem → filme.mp4
```
- "Cérebro de direção" com teoria de HQ (Scott McCloud) + 3 atos.
- Local-first: **flux2-klein** (imagem) + **inemavox** (voz) + **pixflow-motion** (parallax). Claude como LLM diretor.
- v1 = **motion comic completo** (painéis + câmera + narração), CLI, PT-BR, 16:9/9:16.
- Estado: em design/prototipagem; já tem pesquisa, spec aprovado e **teste real ponta a ponta** (Hormozi 12, motion comic 1080p 106s).

**Implicação direta:** o **V3 do `inemaref` (filme) provavelmente É o `fontefilm`** — e o motion comic de V1 também mora perto dele. O que o `inemaref` agrega de **distinto**:
1. **Referência de PESSOA REAL** como entrada (foto → protagonista consistente). fontefilm parte de texto+estilo e gera personagens da *bíblia*; aqui a bíblia é uma **pessoa real fotografada** — o **folder**.
2. **Folder (model sheet) como produto de primeira classe**, não só etapa interna.
3. **Saídas estáticas** — página de HQ e **carrossel/série para um canal** (V2), não só filme.

> **Decisão pendente (importante):** `inemaref` é um **repo novo** ou uma **camada/feature dentro do
> fontefilm**? Recomendação inicial: tratar `fontefilm` como o **motor de filme/decupagem** e o `inemaref`
> como a frente de **referência-de-pessoa-real + folder + página/carrossel**, reusando o engine do fontefilm
> em vez de duplicá-lo. **Resolver antes de codar.**

## Motor de vídeo / filme

| Projeto | Repo | Papel para o inemaref |
|---|---|---|
| **fontefilm** | `inematds/fontefilm` | motor de **filme de quadrinhos** (decupagem, montagem) — ver acima. **V3** e base do motion comic. |
| **videoprodutor** | `inematds/videoprodutor` | orquestrador link/assunto → vídeo profissional, 3 camadas, render. Alternativa/par do fontefilm para o filme. |
| **pixflow** | `inematds/pixflow` | imagem estática → vídeo cinematográfico (parallax 2.5D, grain, LUT). **Câmera viajando pelos quadros.** |
| **skill-video-plan-editor** | `inematds/skill-video-plan-editor` | assunto/link → plano de edição (roteiro, beats). Útil pro roteiro da HQ. |

## Direção / prompt

| Projeto | Repo | Papel |
|---|---|---|
| **mdd** | `inematds/mdd` | direção de cena com movimento/intenção/continuidade. **Quebrar história em quadros** (decupagem). |
| **promptprof** | `inematds/promptprof` | pesquisa/refino de prompt (imagem/vídeo/arte). **Prompt fiel por quadro.** |

## Imagem

| Projeto | Repo | Papel |
|---|---|---|
| **inemaimg** | `inematds/inemaimg` | servidor local multi-modelo (Qwen-Edit, **FLUX.2/flux2-klein**, ERNIE). **Padrão**, local, sem API. Arte textless por quadro. |
| **NanoBanana** | `inematds/NanoBanana` | Nano Banana / Gemini — forte prendendo rosto a partir de 1 foto. Candidato p/ consistência (ver `docs/04`). |

## Voz

| Projeto | Repo | Papel |
|---|---|---|
| **inemavox** | `inematds/inemavox` | suíte de voz com IA (voz clonada local). **Narração do motion comic** + timestamps. |

## Camada de balões / leitura

| Projeto | Repo | Papel |
|---|---|---|
| **animabook** | `inematds/animabook` | leitor/editor de HQ animada, **balões arrastáveis**, narrador, publicar, likes/comentários. Camada de texto + leitura/publicação. |
| **animabooksf** | `inematds/animabooksf` | versão infantil (sprites, cenários, diálogos HQ). Referência de editor. |
| **remotion-templates** | reactvideoeditor/remotion-templates | 81 componentes Remotion (texto cinético, charts, transições). Montagem da prancha + camadas. |

## Leitura do inventário

- **~80% já existe.** O que falta é específico de `inemaref`: **folder de pessoa real** + **consistência de
  rosto travada** + **página/carrossel estático** como produto.
- O **motion comic e o filme não se constroem do zero** — saem de `fontefilm` / `pixflow` / `videoprodutor`.
- **Primeira decisão a tomar** (antes de codar): a relação `inemaref` × `fontefilm` (repo novo vs camada).
