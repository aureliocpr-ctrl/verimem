"""Il doctor nominava una soglia su due, e la banda è accesa di default.

Diceva::

    admission threshold in force: 40/100 … a write scoring below it is quarantined

⇒ Chi legge conclude «sopra 40 si passa». **Per tutta la fascia 40–80 non è
vero.** Con la banda accesa — ed è il default, `VERIMEM_CE_BAND_ENFORCE=1` — il
verdetto ha **tre** esiti::

    sotto 40      quarantinato
    fra 40 e 80   la banda: escalation a un giudice llm, o held-for-review
    sopra 80      ammesso

Le due costanti::

    LOCAL_CE_MOAT_THRESHOLD = 40.0
    CE_BAND_TAU_HI_DEFAULT  = 80.0

⚖️ IL README LO RACCONTA GIUSTO — «a two-threshold band (**on by default**)» —
e questa superficie no. È la stessa forma dei due pesi del modello
(`95e53832`): **due superfici che descrivono lo stesso meccanismo, e una
racconta metà.** Chi apre il doctor lo apre proprio per sapere quali regole
sono in vigore *adesso*.
"""
from __future__ import annotations

import pytest


def _la_banda_e_in_vigore() -> bool:
    """Se il regime di questa macchina prevede la banda.

    ⚠️ SI CHIEDE AL PRODOTTO, NON AL TESTO DEL REFERTO. La prima stesura
    saltava quando «band» non compariva nel detail — cioè esattamente quando la
    cura manca: il test non poteva essere rosso in nessun caso, ed è uno dei
    quattro stati che il registro nomina, il SENSORE SCOLLEGATO. Il RED su due
    alberi lo ha mostrato: senza la cura usciva «2 passed, 2 skipped».
    """
    try:
        from verimem.grounding_gate import _ce_band_enforced
        from verimem.local_grounding import judge_state
        return judge_state() != "absent" and _ce_band_enforced()
    except Exception:  # noqa: BLE001
        return False


def _riga_parametri(monkeypatch, banda: bool) -> str:
    # ⚠️ IL REGIME SI FORZA, NON SI SPERA. La banda esiste SOLO col giudice
    # locale (`doctor.py`: `if _giudice == "local" and _ce_band_enforced()`), e
    # il giudice in vigore lo decide `_autodetect_provider()` DALL'AMBIENTE.
    # In CI una OPENAI_API_KEY nell'ambiente lo sposta su `openai`: il doctor
    # allora tace sulla banda — correttamente — e questi test cadevano su
    # tutte e cinque le celle mentre erano verdi su ogni macchina di sviluppo.
    #
    # 🔑 LA GUARDIA SOPRA CHIEDEVA UNA DOMANDA DIVERSA DA QUELLA DEL PRODOTTO:
    # `judge_state() != "absent"` dice «il modello locale c'è sul disco», il
    # doctor chiede «il giudice IN VIGORE è quello locale». In CI il modello
    # c'è ma non decide lui ⇒ la guardia non saltava e l'asserzione mordeva a
    # vuoto. Misurato con un A/B nella stessa esecuzione:
    #     provider=mock    → giudice=local   guardia=True  prodotto_nomina=True
    #     provider=openai  → giudice=openai  guardia=True  prodotto_nomina=False
    #
    # ⚖️ NON restringo la guardia: allargarla è stata una cura deliberata
    # contro il sensore scollegato (vedi il suo docstring) e resta giusta per
    # la macchina SENZA modello locale. Forzo invece il giudice, così il test
    # misura davvero il regime che dichiara — anche dove l'ambiente ne impone
    # un altro. `doctor` importa il simbolo dentro la funzione, quindi la
    # sostituzione sul modulo `verimem.llm` lo raggiunge a ogni chiamata.
    monkeypatch.setattr("verimem.llm._autodetect_provider", lambda: None)
    monkeypatch.setenv("VERIMEM_CE_BAND_ENFORCE", "1" if banda else "0")
    from verimem import doctor as _d
    for c in _d.run_doctor():
        if c["name"] == "parameters":
            return c["detail"]
    pytest.fail("il check parameters non compare nel referto")


def test_con_la_banda_accesa_il_doctor_nomina_ENTRAMBE_le_soglie(monkeypatch):
    """IL CUORE: la soglia bassa da sola fa dedurre il contrario del vero per
    tutta la fascia di mezzo."""
    from verimem.grounding_gate import _ce_band_tau_hi
    if not _la_banda_e_in_vigore():
        pytest.skip("su questa macchina la banda non è in vigore")
    detail = _riga_parametri(monkeypatch, banda=True)
    assert f"{_ce_band_tau_hi():.0f}" in detail, (
        f"il doctor non nomina l'estremo alto della banda "
        f"({_ce_band_tau_hi():.0f}): {detail[:220]!r}")


def test_dice_che_la_fascia_di_mezzo_NON_passa(monkeypatch):
    """Non basta stampare il numero: va detto che cosa SUCCEDE là in mezzo.
    Un secondo numero senza il suo esito è un dettaglio, non una regola."""
    if not _la_banda_e_in_vigore():
        pytest.skip("su questa macchina la banda non è in vigore")
    detail = _riga_parametri(monkeypatch, banda=True)
    assert "does NOT pass" in detail, (
        f"il doctor nomina la banda ma non dice che la fascia di mezzo non "
        f"passa: {detail[:220]!r}")


def test_presidio_con_la_banda_SPENTA_la_riga_non_la_promette(monkeypatch):
    """⚖️ L'ALTRA POPOLAZIONE, e senza di essa la cura sarebbe il difetto
    speculare: se qualcuno spegne la banda, il doctor descriverebbe un
    meccanismo che non è in vigore — e allora sarebbero due esiti, che a quel
    punto è la verità."""
    detail = _riga_parametri(monkeypatch, banda=False)
    assert "two-threshold band" not in detail, (
        f"la banda è spenta ma il doctor la annuncia lo stesso: "
        f"{detail[:220]!r}")


def test_la_soglia_bassa_resta_dichiarata(monkeypatch):
    """Il presidio più banale e il più importante: aggiungere la seconda
    soglia non deve far sparire la prima."""
    for banda in (True, False):
        detail = _riga_parametri(monkeypatch, banda=banda)
        assert "admission threshold in force" in detail, (
            f"banda={banda}: la soglia di ammissione non è più dichiarata: "
            f"{detail[:160]!r}")
