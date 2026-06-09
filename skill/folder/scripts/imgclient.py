# skill/folder/scripts/imgclient.py
import base64, json, urllib.request

BASE_URL = "http://localhost:8000"
_urlopen = urllib.request.urlopen  # seam for tests

def _b64_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def generate(prompt, out_path, model="flux2-klein", width=None, height=None,
             images=None, negative_prompt=None, seed=None, base_url=BASE_URL):
    """POST inemaimg /generate and save the returned PNG to out_path.

    images: optional list of reference image file paths (used by edit models
    like qwen-edit-2511; flux2-klein may ignore them — that is the documented
    fallback seam, see referencias/consistencia.md)."""
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
    with _urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode())
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data["image"]))
    return out_path
