# face_zones.py — detecta rostos em cada painel e retorna zonas seguras para texto.
#
# Divide o painel em 4 quadrantes (top-left, top-right, bottom-left, bottom-right).
# Detecta faces com Haar cascade e marca os quadrantes ocupados.
# Retorna as zonas livres de rosto pra posicionar narracao, fala e sfx.
import cv2
import os

_CASCADE_PATH = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")

# quadrantes: nome -> (posicao CSS)
QUADRANTS = {
    "top-left":     {"top": "0",  "left": "0",  "bottom": "auto", "right": "auto"},
    "top-right":    {"top": "0",  "right": "0",  "bottom": "auto", "left": "auto"},
    "bottom-left":  {"bottom": "0", "left": "0",  "top": "auto", "right": "auto"},
    "bottom-right": {"bottom": "0", "right": "0", "top": "auto", "left": "auto"},
}

# prioridade de posicao por tipo de elemento (quando nao ha rosto)
DEFAULT_POS = {
    "narracao": "top-left",
    "fala":     "bottom-right",
    "sfx":      "top-right",
}

# fallback se todas as zonas estiverem ocupadas (improvavel com 4 zonas)
FALLBACK_POS = {
    "narracao": "bottom-left",
    "fala":     "bottom-right",
    "sfx":      "top-right",
}


def face_quadrants(img_path):
    """Detecta rostos na imagem e retorna set de quadrantes ocupados.
    Ex: {'top-left', 'top-right'} = rostos na metade superior."""
    img = cv2.imread(img_path)
    if img is None:
        return set()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    cascade = cv2.CascadeClassifier(_CASCADE_PATH)
    # detectMultiScale com parametros ajustados pra cartoon/ilustracao
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3,
                                     minSize=(int(w * 0.08), int(h * 0.08)))

    occupied = set()
    mid_x, mid_y = w // 2, h // 2
    for (fx, fy, fw, fh) in faces:
        cx = fx + fw // 2
        cy = fy + fh // 2
        v = "top" if cy < mid_y else "bottom"
        hz = "left" if cx < mid_x else "right"
        occupied.add(f"{v}-{hz}")
    return occupied


_face_quadrants = face_quadrants  # compat


def safe_positions(panel_path):
    """Retorna dict com posicao segura pra cada tipo de texto.
    Ex: {"narracao": "bottom-left", "fala": "bottom-right", "sfx": "top-right"}"""
    occupied = face_quadrants(panel_path)

    result = {}
    used = set()
    for elem in ("narracao", "sfx", "fala"):
        preferred = DEFAULT_POS[elem]
        if preferred not in occupied and preferred not in used:
            result[elem] = preferred
            used.add(preferred)
        else:
            # tenta quadrantes livres, priorizando os opostos
            candidates = [q for q in QUADRANTS if q not in occupied and q not in used]
            if candidates:
                result[elem] = candidates[0]
                used.add(candidates[0])
            else:
                result[elem] = FALLBACK_POS[elem]
    return result


def css_for_position(elem_type, quadrant):
    """Retorna string CSS inline pra posicionar o elemento no quadrante dado."""
    pos = QUADRANTS[quadrant]
    parts = []
    for prop in ("top", "right", "bottom", "left"):
        val = pos[prop]
        if val != "auto":
            parts.append(f"{prop}: {val}")
        else:
            parts.append(f"{prop}: auto")
    return "; ".join(parts)
