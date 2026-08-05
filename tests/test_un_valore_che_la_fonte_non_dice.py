"""Il moat approva «l'ordine 77 conteneva 40 pezzi» a 97, e la fonte non lo dice.

IL DIFETTO CENTRALE, trovato da ws5 e riprodotto qui prima di curarlo. Due
popolazioni, stessa fonte, stesso giudice::

    CONTROLLO POSITIVO — fatti VERI          ammessi 4/4   ok
    A — inventa un'ENTITÀ (fornitore Verdi)  ammessi 0/4   ok, il gate li ferma
    B — DETTAGLIO non detto su entità vera   ammessi 5/5   con g 97,1–99,5

        «La riunione trimestrale e' durata due ore.»        g=98.6
        «L'ordine 77 conteneva 40 pezzi.»                   g=97.1
        «L'ispezione ... e' iniziata alle nove.»            g=99.5
        «Il fornitore Bianchi ha partecipato per 45 minuti» g=98.7
        «L'ordine 77 vale 1200 euro.»                       g=98.0

🔑 (B) È LA FORMA IN CUI UN LLM ALLUCINA DAVVERO. Nessun modello inventa un
fornitore che non esiste; inventa la durata, l'importo, il numero di pezzi. Su
una memoria che si vende VERIFICATA quella è l'unica classe che conta, ed è
quella scoperta — **e non entra di nascosto: entra col punteggio più alto del
sistema.**

LA DIAGNOSI È DI ws5, e ha un indirizzo::

    «Nessun rilevatore L1 riceve la fonte. Il confronto claim↔fonte esiste in
     UN SOLO posto: dentro il cross-encoder, che è esattamente quello che
     sbaglia su questa classe.
        L1  vede il claim, NON la fonte
        L4  vede claim + fonte, ma confonde PLAUSIBILE con IMPLICATO
     ⇒ manca un controllo DETERMINISTICO claim↔fonte»

e da ws4 il numero che la rende strutturale: **il 91,8% dei verdetti del moat
sta agli estremi (1324 su 1673 sopra 99) — nessuna soglia può separare.**

LA CURA è deterministica e non usa modelli: se il claim porta un VALORE
NUMERICO che nella fonte non compare, il verdetto del moat non basta.

⚠️ LIMITE DICHIARATO: copre i valori in CIFRE. «durata due ore» e «alle nove»
sono numeri in lettere e restano scoperti — coprirli vuol dire una lista di
parole per lingua, cioè la classe che questa casa ha visto cadere sei volte in
una notte. Prima il pezzo deterministico, misurato; la lista solo se il numero
la giustifica.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory

FONTE = ("Verbale del 3 marzo: si e' tenuta la riunione trimestrale. Ha "
         "partecipato il fornitore Bianchi. E' stato consegnato l'ordine 77. "
         "Il magazzino di Verona e' stato ispezionato.")


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


@pytest.mark.parametrize("claim", [
    "L'ordine 77 conteneva 40 pezzi.",
    "Il fornitore Bianchi ha partecipato per 45 minuti.",
    "L'ordine 77 vale 1200 euro.",
])
def test_un_valore_in_cifre_assente_dalla_fonte_non_passa(mem, claim):
    """IL CUORE: il moat li ammette a 97-99. La fonte non contiene 40, 45,
    1200 — e un numero che la fonte non dice non è un fatto verificato."""
    r = mem.add(claim, topic="az/v", source=FONTE)
    assert r.get("status") == "quarantined", (
        f"ammesso con g={r.get('grounding_score')}: {claim}")


@pytest.mark.parametrize("claim", [
    "Si e' tenuta la riunione trimestrale.",
    "Ha partecipato il fornitore Bianchi.",
    "E' stato consegnato l'ordine 77.",
    "Il magazzino di Verona e' stato ispezionato.",
])
def test_CONTROLLO_POSITIVO_i_fatti_VERI_passano(mem, claim):
    """⚠️ IL PRESIDIO CHE VALE PIÙ DELLA CURA. «E' stato consegnato l'ordine
    77» PORTA un numero — 77 — e quel numero è nella fonte: deve passare.

    Se questo cade, ho costruito un gate che rifiuta i fatti veri per il solo
    fatto che contengono una cifra, ed è molto peggio del difetto che curo."""
    r = mem.add(claim, topic="az/w", source=FONTE)
    assert r.get("status") != "quarantined", (
        f"fatto VERO trattenuto: {claim} (g={r.get('grounding_score')})")


@pytest.mark.parametrize("claim", [
    "Ha partecipato il fornitore Verdi.",
    "E' stato consegnato l'ordine 91.",
])
def test_le_entita_inventate_restano_fermate(mem, claim):
    """L'altro presidio: la classe che il gate già prendeva (0/4) non deve
    peggiorare. La cura si AGGIUNGE al moat, non lo sostituisce."""
    r = mem.add(claim, topic="az/x", source=FONTE)
    assert r.get("status") == "quarantined"


def test_senza_fonte_il_criterio_NON_scatta(mem):
    """Senza una fonte non c'è nulla con cui confrontare: il criterio non può
    dire niente e non deve inventarsi un verdetto. Un fatto scritto senza
    source resta un `model_claim`, come è sempre stato."""
    r = mem.add("La riunione e' durata due ore e sono stati consegnati 40 "
                "pezzi.", topic="az/y")
    assert r.get("status") != "quarantined"
    assert r.get("moat") == "not_run:no_source"


def test_il_valore_va_DICHIARATO_a_chi_scrive(mem):
    """Chi viene trattenuto deve sapere QUALE numero non torna: senza, si
    trova un fatto in quarantena e una fonte che a occhio lo sostiene."""
    r = mem.add("L'ordine 77 conteneva 40 pezzi.", topic="az/z", source=FONTE)
    testo = " ".join(str(w) for w in (r.get("warnings") or []))
    assert "40" in testo, r.get("warnings")
