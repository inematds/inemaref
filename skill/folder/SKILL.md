---
name: folder
description: Cria a FICHA DE REFERENCIA (model sheet) de um personagem a partir de uma FOTO (pessoa real) ou de um TEXTO (descricao/historia). Saida = pagina editorial (folder.png) + folder.html editavel + assets/ (imagens cruas) + referencia.json travado. Use quando o usuario quiser "criar referencia", "ficha de personagem", "model sheet", "folder do personagem", ou der uma foto/historia e pedir a pagina de referencia do inemaref. Dois layouts (editorial-revista, dossie) x duas artes (foto, cartoon), combinaveis.
---

# Skill: folder — ficha de referencia (passo 0 do inemaref)

Arquitetura **textless + camada**: o flux2-klein gera so as imagens; o texto e o layout sao camada
HTML/CSS renderizada pra PNG. Detalhes em `docs/superpowers/specs/2026-06-09-folder-skill-design.md`.

## Entrada
- **Foto** (pessoa real) **ou** **texto** (descricao/historia). Um dos dois e obrigatorio.
- Opcionais: nome, idade, **arte** (`foto`|`cartoon`, default `foto`), **layout**
  (`editorial-revista`|`dossie`, default `editorial-revista`).

## Passos
1. **Monte a ficha** — produza um `ficha.json` no formato de
   `skill/folder/tests/fixtures/ficha-exemplo.json`:
   `id` (slug do nome), `kicker`, `nome`, `subtitulo`, `aparencia` (descricao reutilizavel da
   pessoa — ver `skill/referencias/consistencia.md`), `personalidade[]`, `caracteristicas[{icone,label}]`,
   `detalhes[{k,v}]` (inclua IDADE), `frase`, e **exatamente 5** `focos[{legenda}]`.
   - Modo texto: escreva os campos a partir da historia.
   - Modo foto: descreva a pessoa em `aparencia` e guarde o caminho da foto.
2. **Rode o pipeline:**
   ```bash
   python3 - <<'PY'
   import sys, json
   sys.path.insert(0, "skill/folder/scripts")
   from build_folder import build_folder
   ficha = json.load(open("CAMINHO/ficha.json"))
   build_folder(ficha,
       template_dir="skill/folder/templates/<layout>",
       arte="<foto|cartoon>",
       out_dir="<pasta de saida>",
       modo="<texto|foto>",
       foto_origem="<caminho da foto ou None>")
   PY
   ```
   (Pre-requisito: servidor `inemaimg` em `http://localhost:8000`.)
3. **Mostre** o `folder.png` ao usuario. Para ajustes de texto, edite `folder.html` e re-renderize
   com `skill/folder/scripts/render.py`. As imagens ficam em `assets/`; a referencia travada em
   `referencia.json` (consumida depois pela skill `quadrinho`).

## Estilos
- **Layout:** adicione uma pasta em `skill/folder/templates/` (template.html + style.css + meta.json,
  mesmos placeholders).
- **Arte:** adicione uma chave em `skill/referencias/artes.json`.

## Motor de imagem
Padrao `flux2-klein`. Se o rosto nao fixar no modo foto, troque para `qwen-edit-2511` (parametro
`model=` em `build_folder`) — ver `skill/referencias/consistencia.md`.
