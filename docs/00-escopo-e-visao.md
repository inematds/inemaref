# 00 — Escopo e visão

## O que é

`inemaref` é uma **fábrica de conteúdo a partir de referência de pessoa real**. O usuário entra com
**uma foto (pessoa real) + uma história** e o sistema produz artefatos onde **a mesma pessoa aparece
consistente**: ficha → quadrinho → série → filme.

O **ativo central é a referência**: o *model sheet* da pessoa, travado uma vez e reusado em tudo. Esse é o
motivo do nome e o motivo de tudo viver num repo só — o núcleo (consistência da pessoa real) é compartilhado.

## O nó que justifica o projeto

HQ com IA sempre quebra no mesmo ponto: **manter o personagem igual** entre quadros, páginas e episódios.
A aposta do `inemaref`: resolver isso de uma vez no **passo 0 (o folder)** e reusar essa referência em
todos os artefatos seguintes.

## As três versões (roadmap)

### V1 — a peça
- Entrada: **1 foto + a história**.
- Saída: **folder** (ficha de referência) **ou página** de quadrinho.
- Arte gerada **sem texto**; o texto entra em **2ª camada** — ou, no lugar de texto, **narração**.
- Diferencial: **não é imagem parada**. A câmera **abre na prancha inteira** e **viaja pelos quadros**
  (zoom no quadro → volta → segue pro próximo) = **motion comic** narrado. (Ver `docs/02`.)
- **Dois estilos**: foto-realista e cartoon/ilustrado.
- **Personagens são pessoas reais** (foto de referência), não só inventados.

### V2 — a série
- Vários quadrinhos (multi-página), **escrito ou narrado**, num **carrossel**.
- Objetivo: virar **episódios de um canal** (série).

### V3 — o filme
- A partir da série, **gerar filmes**.
- **Já existe**: é o `videoprodutor`. (Ver `docs/05`.)

## Princípios

1. **Referência primeiro.** O folder (model sheet) é passo 0 obrigatório; trava a pessoa real.
2. **Textless-first.** Gera a arte sem texto; balões/legendas/narração entram em camada → flexível para
   estático, motion e tradução.
3. **Reusar, não refazer.** O motor dinâmico (câmera, narração, render, filme) já está no ecossistema de
   vídeo do usuário. `inemaref` agrega só a frente específica de HQ.
4. **Escopo fechado.** Referência de pessoa → personagem → história. Nada fora disso entra no repo.
