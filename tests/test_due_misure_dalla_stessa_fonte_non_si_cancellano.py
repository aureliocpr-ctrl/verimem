"""Due misure diverse tratte dalla STESSA evidenza: la seconda cancella la prima.

MISURATO ALL'SDK (`verimem.client.Memory`, porta pubblica) il 2026-09-09, store
temporaneo, una sola fonte::

    fonte   «latency over 5 queries: min 16.3s, median 33.0s, max 41.2s»
    add A   «La latenza riporta mediana 33.0s su 5 query.»
    add B   «La latenza riporta min 16.3s su 5 query.»

    1 failed, 1 passed, 23 warnings in 66.93s   EXIT=1
    E   AssertionError: ritirata da c9f830033ae9 per «same-source evolution»

⇒ **Nessuno dei due fatti nega l'altro**: sono la mediana e il minimo della
STESSA esecuzione, entrambi veri, entrambi scritti dalla stessa riga di output.
La politica li tratta come due VERSIONI dello stesso fatto perché condividono
la fonte, e la più recente vince per costruzione.

🔍 DOVE SCATTA, per chi verrà dopo: `anti_confab_gate.py:2131` — la
supersessione same-source parte SOLO quando il layer L3 (`_l3_check`,
`validate_claim`) dà `verdict == "contradicted"`. Due numeri diversi per quella
che L3 legge come la stessa grandezza SONO una contraddizione lessicale; che
siano `min` e `median` della stessa riga, L3 non lo distingue. Il banco è
sensibile a questo: con due fatti complementari SENZA contraddizione numerica
(«30 passed» e «22.81s») il ritiro non avviene affatto — provato, 2 passed —
e un banco così avrebbe dichiarato il difetto inesistente.

📌 GIÀ MISURATO DUE VOLTE, con due righelli diversi, prima di questo banco:
  · `docs/stato-reale/66-il-criterio-scartava-proprio-i-casi-piu-comuni.md`
    (31/08): campione dei ritiri `same-source evolution`, **30 letti, 30
    sbagliati, zero eccezioni** — i due bracci di un A/B, due workflow diversi,
    due scritture dello stesso banco;
  · sul corpus di casa il 09/09, su TUTTE le 529 coppie ritirate:
    **425 (80%) hanno numeri nel vecchio che il nuovo non porta**.

🔑 PERCHÉ SUCCEDE, e perché la cura NON sta nel classificatore.
`supersession_policy.classify_write_relation` è conservativo per progetto («any
ambiguity → conflict») ma `_when_true` ripiega su `created_at` quando manca
`asserted_at` — che nessuna porta valorizza (0 fatti su 15.978, misurato il
30/08) — e il momento di scrittura del candidato è sempre *adesso*: l'ordine
non è ambiguo-e-risolto-in-conflitto, è **inventato**, e il verdetto è
`evolution` per costruzione. Il docstring di quella funzione VIETA la cura
ovvia: togliere il ripiego manderebbe quasi ogni coppia a `conflict` e a
pagarlo sarebbero i fatti veri («whoever touches it must measure BOTH
populations»). Quindi qui non si tocca la classificazione: si cambia **che cosa
succede quando il verdetto è `evolution`** — versionare invece di ritirare,
come già fa il tier documenti (`document_index.py:90`: `version INTEGER NOT
NULL`, cerca l'ultima, tiene tutte). Decisione del 05/08, innesto UNO:
`SemanticMemory.supersede`.

⚠️ IL PRESIDIO CHE VIENE PRIMA DELLA CURA (secondo test di questo file): la
RIMISURA dello stesso valore deve continuare a far vincere il valore NUOVO.
Una memoria che non aggiorna più è rotta quanto una che cancella, e una cura
che salva il vecchio rompendo l'aggiornamento non è una cura.

🚧 IL CONFINE DELLA CURA, e l'ho trovato ROMPENDOLO. La prima stesura faceva
coesistere QUALUNQUE coppia a impronta uguale, e rendeva rosso
`tests/test_due_guardie_si_coprono_e_nessuno_lo_sa.py`::

    con la cura larga                        1 failed, 2 passed in 48.18s  EXIT=1
    sulla BASE 20257636 (git worktree a parte)      3 passed in 57.09s     EXIT=0
    con la cura RISTRETTA (`references_fact` escluso) 3 passed in 54.60s   EXIT=0

Il caso: «La coda ha 540 elementi (rettifica del fatto <id>)» lasciava vivo il
500 accanto alla sua stessa correzione. Chi rettifica la propria lettura lo
DICHIARA nominando il fatto che corregge, e quel ritiro deve continuare ad
avvenire — `references_fact`, dal 2026-07-25.

📌 E QUI NON C'È UN MIO TEST SU QUEL CONFINE, di proposito. Provandolo da
questo file il banco pretendeva un ritiro che **sulla base non avviene
nemmeno**: stessa sonda sui due alberi, entrambi rendono `L3-coexistence «a
contradiction was found but both facts are kept»` e due righe vive — senza
`verified_by` la citazione dell'id passa dal percorso semantico, dove tenere
entrambi è la decisione di progetto. Un banco lasciato rosso qui avrebbe
accusato questa cura di un comportamento che non ha introdotto; e un test
senza asserzioni, tenuto per il suo commento, sarebbe stato un verde che non
misura niente. Il presidio vero è il file citato sopra: chi tocca questa rotta
lo esegua.

Ticket: piano di ripresa 09/09 §5 riga 2 (ws6), gamba B. Ramo
`aldo/tetto-e-supersede`.
"""

