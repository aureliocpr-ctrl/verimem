"""Cycle #136 (2026-05-17) — Windows console pop-up suppression helper.

Direttiva 2026-05-17: le shell che si aprono e chiudono da sole sono
fastidiosissime per chi guarda lo schermo. Root cause: every ``subprocess.run / Popen`` call
in ``engram/`` that doesn't pass ``creationflags=CREATE_NO_WINDOW``
flashes a Windows CMD window on the user's screen. This module exposes
one tiny helper, ``quiet_popen_kwargs()``, that returns the right
kwargs for the current platform — empty dict on Linux/macOS so the
helper is a no-op cross-platform.

Usage::

    from verimem._proc_quiet import quiet_popen_kwargs
    subprocess.run(["git", "rev-parse", sha], **quiet_popen_kwargs())

The Windows ``CREATE_NO_WINDOW`` constant is only defined when running
on Windows (it lives in ``subprocess`` only on win32 Python builds).
We guard the attribute access defensively.

⚠️ QUI NON CI VA ``encoding``, e la domanda viene a chiunque passi (T118,
2026-09-19). Leggere l'output di un figlio con ``text=True`` e senza
``encoding=`` usa la codifica di SISTEMA — cp1252 su Windows — e il thread
lettore muore sul primo byte che non sa decodificare: il processo esce 0 e il
canale torna ``None``. Sembra il caso perfetto per una riga sola in questo
helper, che è la superficie che tutti spargono.

Non lo è, ed è un conto: delle 14 chiamate che spargono ``quiet_popen_kwargs()``
**cinque leggono BYTE** e decodificano a mano con ``decode("utf-8",
errors="replace")`` (``code.py``, ``ide.py``, ``interactive_judge.py``,
``provenance_validator.py`` ×2). Un ``encoding`` messo qui cambierebbe LORO il
tipo del risultato, in silenzio e senza che nessun banco lo chieda: quelle
cinque non sono difettose, usano l'altro idioma corretto.

Quindi ``encoding="utf-8", errors="replace"`` sta ACCANTO a ogni ``text=True``,
e a contare che non ne manchi nessuno ci pensa
``tests/test_ogni_lettura_di_un_figlio_dichiara_la_codifica.py`` — perché la
regola era già scritta in ``.github/workflows/ci.yml`` dal 3 settembre e
applicata in ``band_escalation.py``, e in due settimane non ha raggiunto gli
altri otto siti: una riga che manca non emette segnale.
"""
from __future__ import annotations

import subprocess
import sys
from typing import Any


def quiet_popen_kwargs() -> dict[str, Any]:
    """Return kwargs that suppress the Windows console pop-up.

    On Windows this is ``{"creationflags": subprocess.CREATE_NO_WINDOW}``;
    on every other platform it is the empty dict (no behaviour change).
    """
    if sys.platform == "win32":
        flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if flag:
            return {"creationflags": flag}
    return {}
