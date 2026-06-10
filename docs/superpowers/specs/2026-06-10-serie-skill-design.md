# Spec — skill `serie` (V2 do inemaref): criador de série ponta a ponta

**Data:** 2026-06-10
**Estado:** aprovado (brainstorming) — pronto para o plano de implementação.

## 1. Objetivo

Uma skill **`serie`** que, a partir de um **assunto**, cria a **bíblia da série** (contexto +
referência/folder do protagonista + elenco + estilo + outline de episódios), e — após aprovação —
**corre por conta** gerando todos os **episódios** e suas **páginas**, em **texto / HQ / vídeo**,
reusando as skills que já existem (`folder`, `quadrinho`, `motioncomic`). É o **orquestrador-criador**
(V2): o Claude é o cérebro criativo; o Python é o motor determinístico que encadeia os fluxos.

A saída final é **largada numa pasta de destino** (ex.: `~/projetos/yt-pub-lives2/import/<serie>/`),
com **nomes descritivos** (título do assunto) e um **`manifesto.json`** sempre junto, para um
uploader/canal externo consumir. **Publicar/subir no canal está fora do escopo** desta versão
(handoff por pasta).

## 2. Decisões (do brainstorming)

1. **Escopo:** produzir artefatos numa **pasta de destino** + manifesto; upload/publicação fora.
2. **Unidade de entrega (depende do tipo):** vídeo junta as páginas em **1 MP4 por episódio**;
   `hq`/`texto` ficam em **páginas/arquivos separados** por episódio. Nomes **descritivos**.
   **Manifesto sempre junto.**
3. **Tipos suportados nesta versão:** `texto`, `hq`, `video-slideshow` (Forma A),
   `video-pagina` (Forma B). **Adiados:** pixflow/fontefilm (cinematográfico) e animabook (HQ animada).
4. **Portão de aprovação:** bíblia (`biblia.md`) + **folder do protagonista** + **1 página-piloto**
   (ep1/pág1) antes do lote. Flag **`auto`** pula o portão e roda sozinho.
5. **Runner:** **híbrido plugável** — default **inline** (idempotente, progresso no openpcbot); se o
   serviço **mkivideos** estiver de pé **e** o tipo for vídeo, **despacha os renders pra fila**.

## 3. Arquitetura / componentes

Mesmo padrão das skills atuais: **`SKILL.md` (cérebro/LLM)** + **`scripts/` (orquestrador
determinístico, testável sem daemon)**.

```
skill/serie/
  SKILL.md                 # guia o Claude: assunto+config -> biblia.json; depois -> roteiros dos episodios
  config.yaml              # defaults globais, comentados (fonte unica)
  scripts/
    config.py              # carrega config.yaml (com fallback embutido) + resolve(biblia)
    biblia.py              # schema/validacao da biblia; gera biblia.md legivel
    naming.py              # slug + nome descritivo dos arquivos de saida
    manifesto.py           # monta manifesto.json (serie + episodios + arquivos)
    runner.py              # runner_inline | runner_mkivideos | escolha automatica
    build_serie.py         # orquestrador: build_biblia(...) e build_serie(...)
  tests/
    test_config.py  test_biblia.py  test_naming.py  test_manifesto.py  test_runner.py
  templates/ (se preciso)  # cabecalho da biblia.md, etc.
```

- **`build_biblia(biblia, out_dir)`** → monta o **pacote de aprovação**: folder do protagonista
  (reusa `folder.build_folder`), `biblia.md` legível, e **1 página-piloto** (reusa
  `quadrinho.build_pagina` no ep1/pág1). Retorna os caminhos. Não inicia o lote.
- **`build_serie(biblia, episodios, out_dir=None, auto=False, runner="auto")`** → após aprovação,
  para cada episódio renderiza por tipo, nomeia descritivo, escreve `manifesto.json`, e **larga no
  destino**. **Idempotente** (pula o que já existe, por arquivo). Avisa progresso no openpcbot.

