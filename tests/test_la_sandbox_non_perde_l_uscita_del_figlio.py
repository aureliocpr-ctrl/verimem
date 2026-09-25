"""T215 — la sandbox perde in silenzio l'uscita di un figlio che non parla utf-8.

`SandboxedShell.execute` apre il figlio con ``text=True`` e nessun ``encoding=``
né ``errors=``, nelle due vie (``popen_kw`` e ``popen_kw_strict``). Su Windows
``communicate()`` legge con due thread: sul primo byte che la codifica non sa
leggere il thread muore (pytest lo segnala come
``PytestUnhandledThreadExceptionWarning``), il canale resta vuoto e il risultato
esce con l'azione «allow» e ``stdout=""``. Su Linux e macOS la stessa decodifica
stretta solleva ``UnicodeDecodeError`` fuori da ``execute``. Visto il 24/09 in
``test_env_scrub_removes_secret_prefixes``: «can't decode byte 0x8a in position
13», che è la «è» di «'python' non è riconosciuto…» di cmd.exe in cp850.

La stessa forma è già raccontata in ``verimem/_proc_quiet.py`` (T118, 19/09):
«il thread lettore muore sul primo byte che non sa decodificare: il processo
esce 0 e il canale torna None».

Il figlio scrive «x», i byte 0x81 0x8a, «y». 0x81 non si decodifica né in utf-8
(byte di continuazione senza inizio) né in cp1252 (non definito), quindi il
rosso non dipende dalla modalità utf-8 del processo né dalla gamba di CI.
⚠️ Solo la via di default: nella via strict ``python -c`` è bloccato di proposito
(esecuzione arbitraria), e la cura là è la stessa riga, non esercitata da qui.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.sandbox import SandboxedShell

#: il codice del figlio; ``\\x81`` resta una barra e una x fino a python -c,
#: sia dentro le virgolette doppie di cmd.exe sia in quelle di /bin/sh
_CODICE = "__import__('sys').{canale}.buffer.write(b'x\\x81\\x8ay')"


@pytest.mark.parametrize("canale", ["stdout", "stderr"])
def test_un_byte_non_utf8_non_cancella_l_uscita_del_figlio(tmp_path: Path, monkeypatch,
                                                            canale: str) -> None:
    monkeypatch.delenv("ENGRAM_SANDBOX_MODE", raising=False)
    shell = SandboxedShell(audit_root=tmp_path / "audit")
    r = shell.execute(f'python -c "{_CODICE.format(canale=canale)}"', cwd=tmp_path)
    assert r.action == "allow", (r.action, r.reason)
    assert r.returncode == 0, (r.returncode, r.stderr)
    uscita = getattr(r, canale)
    assert uscita.startswith("x") and uscita.endswith("y"), (
        f"l'uscita del figlio su {canale} è andata persa: {uscita!r}")
    # il prezzo dichiarato: i byte che utf-8 non legge diventano U+FFFD
    assert "�" in uscita, repr(uscita)
