"""`verimem doctor` non poteva uscire 0 su un'installazione fatta col README.

Il comando dichiara il proprio contratto (`cli.py:472`)::

    Exit code: 0 all-ok · 1 warnings · 2 failures (scriptable)

Ma due check segnalavano come avviso ciò che il prodotto documenta come
NORMALE, e quindi `all-ok` era irraggiungibile. Misurato il 16/08 su uno store
fresco::

    senza nulla              9 check, 2 warn (offline + llm)   EXIT 1
    con VERIMEM_OFFLINE=1    9 check, 1 warn (llm)             EXIT 1

⇒ L'ultimo avviso si spegne solo configurando un provider llm — cioè proprio
ciò che il README dichiara **due volte** non necessario (`README:36` «It works
with no llm», `README:252` «No llm needed for the moat»). ⇒ **Chi segue il
README esegue il comando che il README gli prescrive per verificare l'install e
riceve un fallimento.** In un Dockerfile o in una CI, `doctor` che esce 1 è un
deploy fallito su un'installazione perfetta.

Trovato da ws4 misurando il percorso di installazione; la causa è stata isolata
leggendo il contratto invece di configurare un llm.

═══ PERCHÉ SI CURA LA CLASSIFICAZIONE E NON L'EXIT CODE ═══

La semantica 0/1/2 è buona e scriptabile: va tenuta. Ciò che era sbagliato è
chiamare «avviso» l'assenza di una cosa opzionale. L'informazione resta — il
messaggio dice ancora cosa NON è disponibile senza llm, e come attivarlo — ma
non trascina più l'intero verdetto.

⚠️ Un avviso vero resta un avviso: se la sonda del provider FALLISCE, quello è
un problema e continua a valere WARN (`test_una_sonda_rotta_resta_un_avviso`).
"""
from __future__ import annotations

import pytest

from verimem import doctor as doc


def _checks(**kw) -> dict[str, dict]:
    return {c["name"]: c for c in doc.run_doctor(**kw)}


@pytest.fixture(autouse=True)
def _senza_flag_offline(monkeypatch):
    from verimem.airgap import _OFFLINE_FLAGS
    for f in _OFFLINE_FLAGS:
        monkeypatch.delenv(f, raising=False)


def test_senza_llm_il_check_non_e_un_avviso(monkeypatch):
    """Il README promette due volte che l'llm non serve: la sua assenza non
    può essere l'anomalia che rende non-zero l'uscita."""
    import verimem.llm as llm_mod
    monkeypatch.setattr(llm_mod, "_autodetect_provider", lambda: None)

    c = _checks()["llm"]
    assert c["status"] == doc.OK, (
        f"«no llm» è classificato {c['status']}: è la configurazione che il "
        f"README insegna, e da sola porta `doctor` a uscire 1. Dettaglio: "
        f"{c['detail']}")


def test_senza_llm_il_messaggio_dice_ancora_cosa_resta_spento(monkeypatch):
    """⚠️ La cura non deve TACERE: cambia il verdetto, non l'informazione."""
    import verimem.llm as llm_mod
    monkeypatch.setattr(llm_mod, "_autodetect_provider", lambda: None)

    c = _checks()["llm"]
    assert "llm" in c["detail"].lower(), c["detail"]
    assert c.get("fix"), (
        "senza provider l'utente deve continuare a leggere COME attivarne uno")


def test_non_essere_air_gapped_non_e_un_avviso():
    """Il suggerimento del check stesso dice «for air-gapped deploys»: non
    esserlo è la condizione normale, non un difetto da segnalare."""
    c = _checks()["offline"]
    assert c["status"] == doc.OK, (
        f"«no offline flag set» è classificato {c['status']}, ma non essere in "
        f"air-gap è il caso normale. Dettaglio: {c['detail']}")


def test_una_sonda_rotta_resta_un_avviso(monkeypatch):
    """⚠️⚠️ LA POPOLAZIONE OPPOSTA — senza questo, «doctor non avvisa più» si
    soddisfa anche rendendolo cieco. Se la sonda del provider ESPLODE, quello è
    un problema vero e deve restare un avviso."""
    import verimem.llm as llm_mod

    def _esplode():
        raise RuntimeError("sonda rotta")

    monkeypatch.setattr(llm_mod, "_autodetect_provider", _esplode)
    c = _checks()["llm"]
    assert c["status"] == doc.WARN, (
        f"la sonda del provider ha sollevato un'eccezione e il check dice "
        f"{c['status']}: un guasto vero deve restare visibile")


def test_un_provider_configurato_viene_ancora_nominato(monkeypatch):
    """L'altra metà della popolazione: quando un provider C'È, `doctor` deve
    continuare a dirlo — altrimenti la cura ha reso il check muto."""
    import verimem.llm as llm_mod
    monkeypatch.setattr(llm_mod, "_autodetect_provider", lambda: "anthropic")

    c = _checks()["llm"]
    assert c["status"] == doc.OK
    assert "anthropic" in c["detail"], c["detail"]
