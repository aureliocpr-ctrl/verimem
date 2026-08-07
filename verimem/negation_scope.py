"""La PORTATA di una negazione: quel «non» governa questa parola?

Il LESSICO dei negatori non sta qui e non si riscrive: vive in
``quantity_match._NEGATOR_RE``, esteso a undici lingue il 2026-08-03
(``d06f1521``) dopo aver scoperto che il prodotto sapeva riconoscere una
negazione italiana **in due posti diversi e mai insieme**. Questo modulo
aggiunge l'unica cosa che a quella superficie mancava per servire i detector
L1: sapere **fin dove arriva** il negatore.

PERCHE' ESISTE (2026-08-04). Curata la negazione dentro ``l1_tested_detector``,
ws5 ha misurato la cura e ha trovato che nove detector su dodici avevano lo
stesso difetto:

    L1.10  «Il modulo NON funziona in produzione.»          scattava
    L1.11  «Il sistema NON e' pronto per la produzione.»    scattava
    L1.12  «Il servizio NON e' sicuro contro SQL injection» scattava
    L1.13  «La migrazione NON e' completata.»               scattava
    L1.14 · L1.16 · L1.17 · L1.18                           scattavano

Un gate anti-confabulazione che punisce «questo non funziona» scoraggia
esattamente la scrittura piu' preziosa per una memoria verificata — la
smentita, il limite noto, il non-ancora-fatto: chi e' onesto viene quarantinato
e chi tace no.

⚠️ LA GUARDIA STA IN UN PUNTO SOLO, e questo e' il punto. Copiarla in nove
detector sarebbe la seconda classe ricorrente di questo progetto — una copia
invece della superficie unica — e fra sei mesi le nove copie divergerebbero
come sono gia' divergiate le due liste di negatori. Applicata dove i warning si
raccolgono, vale per i detector di oggi **e per quelli che verranno scritti
domani**.
"""
from __future__ import annotations

import re

from .quantity_match import _NEGATOR_RE

#: Confini oltre i quali un negatore sta parlando di un'ALTRA cosa. Senza
#: questi, «non e' stato rilasciato, ma funziona» risulterebbe negato tutto, e
#: un «non» in apertura spegnerebbe il gate su ogni claim successivo — cioe'
#: la guardia diventerebbe un interruttore per chi la conosce.
_FINE_PORTATA = re.compile(
    r"[,;.:!?]|\bma\b|\bpero'?\b|\bbut\b|\byet\b|\bhowever\b|\btuttavia\b",
    re.IGNORECASE,
)

#: Quanto indietro guardare. «non e' mai stato validato» sono 25 caratteri;
#: sessanta lasciano spazio a un paio di ausiliari senza raccogliere la frase
#: precedente, che comunque e' tagliata dalla punteggiatura.
_FINESTRA = 60


def governata_da_negazione(testo: str, inizio: int) -> bool:
    """C'e' un negatore che governa la parola che comincia a ``inizio``?"""
    if not testo or inizio <= 0:
        return False
    finestra = testo[max(0, inizio - _FINESTRA):inizio]
    tagli = [m.end() for m in _FINE_PORTATA.finditer(finestra)]
    if tagli:
        finestra = finestra[tagli[-1]:]
    return bool(_NEGATOR_RE.search(finestra))


def tutte_le_occorrenze_sono_negate(testo: str, parola: str) -> bool:
    """Ogni occorrenza di ``parola`` in ``testo`` e' sotto una negazione?

    Serve al filtro sui warning, che conosce la parola scatenante ma non la sua
    posizione. La domanda e' volutamente al plurale: se il fatto dice «non
    funziona in staging» **e** «funziona in produzione», il claim c'e' e va
    visto. Basta un'occorrenza libera perche' il warning resti.

    Restituisce ``False`` se la parola non compare (niente da negare): un
    warning che nomina qualcosa che non e' nel testo non va toccato.
    """
    if not testo or not parola:
        return False
    trovata = False
    for m in re.finditer(re.escape(parola), testo, re.IGNORECASE):
        trovata = True
        if not governata_da_negazione(testo, m.start()):
            return False
    return trovata


def e_un_claim_negativo(testo: str) -> bool:
    """Il claim afferma un'ASSENZA?

    Domanda diversa dalle due qui sopra, che chiedono se una PAROLA e' sotto
    negazione. Al moat serve sapere se l'intero claim e' una smentita, perche'
    su quella classe il suo verdetto non e' affidabile: un cross-encoder di
    entailment non ha l'assunzione di mondo chiuso, quindi «Verdi non era
    presente» non risulta implicato da un elenco che semplicemente non lo
    nomina (misurato: g fra 0.42 e 1.39 su negazioni VERE, in quattro lingue).

    Sta qui e non nel gate perche' il lessico dei negatori vive in un posto
    solo — ``quantity_match._NEGATOR_RE``, undici lingue — e la lezione che ha
    creato questo modulo e' esattamente che il prodotto riconosceva una
    negazione «in due posti diversi e mai insieme».
    """
    return bool(testo) and bool(_NEGATOR_RE.search(testo))


__all__ = ["e_un_claim_negativo", "governata_da_negazione",
           "tutte_le_occorrenze_sono_negate"]
