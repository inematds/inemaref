"""casting — gera fichas-âncora por personagem/elemento do canon.

Expõe:
  _prompt_ficha(aparencia, arte_positivo) -> str
  gerar_fichas(biblia, out_dir, arte_positivo, generate_fn, width, height) -> dict
"""
import json
import os

from naming import slug


def _prompt_ficha(aparencia: str, arte_positivo: str) -> str:
    return (
        f"{aparencia}, single subject isolated on a neutral plain background, "
        f"full reference view, model sheet, {arte_positivo}, no text"
    )


def gerar_fichas(
    biblia: dict,
    out_dir: str,
    arte_positivo: str,
    generate_fn,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    """Gera uma ficha-âncora por entidade (elenco + elementos) e monta ancoras dict.

    Args:
        biblia: dict da bíblia com chaves opcionais 'elenco', 'elementos', 'protagonista'.
        out_dir: diretório raiz da série (out_dir/casting/ criado automaticamente).
        arte_positivo: sufixo de estilo adicionado a cada prompt.
        generate_fn: callable(prompt, out_path, *, width, height) — injetável p/ testes.
        width, height: dimensões das fichas geradas.

    Returns:
        dict nome_lower -> caminho absoluto da imagem âncora.
    """
    casting_dir = os.path.join(out_dir, "casting")
    os.makedirs(casting_dir, exist_ok=True)

    ancoras: dict = {}

    entidades = biblia.get("elenco", []) + biblia.get("elementos", [])
    for entidade in entidades:
        nome = entidade["nome"]
        aparencia = entidade["aparencia"]
        png = os.path.join(casting_dir, f"{slug(nome)}.png")
        if not os.path.exists(png):
            generate_fn(_prompt_ficha(aparencia, arte_positivo), png,
                        width=width, height=height)
        ancoras[nome.lower()] = png

    # protagonista (opcional): usa retrato existente se disponível; NÃO regenera
    prot = biblia.get("protagonista") or {}
    prot_id = prot.get("id")
    if prot_id:
        retrato = os.path.join(out_dir, "biblia", prot_id, "assets", "retrato.png")
        if os.path.exists(retrato):
            prot_nome = prot.get("nome", "")
            if prot_nome:
                ancoras[prot_nome.lower()] = retrato
            ancoras[prot_id.lower()] = retrato

    # persiste ancoras.json
    json_path = os.path.join(casting_dir, "ancoras.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(ancoras, fh, ensure_ascii=False, indent=2)

    return ancoras
