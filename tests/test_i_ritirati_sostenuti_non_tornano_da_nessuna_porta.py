"""M3 — un fatto RITIRATO ma ancora sostenuto non torna da nessuna porta.

Il versioning è implementato in `SemanticMemory`: `include_superseded` è un
parametro pubblico e documentato di `recall()`, propagato 16 volte, con la
superficie unica `_passes_recall_view` e il fast-path che si disattiva da solo.
Ma **nessuna porta lo espone**: misurato il 02/09 alle 19:55, `hippo_recall`,
`hippo_facts_recall` e `hippo_facts_search` hanno `include_superseded=False`
nello schema, e sette chiamate a `semantic.recall(` su sette non lo passano.

Il banco è di DUE SCRITTURE, che è il minimo per vedere una supersessione — la
lezione di `d2830eb27716`: «il difetto è il WRITE, non il retrieval».

⚠️ `--deep` NON basta: provato il 02/09 alle 20:18 su una copia dello store con
un fatto ritirato reale a grounding 100 — `recall` 0 volte, `recall --deep` 0
volte, con il controllo positivo acceso (lo stesso recall trovava il sostituto).
"""
from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def due_scritture(tmp_path):
    """Un fatto ritirato da un secondo, entrambi nello stesso store."""
    m = Memory(str(tmp_path / "m.db"))
    vecchio = m.add("Il collaudo del lotto B ha rilevato 12 anomalie.",
                    source="Verbale: collaudo lotto B, 12 anomalie rilevate.",
                    topic="banco/m3")
    nuovo = m.add("Il collaudo del lotto B ha rilevato 15 anomalie.",
                  source="Verbale rev.2: collaudo lotto B, 15 anomalie rilevate.",
                  topic="banco/m3")
    vid = vecchio["id"] if isinstance(vecchio, dict) else vecchio.id
    nid = nuovo["id"] if isinstance(nuovo, dict) else nuovo.id
    m.semantic.supersede(vid, nid, principal="test:m3",
                         reason="same-source evolution")
    return m, vid, nid


def _ids(hits) -> set[str]:
    out = set()
    for h in hits or []:
        v = h.get("id") if isinstance(h, dict) else getattr(h, "id", None)
        if v:
            out.add(v)
    return out


def test_il_ritirato_non_torna_dal_recall_di_default(due_scritture):
    """CONTROLLO POSITIVO + il fatto atteso: il sostituto torna, il ritirato no."""
    m, vid, nid = due_scritture
    hits = m.search("quante anomalie ha rilevato il collaudo del lotto B", k=5)
    ids = _ids(hits)
    assert nid in ids, ("controllo positivo SPENTO: non torna nemmeno il "
                        "sostituto, quindi lo zero sul ritirato non dice nulla")
    assert vid not in ids, "il ritirato torna già dal default: il banco non misura nulla"


def test_la_porta_python_puo_chiedere_i_ritirati(due_scritture):
    """RED finché `Memory.search` non espone `include_superseded`.

    Non è un test sul motore — quello il parametro ce l'ha da `cycle #78`. È un
    test sulla PORTA: la capacità esiste e chi usa la libreria non la raggiunge.
    """
    m, vid, _nid = due_scritture
    hits = m.search("quante anomalie ha rilevato il collaudo del lotto B",
                    k=5, include_superseded=True)
    assert vid in _ids(hits), (
        "il ritirato non torna nemmeno chiedendolo esplicitamente")
