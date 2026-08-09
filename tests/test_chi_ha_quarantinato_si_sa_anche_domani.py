"""Chi guarda un fatto quarantinato il giorno dopo non sapeva chi l'avesse deciso.

IL DIFETTO, trovato indagando il caso irrisolto di ws5 (un fatto quarantinato in
produzione con grounding 99.96 che riscrivendolo non si riproduce)::

    colonne di stato in `facts`   [created_at, status, grounding_score]
    audit_mutations               ZERO righe per quei fatti
    facts_undo_log                ZERO righe per quei fatti

Il campo ``quarantined_by`` — che dice QUALE layer ha deciso — l'ho aggiunto io
ieri, e esce **solo nella ricevuta**: la vede chi scrive, nell'istante in cui
scrive. Un minuto dopo l'informazione non esiste più da nessuna parte.

🔑 E NON È UN DETTAGLIO DI COMODITÀ: è il motivo per cui un caso aperto resta
aperto. I due fatti di ws5 sono lì, quarantinati, con il punteggio più alto del
corpus — e non possono dire da soli chi li ha fermati. Sei tentativi di
riproduzione (testo, fonte, topic, dimensione del corpus, canale SDK/CLI,
``validate`` full/fast) non hanno chiuso la domanda che una colonna avrebbe
risposto in un secondo.

📌 PERCHÉ NON IN ``audit_mutations``, che pure esiste ed è chiamata così: quella
tabella è **action-only per scelta deliberata e motivata** — *«storing WHAT was
deleted, even as a hash, inside an immutable chain makes GDPR Art.17 erasure a
logical contradiction»* — ed è per le operazioni DISTRUTTIVE (delete / purge /
forget / supersede / reset). Una quarantena al write non distrugge niente: è una
decisione di ammissione. Metterla lì sarebbe piegare una superficie al caso
sbagliato.

📌 E PERCHÉ FUORI DALLA SCALA VERSIONATA: accanto alla tabella dell'audit c'è
scritto il prezzo già pagato — *«deliberately outside the versioned ladder (v15
history: two forgotten target-bumps broke production writes)»*. Una colonna
nullable aggiunta in modo idempotente non ha bisogno di un numero di versione, e
non può rompere una scrittura per un bump dimenticato.
"""
from __future__ import annotations

import sqlite3

import pytest

from verimem.client import Memory

#: Frasi che L1 ferma per quello che sono: auto-attestazioni senza prova.
VANTI = [
    "Ho verificato che la funzione ora funziona correttamente.",
    "Il modulo e' stato testato ed e' pronto per la produzione.",
]


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def _colonna(mem, fact_id: str, nome: str):
    c = sqlite3.connect(str(mem.semantic.db_path))
    try:
        cols = [r[1] for r in c.execute("PRAGMA table_info(facts)")]
        if nome not in cols:
            return "COLONNA ASSENTE"
        return c.execute(f"SELECT {nome} FROM facts WHERE id=?",
                         (fact_id,)).fetchone()[0]
    finally:
        c.close()


@pytest.mark.parametrize("vanto", VANTI)
def test_la_causa_della_quarantena_sopravvive_alla_ricevuta(mem, vanto):
    """IL CUORE: il fatto è nel database, quarantinato. Chi lo rilegge domani
    deve poter sapere CHI l'ha fermato senza avere sotto mano la ricevuta di
    quel momento."""
    r = mem.add(vanto, topic="az/q")
    assert r.get("status") == "quarantined", r
    assert r.get("id"), r
    persistito = _colonna(mem, r["id"], "quarantined_by")
    assert persistito, (
        f"la causa non è nel DB (valore: {persistito!r}) — l'informazione "
        f"esiste solo nella ricevuta, che nessuno rilegge")
    assert persistito == r.get("quarantined_by"), (
        f"il DB dice {persistito!r}, la ricevuta {r.get('quarantined_by')!r}: "
        f"due viste della stessa cosa che già divergono")


def test_CONTROLLO_POSITIVO_un_fatto_AMMESSO_non_porta_una_causa(mem):
    """⚠️ IL PRESIDIO: la colonna deve restare vuota per i fatti ammessi. Se
    fosse valorizzata sempre non distinguerebbe niente, ed è lo stesso motivo
    per cui `nascosti` deve essere zero su un documento pulito."""
    r = mem.add("Il magazzino di Prato contiene 300 pallet.", topic="az/ok",
                source="Inventario: il magazzino di Prato contiene 300 pallet.")
    assert r.get("status") != "quarantined", r
    assert not _colonna(mem, r["id"], "quarantined_by")


def test_il_DB_e_la_RICEVUTA_dicono_la_stessa_cosa(mem):
    """La proprietà che conta più del campo: due superfici della stessa
    informazione non devono divergere. È la classe che questa casa ha pagato
    tre volte (`_fact_view` copiata in `search`, poi in `history`), qui
    prevenuta prima che nasca la seconda copia."""
    r = mem.add(VANTI[0], topic="az/z")
    assert _colonna(mem, r["id"], "quarantined_by") == r.get("quarantined_by")


def test_uno_store_GIA_ESISTENTE_prende_la_colonna_senza_rompersi(tmp_path):
    """⚠️ IL PRESIDIO CHE PROTEGGE IL CORPUS DI PRODUZIONE: la colonna si
    aggiunge a un database già popolato, e i fatti che c'erano prima restano
    leggibili con la causa a `NULL` — «non registrata», che è la verità per
    tutto ciò che è stato scritto prima di oggi."""
    p = tmp_path / "vecchio.db"
    m1 = Memory(str(p))
    vecchio = m1.add("Il contratto vale 4500 euro.", topic="az/v",
                     source="Listino: il contratto vale 4500 euro.")
    del m1
    m2 = Memory(str(p))                      # riapertura: la migrazione rigira
    assert m2.get(vecchio["id"]) is not None, "il fatto vecchio non si rilegge"
    nuovo = m2.add(VANTI[0], topic="az/n")
    assert _colonna(m2, nuovo["id"], "quarantined_by")
