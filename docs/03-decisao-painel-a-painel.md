# 03 — Decisão: gerar quadro-a-quadro (caminho B)

## A bifurcação

Como produzir a prancha? Duas opções, e ela define a arquitetura inteira.

### (A) Página inteira num shot
Um gerador forte em texto+layout (gpt-image / Nano Banana) produz a **prancha completa**, com balões
embutidos — foi assim que os exemplos do ChatGPT saíram.

- ✅ linda, impacto imediato, rápida.
- ❌ o sistema **não sabe onde estão os quadros** → câmera viaja no chute.
- ❌ texto **grudado** → difícil pôr em camada, narrar, traduzir, editar (editar = re-gerar a página toda).
- ❌ **consistência de personagem** entre páginas frágil.

### (B) Quadro-a-quadro + montar a prancha
Define-se o **layout (grid)**; gera-se **cada quadro sem texto**, com a pessoa real consistente; o sistema
**conhece as coordenadas de cada quadro**; monta-se a prancha por código (Remotion / animabook).

- ✅ **coordenadas conhecidas** → câmera viaja com precisão (necessário pro motion comic, `docs/02`).
- ✅ **texto/balões em camada** → narração, tradução, edição barata.
- ✅ controle de **consistência** por quadro (referência aplicada quadro a quadro).
- ❌ a prancha é **montada por código**, não "sai pronta da IA".

## Decisão

**Caminho B é a base.** É o único que entrega o motion comic narrado (texto em camada + câmera pelos
quadros) que o usuário descreveu. O look "página inteira do ChatGPT" continua disponível como **preset
estático paralelo** (export), mas **não é o motor**.

## Consequência

- A skill `quadrinho` trabalha com um **layout de prancha** (grid de quadros) + **geração textless por
  quadro** + **camada de texto/balões**.
- O **mapa de quadros** (coordenadas + ordem) é subproduto natural de B e alimenta direto o motion comic.
- Montagem da prancha: Remotion (mesmo motor do vídeo) ou animabook (balões arrastáveis já prontos).
