# 02 — Motion comic (o diferencial dinâmico)

## A ideia (palavras do usuário)

Em vez de imagens isoladas, a câmera **começa aberta na prancha inteira** e **vai seguindo os quadros**:
faz **zoom no quadro**, depois **volta**, e segue pro próximo. Com **narração** no lugar (ou além) do texto.
Resultado: a HQ vira **vídeo dinâmico** — um *motion comic* narrado.

## Sequência de câmera

```
[abre] prancha inteira (estabelece a página)
  → zoom-in no quadro 1   (narra o quadro 1)
  → pull-back / transição
  → zoom-in no quadro 2   (narra o quadro 2)
  → ...                    (segue a ordem de leitura)
  → [fecha] prancha inteira / SFX final / "continua"
```

## O que isso exige

1. **Mapa de quadros** — as **coordenadas de cada painel** na prancha (x, y, w, h) e a **ordem de leitura**.
   Sem isso a câmera não sabe para onde ir. → é o motivo da decisão em `docs/03` (gerar quadro-a-quadro,
   onde as coordenadas já são conhecidas).
2. **Arte sem texto** — para a narração casar e para os balões entrarem em camada quando quiser texto.
3. **Timing por quadro** — duração de cada parada = duração da narração daquele quadro (timestamps).
4. **Profundidade opcional** — parallax 2.5D dentro de cada quadro dá premium (camada cinema do `pixflow`).

## Onde isso já existe

- Câmera (pan/zoom/parallax) + profundidade → **pixflow**.
- Narração + timestamps por trecho → **inemavox** + **videoprodutor**.
- Render final em vídeo (16:9 / 9:16) → **videoprodutor** / Remotion.

Ver `docs/05`. O motion comic é, na prática, o `videoprodutor` com um **preset "quadrinho"**: o fundo é a
prancha, a câmera viaja pelos quadros, a narração guia o timing.

## Modos de saída de V1

- **Estático** — prancha pronta; texto baked OU balões em camada.
- **Dinâmico (motion comic)** — câmera viaja pelos quadros + narração.
