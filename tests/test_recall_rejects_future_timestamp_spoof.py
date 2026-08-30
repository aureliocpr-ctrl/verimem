"""TDD anti-spoof — buco #3b (stessa classe del buco #1 writer_role):
`last_verified_at` e' un campo che GOVERNA la freschezza e store() si fida del
valore del CALLER (semantic.py store: lv_at = fact.last_verified_at se settato).

EXPLOIT: un client salva un Fact con last_verified_at NEL FUTURO. Allora
`age_days = (now - last_verified_at) / 86400` e' NEGATIVO; freshness.decay_factor
(freshness.py:22) con `age_days <= 0` ritorna 1.0 -> is_stale sempre False ->
il fatto NON SCADE MAI -> il cutoff freshness (#3) e' aggirato.

Principio (verbatim Aurelio): un campo che governa freschezza/fiducia non deve
MAI fidarsi del valore del caller. Un timestamp di verifica nel FUTURO e'
impossibile -> e' un segnale di manomissione -> fail-closed = stale/escluso.

Questo test FALLISCE oggi (pre-fix): il fatto spoof con lv nel futuro viene
ritornato dal recall. Diventa GREEN col fail-closed su `base > now` in
_fact_is_stale (legacy path) + nella maschera numpy (cache path).

HERMETIC: SemanticMemory su tmp_path, MAI il DB reale.
"""
from __future__ import annotations

import time

from verimem.semantic import Fact, SemanticMemory

_TEN_YEARS_S = 10 * 365 * 24 * 3600
_TOPIC = "capability/test"  # fuori dalla telemetry-denylist.
_QUERY = "does capability X still work via the /foo endpoint"


def _seed(sm: SemanticMemory) -> tuple[str, str]:
    now = time.time()
    fresh = Fact(
        id="fresh01",
        proposition="Capability X works: the /foo endpoint returns 200 OK.",
        topic=_TOPIC,
        created_at=now,
    )
    # SPOOF: il caller mette last_verified_at nel FUTURO per restare "fresco
    # per sempre" e bypassare il decadimento temporale del buco #3.
    spoof = Fact(
        id="spoof01",
        proposition="Capability X works: the /foo endpoint returns 200 OK.",
        topic=_TOPIC,
        created_at=now,
        last_verified_at=now + _TEN_YEARS_S,
    )
    sm.store(fresh)
    sm.store(spoof)
    return fresh.id, spoof.id


def test_cache_path_rejects_future_last_verified_at(tmp_path) -> None:
    """Cache fast-path (topic=None)."""
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fresh_id, spoof_id = _seed(sm)

    ids = [f.id for f, _sim in sm.recall(_QUERY, k=5)]

    assert fresh_id in ids, f"setup rotto: fresco assente (ids={ids})"
    assert spoof_id not in ids, (
        f"spoof #3b: recall ha ritornato un fatto con last_verified_at nel "
        f"futuro (id={spoof_id}) -> freschezza falsificata dal caller. ids={ids}"
    )


def test_legacy_path_rejects_future_last_verified_at(tmp_path) -> None:
    """Legacy SQL path (topic esplicito)."""
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fresh_id, spoof_id = _seed(sm)

    ids = [f.id for f, _sim in sm.recall(_QUERY, k=5, topic=_TOPIC)]

    assert fresh_id in ids, f"setup rotto: fresco assente legacy (ids={ids})"
    assert spoof_id not in ids, (
        f"spoof #3b (legacy path): recall ha ritornato un fatto con "
        f"last_verified_at nel futuro (id={spoof_id}). ids={ids}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-31: LA TERZA PORTA — `deep`, che il file non nominava.
#
# Lo schema MCP di `hippo_facts_recall` descrive `deep` come *«v14 ARCHAEOLOGY
# mode: lift the 45-day age-based hiding … Integrity guards stay (future
# timestamp = tamper, valid_until hard-expire)»*. La promessa ha DUE meta', e
# la seconda e' quella che rende la prima non banale: un `deep` che facesse
# riemergere tutto sarebbe facile e sbagliato.
#
# 🚨 CORREZIONE, 01:22 — LA COPERTURA ESISTEVA GIA' ALTROVE, e questa cella NON
# colma un buco. `tests/test_deep_recall_asof.py::test_deep_keeps_integrity_guards`
# fa gia' la stessa asserzione (spoof con transaction time futuro escluso con
# `deep=True`, piu' `valid_until` scaduto). Quando ho aggiunto questa cella
# avevo sweepato SOLO questo file e avevo scritto sul canale «nessuna cella
# nomina `deep`»: vero di questo file, falso del repo. ⚠️ E' la classe che
# avevo citato un'ora prima — *manca lo sweep: chi ALTRO fa la stessa cosa?* —
# commessa mentre la citavo.
# ⚖️ PERCHE' LA CELLA RESTA: localizzazione, non copertura. Chi apre il file
# dello spoof per capire quanto sia difesa la guardia trova qui anche il caso
# `deep`, senza dover sapere dell'altro file. Il valore e' quello, ed e'
# dichiarato: se un giorno pesasse piu' del suo costo, si toglie questa e resta
# quella.
#
# I due test qui sopra presidiano la guardia nei due percorsi di recall in
# regime NORMALE. Misurato il 2026-08-31 alle 01:13, store temporaneo, tre
# fatti con tre soggetti distinti e le date spostate via SQL diretto — lo
# scenario che il docstring di `_fact_is_stale` rivendica esplicitamente di
# coprire («per QUALSIASI path di scrittura: store, SQL diretto, migrazione»),
# e che l'altro file NON esercita (li' le date si scrivono via `Fact(...)`)::
#
#     senza deep   torna solo il fatto recente
#     con deep     torna anche il dormiente (200 giorni), NON quello futuro
#
# ⇒ La promessa regge in entrambe le meta'.
#
# 🪞 E vale la pena scriverlo: la prima misura diceva il CONTRARIO — che il
# fatto futuro riemergesse con `deep`. Era un difetto del misuratore (il token
# che riconosceva i fatti nella risposta era «di», una preposizione presente in
# tutti). Il sospetto e' nato dal contrasto con la lettura del sorgente, dove
# `base > now` precede `ignore_age` e non e' scavalcabile. **Quando la misura
# contraddice una lettura netta, il primo indiziato e' la misura.**
# Banco: docs/stato-reale/banchi/ws3-l-archeologia-e-le-due-guardie.py


def test_archaeology_mode_still_rejects_future_last_verified_at(tmp_path) -> None:
    """`deep` lifta l'ETA', non l'INTEGRITA'."""
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fresh_id, spoof_id = _seed(sm)

    ids = [f.id for f, _sim in sm.recall(_QUERY, k=5, deep=True)]

    assert fresh_id in ids, f"setup rotto: fresco assente con deep (ids={ids})"
    assert spoof_id not in ids, (
        f"spoof #3b in ARCHAEOLOGY mode: `deep` ha fatto riemergere un fatto "
        f"con last_verified_at nel futuro (id={spoof_id}). Lo schema promette "
        f"che le guardie d'integrita' restino: `deep` sta liftando piu' "
        f"dell'eta'. ids={ids}"
    )
