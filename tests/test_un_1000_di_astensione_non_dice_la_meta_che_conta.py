"""Il README pubblicava «1.000 di astensione» e non la metà che lo rende leggibile.

Un'astensione a **1.000** non distingue *«si astiene quando deve»* da *«si
astiene sempre»*: sono la stessa cifra, e la seconda sarebbe un prodotto
inutile. La metà che decide è quanto si astiene sulle domande che una risposta
**ce l'hanno**.

Quel numero ESISTE, è misurato, ed è **favorevole**::

    docs/BENCHMARKS.md
      vanilla       (plain RAG)          QA 0.66   abstention 0.30
      engram        (production default) QA 0.76   abstention 0.20

⇒ Verimem si astiene **meno** del baseline e risponde **meglio**. Ometterlo
faceva sembrare il prodotto peggiore di com'è: chi legge «1.000» senza il
complemento conclude «allora si astiene sempre», che è l'accusa esatta che il
dato smentisce.

⚠️ E BENCHMARKS.md lo dice a chiare lettere::

    **Honest caveats (load-bearing — do not quote the number without them)**

Il README quotava il numero senza di essi. Non era una tabella inventata: era
**una metà pubblicata e l'altra no**, che è più difficile da vedere e più facile
da difendere.

═══ PERCHÉ IL TEST LEGGE IL FILE INVECE DI RICOPIARE LE CIFRE ═══

Correggere il README lo rende giusto **oggi**. La promessa e il dato vivono in
due file che cambiano in momenti diversi: il bench si rilancia, i numeri si
spostano, e nessuno rilegge il README. Qui la riga del README viene confrontata
con `docs/BENCHMARKS.md`: se un domani l'astensione cambiasse, questo test
diventerebbe rosso e chiederebbe di aggiornare la riga.

📌 I due numeri vengono da banchi DIVERSI e non vanno sommati: `1.000` è
`benchmark/end_to_end_reality.py` (astensione sulle domande impossibili), `0.20`
è `benchmark/qa_comparative.py` su LongMemEval. Il README deve portarli
entrambi proprio perché misurano le due facce, non la stessa cosa.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parent.parent
_README = _RADICE / "README.md"
_BENCH = _RADICE / "docs" / "BENCHMARKS.md"


def _testo(p: Path) -> str:
    if not p.exists():
        pytest.skip(f"{p.name} non è in questo albero")
    return p.read_text(encoding="utf-8", errors="replace")


def _tassi_dal_bench(testo: str) -> dict[str, str]:
    """I tassi di astensione dalla tabella degli arm di BENCHMARKS.md.

    La tabella ha la forma `| arm | descrizione | QA | abstention |`: si legge
    l'ULTIMA cella numerica della riga, che è l'astensione.
    """
    fuori: dict[str, str] = {}
    for riga in testo.splitlines():
        if not riga.startswith("|"):
            continue
        celle = [c.strip() for c in riga.strip("|").split("|")]
        if len(celle) < 4:
            continue
        arm = celle[0].strip("* ").lower()
        ultima = celle[-1].replace("*", "").strip()
        if arm in ("vanilla", "engram", "engram-base") and re.fullmatch(
                r"0\.\d+", ultima):
            fuori[arm] = ultima
    return fuori


def test_il_bench_misura_ENTRAMBE_le_meta():
    """Il controllo positivo: se questa cade, non è il README ad essere
    cambiato — è il banco, e la riga va rifatta sui numeri nuovi."""
    tassi = _tassi_dal_bench(_testo(_BENCH))
    assert {"vanilla", "engram"} <= set(tassi), (
        f"BENCHMARKS.md non espone più i tassi di astensione per arm: {tassi}")


def _righe_sull_astensione(readme: str) -> list[str]:
    """Le righe del README che parlano di astensione.

    ⚠️ SI CERCA NELLA RIGA, NON NEL FILE, e non è un dettaglio: sull'albero
    senza la cura il numero `0.20` compariva già a riga 202 — «naive counting
    is demolished to 0.20» — che con l'astensione non c'entra niente. Un
    `in readme` faceva passare l'asserzione per COINCIDENZA, e un presidio che
    passa per la ragione sbagliata è un guardiano che mente.
    """
    return [r for r in readme.splitlines()
            if "abstention" in r.lower() or "abstain" in r.lower()]


def test_dove_il_readme_dice_1000_dice_anche_quanto_costa():
    """IL CUORE: la cifra da sola è ambigua, e l'ambiguità va nella direzione
    che ci conviene."""
    readme = _testo(_README)
    righe = _righe_sull_astensione(readme)
    assert any("1.000" in r for r in righe), (
        "il banco non trova più la riga da presidiare")
    tassi = _tassi_dal_bench(_testo(_BENCH))
    engram, vanilla = tassi.get("engram"), tassi.get("vanilla")
    assert engram and vanilla, f"tassi non leggibili dal bench: {tassi}"
    assert any(engram in r for r in righe), (
        f"il README pubblica «1.000» ma in nessuna riga sull'astensione "
        f"compare il tasso sulle domande CHE HANNO risposta ({engram}, da "
        f"BENCHMARKS.md). Un 1.000 da solo non distingue «si astiene quando "
        f"deve» da «si astiene sempre».")
    assert any(vanilla in r for r in righe), (
        f"manca il termine di paragone ({vanilla}, il plain-RAG baseline) "
        f"nelle righe sull'astensione: senza, {engram} non dice se è tanto "
        f"o poco")


def test_il_confronto_e_nella_direzione_che_i_dati_sostengono():
    """⚠️ IL PRESIDIO CHE VALE PIÙ DELL'ALTRO: se un domani verimem si
    astenesse PIÙ del baseline, la frase «it abstains *less*» diventerebbe
    un'inversione — la stessa forma d'errore di
    `test_il_readme_non_puo_invertire_il_bench_che_cita`.
    """
    tassi = _tassi_dal_bench(_testo(_BENCH))
    engram, vanilla = tassi.get("engram"), tassi.get("vanilla")
    assert engram and vanilla, f"tassi non leggibili: {tassi}"
    readme = _testo(_README)
    dice_meno = "abstains *less*" in readme or "abstains less" in readme
    if dice_meno:
        assert float(engram) < float(vanilla), (
            f"il README afferma che verimem si astiene MENO del baseline, ma "
            f"il bench dice engram={engram} contro vanilla={vanilla}")
