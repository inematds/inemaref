# 04 — Consistência da pessoa real (o nó técnico)

## O problema

O personagem é uma **pessoa real** (foto de referência). O sistema precisa manter **o mesmo rosto/pessoa**
em todos os quadros, páginas e episódios. Esse é o ponto que mais quebra em HQ com IA e o que justifica a
referência (folder) como passo 0.

## Candidatos a testar

### Nano Banana / Gemini (`~/projetos/NanoBanana`)
- Forte em **prender rosto a partir de 1 foto** e em **texto/layout**.
- Foi (provavelmente) o tipo de modelo por trás dos exemplos do ChatGPT.
- ❌ não é local; depende de API.

### flux2-klein local (`~/projetos/inemaimg`)
- **Padrão do usuário**, local, sem chave de API.
- Consistência via **referência de rosto** (IP-adapter / face ref / LoRA da pessoa).
- ❌ fraco em texto longo legível e em montar grid de prancha num shot — mas isso **não importa**, porque
  o caminho B gera **quadro textless** (ver `docs/03`), que é o forte do flux.

## O experimento que destrava o projeto

**Antes de codar qualquer skill**, rodar o teste de consistência:

1. Pegar **1 foto de uma pessoa real** (ex.: do próprio usuário / família — os exemplos já usam "Ideni Maldaner").
2. Gerar o **folder** (model sheet) com essa pessoa.
3. Gerar **3–4 quadros textless** da mesma pessoa em poses/cenas diferentes, **nos dois estilos** (foto e cartoon).
4. Comparar **Nano Banana × flux2-klein** lado a lado: qual mantém o rosto/identidade melhor, em cada estilo.

**Saída do experimento:** decidir o motor de imagem padrão (provável: híbrido — flux local quando dá conta,
Nano Banana quando precisa de fidelidade de rosto difícil), e o método de referência (face ref / LoRA).

## Em aberto (decidir após o teste)

- Modelo padrão por estilo (foto vs cartoon podem querer modelos diferentes).
- Método de travamento do rosto (IP-adapter vs LoRA por pessoa vs referência simples).
- Quanto do folder vira "prompt de identidade" reutilizável nos quadros.

## Resultado (folder) — 2026-06-09

Primeiro e2e da skill `folder` com **flux2-klein local** (servidor `inemaimg`, 6 imagens + render
em ~28s):

- **Modo texto** (personagem inventado), **4 cruzamentos** (editorial-revista × dossiê) × (foto ×
  cartoon): ✅ todos rodam e o personagem sai **consistente nos 6 shots** (retrato + 5 "detalhes em
  foco"). A consistência vem do campo `aparencia` (prompt de identidade compartilhado) injetado em
  todos os prompts — flux2-klein puro (T2I) já segura bem nesse modo.
- **Modo foto** (pessoa real travada): **ainda não avaliado** — precisa de 1 foto real de entrada.
  Como flux2-klein é T2I e ignora `images`, a expectativa é que o rosto **não** fixe; nesse caso o
  caminho é trocar `model="qwen-edit-2511"` (face-swap, usa `images`) — troca de 1 linha em
  `build_folder.py`, ponto de seam isolado (ver `../skill/referencias/consistencia.md`).

Decisão prática: **flux2-klein é o motor padrão** e basta para o folder em modo texto. O veredito de
modo foto fica pendente do teste com foto real (não bloqueia a V1 de personagens inventados).
