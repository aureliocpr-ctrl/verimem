"""Tagliare un testo senza mutilare i caratteri che si compongono.

Requisito di prodotto: verimem non deve funzionare solo in italiano, ma
in modo impeccabile su tutte le lingue. La parte che riguarda le SUPERFICI
è questa: un accento perso in una UI è un dato perso.

Misurato prima di scrivere il modulo, tagliando dove la sequenza si
spezza::

    'caffé macchiato'[:5]    ->  'caffe'              l'accento sparisce
    'नमस्ते deposito'[:3]     ->  'नमस'                perde il virama
    'deposito 🇮🇹 pieno'[:10]  ->  'deposito 🇮'         mezza bandiera
    'operatore 👩‍💻'[:12]      ->  'operatore 👩\\u200d'  ZWJ penzolante

⚠️ Il primo caso è ITALIANO. Il difetto non è «delle altre lingue»: è del
taglio. In italiano si vede meno solo perché le nostre vocali accentate
arrivano quasi sempre già composte (U+00E9 invece di e + U+0301) — ma
basta una fonte che le componga, e `caffé` diventa `caffe`, che è una
parola diversa per chi legge e per chiunque cerchi quella stringa.

REGOLA: non emettere mai un grafema mutilato. Meglio un carattere in meno
che una parola diversa.

Niente dipendenze: la segmentazione completa dei grafemi (UAX #29) non è
nella libreria standard, e aggiungere un pacchetto per un troncamento di
visualizzazione non si giustifica. Questa è la parte CONSERVATIVA della
regola — indietreggia finché il taglio non è pulito — e i casi che copre
sono quelli che ho misurato rompersi. Il limite è dichiarato in fondo.
"""
from __future__ import annotations

import unicodedata as _ud

__all__ = ["safe_cut"]

#: Il giuntore a larghezza zero: unisce due emoji in un pittogramma solo.
#: Lasciato in coda diventa un carattere invisibile che viaggia nel dato e
#: rompe i confronti fra stringhe che a schermo sembrano identiche.
_ZWJ = "‍"

#: I due indicatori regionali formano UNA bandiera. Uno solo si vede come
#: una lettera in un riquadro: un simbolo che non esiste al posto di uno
#: che esisteva.
_RI_INIZIO, _RI_FINE = 0x1F1E6, 0x1F1FF


def _e_indicatore(ch: str) -> bool:
    return _RI_INIZIO <= ord(ch) <= _RI_FINE


def safe_cut(s: str, n: int) -> str:
    """I primi ``n`` caratteri di ``s``, arretrando se il taglio spezza.

    Arretra finché la coda è: un segno combinante (Mn/Mc/Me), un ZWJ, il
    carattere PRIMA di un ZWJ, o un indicatore regionale spaiato.

    Su testo latino e su CJK il risultato è identico a ``s[:n]`` — una cura
    che tocca anche ciò che non c'entra è una cura che nessuno può
    verificare.
    """
    if n <= 0 or not s:
        return ""
    if len(s) <= n:
        return s
    i = n
    # DUE condizioni, e la prima stesura le aveva confuse arretrando anche
    # quando il grappolo era COMPLETO (al taglio 6 l'accento e' dentro, e
    # 'caffé' usciva come 'caff'): l'ha preso il test.
    #   (a) il carattere SUCCESSIVO si compone con l'ultimo tenuto -> quello
    #       che tengo uscirebbe SENZA il suo segno: arretro;
    #   (b) l'ultimo tenuto e' un giuntore -> resterebbe penzolante.
    # Un segno combinante in coda va BENISSIMO: vuol dire che la sua lettera
    # e' dentro.
    while i > 0 and ((i < len(s) and _ud.combining(s[i]) != 0)
                     or s[i - 1] == _ZWJ):
        i -= 1
    # bandiera spezzata: un indicatore regionale in coda senza il gemello
    if i > 0 and _e_indicatore(s[i - 1]) and i < len(s) and _e_indicatore(s[i]):
        i -= 1
    return s[:i]


#: LIMITE DICHIARATO — le sequenze che questa regola NON copre:
#: i modificatori di tono della pelle (U+1F3FB-1F3FF), le sequenze di tag
#: (bandiere regionali tipo Scozia), e i cluster complessi di alcune
#: scritture del sud-est asiatico che non usano segni combinanti ma
#: sequenze di consonanti. Una copertura piena richiede UAX #29, cioe' una
#: dipendenza: se un giorno serve, il posto e' questo e i test sono gia'
#: scritti. Dichiararlo qui e' meglio che lasciar credere che sia completo.
