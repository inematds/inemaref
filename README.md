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

**Fase de base/arquitetura.** A skill `folder` está **construída e validada end-to-end** (modo texto, 2 layouts × 2 artes). `quadrinho`, série e filme permanecem à frente.

## Skills

- `skill/folder/` — ✅ **construída** — **cria a referência**: a ficha do personagem (retrato + bio + traços + grid), a partir de 1 foto ou texto.
- `skill/quadrinho/` — **consome a referência**: monta a página de HQ (quadro-a-quadro, texto em camada), 2 estilos.
- `skill/referencias/` — núcleo comum: estilos (foto/cartoon), regra de consistência, mapa de quadros.

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
