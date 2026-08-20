"""Il riconoscitore dei comandi dentro il riquadro di Rich: **uno solo**.

Perche' condiviso e non una riga in ogni file, come per ``_esito``: due copie
della stessa lettura divergono, e la prima a divergere e' quella che nessuno
rilegge. Qui e' gia' successo — il 20/08 la stessa regola stava in due file
(l'aiuto di ``verimem`` e quello di ``verimem facts``) e ho curato prima uno
e poi l'altro, con la seconda copia rimasta scoperta per mezz'ora.

IL DIFETTO CHE CURA, misurato il 20/08: il regex pretende una LETTERA subito
dopo il bordo del riquadro. Quando Rich colora, dopo il bordo arriva una
sequenza di escape ANSI, e la ricerca rende **ZERO su un help perfettamente
leggibile**. In CI su ubuntu era esattamente cosi': 8980 caratteri, 70 righe
col bordo, e l'inizio pieno di escape — mentre in locale l'help ne ha 6161 e
nessun escape.

Provato senza CI, iniettando gli escape nell'help locale::

    help normale            6161 car,  0 ansi  ->  40 comandi
    stesso help colorato    6481 car, 80 ansi  ->   0 comandi
    colorato, ANSI tolti                       ->  40 comandi

Uno zero da un parser rotto sembra uno zero vero: e' la stessa famiglia degli
skip che si contano fra i verdi, e per questo la regola vive qui invece che
in due punti che possono allontanarsi.
"""
from __future__ import annotations

import re

#: Il nome di un comando dentro il riquadro: il bordo, uno spazio, il nome.
RE_COMANDO = chr(0x2502) + r"\s([a-z][a-z0-9-]{2,})\s{2,}"
#: Le sequenze di escape ANSI, da togliere PRIMA di cercare.
RE_ANSI = chr(27) + r"\[[0-9;]*[a-zA-Z]"


def comandi_dal_box(testo: str) -> set[str]:
    """I comandi elencati nel riquadro dell'aiuto, colorato o no."""
    return set(re.findall(RE_COMANDO, re.sub(RE_ANSI, "", testo)))
