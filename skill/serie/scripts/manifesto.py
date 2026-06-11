def build(biblia, entregas, gerado_em):
    """Monta o manifesto.json. `entregas` = [{n, arquivos:[...], thumb?}].
    Junta titulo/descricao/tags da biblia por numero de episodio."""
    by_n = {e["n"]: e for e in biblia.get("episodios", [])}
    episodios = []
    for d in entregas:
        e = by_n.get(d["n"], {})
        episodios.append({
            "n": d["n"],
            "titulo": e.get("titulo", ""),
            "descricao": e.get("sinopse", ""),
            "tags": e.get("tags", []),
            "arquivos": d.get("arquivos", []),
            "thumb": d.get("thumb"),
        })
    return {
        "serie": biblia.get("premissa", {}).get("logline", biblia.get("assunto", "")),
        "assunto": biblia.get("assunto", ""),
        "serie_id": biblia.get("id", ""),
        "tipo": biblia.get("formato", {}).get("tipo", ""),
        "gerado_em": gerado_em,
        "episodios": episodios,
    }
