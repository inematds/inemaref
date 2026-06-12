"""Motion comic: para cada quadro gera imagem (textless cartoon), sobrepoe so
balao/SFX, narra (inemavox) e da ZOOM no quadro durante a narracao (ffmpeg
zoompan). Junta tudo num MP4 16:9. (docs/02 — a camera viaja pelos quadros.)"""
import html as _h
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _deps  # noqa: E402
sys.path.insert(0, _deps.scripts("folder"))
import imgclient            # noqa: E402
from artes import load_arte  # noqa: E402
sys.path.insert(0, os.path.dirname(__file__))
from overlay import render_panel  # noqa: E402
from render import render_html_to_png  # noqa: E402
from tts import say, duration         # noqa: E402

W, H, FPS = 1280, 720, 30
GEN_W, GEN_H = 1280, 704  # multiplos de 64 p/ o flux

def _gen_image(prompt, personagem, out_png, model="flux2-klein"):
    a = load_arte("cartoon")
    who = (personagem or "").strip().rstrip(".")
    scene = prompt.strip().rstrip(".")
    full = (f"{who}, {scene}, {a['positivo']}, comic panel, no text"
            if who else f"{scene}, {a['positivo']}, comic panel, no text")
    imgclient.generate(full, out_png, model=model, width=GEN_W, height=GEN_H,
                       negative_prompt=a["negativo"])

def _spoken(panel):
    parts = []
    if panel.get("narracao"):
        parts.append(panel["narracao"].strip())
    if panel.get("fala"):
        parts.append(panel["fala"]["texto"].strip())
    return " ".join(parts).strip()

def _panel_clip(panel_png, wav, dur, out_mp4):
    frames = max(1, int(round(dur * FPS)))
    z = f"min(1.0+0.13*on/{frames},1.13)"  # push-in suave ate ~1.13x
    vf = (f"scale=2560:1440,zoompan=z='{z}':d=1:"
          f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS}")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error",
                    "-framerate", str(FPS), "-loop", "1", "-t", f"{dur:.3f}", "-i", panel_png,
                    "-i", wav, "-filter_complex", f"[0:v]{vf}[v]",
                    "-map", "[v]", "-map", "1:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out_mp4], check=True)

def _title_clip(text, out_mp4, secs=1.8, audio=None, voice="bella"):
    png = out_mp4 + ".png"
    html = ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
            '*{margin:0;padding:0}body{width:1280px;height:720px;background:#10141c;'
            'display:flex;align-items:center;justify-content:center;'
            'font-family:"Arial Black",Arial,sans-serif}'
            '.t{color:#fff;font-size:56px;font-weight:900;text-align:center;max-width:84%;line-height:1.18}'
            '.t small{display:block;color:#ffd23f;font-size:24px;letter-spacing:.2em;margin-bottom:18px}'
            '</style></head><body><div class="t">__T__</div></body></html>').replace("__T__", text)
    hp = out_mp4 + ".html"
    with open(hp, "w") as f:
        f.write(html)
    render_html_to_png(hp, png, W, H)
    cmd = ["ffmpeg", "-nostdin", "-y", "-v", "error", "-loop", "1"]
    if audio:
        wav = audio if os.path.exists(str(audio)) else out_mp4 + ".wav"
        if not os.path.exists(wav):
            say(audio, wav, voice=voice)
        dur = duration(wav) + 0.4
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-i", wav,
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}", "-af", "apad"]
    else:
        dur = secs
        cmd += ["-t", f"{dur:.3f}", "-i", png, "-f", "lavfi", "-t", f"{dur:.3f}",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                "-vf", f"scale={W}:{H},setsar=1,fps={FPS}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-ar", "44100", "-ac", "2", "-t", f"{dur:.3f}", out_mp4]
    subprocess.run(cmd, check=True)
    return out_mp4

def build_video(roteiro, out_dir="output", voice="bella", model="flux2-klein", intro=True):
    base = os.path.join(out_dir, roteiro["id"])
    panels_dir = os.path.join(base, "assets")
    clips_dir = os.path.join(base, "clips")
    os.makedirs(panels_dir, exist_ok=True)
    os.makedirs(clips_dir, exist_ok=True)
    personagem = roteiro.get("personagem", "")
    clips = []

    if intro:
        tc = os.path.join(clips_dir, "000-intro.mp4")
        _title_clip(f'<small>{_h.escape(roteiro.get("subtitulo","MOTION COMIC"))}</small>'
                    + _h.escape(roteiro["titulo"]), tc, secs=2.2)
        clips.append(tc)

    for pg in roteiro["paginas"]:
        pn = pg["n"]
        tc = os.path.join(clips_dir, f"{pn:02d}0-titulo.mp4")
        _title_clip(f'<small>PAGINA {pn}</small>{_h.escape(pg["titulo"])}', tc, secs=1.8)
        clips.append(tc)
        for idx, panel in enumerate(pg["paineis"], start=1):
            tag = f"p{pn:02d}q{idx}"
            img = os.path.join(panels_dir, f"{tag}.png")
            framed = os.path.join(panels_dir, f"{tag}-frame.png")
            wav = os.path.join(panels_dir, f"{tag}.wav")
            clip = os.path.join(clips_dir, f"{pn:02d}{idx}-{tag}.mp4")
            # per-panel character: "quem" overrides the protagonist; "" = no person
            char = panel["quem"] if "quem" in panel else personagem
            _gen_image(panel["prompt"], char, img, model=model)
            fala = panel["fala"]["texto"] if panel.get("fala") else None
            render_panel(img, framed, fala=fala, sfx=panel.get("sfx"))
            say(_spoken(panel), wav, voice=voice)
            _panel_clip(framed, wav, duration(wav), clip)
            clips.append(clip)

    listfile = os.path.join(base, "concat.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    out_mp4 = os.path.join(base, f"{roteiro['id']}.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", listfile, "-c", "copy", out_mp4], check=True)
    return out_mp4
