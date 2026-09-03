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


def test_lo_schema_del_tool_mcp_espone_il_parametro():
    """Il tool `hippo_facts_recall` deve DICHIARARE `include_superseded`.

    ⚠️ `hippo_recall` NON è il bersaglio, e l'ho verificato LEGGENDO invece che
    deducendo: il suo handler chiama ``a.memory.recall`` — è il recall degli
    EPISODI, che non hanno supersessione. Il recall dei FATTI è
    ``hippo_facts_recall``, che chiama ``a.semantic.recall`` col dizionario
    ``_pf``. Il mio conteggio del 02/09 («hippo_recall non espone il campo»)
    era vero e IRRILEVANTE.

    ⚠️ QUESTO TEST PROVA LA DICHIARAZIONE, NON IL COMPORTAMENTO — e il
    comportamento ORA è provato altrove: `docs/stato-reale/banchi/
    m3-la-porta-mcp-serve-i-ritirati.py`, verde il 03/09 alle 19:38 (il
    ritirato torna col flag e non senza, col controllo positivo acceso).

    ⚠️⚠️ QUEL BANCO È STATO ROSSO TRE VOLTE PRIMA, E NON PER UN DIFETTO DEL
    PRODOTTO: `python docs/.../banco.py` mette in `sys.path[0]` la directory
    dello script, quindi `import verimem` prendeva il pacchetto INSTALLATO —
    per chi lavora in un `git worktree`, un ALTRO albero, senza la porta che
    il banco stava provando. Il banco ora se ne difende da solo e si ferma se
    sta per misurare un albero che non è il suo. La morale che vale oltre
    questo file: un rosso va classificato PRIMA di essere spiegato, perché
    «la porta non funziona» e «ho misurato un altro codice» hanno lo stesso
    colore.
    """
    import pathlib as _p
    src = (_p.Path(__file__).resolve().parents[1]
           / "verimem" / "mcp_server.py").read_text(encoding="utf-8")
    i = src.find('name="hippo_facts_recall"')
    assert i > 0, "tool hippo_facts_recall non trovato"
    blocco = src[i:i + 6000]
    assert '"include_superseded"' in blocco, (
        "lo schema del tool non dichiara include_superseded: un agente non può "
        "chiederlo nemmeno sapendo che il motore lo accetta")
    assert '_pf["include_superseded"] = True' in src, (
        "lo schema lo dichiara ma l'handler non lo passa a semantic.recall: "
        "sarebbe una promessa senza effetto")
