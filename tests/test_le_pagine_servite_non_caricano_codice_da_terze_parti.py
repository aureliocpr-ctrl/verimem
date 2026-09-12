"""README:578-579 — «the data never leaves your infrastructure».

E' la promessa su cui si sceglie il self-host: chi lo fa, lo fa **per stare in
casa propria**. Questo presidio la misura dove l'utente la incontra — le pagine
che il prodotto serve al browser.

🔴 Il difetto, misurato il 12/09/2026 su `origin/main`, in sola lettura:

    dashboard_routes/lineage.py:22      unpkg.com/vis-network/…      ← senza versione
    dashboard_routes/memory_map.py:270  cdnjs.cloudflare.com/…/graphology
    dashboard_routes/memory_map.py:271  cdnjs.cloudflare.com/…/d3
    dashboard_routes/memory_map.py:272  cdn.jsdelivr.net/…/sigma
    ide.py:834                          cdn.jsdelivr.net/…/monaco-editor

    5 tag <script src="https://…">  ·  4 domini terzi  ·  0 con `integrity=`

Tre conseguenze, in ordine di gravita':
  ① uno script servito da una CDN gira **nella stessa pagina che mostra la
     memoria**: senza `integrity` chi controlla quel dominio serve JavaScript
     diverso, e quel JavaScript legge i dati che la pagina ha in mano;
  ② `vis-network` non ha una versione: prende l'ultima, quindi il codice che gira
     puo' cambiare **senza che nessun presidio lo veda**;
  ③ in una rete isolata — il motivo per cui si fa self-host — quelle pagine **non
     caricano**.

La cura che chiude tutti e tre: servire quei file **dal pacchetto**. Il ripiego
(`integrity=` + versione pinnata) chiude ① e ②, non ③.

⚠️ LIMITE DICHIARATO: **questo file non e' stato eseguito da chi lo ha scritto**
(sola lettura). Va eseguito dal pari: atteso **1 xfailed**.
⚠️ Questo test legge il SORGENTE, non la pagina resa: dice che cosa il prodotto
scrive nell'HTML, non che cosa il browser esegue. Il livello e' dichiarato perche'
un presidio a un livello piu' basso della porta vale meno, e chi legge deve
saperlo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
PRODOTTO = RADICE / "verimem"

# Un tag <script> con una sorgente ASSOLUTA (http/https): e' codice di terze parti.
# I `src` relativi restano fuori: quelli li serve il pacchetto ed e' cio' che vogliamo.
SCRIPT_ESTERNO = re.compile(r"""<script[^>]*\bsrc\s*=\s*["']https?://[^"']+["'][^>]*>""", re.I)
HA_INTEGRITY = re.compile(r"\bintegrity\s*=", re.I)


def _tag_esterni() -> list[tuple[str, str]]:
    """(file:riga, tag) per ogni <script> con sorgente assoluta nel prodotto."""
    fuori: list[tuple[str, str]] = []
    for f in sorted(PRODOTTO.rglob("*.py")):
        try:
            testo = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in SCRIPT_ESTERNO.finditer(testo):
            riga = testo.count("\n", 0, m.start()) + 1
            fuori.append((f"{f.relative_to(RADICE).as_posix()}:{riga}", m.group(0)))
    return fuori


@pytest.mark.xfail(
    strict=True,
    reason=(
        "5 tag <script> da 4 domini terzi senza `integrity=` nelle pagine che mostrano "
        "la memoria, mentre README:578-579 promette che i dati non lasciano "
        "l'infrastruttura. Difetto APERTO, registrato senza curarlo: la cura tocca il "
        "prodotto e la decide chi lo mantiene. Quando entra, questo xfail diventa "
        "XPASS e strict lo segnala."
    ),
)
def test_nessuna_pagina_servita_carica_codice_da_un_dominio_che_non_controlliamo():
    tag = _tag_esterni()

    # Controllo positivo: se i tag sparissero del tutto, questo test non starebbe
    # piu' misurando niente e passerebbe per la ragione sbagliata. Lo dice.
    assert tag, (
        "nessun <script> con sorgente assoluta trovato nel prodotto. Se sono stati "
        "tolti davvero, il difetto e' curato e questo test va riscritto come verde; "
        "se e' cambiato il modo di servire l'HTML, il presidio non misura piu'."
    )

    senza_integrity = [dove for dove, t in tag if not HA_INTEGRITY.search(t)]
    assert not senza_integrity, (
        f"{len(senza_integrity)} script di terze parti senza `integrity=`, serviti "
        f"nelle pagine del prodotto: {senza_integrity}. Chi controlla quei domini "
        "serve JavaScript che gira dove stanno i dati della memoria."
    )
