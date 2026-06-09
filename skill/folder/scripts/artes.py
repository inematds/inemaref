import json, os

_ARTES_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "referencias", "artes.json")

def load_arte(arte):
    with open(_ARTES_PATH) as f:
        data = json.load(f)
    if arte not in data:
        raise ValueError(f"unknown art style: {arte} (have {list(data)})")
    return data[arte]

def build_prompts(ficha, arte):
    """Build textless prompts: 1 big portrait + 5 'detalhes em foco' shots.

    Each foco may carry an optional `prompt` field — a full scene description
    (e.g. a life-stage vignette). When present it is used as-is (only the art
    style is appended), giving real scene variation instead of a repeated
    portrait. Without it, the foco is a detail shot derived from `legenda`,
    anchored to `aparencia` for maximum identity consistency."""
    a = load_arte(arte)
    aparencia = ficha["aparencia"].strip().rstrip(".")
    base = f"{aparencia}, {a['positivo']}, plain neutral background, no text"
    retrato = f"{base}, head-and-shoulders portrait, looking at camera"
    focos = []
    for foco in ficha["focos"][:5]:
        if foco.get("prompt"):
            scene = foco["prompt"].strip().rstrip(".")
            focos.append(f"{scene}, {a['positivo']}, no text")
        else:
            scene = foco["legenda"].strip().lower()
            focos.append(f"{base}, {scene}, candid close detail")
    return {"retrato": retrato, "focos": focos, "negativo": a["negativo"]}
