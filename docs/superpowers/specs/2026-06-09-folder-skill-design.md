# Spec — Skill `folder` (ficha de referência / model sheet)

**Data:** 2026-06-09
**Repo:** `inemaref`
**Status:** aprovado para planejamento

## 1. Objetivo

Construir a skill `folder` — o **passo 0** do `inemaref`. A partir de **uma foto (pessoa real)**
OU **um texto (descrição/história do personagem)**, ela produz a **ficha de referência** (o *model
sheet*): página editorial com retrato grande, personalidade, características, detalhes e a tira
"DETALHES EM FOCO". Essa ficha é o **ativo central** travado que o `quadrinho` (e o resto do
ecossistema) vai consumir depois.

Referência visual: `assets/exemplos/folder-*.png` (3 exemplos).

## 2. Decisões travadas (no brainstorming)

1. **Arquitetura B — textless + camada.** O motor de imagem gera **só as imagens** (retrato +
   mini-retratos, sem texto); o **layout e o texto** são uma camada HTML/CSS renderizada para PNG.
   Alinha com o princípio *textless-first* do projeto (`docs/00`, `docs/03`), com o default
   flux2-klein do usuário, garante texto sempre legível e dá os múltiplos estilos via templates.
   Caminho A (single-shot Nano Banana) foi descartado.
2. **Dois eixos de estilo, combináveis (escolha c).**
   - **Layout** = templates de página (HTML/CSS).
   - **Arte** = visual das imagens (foto-realista / cartoon).
   Escolhe-se layout **e** arte por geração.
3. **Motor padrão: flux2-klein**, nos dois modos (texto e foto), via `inemaimg`.
   - O motor é **trocável num único ponto de configuração**.
   - **Fallback documentado:** `qwen-edit-2511` (tarefas `face-swap` / `multiple-angles`) para o
     modo foto, **se** o flux2-klein não fixar o rosto. Não implementar a troca agora — apenas
     deixar o ponto de troca isolado e o fallback registrado.
4. **Saída = 4 artefatos** (escolha a): `folder.png`, `folder.html`, `assets/` (imagens cruas),
   `referencia.json`.

## 3. Entrada

- **Obrigatório (um dos dois):**
  - **foto** — caminho para imagem de pessoa real; **ou**
  - **texto** — descrição/história do personagem (modo personagem inventado).
- **Opcionais:**
  - `nome`, `idade`
  - `arte` — `foto` | `cartoon` (default: `foto`)
  - `layout` — id de template (default: `editorial-revista`)
  - `bio` / história livre
- **Preenchimento automático:** o que não for fornecido, o Claude **escreve** a partir da foto e/ou
  do texto — personalidade, características (ícone + label), detalhes (nome, idade, estilo, hobby,
  frase), e as 5 legendas da tira "detalhes em foco".

## 4. Pipeline

1. **Ficha de dados** — normalizar o input num objeto único (a "ficha"):
   ```
   nome, idade, subtitulo, personalidade[], caracteristicas[{icone,label}],
   detalhes{}, frase, focos[5]{legenda}
   ```
2. **Prompts de imagem** — gerar prompts textless para:
   - **1 retrato grande** (a foto principal da ficha);
   - **5 mini-retratos** ("detalhes em foco") em ângulos/poses/ações distintos.
   Todos no **estilo de arte** escolhido. Modo texto → T2I; modo foto → passar a foto como
   referência ao motor.
3. **Gerar imagens** — chamar `inemaimg` `POST /generate` (HTTP local) com `model=flux2-klein`,
   `prompt`, e (modo foto) `images=[base64]`. Salvar 6 PNGs em `assets/`.
4. **Montar `folder.html`** — carregar o template do `layout` escolhido e injetar as 6 imagens + os
   campos de texto da ficha.
5. **Renderizar HTML→PNG** — abrir o HTML em browser headless no tamanho fixo do template e
   capturar → `folder.png`.
6. **Emitir `referencia.json`** — a referência travada (ver §6).

## 5. Estrutura de arquivos da skill

```
inemaref/skill/
  folder/
    SKILL.md                 # a skill (instruções + invocação do pipeline)
    templates/
      editorial-revista/     # template do look dos exemplos
        template.html
        style.css
        meta.json            # tamanho (px), nome, descrição
      dossie/                # 2º template (alternativo)
        template.html
        style.css
        meta.json
  referencias/
    artes.md                 # fragmentos de prompt: `foto`, `cartoon`
    consistencia.md          # regra de identidade (descrição de aparência reutilizável)
    referencia.schema.json   # schema do referencia.json
```

- **Adicionar um estilo de layout** = adicionar uma pasta em `templates/` (HTML+CSS+meta). Sem
  mexer no resto.
- **Adicionar um estilo de arte** = adicionar um fragmento em `referencias/artes.md`.

## 6. `referencia.json` (a referência travada)

Consumido pelo futuro `quadrinho`. Campos mínimos:

```json
{
  "id": "ideni-maldaner",
  "modo": "foto | texto",
  "nome": "Ideni Maldaner",
  "idade": 84,
  "arte": "foto",
  "aparencia": "descrição textual reutilizável da pessoa/personagem para prompts (o 'prompt de identidade')",
  "retrato_ancora": "assets/retrato.png",
  "foto_origem": "caminho da foto de entrada (modo foto) ou null",
  "ficha": { "...": "a ficha de dados completa do §4.1" }
}
```

O `aparencia` é o "quanto do folder vira prompt de identidade reutilizável" que `docs/04` deixou em
aberto — resolvido aqui como um campo de texto.

## 7. Saída (pasta por personagem)

```
<saida>/<id>/
  folder.png         # entregável visual
  folder.html        # layout editável (texto é camada real)
  assets/            # 6 imagens cruas textless (retrato + 5 focos)
  referencia.json    # referência travada
```

## 8. Tamanho / formato

- Folder é **retrato** (página de revista). Tamanho fixo definido no `meta.json` de cada template
  (ex.: 1200×1600 px, proporção ~3:4). A geração de imagem usa aspect compatível com o slot do
  template (retrato grande ≈ retrato/quadrado; focos ≈ quadrado).

## 9. Integração externa

- **`inemaimg`** — servidor local já existente. Endpoint `POST /generate`:
  `{ model, prompt, images?[base64], negative_prompt? }`. Confirmar host/porta no
  `~/projetos/inemaimg/docker-compose.yml` na fase de plano.
- **Render HTML→PNG** — browser headless (a definir no plano: Playwright/Puppeteer já disponível no
  ambiente, ou a skill `agent-browser`). Apenas screenshot de tamanho fixo; sem animação.

## 10. Verificação (o teste de aceitação)

Rodar a skill em **2 modos × 2 layouts × 2 artes** e conferir:

1. **Modo foto** — usar 1 foto real (ex.: "Ideni"): o rosto deve sair **plausível e consistente**
   nos 6 shots. Se não fixar → registrar e acionar o fallback qwen-edit (decisão fora deste spec).
2. **Modo texto** — personagem inventado a partir de uma história.
3. **Texto legível** em todos os campos; **layout sem quebra/overflow** nos dois templates.
4. `referencia.json` válido contra `referencia.schema.json`.

Este teste também serve como o "experimento de consistência" mínimo do `docs/04`, restrito ao
folder (não cobre os quadros do `quadrinho`).

## 11. Fora de escopo (YAGNI)

- A troca real para qwen-edit (só deixar o ponto isolado + fallback documentado).
- A skill `quadrinho` e o motion comic (`docs/02`, `docs/03`).
- Mais de 2 templates de layout em V1 (o sistema é extensível; começa com 2).
- Série/filme (V2/V3).
