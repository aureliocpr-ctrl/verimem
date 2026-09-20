"""T161 END-TO-END: le tre righe della tabella che il 2026-08-04 fece ritirare la cura.

Il docstring di `canonical_source_of` porta questa tabella, ed è la ragione per
cui la cura che legge la firma fu scritta, misurata e tolta:

    caso                                riga attuale   con la signature
    source DIVERSE (due cartelle)          1 vivo         2 vivi   ✅
    STESSA source, valore aggiornato       1 vivo         2 vivi   ❌
    nessuna source (compatibilita')        1 vivo         1 vivo   ✅

La riga di mezzo era la regressione: l'aggiornamento legittimo smetteva di
ritirare. E il file dice anche: «la funzione, chiamata da sola, è CORRETTA in
tutti e tre i casi... Il comportamento cambia più a valle, in un punto che non
è stato isolato».

⚠️ QUESTO BANCO MISURA DALLA PORTA, NON DALLA FUNZIONE, ed è tutto il punto: il
punto non isolato era il candidato che il gate costruisce, che non portava la
firma — quindi un lato era sempre `None` e ogni aggiornamento diventava un
conflitto. Un banco sulla funzione avrebbe detto «verde» anche allora, ed è
esattamente quello che successe. Qui si scrive con `Memory.add`, come un utente.

BANCO MINIMO = DUE SCRITTURE: un fatto solo non può mostrare una supersessione.
"""
from __future__ import annotations

import pytest

from verimem import Memory

TOPIC = "magazzino/scorte"


def _mem(tmp_path):
    return Memory(path=tmp_path / "sem" / "sem.db")


@pytest.fixture(autouse=True)
def _supersessione_accesa(monkeypatch):
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", "enforce")
    monkeypatch.delenv("ENGRAM_SEMANTIC_CONFLICT", raising=False)


# ---------------------------------------------------------------- riga 1 ----
def test_due_fonti_diverse_lasciano_due_fatti_vivi(tmp_path) -> None:
    """source DIVERSE → 2 vivi. È il bersaglio: 159 ritiri su 533 stanno qui.

    Due misure su oggetti diversi che citano documenti diversi. Prima della
    cura il secondo archiviava il primo perché entrambi anonimi: è il caso
    reale di «explain con file assente 81013 ms» ritirato da «explain con file
    scritto 2264 ms», i due bracci di uno stesso A/B.
    """
    mem = _mem(tmp_path)
    r1 = mem.add("Il magazzino di Anzio contiene 100 pezzi.", topic=TOPIC,
                 source="Inventario di Anzio, foglio 1: 100 pezzi.",
                 validate="full")
    mem.add("Il magazzino di Bracciano contiene 150 pezzi.", topic=TOPIC,
            source="Inventario di Bracciano, foglio 9: 150 pezzi.",
            validate="full")

    primo = mem.semantic.get(r1["id"])
    assert primo is not None, "il primo fatto deve esistere"
    assert primo.superseded_by is None, (
        f"due scritture con fonti DIVERSE si sono ritirate a vicenda: "
        f"superseded_by={primo.superseded_by!r}. Sono due oggetti diversi, e "
        f"il prodotto le ha chiamate evoluzione")


# ---------------------------------------------------------------- riga 2 ----
def test_la_stessa_fonte_ripresentata_ritira_ancora(tmp_path) -> None:
    """STESSA source, valore aggiornato → RITIRA. La riga che fece ritirare la cura.

    Se questa cade, la cura ha ripreso la regressione del 04/08 e non va
    consegnata: l'aggiornamento legittimo è la promessa centrale del prodotto.
    """
    mem = _mem(tmp_path)
    fonte = "Listino ufficiale, revisione unica."
    r1 = mem.add("L'abbonamento costa 100 euro al mese.", topic=TOPIC,
                 source=fonte, validate="full")
    r2 = mem.add("L'abbonamento costa 150 euro al mese.", topic=TOPIC,
                 source=fonte, validate="full")

    primo = mem.semantic.get(r1["id"])
    assert primo is not None
    assert primo.superseded_by == r2["id"], (
        f"l'aggiornamento con la STESSA fonte non ha ritirato il vecchio: "
        f"superseded_by={primo.superseded_by!r}, atteso {r2['id']!r}. È la "
        f"regressione per cui la cura del 2026-08-04 fu tolta")


# ---------------------------------------------------------------- riga 3 ----
def test_senza_fonte_il_comportamento_non_cambia(tmp_path) -> None:
    """nessuna source → 1 vivo. La compatibilità, e vale per la maggioranza.

    Sul corpus vivo quasi nessun fatto porta un `verified_by`, e molti non
    portano nemmeno una source: se la cura cambiasse anche questo caso, ogni
    ritiro legittimo fra scritture anonime sparirebbe di colpo.
    """
    mem = _mem(tmp_path)
    r1 = mem.add("La soglia vale 40 punti.", topic=TOPIC, validate="full")
    r2 = mem.add("La soglia vale 70 punti.", topic=TOPIC, validate="full")

    primo = mem.semantic.get(r1["id"])
    assert primo is not None
    assert primo.superseded_by == r2["id"], (
        f"senza fonte il comportamento è cambiato: superseded_by="
        f"{primo.superseded_by!r}, atteso {r2['id']!r}. La cura ha toccato il "
        f"caso che doveva lasciare intatto")


# ------------------------------------------------------- controllo positivo --
def test_il_banco_vede_davvero_una_supersessione(tmp_path) -> None:
    """Se le tre celle sopra diventassero verdi, questa dice che non è perché
    il banco ha smesso di guardare: una supersessione DEVE potersi osservare."""
    mem = _mem(tmp_path)
    fonte = "Un solo documento, citato due volte."
    r1 = mem.add("Il contatore segna 10.", topic=TOPIC, source=fonte,
                 validate="full")
    r2 = mem.add("Il contatore segna 20.", topic=TOPIC, source=fonte,
                 validate="full")

    primo = mem.semantic.get(r1["id"])
    assert primo is not None and primo.superseded_by == r2["id"], (
        "il banco non riesce a osservare NESSUNA supersessione: sta misurando "
        "il vuoto, e le tre celle sopra non provano niente")
