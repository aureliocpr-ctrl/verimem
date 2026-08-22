"""Il README e la CLI dicevano due numeri diversi per lo stesso modello.

    README   «announced as 656 MB (the download); on disk it takes 711 MB»
    CLI      «~746 MB»   (`verimem warmup --help`)

Nessuno dei due era sbagliato, ed è questo che rendeva la cosa difficile da
vedere::

    746 058 368 byte  =  746,1 MB (10⁶)  =  711,5 MiB (2²⁰)

**Stesso byte, due unità** — e il README chiamava «MB» una misura in MiB. Il
`656` era il numero che l'help stampava fino al 21/08, quando è stato corretto
in `746` (commit `904be678`): da quel momento il README citava un «announced»
che non esisteva più. **La discrepanza l'ha creata la cura precedente**, ed è la
forma tipica: si allinea una superficie e l'altra resta indietro.

⚖️ Un utente che confronta i due numeri conclude che uno dei due mente. Peggio
del numero sbagliato è il numero *incoerente*: toglie fiducia a entrambe le
superfici invece che a una.

═══ PERCHÉ IL TEST LEGGE LA TABELLA INVECE DI RICOPIARE LA CIFRA ═══

`_MODEL_DOWNLOAD_MB` è la fonte: se domani il modello cambia, quella si
aggiorna e il README no. Qui il README viene confrontato con essa, così la
divergenza diventa rossa invece che silenziosa — è lo stesso schema di
`test_un_1000_di_astensione_non_dice_la_meta_che_conta`, che lega il README a
BENCHMARKS.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from verimem.cli import _MODEL_DOWNLOAD_MB, _WARMUP_DI_DEFAULT, _totale_di_default

_README = Path(__file__).resolve().parent.parent / "README.md"


def _testo() -> str:
    if not _README.exists():
        pytest.skip("README.md non è in questo albero")
    return _README.read_text(encoding="utf-8", errors="replace")


def _righe_sul_gate(readme: str) -> list[str]:
    """Le righe che parlano del modello del giudice.

    ⚠️ SI CERCA NELLA RIGA, NON NEL FILE: un numero come `746` può comparire
    altrove per tutt'altro motivo, e un `in readme` farebbe passare
    l'asserzione per coincidenza — è già successo con `0.20`, che nel README
    stava in una frase su «naive counting».
    """
    return [r for r in readme.splitlines()
            if ("judge model" in r or "gate model" in r
                or "moat gate" in r or "the judge)" in r
                or "announced as" in r)]


def test_la_tabella_dei_pesi_conosce_ancora_il_gate():
    """Controllo positivo: se questa cade non è il README ad essere cambiato,
    è la fonte — e allora è la riga del README che va rifatta sul numero
    nuovo, non questo test che va rilassato."""
    assert "local_gate_ce_v2" in _MODEL_DOWNLOAD_MB, (
        f"la tabella dei pesi non porta più il gate: "
        f"{sorted(_MODEL_DOWNLOAD_MB)}")


def test_il_readme_dice_lo_stesso_peso_della_cli():
    """IL CUORE: due superfici, un numero solo."""
    atteso = _MODEL_DOWNLOAD_MB["local_gate_ce_v2"]
    righe = _righe_sul_gate(_testo())
    assert righe, "il banco non trova più le righe da presidiare"
    assert any(str(atteso) in r for r in righe), (
        f"nessuna riga del README sul modello del giudice porta il peso che "
        f"la CLI stampa ({atteso} MB). Righe trovate: "
        f"{[r[:80] for r in righe]}")


def test_il_numero_vecchio_non_e_tornato():
    """`656` era il valore dell'help fino a `904be678`. Se ricompare accanto al
    gate, qualcuno ha riallineato la superficie sbagliata."""
    righe = _righe_sul_gate(_testo())
    colpevoli = [r for r in righe if re.search(r"\b656\b", r)]
    assert not colpevoli, (
        f"il numero superato è tornato in una riga sul gate: {colpevoli}")


def test_l_unita_di_misura_e_dichiarata():
    """⚖️ IL PRESIDIO CHE VALE PIÙ DEL NUMERO: `746` e `711` sono lo STESSO
    byte in MB e in MiB. Senza dire quale unità si usa, il prossimo che misura
    con un altro strumento riapre la discrepanza — e questa volta credendo di
    aver trovato un errore.
    """
    testo = _testo()
    assert re.search(r"MiB|10\^6|10⁶", testo), (
        "il README non dichiara in quale unità sono i pesi dei modelli: "
        "746 MB e 711 MiB sono la stessa cartella")


def test_anche_il_TOTALE_e_lo_stesso_sulle_due_superfici():
    """⚠️ LO STESSO ERRORE ERA NEL CLI, ed è mio: `_totale_di_default()`
    divideva per 1024 e scriveva «GB», cioè dava GiB con l'etichetta dei GB.

        somma dei modelli   2298 MB   (la tabella è in MB decimali)
        CLI    2298/1024 = 2.24  ->  «~2.2 GB»
        README 2298/1000 = 2.30  ->  «~2.3 GB»

    Ho curato nel README l'ambiguità che avevo appena introdotto nel CLI. Se
    una delle due superfici torna a 1024, questo test lo prende.
    """
    tot = sum(_MODEL_DOWNLOAD_MB[n] for n in _WARMUP_DI_DEFAULT
              if n in _MODEL_DOWNLOAD_MB)
    atteso = f"{tot / 1000:.1f} GB"
    testo = _totale_di_default()
    assert atteso in testo, (
        f"il CLI non usa MB decimali: dice {testo!r}, atteso {atteso!r} "
        f"({tot} MB / 1000)")
    readme = _testo()
    assert atteso in readme, (
        f"il README non porta lo stesso totale del CLI ({atteso}): le due "
        f"superfici tornerebbero a dire due numeri per la stessa cartella")
