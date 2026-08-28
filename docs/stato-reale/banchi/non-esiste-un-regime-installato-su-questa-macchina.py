# -*- coding: utf-8 -*-
"""«LA 0.7.0 INSTALLATA» SU QUESTA MACCHINA E' L'ALBERO DI SVILUPPO.

Il punto 3 della DIREZIONE del 28/08 20:09 chiede di riverificare i verdi «in
regime installato». Misurando se le mie celle dipendessero dalle nostre
variabili d'ambiente ho dichiarato il limite: resta la dimensione del PACCHETTO.
Andando a chiuderla, viene fuori che su questa macchina quella dimensione **non
si puo' misurare cosi'**, e la ragione riguarda tutte.

`pip` dichiara `verimem 0.7.0` installata. Ma:

  · in `site-packages` NON c'e' nessuna cartella `verimem/`;
  · il RECORD della dist-info elenca **15 file**, di cui **UNO** solo e' un
    `.py` di verimem: `__editable___verimem_0_7_0_finder.py`;
  · importando da una directory neutra, `verimem.client.__file__` risolve a
    `C:\\Users\\aurel\\Code\\HippoAgent\\verimem\\client.py`.

⇒ E' un'installazione EDITABLE (PEP 660): la versione dichiarata e' `0.7.0`, il
codice servito e' **l'albero di sviluppo**. Chi scrive «misurato sulla 0.7.0
installata» senza guardare `__file__` ha misurato l'albero.

⚠️ Questo NON contraddice la misura di @ws1 sulla 0.7.0: lei l'ha fatta in una
**venv separata mai toccata**, che e' la via giusta. Dice che **su QUESTA
macchina** un regime installato non esiste, e che per averlo serve fare come lei.

Il banco stampa i tre indizi insieme, cosi' chiunque puo' rifarlo in dieci
secondi prima di dichiarare un regime.

CONTROLLO CHE DEVE POTER FALLIRE: se `verimem` risultasse davvero dentro
`site-packages`, la tesi cade e il banco lo dice.

    python docs/stato-reale/banchi/non-esiste-un-regime-installato-su-questa-macchina.py
"""

from __future__ import annotations

import importlib.metadata as md
import sys
from pathlib import Path


def main() -> int:
    import verimem
    from verimem import client

    f_pkg = Path(verimem.__file__)
    f_cli = Path(client.__file__)
    try:
        ver = md.version("verimem")
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: metadata assente — {type(e).__name__}: {e}")
        return 1

    print("  ① COSA DICE pip")
    print(f"     importlib.metadata.version('verimem') = {ver}")

    print("\n  ② DOVE STA IL CODICE CHE VIENE IMPORTATO")
    print(f"     verimem.__file__      = {f_pkg}")
    print(f"     verimem.client.__file__ = {f_cli}")
    in_site = "site-packages" in str(f_cli)
    print(f"     dentro site-packages? {in_site}")

    print("\n  ③ COSA CONTIENE IL RECORD DELLA DIST-INFO")
    try:
        d = md.distribution("verimem")
        files = [str(x) for x in (d.files or [])]
    except Exception as e:  # noqa: BLE001
        print(f"     RECORD illeggibile: {type(e).__name__}: {e}")
        files = []
    py_verimem = [x for x in files if x.endswith(".py") and "verimem" in x]
    print(f"     file nel RECORD: {len(files)} · di cui .py di verimem: {len(py_verimem)}")
    for x in py_verimem[:3]:
        print(f"       {x}")
    editable = any("__editable__" in x for x in files)
    print(f"     c'e' un finder editable? {editable}")

    print("\n  -- VERDETTO")
    if in_site and not editable:
        print("     Il codice importato sta in site-packages e non c'e' finder editable:")
        print("     su questa macchina un regime installato ESISTE, e la tesi cade.")
        return 0
    if editable and not in_site:
        print("     Installazione EDITABLE: pip dichiara la versione, il codice servito e'")
        print("     l'albero di sviluppo. ⇒ su questa macchina «regime installato» NON si")
        print("     ottiene importando: serve una venv separata, come ha fatto @ws1.")
        print("     ⇒ Chi scrive «misurato sulla versione installata» senza guardare")
        print("       __file__ ha misurato l'albero.")
        return 0
    print("     quadro misto: leggi i tre indizi sopra prima di dichiarare un regime.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
