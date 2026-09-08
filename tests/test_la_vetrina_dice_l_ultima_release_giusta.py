"""La pagina di PyPI non puo' dire una versione pubblicata che non e' l'ultima.

PERCHE' ESISTE
==============
`pyproject.toml:16` dice `readme = "README.md"`: quel file **e'** la pagina di
PyPI. Fino all'08/09 diceva «*the latest release is 0.7.0 (22 July)*» mentre la
**0.7.1** e la **0.7.6** erano gia' pubblicate, e portava **due** conteggi
diversi per la stessa distanza — **1900** e «*over 400*» commit, a tre righe
l'uno dall'altro — mentre il numero misurato e' **3891**.

🔑 E la nota che avvertiva di aggiornarli **c'era gia' dal 26/08**, scritta da me:
«*chi pubblica: aggiornare i numeri o togliere il blocco*». Non e' bastata.
**Una nota non e' un presidio**: questo file e' la differenza fra le due.

COSA CONTROLLA, e con quale severita'
-------------------------------------
1. **La VERSIONE, esatta**: la versione che il README dichiara pubblicata deve
   essere l'ultimo tag `vX.Y.Z` del repo. Un numero sbagliato qui manda un
   utente a cercare una release che non e' quella che riceve.
2. **La distanza in commit NON la guarda questo file**, e la ragione e' una
   correzione che ho dovuto farmi: l'avevo scritta, con una tolleranza di un
   fattore 2, perche' leggevo «more than 1900» e «over 400» come due numeri
   FALSI. **Non lo erano**: sono **soglie**, e una soglia monotona resta vera
   mentre la distanza cresce — cura deliberata del 29/08 (LANT-62). Lo ha detto
   il presidio che gia' esisteva,
   `test_il_pacchetto_ha_cio_che_promettiamo.py::test_la_soglia_in_commit_del_readme_e_ancora_vera`,
   diventando **rosso** quando ho messo un numero esatto al posto della soglia.
   ⇒ **la distanza resta a quel presidio, questo file guarda solo la versione.**
   *Due righelli sulla stessa grandezza divergono: e' la prima delle cinque
   classi che ci costano.*

⚠️ LIMITE: serve `git`. Se non c'e', il test si **salta dichiarandolo** invece
di passare in silenzio — un verde che non ha guardato niente e' peggio di niente.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

import pytest

RADICE = pathlib.Path(__file__).resolve().parents[1]
README = RADICE / "README.md"

_VERSIONE = re.compile(r"latest published release is \*\*(\d+\.\d+\.\d+)", re.I)


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(("git", *args), cwd=RADICE, capture_output=True,
                             text=True, timeout=30)
    except Exception:  # noqa: BLE001 — git assente o non eseguibile
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def _ultimo_tag() -> str | None:
    grezzo = _git("tag", "-l", "v[0-9]*")
    if not grezzo:
        return None
    def chiave(t: str):
        try:
            return tuple(int(x) for x in t.lstrip("v").split("."))
        except ValueError:
            return (0,)
    return sorted(grezzo.splitlines(), key=chiave)[-1]


def test_la_versione_dichiarata_e_l_ultimo_tag():
    testo = README.read_text(encoding="utf-8", errors="replace")
    m = _VERSIONE.search(testo)
    assert m, ("il README non dichiara piu' quale release e' pubblicata nella "
               "forma che questo presidio conosce ('latest published release is "
               "**X.Y.Z'). Se il blocco e' stato riscritto, aggiorna QUESTO file: "
               "un presidio che non trova il suo bersaglio non e' verde, e' cieco.")
    tag = _ultimo_tag()
    if tag is None:
        pytest.skip("git non disponibile: il presidio non ha guardato nulla")
    assert m.group(1) == tag.lstrip("v"), (
        f"il README dice che l'ultima release pubblicata e' {m.group(1)}, "
        f"l'ultimo tag del repo e' {tag}. Questo file E' la pagina di PyPI "
        "(`pyproject.toml`: readme = README.md): il numero sbagliato lo legge "
        "chi installa."
    )
