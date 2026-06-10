# skill/folder/scripts/render.py
import glob, os, subprocess

def find_chromium():
    """Locate a Chromium binary: env override, ms-playwright cache, then PATH."""
    env = os.environ.get("CHROMIUM_BIN")
    if env and os.path.exists(env):
        return env
    cache = os.path.expanduser("~/.cache/ms-playwright")
    hits = sorted(glob.glob(os.path.join(cache, "chromium-*/chrome-linux/chrome")))
    if hits:
        return hits[-1]  # highest version
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        from shutil import which
        p = which(name)
        if p:
            return p
    raise RuntimeError("no Chromium binary found (set CHROMIUM_BIN)")

def render_html_to_png(html_path, png_path, width, height):
    """Screenshot a local HTML file to PNG at an exact pixel size."""
    chrome = find_chromium()
    url = "file://" + os.path.abspath(html_path)
    cmd = [
        chrome, "--headless=new", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=1",
        f"--window-size={width},{height}",
        f"--screenshot={os.path.abspath(png_path)}",
        url,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    if not os.path.exists(png_path):
        raise RuntimeError("chromium produced no screenshot")
    return png_path
