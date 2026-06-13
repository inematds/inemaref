import os, sys, json, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import forma_c

def _fake_assets(d):
    """Cria assets/pNNqN.png + .wav vazios p/ 2 paginas x 6 paineis."""
    a = os.path.join(d, "assets"); os.makedirs(a, exist_ok=True)
    for pn in (1, 2):
        for q in range(1, 7):
            open(os.path.join(a, f"p{pn:02d}q{q}.png"), "wb").close()
            open(os.path.join(a, f"p{pn:02d}q{q}.wav"), "wb").close()
    return a

ROT = {
    "id": "demo-ep01", "n": 1, "titulo": "Um Titulo",
    "abertura": "Gancho de abertura.", "subtitulo": "subt",
    "paginas": [
        {"n": 1, "titulo": "P1", "paineis": [{"prompt": f"cena {i}"} for i in range(1, 7)]},
        {"n": 2, "titulo": "P2", "paineis": [{"prompt": f"cena {i}"} for i in range(7, 13)]},
    ],
}

def test_coletor_encena_em_ordem(tmp="/tmp/_forma_c_col"):
    shutil.rmtree(tmp, ignore_errors=True)
    src = _fake_assets(os.path.join(tmp, "src"))
    stage = os.path.join(tmp, "stage")
    man = forma_c.coletar_forma_c(ROT, src, stage)
    # 12 paineis -> s01..s12, encenados em img/ e audio/
    assert len(man["imagens"]) == 12 and len(man["narracoes"]) == 12
    assert os.path.exists(os.path.join(stage, "assets", "img", "s01.png"))
    assert os.path.exists(os.path.join(stage, "assets", "img", "s12.png"))
    assert os.path.exists(os.path.join(stage, "assets", "audio", "s01.wav"))
    # ordem de leitura: p01q1..p01q6, p02q1..p02q6
    assert man["narracoes"][0].endswith("s01.wav")
    assert man["narracoes"][6].endswith("s07.wav")   # 1o painel da pagina 2
    # manifesto persistido + meta
    saved = json.load(open(os.path.join(stage, "forma-c.json")))
    assert saved["meta"]["titulo"] == "Um Titulo"
    assert saved["meta"]["abertura"] == "Gancho de abertura."
    assert saved["cenas"][6]["origem"] == "p02q1"      # rastreabilidade
    # bloco de direcao p/ o diretor-animacao nao cair no default sutil
    assert saved["meta"]["direcao"]["energia"] == "media"   # sem genero -> neutro
    assert "multi-shot" in saved["meta"]["direcao"]["nota"]


def test_direcao_energia_por_genero():
    aventura = dict(ROT, genero="aventura")
    contempl = dict(ROT, tom="contemplativo")
    assert forma_c._energia_do_roteiro(aventura) == "alta"
    assert forma_c._energia_do_roteiro(contempl) == "baixa"
    # override explicito vence o genero
    assert forma_c._energia_do_roteiro(aventura, energia="baixa") == "baixa"

def test_coletor_falta_wav_erro(tmp="/tmp/_forma_c_falta"):
    shutil.rmtree(tmp, ignore_errors=True)
    src = _fake_assets(os.path.join(tmp, "src"))
    os.remove(os.path.join(src, "p01q3.wav"))          # remove uma narracao
    stage = os.path.join(tmp, "stage")
    try:
        forma_c.coletar_forma_c(ROT, src, stage)
        assert False, "deveria ter levantado erro de wav faltando"
    except FileNotFoundError as e:
        assert "p01q3" in str(e)

def test_naming_letra_c_antes_do_ep():
    nome = forma_c.forma_c_out_name("teo-e-o-guardiao-da-noite", 1, "A Noite do Susto")
    assert nome == "teo-e-o-guardiao-da-noite-c-ep01-a-noite-do-susto.mp4"

def _fake_clip(path, secs):
    import subprocess
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error",
                    "-f", "lavfi", "-t", str(secs), "-i", "color=c=black:s=1280x720:r=30",
                    "-f", "lavfi", "-t", str(secs),
                    "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "aac", "-ar", "44100", "-ac", "2", "-shortest", path], check=True)

def _dur(p):
    import subprocess
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=nk=1:nw=1", p],
        capture_output=True, text=True).stdout.strip())

def test_wrapper_envolve_miolo(tmp="/tmp/_forma_c_wrap"):
    import shutil
    shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    miolo = os.path.join(tmp, "miolo.mp4"); _fake_clip(miolo, 4.0)
    out = os.path.join(tmp, "final.mp4")
    forma_c.wrap_forma_c(miolo, out, abertura="Gancho de teste.",
                         titulo="Titulo", subtitulo="sub", voice="bella")
    assert os.path.exists(out)
    # final > miolo (ganhou intro + cta)
    assert _dur(out) > _dur(miolo) + 1.0
    # tem video E audio
    import subprocess
    streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
        "stream=codec_type", "-of", "default=nk=1:nw=1", out],
        capture_output=True, text=True).stdout
    assert "video" in streams and "audio" in streams

if __name__ == "__main__":
    test_coletor_encena_em_ordem()
    test_direcao_energia_por_genero()
    test_coletor_falta_wav_erro()
    test_naming_letra_c_antes_do_ep()
    test_wrapper_envolve_miolo()
    print("OK coletor")
