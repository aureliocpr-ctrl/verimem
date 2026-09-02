"""Un riferimento `file.py:12` scritto in un fatto non può leggere fuori radice.

`content_pin._cited_line` prende il percorso da un **riferimento testuale dentro
un fatto** — cioè da un input che scrive l'utente — e lo apre per citarne la riga.
È l'unico dei tredici punti segnalati dall'analisi statica in cui il percorso non
viene dalla nostra configurazione.

Il contenimento c'è già (`_resolve` fa `p.relative_to(root)` e restituisce `None`
se il percorso esce), ma «c'è» va **misurato**, non dedotto leggendo: questo test
prova ognuna delle forme che `ide.py::_safe_path` elenca come pericolose
(`..`, lettera di unità Windows, UNC, `~`, byte nullo) e pretende `None`.

⚠️ Se anche una sola tornasse un percorso, la dismissione dell'alert sarebbe
sbagliata e servirebbe la cura. Il test esiste per **cercare** quel caso, non per
confermare che non c'è.
"""
import os
import tempfile
from pathlib import Path

import pytest

from verimem.content_pin import _resolve


@pytest.fixture()
def radice():
    d = Path(tempfile.mkdtemp(prefix="test_contenimento_"))
    (d / "dentro.txt").write_text("riga uno\n", encoding="utf-8")
    fuori = d.parent / f"fuori_{os.getpid()}.txt"
    fuori.write_text("segreto\n", encoding="utf-8")
    yield d, fuori
    try:
        fuori.unlink()
    except OSError:
        pass


def test_un_percorso_dentro_la_radice_si_apre(radice):
    """Controllo POSITIVO: senza questo, un `_resolve` che dice sempre None
    passerebbe tutti gli altri casi e il test non misurerebbe nulla."""
    d, _ = radice
    assert _resolve("dentro.txt", d) is not None


@pytest.mark.parametrize("forma", [
    "../fuori.txt",
    "..\\fuori.txt",
    "dentro/../../fuori.txt",
    "/etc/passwd",
    "C:/Windows/win.ini",
    "C:\\Windows\\win.ini",
    "//server/share/x.txt",
    "\\\\server\\share\\x.txt",
    "~/segreto.txt",
    "~root/.ssh/id_rsa",
])
def test_le_forme_che_escono_dalla_radice_sono_rifiutate(radice, forma):
    d, _ = radice
    assert _resolve(forma, d) is None, (
        f"«{forma}» ha superato il contenimento: l'alert di analisi statica "
        f"NON va dismesso, va curato come in ide.py::_safe_path"
    )


def test_il_byte_nullo_non_apre_niente(radice):
    """Il byte nullo tronca il percorso nelle syscall legacy: `a.txt\\0.png`
    diventerebbe `a.txt`. Qui deve restare senza risposta, non sollevare."""
    d, _ = radice
    try:
        esito = _resolve("dentro.txt\x00.png", d)
    except ValueError:
        return  # rifiutato dal sistema operativo: va bene uguale
    assert esito is None


def test_il_file_fuori_radice_non_si_raggiunge_col_nome_esatto(radice):
    """Il caso più diretto: il percorso assoluto del file vicino alla radice."""
    d, fuori = radice
    assert _resolve(str(fuori), d) is None
