# Consistencia da pessoa (campo `aparencia`)

`aparencia` (em `referencia.json`) e o "prompt de identidade" reutilizavel: uma descricao textual
estavel da pessoa/personagem (idade, cabelo, rosto, marca registrada), injetada em TODO prompt de
imagem — no folder e, depois, nos quadros do `quadrinho`. E o que mantem a pessoa igual.

## Modo foto vs modo texto
- **texto** — personagem inventado; `aparencia` e escrita pelo Claude a partir da historia.
- **foto** — pessoa real; `aparencia` descreve a foto, e a foto e passada como `images=[...]` ao
  motor (`imgclient.generate`).

## Seam de troca de motor (a decisao do brainstorming)
Padrao: `flux2-klein` (T2I). Como flux ignora `images`, o rosto pode nao fixar no modo foto. Se o
teste de aceitacao (Task 9) mostrar deriva de rosto, trocar `model="flux2-klein"` por
`model="qwen-edit-2511"` em `build_folder.py` (tarefas face-swap/multiple-angles, que usam `images`).
E uma troca de uma linha — nenhuma outra parte muda.
