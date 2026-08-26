"""Una frase irrilevante nella fonte puo' ribaltare il verdetto del moat.

Misurato il 2026-08-26 alle 21:30, `aad97bcd`, fuori da pytest, store isolato
con `Memory(path=...)`. Claim fisso, nucleo che lo smentisce sempre presente e
mai modificato; l'unica variabile e' cio' che si aggiunge dopo:

    claim:   «Il lotto B12 e' conforme alle specifiche.»
    nucleo:  «Due pezzi del lotto B12 risultano difformi.»

    frasi   char   esito    grounding
    1       43     TRATT      1.8
    2       92     passa     98.9   <- «La mensa aziendale resta chiusa il primo maggio.»
    3       132    passa     99.2
    5       218    passa     99.8

La zavorra ESTRANEA (mensa, corso d'inglese, parcheggio) alza piu' di quella
pertinente al lotto (98.9 contro 97.5): non e' che il contorno sostenga il claim.

⚠️ NON E' UNIVERSALE, e il banco lo dice tenendo dentro il caso che regge. Su
quattro coppie ribalta una sola:

    conforme/difforme  (smentita lontana)  TRATT  1.8  ->  passa  98.9   ribalta
    copertura          (smentita lontana)  TRATT  0.4  ->  TRATT  78.4   +78,0
    collaudo           (smentita vicina)   TRATT 10.3  ->  TRATT   1.6    -8,7
    pagamento          (smentita vicina)   TRATT  2.6  ->  TRATT   1.9    -0,7

Il SEGNO dello spostamento separa le due classi 2 su 2 per direzione: dove la
smentita ripete la parola del claim il punteggio scende, dove non la ripete sale.
Pattern su quattro casi, non legge. Meccanismo compatibile ma NON verificato: il
giudizio prenderebbe la miglior corrispondenza locale — con una frase sola non ha
scelta, con piu' frasi trova una finestra che non contraddice.

Cio' che questo banco afferma e' ESISTENZIALE — «esiste una fonte in cui una
frase irrilevante ribalta il verdetto» — e un caso lo stabilisce. «Succede
sempre» sarebbe universale, vorrebbe una popolazione, e non e' misurato.

⇒ Conseguenza per le misure di casa: le batterie sulla contraddizione (0/10 IT e
EN di ws3, 4/4 con grounding 0.6-1.3 mia) usavano fonti brevi. Restano corrette
nel loro regime; il trasferimento alle fonti reali — output di pytest, log di CI,
documenti — non e' dimostrato.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

ZAVORRA = "La mensa aziendale resta chiusa il primo maggio."
CLAIM = "Il lotto B12 e conforme alle specifiche."
NUCLEO = "Due pezzi del lotto B12 risultano difformi."
# il caso che REGGE: la smentita ripete la parola del claim
CLAIM_VICINO = "Il collaudo del lotto B12 e stato superato."
NUCLEO_VICINO = "Il collaudo del lotto B12 non e stato eseguito."


def _stato(claim: str, fonte: str) -> tuple[str, float | None]:
    mem = Memory(str(Path(tempfile.mkdtemp()) / "z.db"))
    ric = mem.add(claim, topic="t/zavorra", source=fonte, validate="full")
    return str(ric.get("status")), ric.get("grounding_score")


def test_CONTROLLO_con_la_sola_smentita_il_moat_la_ferma():
    """Il righello: se non ferma nemmeno questo, l'xfail sotto non dice nulla."""
    stato, punteggio = _stato(CLAIM, NUCLEO)
    assert stato == "quarantined", (
        f"il moat non ferma il claim contro la sola smentita ({stato}, g={punteggio}): "
        "senza questo il banco non misura l'effetto della zavorra"
    )


@pytest.mark.xfail(
    strict=True,
    reason="una frase irrilevante ribalta il verdetto: da quarantined g=1.8 a "
    "ammesso g=98.9, con la smentita invariata nella fonte (26/08)",
)
def test_una_frase_irrilevante_non_dovrebbe_cambiare_il_verdetto():
    stato, punteggio = _stato(CLAIM, f"{NUCLEO} {ZAVORRA}")
    assert stato == "quarantined", f"ammesso con g={punteggio} grazie a una frase sulla mensa"


def test_E_NON_E_UNIVERSALE_dove_la_smentita_ripete_la_parola_del_claim_regge():
    """L'altra popolazione, e sta qui perche' il banco non deve esagerare.

    Su quattro coppie ne ribalta una: le due in cui la smentita ripete la parola
    del claim reggono, e il punteggio scende invece di salire.
    """
    solo, g_solo = _stato(CLAIM_VICINO, NUCLEO_VICINO)
    con, g_con = _stato(CLAIM_VICINO, f"{NUCLEO_VICINO} {ZAVORRA}")
    assert solo == "quarantined", f"il righello del caso vicino e' caduto: {solo}"
    assert con == "quarantined", (
        f"anche il caso «vicino» ora ribalta (g={g_con} contro {g_solo}): l'effetto "
        "e' piu' esteso di quanto il banco dichiari, allargare la misura"
    )
