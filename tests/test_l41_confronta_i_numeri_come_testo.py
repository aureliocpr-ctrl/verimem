r"""L4.1 confronta i numeri come TESTO, non come VALORI — in ITALIANO e in INGLESE.

La stessa quantità scritta in due formati entrambi validi diventa due valori
diversi, e il claim viene quarantinato con il giudice che lo sostiene al 100.

    source (output di uno strumento):  committed=176.6 MB
    claim  (scritto in italiano):      «il committed e 176,6 MB»
    -> downgrade, layers=['L4.1'], grounding 100.0
       «il claim afferma un valore che la fonte non contiene: 6 mb, 176»

⇒ Il messaggio confessa il meccanismo: **`176,6` è stato spezzato in `176` e
`6 mb`**. Il pattern di `quantity_match.py:102` accetta come decimale **solo il
punto** — `(\d+(?:\.\d+)?)`.

⚠️ NON È UN PROBLEMA ITALIANO, ed è il punto che cambia la cura. In inglese la
virgola separa le MIGLIAIA, e il difetto si presenta specularmente::

    source «total=1,234 facts»  ·  claim «The store holds 1234 facts.»
    -> downgrade, layers=['L4.1', 'L4-grounding']

Stessa quantità, due scritture entrambe corrette, due valori diversi per L4.1.
⇒ **Una cura che aggiunga la virgola ai decimali romperebbe le migliaia inglesi**:
la strada non è allargare il pattern, è NORMALIZZARE i separatori prima di
confrontare, decidendo il ruolo della virgola dal contesto (tre cifre esatte
dopo = migliaia; altrimenti decimale).

Popolazione, misurata da @ws4 (fact `1198fadfc599`): su **144** scritture
`withheld_despite_judge=True` con grounding mediana **99.9**, i layer che le
vetano sono **L4.1 109 volte** e L4.2 43.

xfail(strict=True): il difetto esiste oggi. Quando qualcuno lo cura questo
diventa XPASS e la suite chiede di togliere il marcatore — così il difetto fa
rumore quando SMETTE di esistere, invece di restare un marcatore che nessuno
rilegge.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import run_validation_gate


def _layers(claim: str, source: str) -> list[str]:
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=source, grounding_llm=None,
                            ground_write=True)
    return [w.get("layer") for w in (getattr(r, "warnings", None) or [])]


def test_presidio_stesso_separatore_passa():
    """La controparte: col PUNTO in entrambi il caso passa. Senza di lei non si
    saprebbe se a fermare il claim è il separatore o il contenuto."""
    assert "L4.1" not in _layers("Con il tetto attivo il committed e 176.6 MB.",
                                 "committed=176.6 MB  per_thread=32.2 MB")


def test_la_virgola_decimale_italiana_non_spezza_il_numero():
    """CURATO. Era xfail(strict) e l'ha tolto la cura, non una mano: il pattern
    di `_QUANT_RE` accetta la virgola con 1-2 cifre e il valore viene
    normalizzato prima del confronto.

    ⚠️ NON BASTAVA IL PATTERN. Col solo pattern il test passava per la ragione
    sbagliata: `float("176,6")` solleva ValueError e il numero finiva nel
    `continue`, cioe' il claim smetteva di essere accusato perche' NON VENIVA
    PIU' CONFRONTATO. E' il difetto che il docstring di `numeri_ambigui`
    denuncia — «i falsi negativi nascono convertendo i veri positivi in
    silenzio». Verificato che adesso il valore c'e' davvero::

        extract_quantities("...176,6 MB.")  ->  [('mb', 176.6)]
        extract_quantities("...176.6 MB.")  ->  [('mb', 176.6)]
    """
    # ⚠️ NON BASTA «L4.1 non compare»: quell'asserzione e' vera anche quando il
    # numero non viene confrontato AFFATTO — ed e' il modo in cui questo stesso
    # test passava col pattern vecchio, misurato falsificando la cura. Si
    # asserisce quindi che il VALORE ci sia, ed e' uno solo.
    from verimem.quantity_match import extract_quantities
    virgola = extract_quantities("Con il tetto attivo il committed e 176,6 MB.")
    punto = extract_quantities("Con il tetto attivo il committed e 176.6 MB.")
    assert virgola == punto, (
        f"la stessa quantita' scritta con virgola e con punto deve dare lo "
        f"stesso valore: virgola={sorted(virgola)} punto={sorted(punto)}")
    assert ("mb", 176.6) in virgola, (
        f"«176,6 MB» deve dare UN valore 176.6, non nessuno e non due: {sorted(virgola)}")
    assert "L4.1" not in _layers("Con il tetto attivo il committed e 176,6 MB.",
                                 "committed=176.6 MB  per_thread=32.2 MB")


@pytest.mark.xfail(strict=True, reason=(
    "specularmente in inglese: la virgola delle MIGLIAIA nella fonte non si "
    "riconcilia con la stessa quantita' scritta senza separatore nel claim"))
def test_la_virgola_delle_migliaia_inglese_non_cambia_il_valore():
    assert "L4.1" not in _layers("The store holds 1234 facts.", "total=1,234 facts")
