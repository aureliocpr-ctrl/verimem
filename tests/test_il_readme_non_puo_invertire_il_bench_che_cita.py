"""Il README dichiarava «abstains 2/2» e il file che linka diceva «abstained 0».

⚠️ INVERSIONE ESATTA, SULLA PROMESSA CENTRALE, NELLA DIREZIONE CHE CI CONVIENE.
Il README apre dicendo *«when the evidence isn't there the system abstains»*, e
alla riga della tabella affermava::

    abstains 2/2 on unresolvable conflicts ([bench](…wellgrounded_distractor…))

Il file di risultati che quel link addita dice il contrario::

    unresolvable_conflicts.n         = 2
    unresolvable_conflicts.abstained = 0
    unresolvable_conflicts.fabricated = 2

⇒ Su due conflitti irrisolvibili il sistema **non si è astenuto nemmeno una
volta**: ha scelto una parte entrambe le volte. La riga diceva l'opposto.

📌 Il resto della stessa riga REGGE — «correct 0.17 → 0.92» corrisponde a
`current_answer.correct = 0.1667` e `trust_conditioned.correct = 0.9167`. Il
difetto non è una tabella inventata: è **una cifra girata dentro una riga vera**,
che è più difficile da vedere e più facile da difendere.

═══ PERCHÉ QUESTO TEST ESISTE, e non basta aver corretto la riga ═══

Correggere il testo lo rende giusto **oggi**. La promessa e il dato però vivono
in due file diversi e cambiano in momenti diversi: il bench si rilancia, i
numeri si spostano, e nessuno rilegge il README. È esattamente il meccanismo per
cui «exact citations» era vera quando fu scritta e falsa sei mesi dopo.

⇒ Qui la riga del README **legge il file dei risultati**: se un domani il
sistema imparasse ad astenersi, questo test diventerebbe rosso e chiederebbe di
aggiornare la riga — nella direzione che ci fa onore. E se qualcuno riscrivesse
«abstains 2/2» senza rilanciare il bench, diventerebbe rosso subito.

🔑 È il criterio B applicato a una promessa NUMERICA: non «esiste un test», ma
**il test lega la frase al dato che la sostiene**.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_RADICE = Path(__file__).resolve().parents[1]
_README = _RADICE / "README.md"
_RISULTATI = (_RADICE / "benchmark" / "results"
              / "wellgrounded_distractor_2026-07-16.json")


def _misura() -> dict:
    dati = json.loads(_RISULTATI.read_text(encoding="utf-8"))
    for chiave in ("unresolvable_conflicts", "unresolvable"):
        if chiave in dati:
            return dati[chiave]
    pytest.skip(f"{_RISULTATI.name} non riporta più i conflitti irrisolvibili")


def test_il_readme_non_dichiara_astensioni_che_il_bench_smentisce():
    """Il cuore: la frase e il numero devono raccontare la stessa cosa.

    L'asserzione è condizionale apposta — non vieta di scrivere «abstains»,
    pretende che il file dei risultati lo sostenga. Se il prodotto migliora, il
    test chiede di aggiornare la riga; se la riga viene gonfiata, diventa rosso.
    """
    m = _misura()
    astenuto = int(m.get("abstained", 0))
    testo = _README.read_text(encoding="utf-8")

    riga = next((r for r in testo.splitlines()
                 if "unresolvable conflict" in r), None)
    assert riga is not None, (
        "il README non parla più dei conflitti irrisolvibili: se la riga è "
        "stata tolta di proposito, togli anche questo test")

    vanta = re.search(r"abstains?\s+(\d+)\s*/\s*(\d+)", riga)
    if astenuto == 0:
        assert vanta is None, (
            f"il README dichiara «{vanta.group(0)}» mentre il bench misura "
            f"abstained={astenuto} su n={m.get('n')}: è l'inversione esatta "
            f"della promessa centrale, e nella direzione che ci conviene")
        assert re.search(r"\bnot\b.{0,20}abstain", riga), (
            "il bench dice che il sistema NON si è astenuto: la riga deve "
            f"dirlo. Riga attuale: {riga.strip()[:160]}")
    else:
        assert vanta and int(vanta.group(1)) == astenuto, (
            f"il README dichiara «{vanta.group(0) if vanta else 'nulla'}» "
            f"mentre il bench misura abstained={astenuto}")


def test_gli_altri_numeri_della_stessa_riga_REGGONO():
    """⚠️ IL CONTROLLO CHE IMPEDISCE DI BUTTARE VIA LA RIGA INTERA.

    Il difetto era **una cifra girata dentro una riga vera**: «0.17 → 0.92»
    corrisponde al file. Senza questo test, la cura naturale di un domani
    sarebbe cancellare tutta la riga «per sicurezza» — perdendo un dato
    misurato e onesto per colpa di quello accanto.
    """
    dati = json.loads(_RISULTATI.read_text(encoding="utf-8"))
    prima = round(float(dati["current_answer"]["correct"]), 2)
    dopo = round(float(dati["trust_conditioned"]["correct"]), 2)
    riga = next(r for r in _README.read_text(encoding="utf-8").splitlines()
                if "unresolvable conflict" in r)
    assert f"{prima:.2f}" in riga and f"{dopo:.2f}" in riga, (
        f"la riga non riporta più i valori misurati {prima:.2f} → {dopo:.2f}: "
        f"{riga.strip()[:160]}")
