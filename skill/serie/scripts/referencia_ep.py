"""Referencia EFETIVA por episodio: canon da biblia + delta do episodio.

Quando um episodio muda algo de um personagem/objeto CANONICO (outra roupa, um
uniforme, um estado) ou define um cenario proprio (esta no RIACHO, nao na praia),
aqui a gente deriva a aparencia efetiva = canon + delta e a aplica em TODOS os
paineis do episodio — coerencia interna ao ep SEM perder o canon da biblia.

Dados (decisao de formato):
- CANON: na biblia (`protagonista.aparencia`, `elenco[].aparencia`,
  `elementos[].aparencia`) — fonte unica, nao se repete.
- DELTA (autoral): no proprio episodio:
    "variacoes": { "<id|nome da entidade>": "<clausula da mudanca>" }
    "cenario_padrao": "<ancora de mundo do episodio>"
- EFETIVO (derivado): resolvido aqui e persistido p/ rastreabilidade.

Determinismo total (sem rede) -> testavel.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import _deps  # noqa: E402
sys.path.insert(0, _deps.scripts("folder"))
from referencia import referencia_efetiva  # noqa: E402


def _norm(s):
    return (s or "").strip().lower()


def resolver_referencias(biblia, ep):
    """Resolve as aparencias EFETIVAS do episodio (canon + `variacoes` do ep).
    Retorna {protagonista, elenco:{nome:ap}, elementos:{nome:ap},
    elementos_list:[{nome,aparencia}], cenario_padrao}."""
    var = {_norm(k): v for k, v in (ep.get("variacoes") or {}).items()}
    prot = biblia.get("protagonista", {}) or {}
    prot_delta = next((var[_norm(k)] for k in (prot.get("id"), prot.get("nome"))
                       if _norm(k) in var), "")
    protagonista = referencia_efetiva(prot.get("aparencia", ""), prot_delta)

    elenco = {}
    for c in biblia.get("elenco", []) or []:
        elenco[c.get("nome", "")] = referencia_efetiva(
            c.get("aparencia", ""), var.get(_norm(c.get("nome")), ""))

    elementos, elementos_list = {}, []
    for el in (ep.get("elementos") or biblia.get("elementos", []) or []):
        ap = referencia_efetiva(el.get("aparencia", ""), var.get(_norm(el.get("nome")), ""))
        elementos[el.get("nome", "")] = ap
        elementos_list.append({"nome": el.get("nome", ""), "aparencia": ap})

    return {"protagonista": protagonista, "elenco": elenco,
            "elementos": elementos, "elementos_list": elementos_list,
            "cenario_padrao": (ep.get("cenario_padrao") or "").strip()}


def aplicar(ep, biblia):
    """Retorna um NOVO ep com as referencias efetivas aplicadas: `personagem` =
    protagonista efetivo; `elementos` efetivos; `quem` de painel que CASA um nome
    do elenco/protagonista vira a aparencia efetiva; e o `cenario_padrao` do ep e
    dobrado no fim de cada `prompt` (ancora de mundo: riacho != praia). Guarda o
    resolvido em `referencias_efetivas`. PURO: nao muta o ep de entrada
    (idempotente em re-render)."""
    refs = resolver_referencias(biblia, ep)
    out = copy.deepcopy(ep)
    out["personagem"] = refs["protagonista"]
    out["elementos"] = refs["elementos_list"]

    nomes = {_norm(k): v for k, v in refs["elenco"].items()}
    prot = biblia.get("protagonista", {}) or {}
    for k in (prot.get("id"), prot.get("nome")):
        if k:
            nomes[_norm(k)] = refs["protagonista"]

    cen = refs["cenario_padrao"]
    for pg in out.get("paginas", []):
        for p in pg.get("paineis", []):
            q = p.get("quem")
            if q and _norm(q) in nomes:
                p["quem"] = nomes[_norm(q)]
            if cen:
                base = (p.get("prompt") or "").strip().rstrip(".")
                p["prompt"] = f"{base}, {cen}" if base else cen

    out["referencias_efetivas"] = {"protagonista": refs["protagonista"],
                                   "elenco": refs["elenco"], "elementos": refs["elementos"],
                                   "cenario_padrao": cen}
    return out
