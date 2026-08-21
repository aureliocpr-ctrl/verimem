"""La ricevuta di ``verimem save`` deve distinguere «manca la source» da «manca il giudice».

⚠️ IL CASO REALE, misurato il 2026-08-21 su una macchina pulita (venv nuovo, sdist
0.7.6, ``HF_HOME`` vuoto, ``env -i``): chi installa e scrive con ``--source``
senza aver fatto ``verimem warmup`` legge DUE righe consecutive che si
contraddicono::

    L4-skipped — source provided but no grounding judge is available   <- vera
    not verified — no source, so the entailment moat did not run;
                   pass --source "<the output that proves it>"          <- FALSA

La seconda gli dice di fare la cosa che ha appena fatto. E' il primo messaggio
che un utente nuovo legge sulla promessa centrale del prodotto.

🔑 IL DATO C'ERA GIA' E CHI LO MOSTRA NON LO LEGGEVA. ``client.esito_del_moat``
distingue gia' i tre stati (``not_run:no_source`` / ``not_run:no_judge`` /
``not_run:unknown``) e la ricevuta li porta nel campo ``moat``; ``cli.py``
inventava il messaggio dalla presenza del punteggio, che è un'altra domanda.

Il principio è scritto nel progetto da prima di questo test —
``test_mcp_remember_receipt_says_if_moat_ran``: «Three states, not two. "No
source given" and "source given but no judge available" are different facts
about the world, and collapsing them would repeat the bug doctor was fixed
for». Il canale MCP lo rispettava, la CLI no: stessa promessa, due porte, una
sola presidiata.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]


def _sorgente_ricevuta() -> str:
    """Il blocco di ``cli.py`` che stampa l'esito del moat."""
    testo = open(RADICE / "verimem" / "cli.py", encoding="utf-8").read()
    i = testo.find("def save_cmd(")
    assert i > 0, "save_cmd non trovato: il parser di questo test va rivisto"
    return testo[i:i + 20000]


def test_la_ricevuta_non_dice_no_source_quando_manca_solo_il_giudice() -> None:
    blocco = _sorgente_ricevuta()
    i = blocco.find("not verified")
    assert i > 0, "la riga 'not verified' non c'e' piu': parser da rivedere"
    intorno = blocco[max(0, i - 700):i + 400]
    assert re.search(r"no_judge|not_run:|\bsource\b\s*(?:is|and|or|if)", intorno), (
        "la ricevuta sceglie il messaggio senza guardare se una source c'era: "
        "cosi' dice «no source» anche a chi l'ha passata e manca solo il "
        "giudice. Il campo `moat` della ricevuta distingue gia' i tre stati "
        "(client.esito_del_moat) — leggilo invece di dedurlo dal punteggio."
    )


def test_esiste_un_messaggio_per_il_caso_source_senza_giudice() -> None:
    """Non basta non mentire: il caso va NOMINATO, o l'utente non sa che fare."""
    blocco = _sorgente_ricevuta()
    assert "warmup" in blocco, (
        "la ricevuta di `save` non nomina mai `verimem warmup`, che e' la via "
        "d'uscita per chi ha passato una source e non ha il giudice installato"
    )
