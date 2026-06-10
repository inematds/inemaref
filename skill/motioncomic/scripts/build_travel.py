"""Motion comic — modo CAMERA-SOBRE-A-PAGINA (docs/02).

Em vez de cortar entre imagens isoladas, COMPOE a pagina (quadros empilhados) e
MOVE a camera sobre ela: enquadra+zooma cada quadro durante a sua narracao e
DESLIZA (glide) para o proximo. Reaproveita quadros/narracoes ja gerados.
"""
import os, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
from build_motion import _gen_image, _spoken, _title_clip, FPS  # noqa: E402
from overlay import render_panel  # noqa: E402
from tts import say, duration     # noqa: E402

PW, PH = 1280, 720   # cada quadro
GLIDE = 0.7          # duracao do deslize entre quadros

def _ensure_assets(panel, char, img, framed, wav, model):
    if not os.path.exists(framed):
        if not os.path.exists(img):
            _gen_image(panel["prompt"], char, img, model=model)
        fala = panel["fala"]["texto"] if panel.get("fala") else None
        render_panel(img, framed, fala=fala, sfx=panel.get("sfx"))
    if not os.path.exists(wav):
        say(_spoken(panel), wav)

def _compose_page(framed_list, page_png):
    ins = []
    for p in framed_list:
        ins += ["-i", p]
    n = len(framed_list)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", *ins,
                    "-filter_complex", f"{''.join('['+str(i)+']' for i in range(n))}vstack=inputs={n}",
                    "-frames:v", "1", page_png], check=True)

def _hold(page_png, y, dur, wav, out_mp4):
    z = f"min(1+0.05*on/{max(1,int(dur*FPS))},1.05)"
    vf = (f"[0:v]crop={PW}:{PH}:0:{y},scale={PW*2}:{PH*2},"
          f"zoompan=z='{z}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={PW}x{PH}:fps={FPS}[v]")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-framerate", str(FPS), "-loop", "1",
                    "-t", f"{dur:.3f}", "-i", page_png, "-i", wav, "-filter_complex", vf,
                    "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-r", str(FPS), "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out_mp4], check=True)

def _glide(page_png, y0, y1, out_mp4):
    u = f"(t/{GLIDE})"
    yexpr = f"{y0}+({y1}-{y0})*({u}*{u}*(3-2*{u}))"  # smoothstep
    vf = f"[0:v]crop={PW}:{PH}:0:'{yexpr}'[v]"
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-framerate", str(FPS), "-loop", "1",
                    "-t", f"{GLIDE:.3f}", "-i", page_png, "-f", "lavfi", "-t", f"{GLIDE:.3f}",
                    "-i", "anullsrc=r=44100:cl=stereo", "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", out_mp4], check=True)

def build_video_travel(roteiro, out_dir="output", voice="bella", model="flux2-klein", intro=True):
    import html as _h
    base = os.path.join(out_dir, roteiro["id"])
    assets = os.path.join(base, "assets")
    clips_dir = os.path.join(base, "clips")
    os.makedirs(assets, exist_ok=True)
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

        framed_list, wavs = [], []
        for idx, panel in enumerate(pg["paineis"], start=1):
            tag = f"p{pn:02d}q{idx}"
            img = os.path.join(assets, f"{tag}.png")
            framed = os.path.join(assets, f"{tag}-frame.png")
            wav = os.path.join(assets, f"{tag}.wav")
            char = panel["quem"] if "quem" in panel else personagem
            _ensure_assets(panel, char, img, framed, wav, model)
            framed_list.append(framed)
            wavs.append(wav)

        page_png = os.path.join(assets, f"page{pn:02d}.png")
        _compose_page(framed_list, page_png)
        ys = [i * PH for i in range(len(framed_list))]
        for i in range(len(framed_list)):
            h = os.path.join(clips_dir, f"{pn:02d}{i+1}-hold.mp4")
            _hold(page_png, ys[i], duration(wavs[i]), wavs[i], h)
            clips.append(h)
            if i < len(framed_list) - 1:
                g = os.path.join(clips_dir, f"{pn:02d}{i+1}-glide.mp4")
                _glide(page_png, ys[i], ys[i + 1], g)
                clips.append(g)

    listfile = os.path.join(base, "concat-travel.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    out_mp4 = os.path.join(base, f"{roteiro['id']}-travel.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", listfile, "-c", "copy", out_mp4], check=True)
    return out_mp4
