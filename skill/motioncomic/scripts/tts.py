"""Narração via daemon inemavox (Chatterbox-VC) — POST /tts/vc -> mp3 -> wav."""
import json, os, subprocess, urllib.request, urllib.error

DAEMON = os.environ.get("INEMAVOX_TTS_URL", "http://127.0.0.1:7860")

def say(text, out_wav, voice="bella"):
    """Gera narração e salva como wav 44.1k estéreo. Retorna o caminho."""
    body = json.dumps({"text": text, "voice": voice, "lang": "pt", "bitrate": "128k"}).encode()
    req = urllib.request.Request(DAEMON + "/tts/vc", data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    last = None
    mp3 = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                mp3 = r.read()
            break
        except urllib.error.URLError as e:
            last = e
    if mp3 is None:
        raise last
    tmp = out_wav + ".mp3"
    with open(tmp, "wb") as f:
        f.write(mp3)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", tmp,
                    "-ar", "44100", "-ac", "2", out_wav], check=True)
    os.remove(tmp)
    return out_wav

def duration(wav):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", wav], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())
