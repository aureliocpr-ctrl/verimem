"""L'ultimo passo del rilascio nomina il pacchetto che viene davvero costruito.

La procedura di rilascio termina stampando il comando di pubblicazione. Quel
comando conteneva il nome **precedente** al rinominamento del progetto: la riga
è rimasta indietro nel commit stesso che ha rinominato, e da allora l'ultimo
passo diceva di caricare artefatti che nessuna costruzione produce. Chi lo
eseguiva non trovava niente da pubblicare, e doveva capire da sé perché.

Il difetto è di una classe che si ripete: **un nome copiato a mano è una copia
che diverge**. Non serve un controllo più attento, serve che il nome venga letto
dalla stessa fonte che genera gli artefatti — e allora non può divergere.

Il collaudo lega le due estremità: quello che la procedura dice di caricare e
quello che ``pyproject.toml`` dichiara di costruire. Se qualcuno rinomina di
nuovo il progetto, questo diventa rosso prima che la procedura si rompa.

Il secondo test è quello che tiene onesto il primo: verifica che il criterio
sappia riconoscere un nome sbagliato, altrimenti riporterebbe «coincide» anche
se smettesse di guardare.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
PROCEDURA = RADICE / "scripts" / "release.py"
PYPROJECT = RADICE / "pyproject.toml"

#: Il comando di pubblicazione come la procedura lo stampa. Cattura il nome del
#: pacchetto che precede la versione.
_COMANDO = re.compile(r"twine upload dist/(?P<nome>[^-{}\s]*(?:\{[^}]+\})?)-")


def _nome_dichiarato() -> str:
    testo = PYPROJECT.read_text(encoding="utf-8")
    trovato = re.search(r'^name\s*=\s*"([^"]+)"', testo, flags=re.MULTILINE)
    assert trovato, "pyproject.toml non dichiara un nome: il banco è rotto"
    return trovato.group(1)


@pytest.fixture(scope="module")
def procedura() -> str:
    return PROCEDURA.read_text(encoding="utf-8")


def test_il_comando_di_pubblicazione_non_scrive_il_nome_a_mano(procedura: str):
    """Il nome deve venire da ``pyproject.toml``, non essere una copia."""
    trovato = _COMANDO.search(procedura)
    assert trovato, (
        "il comando di pubblicazione non è più nella forma attesa: questo "
        "collaudo va riscritto, non cancellato")
    nome = trovato.group("nome")
    assert nome.startswith("{"), (
        f"il comando nomina il pacchetto a mano ({nome!r}): è la copia che ha "
        f"già smesso di corrispondere una volta, quando il progetto è stato "
        f"rinominato. Va letto da pyproject.toml, dalla stessa fonte che "
        f"genera gli artefatti.")


def test_il_nome_letto_dalla_procedura_e_quello_che_si_costruisce():
    """Le due estremità coincidono: quel che si pubblica e quel che si genera."""
    import importlib.util

    specifica = importlib.util.spec_from_file_location("procedura", PROCEDURA)
    assert specifica and specifica.loader
    modulo = importlib.util.module_from_spec(specifica)
    specifica.loader.exec_module(modulo)

    assert modulo._nome_del_pacchetto() == _nome_dichiarato(), (  # noqa: SLF001
        "la procedura di rilascio e la dichiarazione del progetto non "
        "nominano lo stesso pacchetto")


def test_il_criterio_riconosce_un_nome_scritto_a_mano():
    """Il controllo positivo: senza, «coincide» non significherebbe nulla."""
    finto = 'print(f"    twine upload dist/pacchetto-vecchio-{args.version}*")'
    trovato = _COMANDO.search(finto)
    assert trovato and not trovato.group("nome").startswith("{"), (
        "il criterio non distingue un nome scritto a mano da uno interpolato: "
        f"ha letto {trovato.group('nome') if trovato else None!r}")
