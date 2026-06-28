# skill/serie/scripts/revisar_acentos.py
"""Checagem/correcao de ACENTUACAO PT-BR do texto NARRADO, ANTES do TTS.

Roda SEMPRE no build_serie (como o lint_paineis). Objetivo: a narracao (voz do
inemavox) nunca sair errada por falta de acento — sem acento o TTS pronuncia errado.

Estrategia conservadora e deterministica (sem rede/LLM):
  - CORRIGE automaticamente palavras que NAO existem como palavra valida sem o
    acento (ex.: "nao"->"nao", "voce"->"voce", "agua"->"agua", "vulcao"->"vulcao"):
    risco ~zero, preserva a CAIXA (minuscula/Inicial/MAIUSCULA).
  - AVISA (conta, sem alterar) sobre formas AMBIGUAS, que existem com e sem acento
    (ex.: "esta"=esta/esta, "pos"=pos/pos): so o autor/uma revisao decide.

So atua nos campos NARRADOS/EXIBIDOS (abertura, titulo, chamada, narracao,
fala.texto); NUNCA em prompt/quem/usa/sfx. Idempotente (texto ja correto nao muda).
"""
import re

# unaccented -> accented: palavra INVALIDA sem o acento => SEGURO auto-corrigir.
_MAP = {
    # nasais / ~ao
    "nao": "não", "entao": "então", "tao": "tão", "irmao": "irmão", "irmaos": "irmãos",
    "mao": "mão", "maos": "mãos", "pao": "pão", "paes": "pães", "chao": "chão",
    "cao": "cão", "caes": "cães", "leao": "leão", "leoes": "leões", "graos": "grãos",
    "verao": "verão", "veroes": "verões", "vulcao": "vulcão", "vulcoes": "vulcões",
    "coracao": "coração", "coracoes": "corações", "manha": "manhã", "amanha": "amanhã",
    "mae": "mãe", "maes": "mães", "irma": "irmã", "irmas": "irmãs",
    "licao": "lição", "licoes": "lições", "estacao": "estação", "estacoes": "estações",
    "atencao": "atenção", "protecao": "proteção", "invencao": "invenção",
    "direcao": "direção", "racao": "ração", "feicao": "feição",
    "calorao": "calorão", "barracao": "barracão", "casacao": "casacão", "casacoes": "casacões",
    # cedilha
    "fumaca": "fumaça", "fumacas": "fumaças", "bagunca": "bagunça", "lamacal": "lamaçal",
    # acentos agudos/circunflexos comuns
    "voce": "você", "voces": "vocês", "ceu": "céu", "ceus": "céus",
    "chapeu": "chapéu", "chapeus": "chapéus", "heroi": "herói", "herois": "heróis",
    "agua": "água", "aguas": "águas", "tambem": "também", "ate": "até", "tres": "três",
    "porem": "porém", "alem": "além", "ninguem": "ninguém", "alguem": "alguém",
    "ja": "já", "so": "só", "la": "lá", "ca": "cá", "pe": "pé", "pes": "pés",
    "ta": "tá", "to": "tô",   # informal de esta/estou (invalido sem acento -> seguro)
    "sitio": "sítio", "silencio": "silêncio", "silencios": "silêncios",
    "lingua": "língua", "linguas": "línguas", "musica": "música", "musicas": "músicas",
    "lampada": "lâmpada", "lampadas": "lâmpadas", "arvore": "árvore", "arvores": "árvores",
    "ultimo": "último", "ultima": "última", "ultimos": "últimos", "ultimas": "últimas",
    "proximo": "próximo", "proxima": "próxima", "rapido": "rápido", "rapida": "rápida",
    "facil": "fácil", "dificil": "difícil", "util": "útil", "obvio": "óbvio",
    "magico": "mágico", "magica": "mágica", "fragil": "frágil", "comecar": "começar",
    "amigao": "amigão", "grandao": "grandão", "devagar": "devagar",
}
# "voo"/"ia"/"devagar" entram so como guarda (nao mudam); remove os no-op.
for _k in ("voo", "ia", "devagar"):
    if _MAP.get(_k) == _k:
        _MAP.pop(_k, None)

# formas que TAMBEM existem sem acento -> so AVISA (nunca auto-corrige): o sentido
# decide (ex.: "esta casa" vs "ela esta"). Funcao-palavra ultra-frequente (e/de/da/
# para/por) fica DE FORA p/ nao virar ruido.
_AMBIGUOS = {"esta", "estao", "pos", "secretaria", "duvida", "fabrica", "pratica",
             "publico", "medico", "numero", "sabia", "habito", "duvidas"}

_PAL = re.compile(r"[0-9A-Za-zÀ-ÿ]+")


def _aplica_caixa(orig: str, novo: str) -> str:
    if orig.isupper():
        return novo.upper()
    if orig[:1].isupper():
        return novo[:1].upper() + novo[1:]
    return novo


def corrigir(texto: str):
    """Retorna (texto_corrigido, trocas, suspeitas).
    - trocas: lista de (original, corrigido) aplicadas automaticamente.
    - suspeitas: lista de palavras AMBIGUAS encontradas (so aviso, nao alteradas)."""
    if not texto:
        return texto, [], []
    trocas, suspeitas = [], []

    def repl(m):
        w = m.group(0)
        low = w.lower()
        if low in _MAP:
            novo = _aplica_caixa(w, _MAP[low])
            if novo != w:
                trocas.append((w, novo))
            return novo
        if low in _AMBIGUOS:
            suspeitas.append(w)
        return w

    return _PAL.sub(repl, texto), trocas, suspeitas


# campos NARRADOS/EXIBIDOS que podem ser corrigidos (nunca prompt/quem/usa/sfx).
def _corrige_campo(d: dict, chave: str, rel: dict):
    if isinstance(d.get(chave), str):
        novo, trocas, susp = corrigir(d[chave])
        if trocas:
            d[chave] = novo
            rel["trocas"].extend(trocas)
        rel["suspeitas"].extend(susp)


def revisar_episodio(ep: dict) -> dict:
    """Corrige a acentuacao dos campos narrados de UM episodio, IN-PLACE. Retorna
    relatorio {'trocas': [(orig,novo)...], 'suspeitas': [palavra...]}. Idempotente."""
    rel = {"trocas": [], "suspeitas": []}
    _corrige_campo(ep, "abertura", rel)
    _corrige_campo(ep, "titulo", rel)
    for pg in ep.get("paginas", []):
        _corrige_campo(pg, "titulo", rel)
        _corrige_campo(pg, "chamada", rel)
        for painel in pg.get("paineis", []):
            _corrige_campo(painel, "narracao", rel)
            fala = painel.get("fala")
            if isinstance(fala, dict):
                _corrige_campo(fala, "texto", rel)
            elif isinstance(fala, str):
                _corrige_campo(painel, "fala", rel)
    return rel
