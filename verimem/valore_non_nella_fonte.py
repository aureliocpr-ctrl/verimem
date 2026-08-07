"""Il controllo DETERMINISTICO claim↔fonte che al gate mancava.

IL DIFETTO CHE LO MOTIVA, misurato da ws5 e riprodotto: stessa fonte, stesso
giudice, due popolazioni di claim falsi::

    A  inventa un'ENTITÀ (fornitore Verdi, ordine 91)   ammessi 0/4   il moat li ferma
    B  DETTAGLIO non detto su un'entità VERA            ammessi 5/5   con g 97,1–99,5

        «L'ordine 77 conteneva 40 pezzi.»                   g=97.1
        «Il fornitore Bianchi ha partecipato per 45 minuti» g=98.7
        «L'ordine 77 vale 1200 euro.»                       g=98.0

🔑 (B) è la forma in cui un LLM allucina davvero: non inventa un fornitore che
non esiste, inventa la durata, l'importo, il numero di pezzi. Ed entra col
punteggio più alto del sistema.

LA DIAGNOSI È DI ws5, e ha un indirizzo::

    «Nessun rilevatore L1 riceve la fonte. Il confronto claim↔fonte esiste in
     UN SOLO posto: dentro il cross-encoder, che è esattamente quello che
     sbaglia su questa classe.
        L1  vede il claim, NON la fonte
        L4  vede claim + fonte, ma confonde PLAUSIBILE con IMPLICATO
     ⇒ manca un controllo DETERMINISTICO claim↔fonte»

e da ws4 il numero che la rende strutturale: il 91,8% dei verdetti del moat sta
agli estremi (1324 su 1673 sopra 99) — **nessuna soglia può separare**, perché
il difetto non è dove si taglia: è che il giudice dà lo stesso punteggio a un
fatto vero e a un dettaglio inventato.

QUESTO MODULO NON USA MODELLI. Confronta i valori numerici del claim con quelli
della fonte, e non decide se il claim sia vero: dice che **un numero che la
fonte non contiene non è un numero verificato**.

⚠️ LIMITI DICHIARATI, entrambi misurati e non aggirati:
  * copre i valori in CIFRE. «durata due ore» e «alle nove» sono numeri in
    LETTERE e restano scoperti. Coprirli vuol dire una lista di parole per
    lingua — la classe che in questa casa è caduta sei volte in una notte.
    Prima il pezzo deterministico; la lista solo se il numero la giustifica.
  * un ANNO nudo non è una quantità (lo esclude già `extract_quantities`): «il
    contratto scade nel 2027» non è un dettaglio inventato dello stesso genere,
    e il percorso delle date è un altro.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .quantity_match import extract_quantities

__all__ = ["ValoreAssente", "valori_non_nella_fonte"]


@dataclass(frozen=True)
class ValoreAssente:
    """Un valore che il claim afferma e la fonte non contiene."""
    valore: float
    unita: str


_DECIMALI_RE = re.compile(r"(?<![\w.])\d+[.,](\d+)")


def _tolleranza_dichiarata(testo: str, valore: float) -> float:
    """±mezza unità dell'ultima cifra che il claim SCRIVE.

    IL FALSO POSITIVO CHE LA MOTIVA, trovato da ws1 senza cercarlo — al primo
    fatto vero salvato dopo la cura::

        fonte «durata 443.0485324859619»  ·  claim «443 secondi»
        -> QUARANTINATO, con grounding 100.0

    Troncare un decimale è la forma più comune in cui un umano riporta una
    durata: il falso positivo è ad alta frequenza.

    🔑 IL CRITERIO È DI ws5, e le due alternative le ha fatte cadere lui stesso:
      * **prefisso letterale** («443» sta dentro «443.048…»): ammette anche
        «44», che è un altro numero. veri 6/10, falsi fermati 8/9.
      * **tolleranza relativa ≤1%**: 19/19 sugli arrotondamenti, poi cade 4
        volte su 4 dove l'1% è una differenza VERA — «505» da «500 mg» è
        un'altra dose, «4.03» da «4 per cento» un altro tasso. *L'1% di una
        durata è rumore, l'1% di una dose è un errore clinico.*

    Un numero riportato con k decimali **dichiara la propria precisione**:
    ``0.5 * 10^-k``. Non è una costante che abbiamo scelto noi — la sceglie chi
    scrive il numero, ed è il modo standard in cui scienza e ingegneria
    trattano un valore riportato. Per questo regge su domini che nessuno di noi
    ha previsto: non c'è niente da ri-calibrare.

    Si contano i decimali SCRITTI e non quelli del float: ``443`` e ``443.00``
    sono lo stesso valore e due precisioni diverse, e il float non lo ricorda.
    Fallback prudente a ``0.5`` (intero) quando la cifra non si ritrova nel
    testo — la stessa tolleranza che il claim si attribuirebbe scrivendola
    senza decimali.
    """
    intero = int(valore) if float(valore).is_integer() else valore
    for m in _DECIMALI_RE.finditer(testo):
        try:
            if abs(float(m.group(0).replace(",", ".")) - valore) < 1e-12:
                return 0.5 * (10.0 ** -len(m.group(1)))
        except ValueError:  # pragma: no cover - gruppo non numerico
            continue
    del intero
    return 0.5


def valori_non_nella_fonte(proposition: str, source: str) -> list[ValoreAssente]:
    """I valori numerici del claim che nella fonte non compaiono.

    Vuoto quando manca uno dei due testi: senza fonte non c'è nulla con cui
    confrontare, e inventarsi un verdetto è esattamente ciò che questo modulo
    esiste per impedire.

    Si confrontano i VALORI e non le coppie (unità, valore): «l'ordine 77» e
    «77 pezzi» portano lo stesso numero con unità diverse, e l'unità in un
    testo libero è la parola che segue — troppo fragile per farci poggiare un
    veto. Il valore no: o quel numero è nella fonte, o non c'è.
    """
    if not proposition or not source:
        return []
    nel_claim = extract_quantities(proposition)
    if not nel_claim:
        return []
    nella_fonte = {v for _u, v in extract_quantities(source)}
    fuori: list[ValoreAssente] = []
    for u, v in sorted(nel_claim, key=lambda q: q[1]):
        if v in nella_fonte:
            continue
        # UN ARROTONDAMENTO NON E' UN'INVENZIONE. Confronto STRETTO (`<` e non
        # `<=`): sulle 38 prove di ws5 l'inclusivo dava 37/38 e lo stretto
        # 38/38 — al bordo esatto due valori sono distinguibili, e ammetterli
        # sarebbe la stessa indulgenza che ha fatto cadere la tolleranza fissa.
        tol = _tolleranza_dichiarata(proposition, v)
        if any(abs(v - y) < tol for y in nella_fonte):
            continue
        fuori.append(ValoreAssente(valore=v, unita=u))
    return fuori