**Reuso:** `folder` (protagonista + elenco), `quadrinho.build_pagina`, `motioncomic.build_video`
(Forma A) e `build_video_travel` (Forma B), `mkivideos` (fila), `tools/notify.py` (bot).

## 4. Dados

### 4.1 `config.yaml` (defaults globais — comentado)

```yaml
# serie — defaults da skill. Cada série sobrescreve na sua biblia.json.
estilo:
  arte: manga                   # manga | cartoon | foto
  modelo_pagina: grade-uniforme # grade-uniforme (2x3) | manga-dinamico (assimétrico)
  voz: bella                    # bella | rachel  (só tipos de vídeo)
  intro: true                   # cartão de abertura no vídeo: true | false
formato:
  tipo: video-pagina            # texto | hq | video-slideshow | video-pagina
  n_episodios: 3                # quantos episódios
  n_paginas: 3                  # páginas por episódio (cada página = 6 quadros)
  destino: output               # pasta de saída -> <destino>/<serie-id>/ (+ manifesto.json)
runtime:
  auto: false                   # true = pula o portão de aprovação
  runner: auto                  # auto (inline; mkivideos se de pé e tipo=vídeo) | inline | mkivideos
  notificar: true               # progresso no openpcbot: true | false
```

**Ordem de resolução de cada campo:** `biblia.json` (por série) **>** `config.yaml` (default global)
**>** fallback embutido em `config.py` (a skill nunca crasha se o arquivo sumir/quebrar).

### 4.2 `biblia.json`

```json
{
  "id": "slug-do-assunto",
  "assunto": "texto do assunto dado pelo usuário",
  "premissa": { "logline": "...", "sinopse": "..." },
  "estilo":  { "arte": "manga", "modelo_pagina": "grade-uniforme", "voz": "bella", "intro": true },
  "formato": { "tipo": "video-pagina", "n_episodios": 3, "n_paginas": 3, "destino": "output" },
  "protagonista": { "nome": "...", "aparencia": "descrição reutilizável travada", "...": "campos do folder" },
  "elenco": [ { "nome": "...", "aparencia": "..." } ],
  "episodios": [ { "n": 1, "titulo": "...", "sinopse": "..." } ]
}
```

`estilo`/`formato` podem vir parciais — campos ausentes caem no `config.yaml`. `protagonista` carrega
o que a skill `folder` precisa (ver `folder/SKILL.md`); `aparencia` é a âncora de consistência reusada
em todos os quadros (como em `quadrinho`/`motioncomic`).

### 4.3 Roteiro por episódio (canônico)

Usa a **forma do `motioncomic`** (que já cobre HQ e vídeo): um episódio é um roteiro com `paginas[]`,
cada página com `paineis[6]` (`prompt` + opcionais `narracao`, `fala{quem,texto}`, `sfx`, `quem`).

```json
{ "id": "slug-ep01", "n": 1, "titulo": "...", "sinopse": "...",
  "personagem": "<aparencia do protagonista>",
  "paginas": [ { "n": 1, "titulo": "...", "paineis": [ { "prompt": "...", "narracao": "...",
                 "fala": {"quem":"...","texto":"..."}, "sfx": "..." }, "...(6)" ] } ] }
```

O orquestrador **adapta** esse roteiro por renderer (o `build_travel._page_roteiro` já faz a ponte
para o `quadrinho`: `fala` dict → string, dobra `quem`/protagonista no prompt). `texto` apenas
serializa o roteiro.

### 4.4 `manifesto.json` (no destino, sempre)

```json
{ "serie": "Título da Série", "assunto": "...", "tipo": "video-pagina", "serie_id": "slug",
  "gerado_em": "2026-06-10",
  "episodios": [ { "n": 1, "titulo": "...", "descricao": "...", "tags": ["..."],
                   "arquivos": ["slug-ep01-titulo.mp4"], "thumb": "slug-ep01-titulo.jpg" } ] }
```

É o contrato com o uploader/canal. `descricao`/`tags`/`thumb` saem da bíblia + 1º quadro do episódio.

## 5. Tipos → render e entrega

