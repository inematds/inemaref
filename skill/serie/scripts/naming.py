import re
import unicodedata


def slug(text):
    """kebab-case ascii, sem acento; nunca vazio."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "x"


def ep_base(serie_slug, ep_n, ep_titulo):
    """Nome descritivo do episodio: <serie>-epNN-<titulo>."""
    return f"{serie_slug}-ep{int(ep_n):02d}-{slug(ep_titulo)}"


def page_base(serie_slug, ep_n, page_n, ep_titulo):
    """Nome de uma pagina: <serie>-epNN-<titulo>-pMM."""
    return f"{ep_base(serie_slug, ep_n, ep_titulo)}-p{int(page_n):02d}"
