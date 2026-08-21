"""`explain` diceva «causa non ricostruibile» su fatti la cui causa c'era.

Il ricalcolo di `_spiega_le_quarantene` girava **a mani vuote** — niente
`source`, niente `ground_write` — e in quel regime L4.1 e L4.2, che confrontano
il claim CON la fonte, non possono accendersi **per costruzione**. Controllo
positivo sul caso noto::

    nudo               -> []          grounding None
    ground_write=True  -> ['L4.1']    grounding 99.89

Sul corpus, ricalcolando 20 quarantinati con grounding >=90 usando la loro
fonte, i layer trovati sono **20 su 20** (L4.1 il 90%, L4.2 il 50%, L1 il 15%):
nessuno resta senza causa. E la vista, con `limit=25`::

    prima   15 righe con un layer (60%), 10 che dicono «causa non registrata»
    dopo    25 righe con un layer (100%), 0 senza causa

⚠️ Questi test provano la CATENA — che la fonte arrivi dalla riga al ricalcolo
— non il verdetto del giudice: sotto pytest `conftest.py` sostituisce
l'embedder con uno stub, quindi un test che si aspettasse un punteggio
misurerebbe il righello. Il caso end-to-end col giudice vero sta nel banco
`docs/stato-reale/banchi/ws3-quale-layer-ha-deciso.py`.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory

FONTE = ("Verbale: il modulo di fatturazione e stato testato e funziona "
         "correttamente in produzione.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def _colonne(mem) -> set[str]:
    con = sqlite3.connect(str(mem.semantic.db_path))
    try:
        return {r[1] for r in con.execute("PRAGMA table_info(facts)")}
    finally:
        con.close()


def test_la_riga_porta_la_fonte_su_cui_il_giudice_ha_deciso(mem, monkeypatch):
    """IL PEZZO CHE MANCAVA: senza `grounding_span` sulla riga, il ricalcolo
    non ha niente da confrontare e la domanda «perché?» non ha risposta."""
    monkeypatch.delenv("VERIMEM_AUDIT_LOG", raising=False)
    assert "grounding_span" in _colonne(mem), "lo schema non porta la fonte"
    mem.add("Ho verificato che il modulo di fatturazione funziona "
            "correttamente.", topic="az/q", source=FONTE)
    righe = mem.quarantine_log(limit=5)
    assert righe, "il banco non produce nessun quarantinato"
    assert "grounding_span" in righe[0], (
        "la SELECT non porta grounding_span: il ricalcolo di explain girerà "
        "a mani vuote e L4.1/L4.2 non potranno accendersi mai")


def test_ogni_riga_del_log_dichiara_una_causa(mem, monkeypatch):
    """Nessuna riga deve uscire senza né `layers` né un `why` che spieghi
    perché non si sa: un referto muto manda a indovinare."""
    monkeypatch.delenv("VERIMEM_AUDIT_LOG", raising=False)
    mem.add("Ho verificato che il modulo di fatturazione funziona "
            "correttamente.", topic="az/q", source=FONTE)
    mem.add("Il modulo di fatturazione ha 9999 utenti attivi.", topic="az/w",
            source="Verbale: il modulo ha 12 utenti attivi.")
    for r in mem.quarantine_log(limit=5, explain=True):
        assert r.get("layers") or r.get("why"), (
            f"riga senza causa né spiegazione: {r.get('id')} "
            f"{(r.get('proposition') or '')[:60]!r}")


def test_explain_non_asserisce_cio_che_il_suo_metodo_non_puo_sapere(
        mem, monkeypatch):
    """⚠️ IL DIFETTO DI FONDO ERA UN'ASSERZIONE, non un'omissione: il ramo
    diceva «NON è L4» su fatti fermati da L4.1, perché il suo ricalcolo non
    poteva vedere L4 nemmeno in linea di principio.

    Un referto muto si nota; uno assertivo e sbagliato manda a cercare nella
    direzione opposta.
    """
    monkeypatch.delenv("VERIMEM_AUDIT_LOG", raising=False)
    mem.add("Ho verificato che il modulo di fatturazione funziona "
            "correttamente.", topic="az/q", source=FONTE)
    for r in mem.quarantine_log(limit=5, explain=True):
        why = str(r.get("why") or "")
        if "NON e' L4" in why or "NON è L4" in why:
            assert not any(str(x).startswith("L4") for x in (r.get("layers") or [])), (
                f"il referto nega L4 mentre nomina un layer L4: "
                f"{r.get('layers')!r} — {why[:120]}")


def test_senza_explain_il_log_resta_gratis(mem, monkeypatch):
    """Il ricalcolo con la fonte carica il giudice (22.58s la prima volta,
    0.04s le successive — misurato). Chi vuole solo l'elenco non deve pagarlo:
    `explain` è opt-in e deve restare l'unica porta che lo attiva."""
    monkeypatch.delenv("VERIMEM_AUDIT_LOG", raising=False)
    mem.add("Ho verificato che il modulo di fatturazione funziona "
            "correttamente.", topic="az/q", source=FONTE)
    righe = mem.quarantine_log(limit=5)
    assert righe
    assert all("why" not in r for r in righe), (
        "senza explain la vista non deve ricalcolare niente")
