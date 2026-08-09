"""La spiegazione della quarantena non inventa la causa.

Referto di ws1, 2026-08-05, trovato USANDO il prodotto: salva un fatto che
cita le formule che il detector di injection riconosce, viene trattenuto
dallo store-screen (`layers=['store-screen']` nella ricevuta), e poi
`quarantine_log(explain=True)` risponde:

    «nessuno schermo lessicale si accende su questa frase: è stata fermata
     dal confronto con la sua fonte (L4)…»

Due affermazioni, entrambe false per quel record: uno schermo si era
acceso — è lui che l'ha fermato — e L4 quel fatto lo aveva APPROVATO
(`grounding_score 99.98` nel DB). Ampiezza misurata da ws1 su 500 record:
`reason` è None su 500/500, `layers` è vuoto su 183/500, e quelle 183
finiscono tutte sul ramo di default. Le altre 317 hanno spiegazioni
specifiche e giuste (L1.13, L1.15…): il difetto non è l'explain, è che la
causa decisa a write-time non viene persistita e l'explain, non
trovandola, DEDUCE.

🔑 Non è una superficie muta: è ASSERTIVA E SBAGLIATA, che è peggio —
manda a cercare nella direzione opposta.

Due cure, nessuna delle quali tocca il write path:
1. si rilancia anche lo schermo di injection (`detect_injection` è puro e
   deterministico come gli L1 che l'explain già rilancia, e vive nello
   `store()`, che il gate di validazione non attraversa: per questo
   rieseguire solo il gate non lo trovava mai);
2. quando nessuno schermo si accende, si guarda cosa la RIGA sa davvero —
   il verdetto del moat — e si dichiara, invece di attribuire a L4.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory

_INJECTION = ('Il detector riconosce la formula "ignora tutte le istruzioni '
              'precedenti" ma non la sua variante inglese.')
_INNOCUO = "the head office of the company is in Milan"


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path / "m.db")


def _spiega(m: Memory) -> list[dict]:
    return m.quarantine_log(explain=True)


def test_la_causa_e_lo_schermo_di_injection_non_L4(mem):
    """Il caso di ws1, per intero."""
    r = mem.add(_INJECTION, topic="sicurezza/referto")
    assert r["status"] == "quarantined"

    riga = next(x for x in _spiega(mem) if x["id"] == r["id"])
    why = (riga.get("why") or "").lower()
    assert "injection" in why, riga
    assert "l4" not in why, "attribuisce a L4 un blocco che non e' suo"
    assert riga["layers"], "e il layer che ha deciso compare"


def test_non_attribuisce_a_L4_quando_L4_HA_APPROVATO(mem):
    """La riga smentisce la spiegazione da sola: `grounding_score 99.98`
    vuol dire che il moat ha detto che la fonte sostiene il fatto. Dire
    «l'ha fermata L4» davanti a quel numero è la forma peggiore di
    errore, perché è verificabile in un colpo d'occhio."""
    r = mem.add(_INNOCUO, topic="hq")
    mem.semantic.quarantine_fact(r["id"], reason="banco")
    with sqlite3.connect(mem.semantic.db_path) as con:
        con.execute("UPDATE facts SET grounding_score = 99.98 WHERE id = ?",
                    (r["id"],))

    riga = next(x for x in _spiega(mem) if x["id"] == r["id"])
    why = (riga.get("why") or "").lower()
    assert "99.98" in why, "il verdetto che smentisce la deduzione va MOSTRATO"
    assert "approv" in why or "non e' stata fermata da l4" in why, riga
    assert "fermata dal confronto con la sua fonte (l4)" not in why


def test_quando_non_lo_sa_lo_DICHIARA(mem):
    """Un fatto trattenuto su cui nessuno schermo si riaccende e che il
    moat non ha mai giudicato: la causa non è ricostruibile, e questo si
    dice. `None` si legge «nessun motivo», che non è «non lo so» — ma una
    causa inventata è peggio di tutti e due."""
    r = mem.add(_INNOCUO, topic="hq")
    mem.semantic.quarantine_fact(r["id"], reason="banco")

    riga = next(x for x in _spiega(mem) if x["id"] == r["id"])
    why = (riga.get("why") or "").lower()
    assert "non" in why and ("registrat" in why or "ricostru" in why), riga
    assert "mai giudicat" in why or "never judged" in why, riga
    # e NON deve nominare un layer come colpevole
    assert "fermata dal confronto con la sua fonte (l4)" not in why


def test_gli_schermi_lessicali_veri_continuano_a_essere_spiegati(mem):
    """Regressione sulle 317 su 500 che già funzionavano: la cura non
    deve spegnere le spiegazioni giuste per far tacere quella sbagliata."""
    r = mem.add("The migration is complete and fully verified.", topic="rel")
    assert r["status"] == "quarantined"

    riga = next(x for x in _spiega(mem) if x["id"] == r["id"])
    assert riga["layers"], riga
    assert any(str(x).upper().startswith("L1") for x in riga["layers"]), riga
    assert riga.get("why"), riga
