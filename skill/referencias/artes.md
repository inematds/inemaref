# Estilos de arte

Fragmentos de prompt em `artes.json` (fonte de verdade do código). Dois estilos:

- **foto** — foto-realista, fotografia editorial de revista. Para fichas de pessoas reais.
- **cartoon** — ilustração aquarela/gouache, lineart, cores vivas. Para personagens ilustrados.

Cada estilo tem `positivo` (injetado no prompt) e `negativo` (negative prompt — sempre proíbe
texto/letras, porque a arquitetura é *textless*: o texto é a camada HTML).

Adicionar um estilo = adicionar uma chave em `artes.json`.
