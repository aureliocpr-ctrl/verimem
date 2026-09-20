"""T161 END-TO-END: le tre righe della tabella che il 2026-08-04 fece ritirare la cura.

Il docstring di `canonical_source_of` porta questa tabella, ed è la ragione per
cui la cura che legge la firma fu scritta, misurata e tolta:

    caso                                riga attuale   con la signature
    source DIVERSE (due cartelle)          1 vivo         2 vivi   ✅
    STESSA source, valore aggiornato       1 vivo         2 vivi   ❌
    nessuna source (compatibilità)         1 vivo         1 vivo   ✅

La riga di mezzo era la regressione: l'aggiornamento legittimo smetteva di
ritirare. E il file dice anche: «la funzione, chiamata da sola, è CORRETTA in
tutti e tre i casi... Il comportamento cambia più a valle, in un punto che non
è stato isolato».

⚠️ QUESTO BANCO MISURA DALLA PORTA, NON DALLA FUNZIONE, ed è tutto il punto: il
punto non isolato era il candidato che il gate costruisce, che non portava la
firma — quindi un lato leggeva `None` sempre e ogni aggiornamento diventava un
conflitto. Un banco sulla funzione avrebbe detto «verde» anche allora, ed è
esattamente quello che successe. Qui si scrive con `Memory.add`, come un utente.

BANCO MINIMO = DUE SCRITTURE: un fatto solo non può mostrare una supersessione.

⚠️ PERCHÉ `ground=False`, E PERCHÉ NON È UN MODO DI ADDOLCIRE IL BANCO. La prima
stesura scriveva con `validate="full"`, e i quattro fatti sono entrati
`status=quarantined`: grounding 71.65845489501953 e 73.36204528808594 su
L4-review, 0.9032012820243835 e 0.8670159578323364 su L4-grounding, perché le
fonti inventate non sostenevano le proposizioni. Un fatto trattenuto non ritira
nulla, e il banco leggeva quel silenzio come «la supersessione è rotta»: due
celle rosse che accusavano la cura di una regressione che non c'era. Il giudice
è una variabile confondente per una misura sulla supersessione, e qui si spegne
— ma la fonte resta, perché è lei a far nascere la firma. Che nasca anche così
non è un'assunzione: lo dice l'ultima cella.

⚠️ E OGNI CELLA PRETENDE CHE I FATTI SIANO ENTRATI VIVI. Senza quella riga un
banco end-to-end sul ritiro può essere verde per il vuoto — due fatti trattenuti
restano «due vivi» e la riga 1 sembrerebbe passare. È il difetto che ha prodotto
i due rossi, e questa è la sua cura.
"""
from __future__ import annotations

import pytest

from verimem import Memory

TOPIC = "magazzino/scorte"


def _mem(tmp_path):
    return Memory(path=tmp_path / "sem" / "sem.db")


def _scrivi(mem, testo, *, source=None):
    """Scrive e PRETENDE che il fatto sia entrato vivo.

    Se il gate lo trattiene, la cella si ferma qui con la ragione vera invece di
    proseguire e attribuire alla supersessione un silenzio che viene da altrove.
    """
    extra = {"source": source} if source else {}
    ric = mem.add(testo, topic=TOPIC, ground=False, **extra)
    assert ric.get("stored"), f"il fatto non è stato scritto affatto: {ric}"
    assert ric.get("quarantined_by") is None, (
        f"il fatto è stato TRATTENUTO dal gate ({ric.get('quarantined_by')}, "
        f"grounding={ric.get('grounding_score')}): un fatto trattenuto non "
        f"ritira nulla, quindi questa cella non sta misurando la supersessione. "
        f"Ricevuta: {ric}")
    return ric


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
    r1 = _scrivi(mem, "Il magazzino di Anzio contiene 100 pezzi.",
                 source="Inventario di Anzio, foglio 1.")
    _scrivi(mem, "Il magazzino di Bracciano contiene 150 pezzi.",
            source="Inventario di Bracciano, foglio 9.")

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
    r1 = _scrivi(mem, "L'abbonamento costa 100 euro al mese.", source=fonte)
    r2 = _scrivi(mem, "L'abbonamento costa 150 euro al mese.", source=fonte)

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
    r1 = _scrivi(mem, "La soglia vale 40 punti.")
    r2 = _scrivi(mem, "La soglia vale 70 punti.")

    primo = mem.semantic.get(r1["id"])
    assert primo is not None
    assert primo.superseded_by == r2["id"], (
        f"senza fonte il comportamento è cambiato: superseded_by="
        f"{primo.superseded_by!r}, atteso {r2['id']!r}. La cura ha toccato il "
        f"caso che doveva lasciare intatto")


# ------------------------------------------------------- controllo positivo --
def test_il_banco_vede_davvero_una_supersessione(tmp_path) -> None:
    """Se le tre celle sopra diventassero verdi, questa dice che non è perché
    il banco ha smesso di guardare: una supersessione DEVE potersi osservare.

    ⚠️ LA PAROLA «unità» NON È DECORAZIONE, ed è un reperto trovato scrivendo
    questa cella. La prima stesura diceva «Il contatore segna 10» → «20» e non
    ritirava; misurate quattro coppie con la stessa fonte, tutte entrate vive:

        contatore 10 → 20            nessun ritiro
        contatore 100 → 150          nessun ritiro
        contatore 10 → 20 unità      RITIRA
        valore misurato 100 → 150    RITIRA

    Non è la grandezza del numero: è che un numero nudo non viene riconosciuto
    come quantità aggiornabile. Qui serve una coppia che il prodotto riconosca,
    altrimenti la cella accuserebbe la supersessione di un silenzio che nasce
    dal riconoscimento delle quantità. Il reperto è stato portato al lead: se
    «Il contatore segna 10» seguito da «20» lascia due verità vive, è il caso
    d'uso più banale che esista e non lo decide questo banco.
    """
    mem = _mem(tmp_path)
    fonte = "Un solo documento, citato due volte."
    r1 = _scrivi(mem, "Il contatore segna 10 unità.", source=fonte)
    r2 = _scrivi(mem, "Il contatore segna 20 unità.", source=fonte)

    primo = mem.semantic.get(r1["id"])
    assert primo is not None and primo.superseded_by == r2["id"], (
        "il banco non riesce a osservare NESSUNA supersessione: sta misurando "
        "il vuoto, e le tre celle sopra non provano niente")


# ------------------------------------------------ controllo sull'attrezzo ---
def test_la_firma_nasce_anche_col_giudizio_spento(tmp_path) -> None:
    """L'ATTREZZO DI QUESTO BANCO, provato invece che assunto.

    Tutte le celle scrivono con `ground=False`. Se quel modo impedisse alla
    firma della fonte di nascere, la riga 1 passerebbe per la ragione sbagliata
    — due fatti senza firma da nessuna parte — e il banco misurerebbe l'assenza
    dell'attrezzo invece della cura.
    """
    mem = _mem(tmp_path)
    r = _scrivi(mem, "Una proposizione qualunque.",
                source="Un documento qualunque, citato una volta.")

    scritto = mem.semantic.get(r["id"])
    assert getattr(scritto, "source_signature", None), (
        "con ground=False la fonte non lascia firma nel fatto: le celle di "
        "questo banco non starebbero esercitando la cascata della cura")
