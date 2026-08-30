"""`L1.20` dichiara e non trattiene: declassato ad AVVISO.

Ratifica del 2026-08-30 (canale `verimem-coord`, 3 SI' informati, zero veti):
«*`L1.20` DECLASSATO AD AVVISO nella forma di `L4-relazione`*». Le tre misure
indipendenti che l'hanno motivata:

    ws7   sugli 80 handoff: `L1.13` 68 volte, `L1.15` 40, **`L1.20` 2**
    ws5   banco a variabile singola (`951dc1fa`): i 4 verbali VERI che cadono
          sono fermati da `L1.13`, `L1.15`, `L1.16`, `L4-relazione` — **mai
          `L1.20`**
    ws4   rimisura indipendente su 5 verbali: `L1.13` per tre volte, `L1.15`,
          `L1.16`, **mai `L1.20`**

⇒ Come veto il beneficio misurato e' **zero** (ridondante: dove ferma, fermano
gia' i lessicali) e il costo non lo e' (ws8, `672172722d22d9fb`: un claim VERO
quarantinato a grounding 99.72 con `layers=['L1.20']`).

⚠️ **DECLASSARE NON E' SPEGNERE**, ed e' il punto che questi test presidiano:
il detector continua a girare e **il suo warning resta in ricevuta**. Chi legge
i `warnings` deve continuare a vedere che `L1.20` ha parlato — altrimenti la
cura scambierebbe un falso allarme con un presidio invisibile, che e' il difetto
gia' registrato in `test_l120_si_disarma_quando_il_daemon_c_e.py`.

⚖️ **CHE COSA NON DIMOSTRANO**: che il difetto dei verbali veri sia chiuso.
**Non lo e'** — quelli li fermano `L1.13`/`L1.15`/`L1.16`, che questa cura non
tocca, e il test `il_veto_lessicale_resta_intero` lo mette nero su bianco.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from verimem import semantic_selfclaim as ssc


def _vec(*components: float) -> np.ndarray:
    v = np.asarray(components, dtype=np.float32)
    return v / np.linalg.norm(v)


_HYPE = _vec(1.0, 0.05, 0.05)
_NEUTRAL = _vec(0.05, 1.0, 0.05)


def _fake_encode(text_or_texts):
    """Stesso spazio giocattolo di `test_l120_multilingual_selfclaim.py`: la
    logica e' deterministica e non carica alcun modello."""
    def one(t: str) -> np.ndarray:
        if "HYPEISH" in t:
            return _vec(0.9, 0.2, 0.1)
        if ssc._is_exemplar_text(t):
            return _HYPE
        return _NEUTRAL
    if isinstance(text_or_texts, str):
        return one(text_or_texts)
    return np.stack([one(t) for t in text_or_texts])


@pytest.fixture(autouse=True)
def _toy_space(monkeypatch):
    monkeypatch.setenv("ENGRAM_L1_SEMANTIC_T_HYPE", "0.7")
    monkeypatch.setenv("ENGRAM_L1_SEMANTIC_T_DELTA", "0.025")
    monkeypatch.setattr(ssc, "_default_encode", lambda: _fake_encode)
    ssc._reset_matrices_for_tests()
    yield
    ssc._reset_matrices_for_tests()


def _scrivi(proposition: str) -> dict:
    from verimem.client import Memory
    m = Memory(Path(tempfile.mkdtemp()) / "l120.db")
    return m.add(proposition)


#: Verificati soli-`L1.20` il 2026-08-30 prima di scrivere questi test: nessuno
#: innesca i detector lessicali, quindi `L1.20` e' l'unica ragione del verdetto.
#: Se un domani un lessicale li prendesse, il test perderebbe il suo bersaglio —
#: per questo `il_detector_parla_ancora` verifica ANCHE che il warning ci sia.
SOLO_L120 = [
    "HYPEISH la merce e' arrivata integra",
    "HYPEISH il pacco e' giunto intatto al destinatario",
    "HYPEISH la spedizione e' partita ieri dal deposito",
]


@pytest.mark.parametrize("proposition", SOLO_L120)
def test_l120_da_solo_non_trattiene_piu(proposition):
    """Il cuore della ratifica: dove `L1.20` e' l'UNICA ragione, il fatto entra."""
    r = _scrivi(proposition)
    layers = [w.get("layer") for w in (r.get("warnings") or []) if isinstance(w, dict)]
    assert layers == ["L1.20"], (
        f"premessa del test caduta: qui deve parlare SOLO L1.20, invece {layers!r}. "
        f"Se un lessicale ha iniziato a prendere questa frase, il test non sta "
        f"piu' misurando il declassamento.")
    assert r["status"] != "quarantined", (
        "L1.20 da solo ha trattenuto la scrittura: e' un VETO, e la ratifica "
        "del 30/08 lo vuole AVVISO")


@pytest.mark.parametrize("proposition", SOLO_L120)
def test_il_detector_parla_ancora_in_ricevuta(proposition):
    """Declassare non e' spegnere: il warning DEVE restare visibile.

    Senza questo, la cura sarebbe indistinguibile dal difetto gia' registrato in
    `test_l120_si_disarma_quando_il_daemon_c_e.py` — un presidio spento di cui
    la ricevuta non dice niente."""
    r = _scrivi(proposition)
    assert any(w.get("layer") == "L1.20" for w in (r.get("warnings") or [])), (
        "L1.20 non compare piu' in ricevuta: la cura ha SPENTO il detector "
        "invece di declassarlo")


def test_il_veto_lessicale_resta_intero():
    """CONTROLLO — e senza di lui i test sopra non varrebbero niente.

    Se il declassamento avesse disarmato l'intera famiglia L1, i test sopra
    passerebbero comunque e leggeremmo «cura riuscita» su un gate spento. Questa
    claim innesca `L1.10` e `L1.15` oltre a `L1.20`: **deve restare
    quarantinata**, ed e' la stessa frase del test storico
    `test_wired_into_the_gate`."""
    r = _scrivi("HYPEISH questo modulo funziona perfettamente ed e' validato")
    layers = {w.get("layer") for w in (r.get("warnings") or []) if isinstance(w, dict)}
    assert {"L1.10", "L1.15"} <= layers, (
        f"premessa caduta: qui devono parlare anche i lessicali, invece {layers!r}")
    assert r["status"] == "quarantined", (
        "la cura ha disarmato TUTTA la famiglia L1, non solo L1.20")