| tipo | render (reuso) | entrega no `<destino>/<serie-id>/` |
|---|---|---|
| `texto` | — | `slug-epNN-titulo.md` (+ `.json`) por episódio |
| `hq` | `quadrinho.build_pagina` por página | `slug-epNN-pMM-titulo.png` (soltos) |
| `video-slideshow` | `motioncomic.build_video` (Forma A) | `slug-epNN-titulo.mp4` (1 por episódio) |
| `video-pagina` | `motioncomic.build_video_travel` (Forma B) | `slug-epNN-titulo.mp4` (1 por episódio) |

Nome descritivo via `naming.py`: `slug(assunto)` + `epNN` + `slug(titulo do episodio)`.

## 6. Fluxo ponta a ponta

1. **Entrada:** assunto + config (qualquer subset; o resto cai no `config.yaml`).
2. **Bíblia:** Claude (guiado pela `SKILL.md`) escreve `biblia.json` + outline de episódios.
3. **Pacote de aprovação:** `build_biblia` → folder do protagonista + `biblia.md` + página-piloto.
4. **Portão:** apresenta ao usuário; "aprovado" (ou `auto=true`) libera. Usuário pode editar a
   `biblia.json` e re-rodar `build_biblia`.
5. **Roteiros:** Claude gera os roteiros de **todos os episódios** (guiado pela bíblia).
6. **Lote:** `build_serie` renderiza por tipo via runner (inline ou mkivideos p/ vídeo), nomeia,
   escreve `manifesto.json`, larga em `<destino>/<serie-id>/`. **Idempotente** + progresso no bot.

## 7. Runner (híbrido plugável)

- `runner="inline"` — renderiza em sequência no próprio processo (default determinístico).
- `runner="mkivideos"` — para tipos de **vídeo**, **submete um job por episódio** à fila do
  `mkivideos` (worker em background vigia até terminar); a skill segue/coleta os resultados.
- `runner="auto"` (default) — usa `mkivideos` se o serviço estiver disponível **e** o tipo for vídeo;
  senão, inline. `runner.py` encapsula a detecção e a submissão; o resto do orquestrador não muda.

## 8. Erros, idempotência, observabilidade

- **Idempotente:** cada arquivo de saída é pulado se já existe; re-rodar continua de onde parou.
- **Degrada com clareza:** se `inemaimg`/`inemavox` estiver fora, falha com mensagem acionável; a
  **página-piloto** no portão pega erro de estilo **antes** do lote pesado.
- **Progresso:** `notificar: true` envia marcos ao openpcbot (`tools/notify.py`): bíblia pronta,
  cada episódio concluído, lote finalizado.

## 9. Testes (sem daemon)

Funções puras + render injetável (como nas skills atuais: `generate_fn`/`render_fn`):
- `test_config` — carrega `config.yaml`, aplica fallback, e a ordem de resolução `biblia > config > fallback`.
- `test_biblia` — validação de schema (campos obrigatórios, `episodios` coerente com `n_episodios`) e geração do `biblia.md`.
- `test_naming` — slug + nome descritivo determinístico e seguro (sem acento/colisão).
- `test_manifesto` — builder produz o manifesto certo a partir de bíblia + lista de arquivos.
- `test_runner` — seleção `auto` (mock de mkivideos de pé/fora) e mapeamento tipo→entrega.

## 10. Fora do escopo / adiado

- **Upload/publicação** real no canal (handoff por pasta de destino).
- **pixflow/fontefilm** (cinematográfico parallax) e **animabook** (HQ animada com social).
- **Modo foto fiel** (rosto real travado) — herda o estado atual do `folder`/`quadrinho`.
- **nº de quadros por página ≠ 6** — herda a limitação atual do `quadrinho`/`fill_pagina`.

## 11. Reuso (inventário)

`folder.build_folder` · `quadrinho.build_pagina` · `motioncomic.build_video` /
`build_video_travel` · `mkivideos` (fila de render) · `tools/notify.py` (openpcbot) ·
helpers compartilhados do `folder` (`imgclient`, `render`, `artes`, `png_size`).
