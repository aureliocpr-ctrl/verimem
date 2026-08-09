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

from .quantity_match import _QUANT_RE, claim_span, extract_quantities

__all__ = ["ValoreAssente", "valori_non_nella_fonte"]


def _numeri_come_scritti(testo: str) -> dict[float, str]:
    """``{valore: il numero COM'E' SCRITTO}`` per i numeri del claim.

    Legge ``_QUANT_RE`` sullo stesso ``claim_span`` che usa
    ``extract_quantities``: il legame valore→testo e' esatto PER COSTRUZIONE,
    non ritrovato a posteriori. E' la differenza fra conservare e indovinare,
    ed e' il motivo per cui questa strada e' stata scelta contro l'alternativa
    di ricercare il token al punto di stampa.

    ⚠️ LIMITE DICHIARATO: se due scritture DIVERSE danno lo stesso ``float``
    («2607.2676» e «2607.26760» nello stesso claim) qui ne resta una — la
    prima. Non e' l'ambiguita' che affossa la ricerca a posteriori: la' i
    candidati sono tutti i numeri del testo, qui solo quelli che collassano
    sullo stesso valore, e fra quelli il gate non ha comunque nulla da
    distinguere: sono lo stesso numero.
    """
    fuori: dict[float, str] = {}
    for m in _QUANT_RE.finditer(claim_span(testo)):
        try:
            v = float(m.group(1))
        except ValueError:      # pragma: no cover — la regex cattura cifre
            continue
        fuori.setdefault(v, m.group(1))
    return fuori


@dataclass(frozen=True)
class ValoreAssente:
    """Un valore che il claim afferma e la fonte non contiene.

    ``testo`` E' IL NUMERO COM'E' SCRITTO NEL CLAIM, e non e' un lusso: senza,
    il gate stampava una cifra che l'utente non aveva mai scritto. Il caso, reale
    e trovato da ws8 usando il prodotto (id=21b5710c46f5)::

        claim  «Il paper Metis arXiv 2607.26760 elenca fra le affiliazioni ...»
        gate   «il claim afferma un valore che la fonte non contiene: 2607.27»

    Il ``2607.27`` non era nel claim ne' nella fonte: nasceva da ``f"{v:g}"``,
    che tiene SEI cifre significative e arrotonda. Corrompe ogni identificatore:
    ``1706.03762`` (Attention is all you need) diventa ``1706.04``.

    🔑 E NON BASTAVA STAMPARE PIU' CIFRE: lo zero finale muore prima, nella
    ``float()`` — ``2607.26760 -> 2607.2676`` — quindi ``:.15g`` darebbe ancora
    la cifra sbagliata. ws8, che ha scelto questa strada contro l'alternativa di
    ricostruire il token a valle: «(B) non e' rischiosa, e' IMPOSSIBILE: chiede
    una funzione inversa che non esiste; non puo' RITROVARE il token, puo' solo
    INDOVINARE quale pezzo di testo lo abbia generato» — e il suo referto di
    quella sera cita CINQUE id arXiv nello stesso claim, tutti della stessa
    forma. Qui invece il testo non si indovina: si conserva quando lo si legge.
    """
    valore: float
    unita: str
    #: vuoto solo per i costruttori che non lo passano: nessuno, oggi, fuori da
    #: questo modulo (verificato: `grep ValoreAssente(` non da' altri esiti).
    testo: str = ""

    def come_scritto(self) -> str:
        """Il numero da mostrare a chi legge: il suo, se ce l'abbiamo.

        Il ripiego su ``:g`` resta per i (nessuni) costruttori che non passano
        ``testo``, ed e' deliberatamente identico al comportamento vecchio: un
        ripiego che cambia anche il resto nasconderebbe quando viene usato.
        """
        return self.testo or f"{self.valore:g}"


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
    come_scritti = _numeri_come_scritti(proposition)
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
        fuori.append(ValoreAssente(valore=v, unita=u,
                                   testo=come_scritti.get(v, "")))
    return fuori
