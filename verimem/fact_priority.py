"""R45: Composite priority score combining confidence + freshness + corroboration.

Priority = 0.5 * confidence + 0.3 * freshness + 0.2 * corroboration
"""
from __future__ import annotations

import re
import time
from typing import Any

from .fact_contract import fact_payload

_TOKEN_RE = re.compile(r"[A-Za-z0-9_\-]+")
_DAY = 86400.0


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "")}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _freshness(fact: Any, now: float, half_life_days: float) -> float:
    created = float(getattr(fact, "created_at", now))
    age_days = max(0.0, (now - created) / _DAY)
    return 0.5 ** (age_days / half_life_days) if half_life_days > 0 else 1.0


def _quantita_divergono(qa: set[tuple[str, float]],
                        qb: set[tuple[str, float]]) -> bool:
    """Esiste un'unita' presente in ENTRAMBI con valori diversi?

    Non e' una stima di somiglianza: se un fatto dice «100 euro» e l'altro
    «500 euro», si contraddicono. Un'unita' presente da una parte sola non e'
    un conflitto — e' un'aggiunta.
    """
    if not qa or not qb:
        return False
    per_unita: dict[str, set[float]] = {}
    for unita, valore in qa:
        per_unita.setdefault(unita, set()).add(valore)
    for unita, valore in qb:
        se_ne_sa = per_unita.get(unita)
        if se_ne_sa and valore not in se_ne_sa:
            return True
    return False


def _corroboration(fact: Any, others: list[Any], threshold: float,
                   quantita: dict[str, set[tuple[str, float]]] | None = None) -> float:
    """Quante ALTRE proposizioni confermano questa.

    DUE FATTI CHE SI CONTRADDICONO NON SI CONFERMANO. Il conto guardava solo il
    Jaccard sui token, ma un overlap lessicale alto e' esattamente il segnale
    che altrove nel prodotto significa CONFLITTO: due frasi che parlano della
    stessa cosa. Misurato il 2026-08-04, tre coppie che si contraddicono
    prendevano `corroboration=0.200` e priorita' 0.590, mentre una coppia che si
    conferma davvero (parole diverse) prendeva 0.000 e 0.550 — il conto era
    ROVESCIATO, e `client.py` chiama questo termine «confirmations by
    independent sources».

    Per il caso numerico la correzione e' LOGICA e non euristica, e usa cio' che
    il prodotto ha gia': `quantity_match.extract_quantities` legge «100 euro» e
    «500 euro» come valori diversi della stessa unita'.

    ⛔ NON copre il caso non numerico («PostgreSQL» contro «MySQL»): li'
    servirebbe sapere che sono valori alternativi dello stesso attributo. E non
    copre il difetto SIMMETRICO — una conferma parafrasata ha Jaccard basso e
    prende 0.0. Si tolgono i falsi positivi che si sanno riconoscere; i falsi
    negativi restano.
    """
    ftok = _tokens(getattr(fact, "proposition", ""))
    if not ftok:
        return 0.0
    fid = getattr(fact, "id", "")
    mie = (quantita or {}).get(fid, set())
    matches = 0
    for o in others:
        oid = getattr(o, "id", "")
        if oid == fid:
            continue
        if _jaccard(ftok, _tokens(getattr(o, "proposition", ""))) < threshold:
            continue
        if _quantita_divergono(mie, (quantita or {}).get(oid, set())):
            continue
        matches += 1
    return min(1.0, matches * 0.2)


def rank_facts_by_priority(
    facts: list[Any],
    *,
    now: float | None = None,
    half_life_days: float = 180.0,
    corr_threshold: float = 0.5,
    top_k: int = 50,
) -> dict[str, Any]:
    """Rank facts by composite priority."""
    if now is None:
        now = time.time()

    # Le quantita' UNA VOLTA per fatto e non per coppia: il conto e' gia'
    # quadratico sui confronti, e non deve diventarlo anche sull'estrazione.
    from .quantity_match import extract_quantities
    quantita: dict[str, set[tuple[str, float]]] = {}
    for f in facts:
        try:
            quantita[getattr(f, "id", "")] = extract_quantities(
                getattr(f, "proposition", "") or "")
        except Exception:  # noqa: BLE001 — un'estrazione fallita non vale un rank perso
            quantita[getattr(f, "id", "")] = set()

    ranked: list[dict[str, Any]] = []
    for f in facts:
        conf = float(getattr(f, "confidence", 0.0) or 0.0)
        fresh = _freshness(f, now, half_life_days)
        corr = _corroboration(f, facts, corr_threshold, quantita)
        priority = 0.5 * conf + 0.3 * fresh + 0.2 * corr
        # 2026-07-30: contratto unico + le chiavi proprie di questa vista.
        # Una priorita' calcolata da confidenza/freschezza/corroborazione
        # senza il verdetto accanto si legge come se il moat fosse gia' dentro
        # il conto, e non c'e'.
        ranked.append({
            **fact_payload(f),
            "proposition": getattr(f, "proposition", "")[:80],
            "priority": round(min(1.0, priority), 4),
            "components": {
                "confidence": round(conf, 3),
                "freshness": round(fresh, 3),
                "corroboration": round(corr, 3),
            },
        })
    ranked.sort(key=lambda r: -r["priority"])
    return {
        "ranked": ranked[:top_k],
        "n_facts_scanned": len(facts),
    }


__all__ = ["rank_facts_by_priority"]