from __future__ import annotations

import pathlib
import sqlite3
import tempfile

import pytest

from verimem.client import Memory

#: La coppia è REALE: è la prima riga della tabella del documento 66 (jaccard
#: 0,667, «la latenza riporta mediana 33.0s» ritirata da «la latenza riporta
#: min 16.3s»). Due letture complementari della STESSA esecuzione, entrambe
#: vere, che il layer L3 legge come contraddizione numerica.
FONTE = ("latency over 5 queries: min 16.3s, median 33.0s, max 41.2s\n"
         "(banco della latenza, 5 query, stessa esecuzione)")
A = "La latenza riporta mediana 33.0s su 5 query."
B = "La latenza riporta min 16.3s su 5 query."

#: La rimisura: stessa grandezza, valore nuovo, fonte nuova. È il caso che la
#: supersessione ESISTE per servire, e che nessuna cura può rompere.
FONTE_2 = "latency over 5 queries (nuova esecuzione): median 12.5s"
A2 = "La latenza riporta mediana 12.5s su 5 query."


def _memoria() -> Memory:
    return Memory(pathlib.Path(tempfile.mkdtemp(prefix="due-misure-")) / "m.db")


def _righe(m: Memory) -> list[dict]:
    con = sqlite3.connect(str(m.semantic.db_path))
    con.row_factory = sqlite3.Row
    righe = [dict(r) for r in con.execute(
        "SELECT id, proposition, status, superseded_by, superseded_reason "
        "FROM facts ORDER BY created_at")]
    con.close()
    return righe


@pytest.fixture
def due_misure():
    m = _memoria()
    m.add(A, source=FONTE, topic="banco/stessa-fonte")
    m.add(B, source=FONTE, topic="banco/stessa-fonte")
    righe = _righe(m)
    # CONTROLLO POSITIVO: le due scritture devono essere ENTRAMBE nello store.
    # Se una fosse stata quarantinata dal gate, questo banco misurerebbe il
    # moat e non la supersessione, e passerebbe per la ragione sbagliata.
    assert len(righe) == 2, [r["proposition"][:40] for r in righe]
    assert all(r["status"] != "quarantined" for r in righe), righe
    return m, righe


def test_la_prima_misura_non_sparisce(due_misure):
    """IL CUORE: due letture complementari della stessa evidenza convivono."""
    m, righe = due_misure
    vecchia = righe[0]
    assert vecchia["superseded_by"] is None, (
        f"ritirata da {vecchia['superseded_by']} "
        f"per «{vecchia['superseded_reason']}»")

    trovate = m.search("mediana della latenza su 5 query", k=10)
    testo = " ".join(str(f) for f in trovate)
    assert "33.0s" in testo, f"la prima misura non torna: {testo[:200]}"


def test_la_ricevuta_dichiara_la_coesistenza():
    """R4 — LA TERZA USCITA NON DEVE ESSERE MUTA.

    Il gate ha tre esiti: ritirare il vecchio, quarantenare il nuovo, o tenerli
    entrambi. La terza è l'unica che non cambia lo stato di niente, quindi è
    anche l'unica che può diventare silenziosa senza che un test se ne accorga
    — è la ragione per cui esiste `tests/test_la_terza_uscita_lo_dice.py`, e
    quel file nasce da una diagnosi fatta LEGGENDO il codice invece di
    eseguirlo. Qui si esegue: la mia uscita nuova passa dallo stesso
    `continue`, quindi deve raccogliere lo stesso avviso.
    """
    m = _memoria()
    m.add(A, source=FONTE, topic="banco/avviso")
    res = m.add(B, source=FONTE, topic="banco/avviso")

    assert res.get("status") != "quarantined", res
    avvisi = [w.get("layer") for w in (res.get("warnings") or [])]
    assert "L3-coexistence" in avvisi, (
        f"la coesistenza non è dichiarata nella ricevuta: {avvisi}")


def test_la_rimisura_fa_ancora_vincere_il_valore_nuovo():
    """⚠️ LA POPOLAZIONE OPPOSTA — il presidio che viene prima della cura.

    Stessa grandezza, valore nuovo: chi chiede la mediana deve ricevere
    12.5s, non 33.0s. Una memoria che non aggiorna più è rotta quanto una che
    cancella; se questo test diventasse rosso, la cura sarebbe peggiore del
    difetto. ✅ Verde OGGI (prima della cura) e deve restarlo dopo.
    """
    m = _memoria()
    m.add(A, source=FONTE, topic="banco/rimisura")
    m.add(A2, source=FONTE_2, topic="banco/rimisura")

    trovate = m.search("mediana della latenza su 5 query", k=10)
    testo = " ".join(str(f) for f in trovate)
    assert "12.5s" in testo, f"il valore nuovo non torna: {testo[:200]}"
    primo = str(trovate[0]) if trovate else ""
    assert "12.5s" in primo, f"il valore nuovo non è il primo: {primo[:200]}"
