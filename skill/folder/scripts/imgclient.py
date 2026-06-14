# skill/folder/scripts/imgclient.py
import base64, json, time, urllib.error, urllib.request

BASE_URL = "http://localhost:8000"
_urlopen = urllib.request.urlopen  # seam for tests
_RETRIES = 3  # the inemaimg server throws transient 5xx during model hot-swaps

def _b64_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def generate(prompt, out_path, model="flux2-klein", width=None, height=None,
             images=None, negative_prompt=None, seed=None, base_url=BASE_URL):
    """POST inemaimg /generate and save the returned PNG to out_path.

    images: optional list of reference image file paths. flux2-klein DOES use
    them (confirmed 2026-06-14 no loader): 1-4 imagens ancoram identidade E
    estilo (>4 -> erro do servidor). Edit models (qwen-edit-2511) tambem usam.
    negative_prompt: IGNORADO pelo flux2-klein (FLUX.2 nao tem negativo); inocuo."""
    payload = {"model": model, "prompt": prompt}
    if width:  payload["width"] = width
    if height: payload["height"] = height
    if negative_prompt: payload["negative_prompt"] = negative_prompt
    if seed is not None: payload["seed"] = seed
    if images: payload["images"] = [_b64_file(p) for p in images]
    req = urllib.request.Request(
        base_url + "/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_err = None
    for attempt in range(_RETRIES):
        try:
            with _urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read().decode())
            break
        except urllib.error.HTTPError as e:
            # retry only transient server errors (5xx); re-raise client errors (4xx)
            if e.code < 500 or attempt == _RETRIES - 1:
                raise
            last_err = e
            time.sleep(2 * (attempt + 1))
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data["image"]))
    return out_path
