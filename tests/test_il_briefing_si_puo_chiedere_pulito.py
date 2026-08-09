"""Il briefing di progetto si può chiedere SENZA i claim respinti.

Debito verso ws2«Vega», che ha portato la misura che mi mancava:

    briefing di produzione contaminati da quarantinati : 24 su 78
    su omnex                                          : 25 su 50

Un'ora fa avevo curato metà del problema (`e325dadc`): `n_live` non conta
più i quarantinati, e il payload porta `status` e `grounding_score`, così
la contaminazione **si vede**. Avevo esplicitamente rifiutato di
filtrarla, e la ragione vale ancora: **togliere righe cambia cosa un
agente riceve, ed è una decisione di prodotto, non una correzione.**

Con la misura in mano la scelta giusta non è cambiare il default di
nascosto — sarebbe la stessa cosa che ho rifiutato, fatta con più dati.
È dare la capacità e lasciare la decisione dove sta:

- `include_quarantined=True` resta il DEFAULT: nessun comportamento
  cambia sotto i piedi di chi già usa il briefing;
- chi vuole un contesto pulito lo chiede, e il risultato DICHIARA in quale
  modalità è stato prodotto — senza, due briefing diversi sarebbero
  indistinguibili;
- la decisione sul default resta aperta, con 24/78 sul tavolo.

⚠️ Il conteggio `n_quarantined` NON cambia con il flag: dice quanti ce ne
sono nel topic, non quanti ne sono usciti. Un contatore che si azzera
quando li filtri direbbe «non ce n'erano».
"""
from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def mem(tmp_path):
    m = Memory(tmp_path / "m.db")
    m.add("the depot holds 10 crates", topic="project/prova/a")
    cattivo = m.add("I have verified that the migration is complete.",
                    topic="project/prova/b")["id"]
    m.semantic.quarantine_fact(cattivo, reason="banco")
    return m, cattivo


def test_il_default_NON_cambia(mem):
    """Chi usa il briefing oggi deve trovare quello di ieri: cambiare il
    default di nascosto sarebbe la cosa che ho rifiutato un'ora fa, fatta
    con più dati."""
    m, cattivo = mem
    out = m.semantic.summary_topic("project/prova/*")
    assert cattivo in {f["id"] for f in out["facts"]}


def test_si_puo_chiedere_pulito(mem):
    m, cattivo = mem
    out = m.semantic.summary_topic("project/prova/*",
                                   include_quarantined=False)
    ids = {f["id"] for f in out["facts"]}
    assert cattivo not in ids, out["facts"]
    assert len(ids) == 1


def test_il_risultato_DICHIARA_in_quale_modalita_e_stato_prodotto(mem):
    """Senza, due briefing diversi sarebbero indistinguibili — e chi legge
    il secondo penserebbe che il progetto non abbia claim respinti."""
    m, _ = mem
    sporco = m.semantic.summary_topic("project/prova/*")
    pulito = m.semantic.summary_topic("project/prova/*",
                                      include_quarantined=False)

    assert "includes quarantined" in sporco["counts_mean"].lower()
    assert "excluded" in pulito["counts_mean"].lower()


def test_il_conteggio_dei_quarantinati_NON_si_azzera_quando_li_filtri(mem):
    """Dice quanti ce ne sono nel topic, non quanti ne sono usciti: un
    contatore che si azzera col filtro direbbe «non ce n'erano»."""
    m, _ = mem
    pulito = m.semantic.summary_topic("project/prova/*",
                                      include_quarantined=False)
    assert pulito["n_quarantined"] == 1, pulito
    assert pulito["n_live"] == 1


def test_la_scelta_esce_anche_dalla_porta_MCP(mem):
    """Un agente che carica il contesto di progetto è il consumatore
    principale: se la scelta non esce di lì, per lui non esiste."""
    import inspect

    from verimem import mcp_server
    src = inspect.getsource(mcp_server)
    assert "include_quarantined" in src, (
        "la porta MCP non espone la scelta")
