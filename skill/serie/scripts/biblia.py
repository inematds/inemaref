REQUIRED = ("id", "assunto", "premissa", "protagonista", "episodios")


def validate(biblia):
    """Valida a biblia. Levanta ValueError com mensagem acionavel."""
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
    n = biblia.get("formato", {}).get("n_episodios")
    if n is not None and len(eps) != n:
        raise ValueError(f"n_episodios={n} mas o outline tem {len(eps)} episodios")
    return True


def to_markdown(biblia):
    """Biblia legivel para o portao de aprovacao."""
    p = biblia.get("premissa", {})
    prot = biblia.get("protagonista", {})
    out = [f"# {biblia.get('assunto', '')}", "",
           f"**Logline:** {p.get('logline', '')}", "",
           p.get("sinopse", ""), "",
           "## Protagonista", "",
           f"**{prot.get('nome', '')}** — {prot.get('aparencia', '')}"]
    elenco = biblia.get("elenco", [])
    if elenco:
        out += ["", "## Elenco", ""]
        out += [f"- **{c.get('nome', '')}** — {c.get('aparencia', '')}" for c in elenco]
    out += ["", "## Episodios", ""]
    out += [f"{e.get('n')}. **{e.get('titulo', '')}** — {e.get('sinopse', '')}"
            for e in biblia["episodios"]]
    return "\n".join(out) + "\n"
