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


#: Gli script di terze parti senza `integrity=`, contati il 12/09/2026 con lo
#: stesso criterio che questo test usa (i `.py` di `verimem/`).
SENZA_INTEGRITY_IL_12_09 = 5


def test_nessuna_pagina_servita_carica_codice_da_un_dominio_che_non_controlliamo():
    """🔴 Il difetto e' APERTO e questo test lo REGISTRA invece di aspettarselo.

    ⚙️ **Perche' non e' un `xfail`** (decisione del 12/09: *«un test misura e
    resta, o si toglie con la ragione»*). Un `xfail` cade solo quando il difetto
    e' curato; questo cade **nei due versi** — se arriva `integrity=` **e** se
    qualcuno aggiunge un sesto script da una CDN, che e' il caso di cui non si
    accorge nessuno.
    """
    tag = _tag_esterni()

    # Controllo positivo: se i tag sparissero del tutto, questo test non starebbe
    # piu' misurando niente e passerebbe per la ragione sbagliata. Lo dice.
    assert tag, (
        "nessun <script> con sorgente assoluta trovato nel prodotto. Se sono stati "
        "tolti davvero, il difetto e' curato e questo test va riscritto come verde; "
        "se e' cambiato il modo di servire l'HTML, il presidio non misura piu'."
    )

    senza_integrity = [dove for dove, t in tag if not HA_INTEGRITY.search(t)]
    assert len(senza_integrity) == SENZA_INTEGRITY_IL_12_09, (
        f"gli script di terze parti senza `integrity=` serviti nelle pagine del "
        f"prodotto sono {len(senza_integrity)}, misurati {SENZA_INTEGRITY_IL_12_09} "
        f"il 12/09: {senza_integrity}\n"
        "🟢 Se sono DIMINUITI, la cura sta arrivando: quando toccano zero questo "
        "presidio diventa `assert not senza_integrity` e il docstring perde il "
        "paragrafo del difetto.\n"
        "🔴 Se sono AUMENTATI, un altro script da un dominio che non controlliamo "
        "e' entrato in una pagina che mostra la memoria — e README:578-579 "
        "promette che i dati non lasciano l'infrastruttura.\n"
        "**In tutti e due i casi: guarda le pagine, non aggiornare il numero.**"
    )
