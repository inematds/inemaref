import os
try:
    import yaml
except ImportError:
    yaml = None

_SERIE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # skill/serie
CONFIG_PATH = os.path.join(_SERIE_DIR, "config.yaml")

FALLBACK = {
    "estilo": {"arte": "manga", "modelo_pagina": "manga-dinamico", "voz": "bella", "intro": True},
    "formato": {"tipo": "video-pagina", "n_episodios": 3, "n_paginas": 3, "destino": "~/projetos/output"},
    "runtime": {"auto": False, "runner": "auto", "notificar": True},
}


def _merge(base, over):
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path=None):
    """Defaults globais: config.yaml mesclado sobre FALLBACK. Nunca crasha —
    se o arquivo sumir/quebrar (ou sem pyyaml), volta o FALLBACK."""
    path = path or CONFIG_PATH
    if yaml and os.path.exists(path):
        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return _merge(FALLBACK, data)
        except Exception:
            return _merge(FALLBACK, {})
    return _merge(FALLBACK, {})


def resolve(biblia, config=None):
    """Achata estilo+formato+runtime aplicando biblia > config > fallback."""
    cfg = config or load_config()
    estilo = _merge(cfg["estilo"], biblia.get("estilo", {}))
    formato = _merge(cfg["formato"], biblia.get("formato", {}))
    flat = {}
    flat.update(estilo)
    flat.update(formato)
    flat.update(cfg["runtime"])
    return flat
