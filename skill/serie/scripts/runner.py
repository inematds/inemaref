import os

VIDEO_TIPOS = ("video-slideshow", "video-pagina")


def is_video(tipo):
    return tipo in VIDEO_TIPOS


def mkivideos_disponivel(check_fn=None):
    """True se a fila do mkivideos esta de pe. `check_fn` injetavel p/ teste;
    default tenta MKIVIDEOS_URL/health (sem a env -> False)."""
    if check_fn is not None:
        return bool(check_fn())
    url = os.environ.get("MKIVIDEOS_URL")
    if not url:
        return False
    try:
        import urllib.request
        urllib.request.urlopen(url.rstrip("/") + "/health", timeout=3)
        return True
    except Exception:
        return False


def escolher(tipo, runner="auto", disponivel=False):
    """Decide 'inline' ou 'mkivideos'. auto = mkivideos so se for video E a fila
    estiver disponivel; senao inline."""
    if runner in ("inline", "mkivideos"):
        return runner
    return "mkivideos" if (is_video(tipo) and disponivel) else "inline"
