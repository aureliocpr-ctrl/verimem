"""G10 — il gate su source-trust NON esiste più, e questi test lo presidiano.

RIMOSSO il 2026-09-02 con voto G10 (4 SÌ su 3 richiesti). Non perché il
meccanismo fosse sbagliato: perché non ha mai avuto materiale su cui lavorare.
Misurato sul corpus vivo (17 279 fatti): **0 scritture marcate**, 156 sorgenti
tutte al valore iniziale `0.500`, tabella `source_trust` con **0 righe**.
La causa sta un piano più sopra: `source_trust_observe` — l'API pubblica che
alimenta il libro — è chiamata da 4 banchi e 5 test e da **zero porte** del
prodotto (`0` in `cli.py`, `0` in `mcp_server.py`).

I due test che documentavano il gate accendevano il flag **e** abbassavano la
soglia a `0.9`, per far scendere sotto il valore iniziale `0.5` una fonte senza
storia: costruivano in laboratorio la condizione che sul corpus vero non si è
mai presentata. Qui si asserisce l'opposto, **nella stessa condizione**.

⚠️ Il terzo test è quello che conta: presidia ciò che NON deve cambiare. Senza,
una rimozione troppo larga — che portasse via anche `canonical_source` o il
libro — passerebbe con i primi due verdi.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.client import Memory  # noqa: E402

_FONTE_SENZA_STORIA = ["source:unknown_feed:1"]
_TESTO = "The sky is a calm blue today."


def _scrivi_col_flag_acceso(tmp_path, monkeypatch, nome, modo="1"):
    """La condizione ESATTA dei due test rimossi: flag acceso e soglia alzata a
    0.9, così che il `0.5` di una fonte senza storia le finisca sotto."""
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", modo)
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST_MIN", "0.9")
    m = Memory(str(tmp_path / nome))
    return m, m.add(_TESTO, verified_by=_FONTE_SENZA_STORIA)


def test_col_flag_acceso_la_scrittura_non_e_piu_marcata(tmp_path, monkeypatch):
    """Era `test_source_trust_enforce_gates_low_trust`, che qui si capovolge."""
    _m, r = _scrivi_col_flag_acceso(tmp_path, monkeypatch, "g10_enf.db")
    assert r["status"] != "quarantined", (
        "il gate su source-trust è stato rimosso: una fonte senza storia non "
        "deve più far quarantenare la scrittura")
    assert not any(w.get("layer", "").startswith("SOURCE_TRUST")
                   for w in r.get("warnings") or []), (
        "nessuna ricevuta deve più portare un layer SOURCE_TRUST")


def test_in_modo_osserva_non_esce_piu_nemmeno_l_avviso(tmp_path, monkeypatch):
    """Era `test_source_trust_observe_logs_but_does_not_gate`: l'avviso
    `SOURCE_TRUST-observe` era l'unico effetto del modo osservazione, e se ne va
    con il gate."""
    _m, r = _scrivi_col_flag_acceso(tmp_path, monkeypatch, "g10_obs.db",
                                    modo="observe")
    assert r["status"] != "quarantined"
    assert not any(w.get("layer") == "SOURCE_TRUST-observe"
                   for w in r.get("warnings") or [])


def test_il_libro_delle_fonti_resta_intatto(tmp_path, monkeypatch):
    """🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: la rimozione tocca il GATE, non il
    MODULO. `canonical_source` ha 3 importatori e `get_book` 1: se una rimozione
    troppo larga li portasse via, i due test sopra resterebbero verdi lo stesso.
    """
    from verimem import source_trust as st

    assert st.canonical_source(_FONTE_SENZA_STORIA) == "unknown_feed"
    m = Memory(str(tmp_path / "g10_libro.db"))
    # il valore di partenza di una fonte senza storia resta leggibile: è il
    # `0.500` osservato su tutte e 156 le sorgenti del corpus vivo.
    assert 0.0 <= float(m.source_trust("unknown_feed")) <= 1.0
    # e l'API che alimenterebbe il registro esiste ancora: la rimozione toglie
    # il consumatore, non il canale.
    assert callable(getattr(m, "source_trust_observe", None))
