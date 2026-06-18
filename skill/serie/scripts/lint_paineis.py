# skill/serie/scripts/lint_paineis.py
"""Linter determinístico de entidades por painel.

Regras:
  - 'quem' ausente        → protagonista implícito (+1)
  - 'quem' presente/não-vazio → personagem explícito (+1)
  - 'quem' presente/vazio  → nenhuma pessoa (+0)
  - 'usa'                  → cada elemento do canon conta +1
"""


def contar_entidades(painel: dict) -> int:
    """Retorna o número de entidades no painel."""
    if "quem" not in painel:
        pessoas = 1                          # protagonista implícito
    elif painel["quem"]:
        pessoas = 1                          # personagem explícito
    else:
        pessoas = 0                          # quem="" → dobrador / off

    elementos = len(painel.get("usa") or [])
    return pessoas + elementos


def lint_episodio(ep: dict, max_entidades: int = 2) -> list:
    """Percorre ep['paginas'][].paineis[] e sinaliza painéis que excedem max_entidades.

    Retorna lista de dicts:
        {"pagina": n, "painel": idx_1based, "n": contagem, "entidades": [str, ...]}
    """
    erros = []
    for pagina in ep.get("paginas", []):
        n_pag = pagina["n"]
        for idx, painel in enumerate(pagina.get("paineis", []), start=1):
            total = contar_entidades(painel)
            if total > max_entidades:
                # monta lista legível de entidades
                entidades = []
                if "quem" not in painel:
                    entidades.append("protagonista")
                elif painel["quem"]:
                    entidades.append(painel["quem"])
                entidades.extend(painel.get("usa") or [])

                erros.append({
                    "pagina": n_pag,
                    "painel": idx,
                    "n": total,
                    "entidades": entidades,
                })
    return erros
