"""Rilevatore: il numero del claim vive nella fonte SOLO dentro una numerazione.

Nasce dal caso misurato in `101b6f08`: il claim inventato «*la penale e' di 3
giorni*» prende **100.0** di grounding perche' la fonte contiene «**Art. 3** -
La penale...». Il `3` c'e' — ma e' il **numero dell'articolo**, non un valore.
La stessa caratteristica testuale che ingannava l'estrattore (curata in
`29ab5544`) inganna anche il **giudice**, su un layer diverso.

⚠️ **NON e' la cura che avevo in programma.** Quella — togliere la numerazione
dal testo — e' caduta: `select_relevant_span` non gira sotto i 1500 caratteri
(`5bd11563`), quindi l'unica forma sarebbe **alterare l'evidenza mostrata al
giudice**. Questo invece **non tocca niente**: guarda e dice.

🔑 **Perche' un rilevatore e non una cura**: un rilevatore che si **astiene**
costa zero; una cura che **edita l'evidenza** costa la verita'.

LA REGOLA, in tre passi:

    ① se il claim porta a sua volta un riferimento di sezione
       («*l'articolo 7 prevede...*») -> **ASTIENI**: il numero e' il suo
       soggetto, non un valore travestito.
    ② per ogni numero del claim, guarda DOVE compare nella fonte.
    ③ se compare **solo** dentro span di numerazione e **mai** fuori
       -> **SEGNALA**.

L'astensione di ① sta **dentro il rilevatore** e non nella cura, ed e' il punto:
condizionare una cura significa a volte editare e a volte no — condizionare un
rilevatore significa a volte parlare e a volte tacere. Il secondo e' reversibile.

⛔ **COSA NON FA**: non giudica se il claim sia vero, non tocca la fonte, non
sostituisce `L4.1`. Un numero **assente** dalla fonte non e' affar suo — quello
lo prende gia' `L4.1`. Qui il numero **c'e'**: e' *dove* sta a essere il difetto.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from verimem.quantity_match import (  # noqa: E402
    _RIFERIMENTO_RE,
    _spans_dei_riferimenti,
)

#: un numero "nudo": interi e decimali, senza ancorarsi alla punteggiatura
_NUMERO_RE = re.compile(r"\d+(?:[.,]\d+)?")


def _dentro(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


def avviso_numero_solo_strutturale(claim: str, source: str) -> dict | None:
    """`None` = nessun avviso (o astensione). Un dict = segnalazione.

    Il dict porta **perche'**: quale numero, e quale numerazione lo copre. Un
    avviso che non dice cosa guardare costringe a rifare la misura a mano.
    """
    if not claim or not source:
        return None

    # ① ASTENSIONE: il claim parla di una sezione, il numero e' il suo soggetto.
    if _RIFERIMENTO_RE.search(claim):
        return None

    spans = _spans_dei_riferimenti(source)
    if not spans:
        return None  # nessuna numerazione nella fonte: niente da confondere

    sospetti: list[dict] = []
    for m in _NUMERO_RE.finditer(claim):
        num = m.group(0)
        # ② dove compare questo numero nella fonte?
        occorrenze = [f.start() for f in re.finditer(
            r"(?<!\d)" + re.escape(num) + r"(?!\d)", source)]
        if not occorrenze:
            continue  # assente dalla fonte: e' L4.1 a occuparsene, non io
        coperte = [p for p in occorrenze if _dentro(p, spans)]
        # ③ SEGNALA solo se OGNI occorrenza e' dentro una numerazione
        if len(coperte) == len(occorrenze):
            ctx = source[max(0, coperte[0] - 14):coperte[0] + len(num) + 4]
            sospetti.append({
                "numero": num,
                "occorrenze": len(occorrenze),
                "contesto": ctx.replace("\n", " ").strip(),
            })

    if not sospetti:
        return None
    return {
        "layer": "L4.4-numero-solo-strutturale",
        "sospetti": sospetti,
        "reason": (
            "il numero del claim compare nella fonte SOLO dentro una "
            "numerazione di sezione (art./comma/§/riga): la fonte non lo "
            "afferma come valore"),
    }
