"""Il banco e2e aveva il dato dell'over-abstention e non lo contava.

`answerable_correct` si calcolava così::

    ok = a != "no answer" and any(x in a for x in must)

Un'astensione su una domanda che HA risposta finiva fra le «non corrette» e
**non veniva mai distinta da una risposta sbagliata**. Due fallimenti opposti —
si curano in direzioni diverse — sommati sotto un unico numero, dove nessuno
dei due si vede.

Il dato c'era già nel `detail` di ogni riga (`answer == "no answer"`). Sui due
run committati in `benchmark/results/`::

    answerable = 10   corrette = 8   ASTENUTE = 2

⇒ Un quarto dei fallimenti erano astensioni, e il referto non lo diceva.

⚠️ IL BANCO NON SI PUÒ ESEGUIRE QUI: chiede un LLM vero. Quindi questi test
NON provano la funzione — provano i **dati committati**, cioè che il difetto
esisteva davvero e che il criterio nuovo lo trova. Lo scrivo perché un test che
non esercita il codice che descrive va detto, non lasciato credere.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_RISULTATI = Path(__file__).resolve().parent.parent / "benchmark" / "results"
_SORGENTE = (Path(__file__).resolve().parent.parent / "benchmark"
             / "end_to_end_reality.py")


def _run_e2e() -> list[dict]:
    fuori = []
    if not _RISULTATI.is_dir():
        pytest.skip("benchmark/results/ non è in questo albero")
    for f in sorted(_RISULTATI.glob("e2e_*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
        except Exception:  # noqa: BLE001 — un file illeggibile non è il tema
            continue
        a = d.get("answer") or {}
        if a.get("answerable_n") and a.get("detail"):
            fuori.append(a)
    if not fuori:
        pytest.skip("nessun risultato e2e col dettaglio delle answerable")
    return fuori


def _astenute(a: dict) -> int:
    return sum(1 for x in (a.get("detail") or [])
               if x.get("kind") == "answerable"
               and (x.get("answer") or "").strip().lower() == "no answer")


def test_i_run_committati_contengono_astensioni_su_domande_rispondibili():
    """IL DIFETTO, sui dati veri: se questo fosse zero, la metà mancante non
    sarebbe mai costata niente e la cura sarebbe teorica."""
    tot_n = tot_ast = 0
    for a in _run_e2e():
        tot_n += a["answerable_n"]
        tot_ast += _astenute(a)
    assert tot_ast > 0, (
        f"su {tot_n} domande answerable nei run committati non risulta "
        f"nessuna astensione: la metà mancante non costava niente")


def test_le_astensioni_erano_nascoste_dentro_le_non_corrette():
    """⚖️ IL PUNTO: non è che il numero fosse sbagliato — è che ne mescolava
    due. Una risposta errata e un'astensione sono difetti diversi."""
    for a in _run_e2e():
        ast = _astenute(a)
        mancate = a["answerable_n"] - a["answerable_correct"]
        assert ast <= mancate, (
            f"astensioni {ast} > risposte mancate {mancate}: il conteggio "
            f"non torna, e allora è il righello a essere rotto")
        if ast:
            assert ast <= mancate, "un'astensione deve pesare fra le mancate"


def test_il_banco_ora_dichiara_entrambe_le_popolazioni():
    """Il presidio sul SORGENTE: il campo e la riga di stampa devono esserci.

    È un controllo debole — legge il testo, non esegue — e per questo sta
    accanto agli altri due invece di sostituirli.
    """
    if not _SORGENTE.exists():
        pytest.skip("benchmark/end_to_end_reality.py non è in questo albero")
    testo = _SORGENTE.read_text(encoding="utf-8", errors="replace")
    assert "answerable_abstained" in testo, (
        "il banco non conta più le astensioni sulle domande che hanno "
        "risposta: senza, il 1.000 sulle impossibili resta illeggibile")
    assert "ANSWERABLE" in testo, (
        "il referto non stampa la seconda metà: un dato contato e non "
        "stampato non lo legge nessuno")
