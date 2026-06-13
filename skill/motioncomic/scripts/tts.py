"""Narração via daemon inemavox (Chatterbox-VC) — POST /tts/vc -> mp3 -> wav.

Antes de chegar ao TTS o texto passa por uma REVISAO leve (`revisar_narracao`):
colapsa espacos, garante pontuacao final (prosodia/entonacao) e aplica o LEXICO
de pronuncia `pronuncias.json` — termos em ingles/outra lingua viram uma
regravacao fonetica em PT para o TTS pt aproximar o som original em vez de
soletrar a forma escrita. `revisar_ortografia` e um LINT opcional (nao muta) pra
revisar o roteiro antes de gerar a voz.
"""
import json, os, re, subprocess, urllib.request, urllib.error

DAEMON = os.environ.get("INEMAVOX_TTS_URL", "http://127.0.0.1:7860")
_LEXICO_PATH = os.environ.get(
    "INEMAVOX_LEXICO",
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "pronuncias.json"))
_lexico_cache = None
_FIM_FRASE = ".!?…:;)\"'"


def carregar_lexico(path=None):
    """Carrega o lexico {termo: regravacao} de `pronuncias.json`. Chaves com _
    sao ignoradas (meta). Tolerante: arquivo ausente/invalido -> {}. O lexico
    padrao e cacheado em memoria."""
    global _lexico_cache
    usar_cache = path is None
    if usar_cache and _lexico_cache is not None:
        return _lexico_cache
    alvo = path or _LEXICO_PATH
    try:
        with open(alvo, encoding="utf-8") as f:
            data = json.load(f)
        lex = {k: v for k, v in data.items() if not k.startswith("_")}
    except (OSError, ValueError):
        lex = {}
    if usar_cache:
        _lexico_cache = lex
    return lex


def aplicar_pronuncias(text, lexico=None):
    """Troca cada termo do lexico pela regravacao fonetica, casando PALAVRA
    INTEIRA e ignorando caixa (Design/design/DESIGN -> regravacao). Termos mais
    longos primeiro (evita casar prefixo). `lexico` explicito pula o arquivo."""
    lex = carregar_lexico() if lexico is None else lexico
    if not lex or not text:
        return text
    for termo in sorted(lex, key=len, reverse=True):
        # \b falha com acento; usa lookaround de caractere-de-palavra (unicode)
        pat = re.compile(rf"(?<!\w){re.escape(termo)}(?!\w)", re.IGNORECASE | re.UNICODE)
        text = pat.sub(lambda _m, r=lex[termo]: r, text)
    return text


def revisar_narracao(text, lexico=None):
    """REVISAO leve aplicada ANTES do TTS: colapsa espacos em branco, aplica o
    lexico de pronuncia e garante pontuacao final (entonacao de fim de frase).
    NAO corrige acentuacao (ver `revisar_ortografia`). Retorna o texto pronto."""
    if not text:
        return text
    text = re.sub(r"\s+", " ", text).strip()
    text = aplicar_pronuncias(text, lexico)
    if text and text[-1] not in _FIM_FRASE:
        text += "."
    return text


def revisar_ortografia(text):
    """LINT opcional (NAO muta) p/ revisar o roteiro antes de narrar: retorna a
    lista de avisos — pontuacao final ausente, espacos duplos e, se a lib
    `spellchecker` (pyspellchecker) estiver instalada, palavras desconhecidas em
    PT (candidatas a estar sem acento). Degrada sem a lib. Lista vazia = ok."""
    if not text or not text.strip():
        return ["texto vazio"]
    avisos = []
    if text.strip()[-1] not in _FIM_FRASE:
        avisos.append("sem pontuacao final")
    if "  " in text:
        avisos.append("espacos duplos")
    try:
        from spellchecker import SpellChecker
        sp = SpellChecker(language="pt")
        palavras = [w.lower() for w in re.findall(r"[^\W\d_]+", text, re.UNICODE) if len(w) > 3]
        lex = {k.lower() for k in carregar_lexico()}
        suspeitas = sorted(w for w in sp.unknown(palavras) if w not in lex)
        if suspeitas:
            avisos.append("palavras suspeitas (acentuacao?): " + ", ".join(suspeitas[:15]))
    except Exception:
        pass
    return avisos


def say(text, out_wav, voice="bella"):
    """Gera narração e salva como wav 44.1k estéreo. Retorna o caminho. O texto
    passa por `revisar_narracao` (lexico de pronuncia + pontuacao) antes do TTS."""
    text = revisar_narracao(text)
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
