"""La licenza è dichiarata come espressione, non come file da incorporare.

Dichiarare ``license = { file = "LICENSE" }`` non sbaglia la licenza: sbaglia il
posto in cui finisce. Lo strumento di costruzione copia il **testo integrale**
del file dentro il campo ``License:`` dei metadati, e il risultato misurato sul
pacchetto è questo:

    License:            40452 caratteri   (il nome ne occuperebbe una decina)
    METADATA totale:    82352 caratteri   -> il 49% è la licenza duplicata
    License-Expression: assente

Il testo della licenza è già imbarcato, una volta, dove va: in
``dist-info/licenses/LICENSE``. La copia nell'intestazione non aggiunge nulla e
occupa metà dei metadati — quelli che gli indici pubblici leggono per mostrare
sotto quale licenza sta il pacchetto.

Lo strumento di costruzione lo segnala da sé, e non come avviso lontano::

    `project.license` as a TOML table is deprecated
    Please use a simple string containing a SPDX expression
    This deprecation is overdue, please update your project

La forma corrente richiede ``setuptools>=77``: cambiare la dichiarazione senza
alzare il minimo dichiarato romperebbe la costruzione per chi ha una versione
precedente. Le due cose sono un unico cambiamento, e questo collaudo le lega.

L'ultimo test è quello che tiene onesti gli altri: senza, basterebbe scrivere
una qualunque espressione SPDX ben formata — anche quella di un'altra licenza —
e i primi tre resterebbero verdi.

Su Python 3.10 — che la matrice di integrazione copre — il lettore TOML non è
nella libreria standard. Se manca anche il pacchetto esterno il file si salta,
e questo è l'unico caso in cui la copertura si riduce: il file letto è lo stesso
su ogni versione, quindi il verde delle altre tre lo copre per intero.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = pytest.importorskip(
        "tomli", reason="serve un lettore TOML: stdlib da 3.11, altrimenti tomli")

RADICE = Path(__file__).resolve().parent.parent
PYPROJECT = RADICE / "pyproject.toml"
LICENZA = RADICE / "LICENSE"

#: Il minimo che serve a `project.license` come stringa SPDX e a
#: `project.license-files`. Lo dice lo strumento stesso nel proprio avviso.
SETUPTOOLS_PER_PEP639 = 77


def _progetto() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_la_licenza_non_e_una_tabella_che_incorpora_il_file():
    """Il caso per cui questo collaudo esiste: metà dei metadati era il testo."""
    licenza = _progetto()["project"]["license"]
    assert isinstance(licenza, str), (
        f"`project.license` è {type(licenza).__name__} ({licenza!r}): con la "
        f"forma a tabella lo strumento copia il testo integrale del file nel "
        f"campo `License:` dei metadati — misurati 40452 caratteri, il 49% del "
        f"METADATA. Serve l'espressione SPDX come stringa; il file resta "
        f"imbarcato da `license-files`.")


def test_il_minimo_dello_strumento_regge_la_forma_dichiarata():
    """Le due righe sono un cambiamento solo: la forma nuova vuole >=77."""
    requisiti = " ".join(_progetto()["build-system"]["requires"])
    trovato = re.search(r"setuptools\s*>=\s*(\d+)", requisiti)
    assert trovato, (
        f"il minimo di setuptools non è dichiarato in `build-system.requires` "
        f"({requisiti!r}): senza, la costruzione può usare una versione che non "
        f"conosce la forma corrente della licenza")
    assert int(trovato.group(1)) >= SETUPTOOLS_PER_PEP639, (
        f"`setuptools>={trovato.group(1)}` non basta per `license` come stringa "
        f"SPDX e per `license-files`: servono >={SETUPTOOLS_PER_PEP639}. Con un "
        f"minimo più basso la costruzione fallisce su chi non aggiorna.")


def test_il_classificatore_della_licenza_non_duplica_l_espressione():
    """Due dichiarazioni della stessa cosa possono divergere; una no."""
    classificatori = _progetto()["project"].get("classifiers", [])
    licenza = [c for c in classificatori if c.startswith("License ::")]
    assert not licenza, (
        f"il classificatore della licenza è deprecato e duplica l'espressione "
        f"SPDX: {licenza}. Lo strumento di costruzione lo segnala — «Please "
        f"consider removing the following classifiers in favor of a SPDX "
        f"license expression».")


def test_l_espressione_dichiarata_corrisponde_al_file_imbarcato():
    """Il controllo che impedisce agli altri tre di essere veri e vuoti.

    Un'espressione SPDX ben formata li soddisfa tutti anche se nomina un'altra
    licenza. Qui si legge il file che il pacchetto imbarca davvero.
    """
    espressione = _progetto()["project"]["license"]
    testo = LICENZA.read_text(encoding="utf-8", errors="replace")

    assert isinstance(espressione, str), (
        f"`project.license` è {type(espressione).__name__}: questo controllo "
        f"legge un'espressione e senza non può confrontare nulla — il primo "
        f"test dice cosa fare, questo resterebbe muto")
    assert "AGPL" in espressione.upper(), (
        f"l'espressione dichiarata è {espressione!r} ma il file imbarcato è la "
        f"GNU Affero General Public License: i metadati direbbero agli indici "
        f"pubblici una licenza diversa da quella che il pacchetto contiene")
    assert "Affero" in testo, f"{LICENZA.name} non è più l'Affero: {testo[:80]!r}"

    #: «or-later» non è cosmetico: dice a chi riusa il codice se può applicare
    #: una versione successiva della licenza. Deve stare in entrambi o in nessuno.
    concede_successive = "any later version" in testo
    dichiara_successive = espressione.lower().endswith("-or-later")
    assert concede_successive == dichiara_successive, (
        f"il file {'concede' if concede_successive else 'NON concede'} l'uso di "
        f"versioni successive, l'espressione {espressione!r} "
        f"{'lo dichiara' if dichiara_successive else 'non lo dichiara'}: è la "
        f"differenza fra `-or-later` e `-only`, e non è una sfumatura")
