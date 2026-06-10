REQUIRED = ("id", "assunto", "objetivo", "premissa", "protagonista", "episodios")


def validate(biblia):
    """Valida a biblia. Levanta ValueError com mensagem acionavel.

    Exige: `objetivo` (o que a serie quer alcancar e pra quem) e, em CADA
    episodio, `contribuicao` (o que aquele episodio entrega rumo ao objetivo) —
    assim nenhum episodio e so cena solta. `elementos` (canon visual) e opcional;
    quando presente, cada item precisa de `nome` e `aparencia` travada."""
    miss = [k for k in REQUIRED if not biblia.get(k)]
    if miss:
        raise ValueError(f"biblia faltando campos: {miss}")
    eps = biblia["episodios"]
    if not isinstance(eps, list) or not eps:
        raise ValueError("episodios deve ser uma lista nao-vazia")
    for i, e in enumerate(eps, 1):
        if "n" not in e:
            raise ValueError(f"episodio {i} sem 'n'")
        if not e.get("titulo"):
            raise ValueError(f"episodio {i} sem 'titulo'")
        if not e.get("contribuicao"):
            raise ValueError(f"episodio {i} sem 'contribuicao' (o que entrega rumo ao objetivo)")
    for j, el in enumerate(biblia.get("elementos", []), 1):
        if not el.get("nome") or not el.get("aparencia"):
            raise ValueError(f"elemento {j} precisa de 'nome' e 'aparencia' travada")
    n = biblia.get("formato", {}).get("n_episodios")
    if n is not None and len(eps) != n:
        raise ValueError(f"n_episodios={n} mas o outline tem {len(eps)} episodios")
    return True


def to_markdown(biblia):
    """Biblia legivel para o portao de aprovacao."""
    p = biblia.get("premissa", {})
    prot = biblia.get("protagonista", {})
    out = [f"# {biblia.get('assunto', '')}", "",
           f"**Objetivo:** {biblia.get('objetivo', '')}", "",
           f"**Logline:** {p.get('logline', '')}", "",
           p.get("sinopse", ""), "",
           "## Protagonista", "",
           f"**{prot.get('nome', '')}** — {prot.get('aparencia', '')}"]
    elenco = biblia.get("elenco", [])
    if elenco:
        out += ["", "## Elenco", ""]
        out += [f"- **{c.get('nome', '')}** — {c.get('aparencia', '')}" for c in elenco]
    elementos = biblia.get("elementos", [])
    if elementos:
        out += ["", "## Elementos (canon visual — travados, referenciados nos quadros)", ""]
        out += [f"- **{el.get('nome', '')}** — {el.get('aparencia', '')}" for el in elementos]
    out += ["", "## Episodios", ""]
    for e in biblia["episodios"]:
        out.append(f"{e.get('n')}. **{e.get('titulo', '')}** — {e.get('sinopse', '')}")
        out.append(f"   ↳ _contribuicao:_ {e.get('contribuicao', '')}")
    return "\n".join(out) + "\n"
