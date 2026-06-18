# skill/motioncomic/scripts/visao_decupagem.py
"""
Schema/validador do plano de cobertura da Forma C.
Sem dependências externas — Python 3 puro.
"""

TIPOS_VALIDOS = {"wide", "close", "insert", "pan", "tilt"}


def _clamp(v, lo, hi):
    return max(lo, min(hi, float(v)))


def validar_shots(shots):
    """
    Normaliza/valida uma lista de shots.

    Levanta ValueError se shots não for lista não-vazia.
    Cada shot (dict) é normalizado:
      - "tipo": deve estar em TIPOS_VALIDOS; senão ValueError.
      - "at": [x, y] clampado para [0.0, 1.0]; ausente → [0.5, 0.5].
      - "zoom": float clampado para [1.0, 3.0]; ausente → 1.0.
      - "peso": float > 0; ausente ou <= 0 → 1.0.
      - "direction": mantém se presente, senão omite.

    Retorna nova lista com shots normalizados (mesma ordem).
    """
    if not isinstance(shots, list) or len(shots) == 0:
        raise ValueError("shots deve ser uma lista não-vazia")

    result = []
    for i, shot in enumerate(shots):
        tipo = shot.get("tipo")
        if tipo not in TIPOS_VALIDOS:
            raise ValueError(
                f"shot[{i}] tipo inválido: {tipo!r}. Válidos: {TIPOS_VALIDOS}"
            )

        raw_at = shot.get("at", [0.5, 0.5])
        at = [_clamp(raw_at[0], 0.0, 1.0), _clamp(raw_at[1], 0.0, 1.0)]

        zoom = _clamp(shot.get("zoom", 1.0), 1.0, 3.0)

        raw_peso = shot.get("peso", 1.0)
        peso = float(raw_peso) if float(raw_peso) > 0 else 1.0

        normalized = {
            "tipo": tipo,
            "at": at,
            "zoom": zoom,
            "peso": peso,
        }
        if "direction" in shot:
            normalized["direction"] = shot["direction"]

        result.append(normalized)

    return result


def contexto_do_painel(ep, sid):
    """
    ep: dict do roteiro com paginas[].paineis[].
    sid: "sNN" (1-based) na ordem de leitura achatada.
    Retorna string com narracao + falas + sfx do painel, ou "" se fora do range.
    """
    # Converte "s07" → índice 6 (0-based)
    try:
        idx = int(sid.lstrip("s")) - 1
    except (ValueError, AttributeError):
        return ""

    # Achata todos os paineis em ordem
    paineis = []
    for pagina in ep.get("paginas", []):
        paineis.extend(pagina.get("paineis", []))

    if idx < 0 or idx >= len(paineis):
        return ""

    painel = paineis[idx]
    partes = []

    narracao = painel.get("narracao", "")
    if narracao:
        partes.append(narracao)

    for fala in painel.get("falas", []):
        texto = fala.get("texto", "")
        if texto:
            partes.append(texto)

    sfx = painel.get("sfx", "")
    if sfx:
        partes.append(sfx)

    return " ".join(partes)
