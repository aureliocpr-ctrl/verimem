"""Un accento scritto con l'apostrofo non deve spegnere il presidio metrico.

`L1.19` chiede un'attestazione di misura ai claim quantitativi: «Latency is 240
ms» senza un `bench:`/`measure:` in `verified_by` viene quarantinato. Il
presidio riconosce l'italiano — il pattern nomina `latenza`, e un commento nel
modulo racconta la cura che ci fu quando si scoprì che «La latenza e 40 ms»
(copula NUDA, senza accento) sfuggiva mentre «La latenza è 40 ms» cadeva.

Quella cura coprì la copula nuda e NON la forma con l'apostrofo, che è l'altro
modo in cui un accento sparisce — e il più comune di tutti quando si scrive da
terminale, dove gli accenti si perdono fra heredoc, redirezioni e pipe.

MISURATO sullo store reale prima di questa cura: fra i claim metrici con un
numero e non ritirati, quelli scritti con «e'» erano 48 e i quarantinati ZERO,
contro il 25,8% (8 su 31) di quelli scritti con «è» — su una quota complessiva
dell'8,5%. Su 48 casi, con quella quota, ce ne si aspetterebbero circa quattro.

⚠️ LE CINQUE FORME INSIEME, e non è pedanteria: la lezione del difetto che
questo file cura è che una cura misurata sulla sola popolazione da cui è nata
sembra sempre sufficiente. La copula nuda fu curata guardando la copula nuda.
Qui il presidio è l'intera famiglia — accento, apostrofo, nudo, assente,
inglese — così che la prossima variante che manca si veda come un buco nella
tabella invece che come un caso da scoprire di nuovo fra due settimane.
"""
from __future__ import annotations

import pytest

from verimem.l1_quantitative_detector import detect_unsupported_quant_claim

#: (etichetta, claim). Dentro ogni famiglia le cinque righe dicono LA STESSA
#: COSA e nessuna porta un'attestazione: il presidio deve vederle tutte.
#:
#: ⚠️ LE FAMIGLIE SONO DUE PERCHE' I PATTERN SONO DUE. Il difetto è stato
#: misurato sulla latenza, ma `_QUANT_PATTERNS` porta la stessa alternanza
#: della copula anche nel pattern delle percentuali: curare solo il punto in
#: cui il difetto è stato notato avrebbe lasciato in piedi la sua copia due
#: righe più sotto. Chi aggiunge un pattern con una copula italiana aggiunga
#: qui la sua famiglia.
FORME = [
    ("latenza/accento", "La latenza è 240 ms."),
    ("latenza/apostrofo", "La latenza e' 240 ms."),
    ("latenza/copula nuda", "La latenza e 240 ms."),
    ("latenza/senza copula", "Latenza 240 ms."),
    ("latenza/inglese", "Latency is 240 ms."),
    ("percentuale/accento", "La copertura è 42.6%."),
    ("percentuale/apostrofo", "La copertura e' 42.6%."),
    ("percentuale/copula nuda", "La copertura e 42.6%."),
    ("percentuale/senza copula", "Copertura 42.6%."),
    ("percentuale/inglese", "Coverage is 42.6%."),
]


@pytest.mark.parametrize("etichetta,claim", FORME, ids=[f[0] for f in FORME])
def test_ogni_forma_della_copula_lascia_intatto_il_presidio(etichetta, claim):
    """Nessuna di queste scritture deve poter aggirare L1.19."""
    esito = detect_unsupported_quant_claim(proposition=claim, verified_by=[])
    assert esito is not None, (
        f"la forma «{etichetta}» aggira il presidio metrico: {claim!r} passa "
        "senza chiedere un'attestazione, mentre le altre scritture dello "
        "stesso identico claim vengono fermate"
    )


def test_una_attestazione_vera_fa_passare_il_claim():
    """⛔ CONTROLLO NEGATIVO — senza questo, un detector che dicesse SEMPRE
    «non attestato» supererebbe il test sopra a pieni voti ed è inutile.

    La prova che il presidio discrimina è che TOGLIENDO il motivo del veto —
    qui: fornendo l'attestazione che chiede — il verdetto cambi."""
    esito = detect_unsupported_quant_claim(
        proposition="La latenza e' 240 ms.",
        verified_by=["bench:latenza_2026_08"])
    assert esito is None, (
        "con un'attestazione in verified_by il claim deve passare: se cade "
        "lo stesso, il presidio non sta guardando l'attestazione e il test "
        "sopra non misura ciò che dice di misurare"
    )
