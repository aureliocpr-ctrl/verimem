"""La finestra di undo era scritta in due modi: letta e ricopiata.

Il doctor la LEGGE dalla costante (`doctor.py:44` importa
`UNDO_TTL_SECONDS`); la CLI la ricopiava a mano in **quattro** frasi
(«7 days»). Due superfici che descrivono la stessa finestra, e una la ricopia.

⚖️ OGGI NON MORDE, e lo dico invece di gonfiarlo: `UNDO_TTL_SECONDS` non si
legge dall'ambiente, quindi le due superfici non possono divergere a runtime.
**È il debito a essere reale** — chi cambiasse la costante aggiornerebbe il
doctor e non quelle quattro frasi, e nessun test lo prenderebbe.

La classe però è nota e ha già prodotto due discrepanze VERE in due giorni:

    21/08  l'help del gate diceva «~656 MB» cablato, il modello ne pesa 746
    22/08  il README diceva «711 MB», la CLI «746 MB» — stesso byte, MB vs MiB

In entrambi i casi il numero era giusto quando fu scritto. Il costo di
chiudere la classe è una funzione; il costo di non chiuderla si paga quando
nessuno se lo aspetta.
"""
from __future__ import annotations

import re
from pathlib import Path

from verimem.cli import _giorni_di_undo
from verimem.undo_log import UNDO_TTL_SECONDS

_CLI = Path(__file__).resolve().parent.parent / "verimem" / "cli.py"


def test_la_cli_deriva_la_finestra_dalla_costante():
    """IL CUORE: un solo posto decide, tutti gli altri leggono."""
    atteso = UNDO_TTL_SECONDS / 86400.0
    assert _giorni_di_undo() == f"{atteso:g} days", (
        f"la CLI non deriva la finestra da UNDO_TTL_SECONDS "
        f"({UNDO_TTL_SECONDS}s = {atteso:g} giorni): dice {_giorni_di_undo()!r}")


def test_se_la_costante_cambia_la_frase_la_segue(monkeypatch):
    """⚠️ IL PRESIDIO CHE VALE: il test precedente passerebbe anche con «7»
    ricablato, perché oggi i due valori coincidono. Qui la costante viene
    SPOSTATA — se la frase resta a 7, la derivazione è finta.

    È la stessa forma del controllo positivo dei banchi: un criterio si prova
    togliendo ciò che dovrebbe farlo cambiare.
    """
    monkeypatch.setattr("verimem.undo_log.UNDO_TTL_SECONDS", 3 * 86400)
    assert _giorni_di_undo() == "3 days", (
        f"spostata la costante a 3 giorni, la CLI dice ancora "
        f"{_giorni_di_undo()!r}: il numero è ricablato, non derivato")


def test_nessuna_frase_della_cli_ricopia_piu_il_numero():
    """Lo sweep: la funzione non serve a niente se accanto restano le frasi
    vecchie. Cerca «N days/giorni» nel sorgente, non il solo «7» — che compare
    in mille altri contesti."""
    testo = _CLI.read_text(encoding="utf-8", errors="replace")
    # ⚠️ SOLO LE RIGHE CHE PARLANO DI UNDO: cercare «N days» in tutto il file
    # prendeva un «78 days» sui tool mai chiamati e il docstring di questo
    # stesso presidio — due falsi positivi su due. È la stessa forma già vista
    # oggi col `0.20` del README: il criterio va applicato dove il fenomeno
    # vive, non ovunque il numero compaia.
    _UNDO = re.compile(r"undo|undoable|expired", re.I)
    colpevoli = [
        r.strip() for r in testo.splitlines()
        if re.search(r"\b\d+\s+days\b", r)
        and _UNDO.search(r)
        and "_giorni_di_undo" not in r
        and not r.lstrip().startswith("#")
        and "UNDO_TTL_SECONDS" not in r
    ]
    assert not colpevoli, (
        "queste righe scrivono una finestra a mano invece di derivarla: "
        + " | ".join(c[:70] for c in colpevoli[:4])
    )
