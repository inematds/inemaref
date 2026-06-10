def build_referencia(ficha, modo, arte, retrato_ancora, foto_origem):
    idade = None
    for d in ficha.get("detalhes", []):
        if d.get("k", "").upper() == "IDADE":
            try: idade = int(d["v"])
            except (ValueError, TypeError): idade = None
    return {
        "id": ficha["id"],
        "modo": modo,
        "nome": ficha["nome"],
        "idade": idade,
        "arte": arte,
        "aparencia": ficha["aparencia"],
        "retrato_ancora": retrato_ancora,
        "foto_origem": foto_origem,
        "ficha": ficha,
    }

def validate_referencia(ref):
    """Minimal validator matching referencia.schema.json. Raises ValueError."""
    required = ["id", "modo", "nome", "arte", "aparencia", "retrato_ancora", "ficha"]
    for k in required:
        if k not in ref:
            raise ValueError(f"missing required field: {k}")
    if ref["modo"] not in ("foto", "texto"):
        raise ValueError(f"invalid modo: {ref['modo']}")
    if ref["arte"] not in ("foto", "cartoon"):
        raise ValueError(f"invalid arte: {ref['arte']}")
    if not isinstance(ref["aparencia"], str) or not ref["aparencia"].strip():
        raise ValueError("aparencia must be a non-empty string")
    if not isinstance(ref["ficha"], dict):
        raise ValueError("ficha must be an object")
    return True
