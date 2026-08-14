"""Dove finiscono i dati: le due promesse del README, misurate su case finte.

Il README chiude con una riga che vale un archivio intero::

    Existing ~/.engram data stores keep working untouched;
    new installs default to ~/.verimem.

Sono **due** promesse con destinatari opposti — chi installa oggi per la prima
volta, e chi ha già anni di fatti in `~/.engram` — e la seconda è quella che non
può rompersi mai: un risolutore che smettesse di riconoscere la cartella storica
non cancellerebbe niente, **la renderebbe invisibile**, che dal posto di chi
guarda è peggio (nessun errore, memoria apparentemente vuota).

Misurato in case temporanee, senza alcuna variabile `*_DATA_DIR`::

    casa vuota                → <casa>/.verimem     ✅ la promessa «new installs»
    con .engram preesistente  → <casa>/.engram      ✅ la promessa «untouched»
    con .verimem soltanto     → <casa>/.verimem
    con ENTRAMBE              → <casa>/.verimem     ← decisione, non promessa

═══ ⚠️ IL CASO «ENTRAMBE» RIGUARDA CHI MIGRA, E IL README NON LO COPRE ═══

`_compat` lo dichiara di sé: *«If ~/.verimem exists, use it (canonical)»*. È una
scelta legittima e documentata, ma ha una conseguenza che il README non dice:
su una macchina con `~/.engram` popolata, **basta che `~/.verimem` venga creata
— anche vuota — perché il risolutore ci si sposti**. I fatti restano sul disco e
diventano irraggiungibili.

⇒ Qui non si pretende di cambiare quella precedenza: si pretende che resti
**misurata**, così che chi un giorno la toccherà veda subito quali due
popolazioni sta muovendo.

📌 Nota di metodo: la prima versione di questa misura creava `.engram` anche nel
caso «entrambe», quindi ripeteva il caso precedente e non misurava nulla. Un
banco che sbaglia a *costruire* lo scenario è indistinguibile da uno che misura
— per questo ogni scenario qui costruisce le cartelle da un parametro esplicito.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from tests._esito import esito

_RADICE = Path(__file__).resolve().parents[1]

#: Si interroga il risolutore condiviso, non `CONFIG`: `CONFIG` congela il
#: percorso alla costruzione, e in un processo di test sarebbe già congelato.
_SONDA = "from verimem._compat import data_dir; print('DIR=' + str(data_dir()))"


def _dove_finiscono_i_dati(casa: Path) -> str:
    """Il nome della cartella scelta, in un processo con quella casa e ZERO env.

    ⚠️ Su Windows `Path.home()` legge `USERPROFILE`, su POSIX `HOME`: vanno
    impostate entrambe, o il test misura la casa vera di chi lancia la suite.
    """
    env = {k: v for k, v in os.environ.items() if not k.endswith("_DATA_DIR")}
    env.update(HOME=str(casa), USERPROFILE=str(casa), ENGRAM_SKIP_HEAVY="1")
    r = subprocess.run(
        [sys.executable, "-c", _SONDA], capture_output=True, text=True,
        env=env, cwd=str(_RADICE), timeout=300,
    )
    # ⚠️ 2026-08-14: qui c'era `pytest.skip(...)`, e saltare era la cosa
    # sbagliata. Un salto e' legittimo quando NON SI PUO' misurare — docker
    # assente, modello non in cache — non quando il soggetto misurato ha
    # fallito. La sonda e' Python puro che importa il prodotto: se non
    # risponde, o l'import e' rotto o il prodotto e' rotto, e sono entrambi
    # difetti da rendere ROSSI.
    # 🔑 Su un banco che verifica una PROMESSA DEL README lo scambio e' il
    # peggiore: la promessa cade e il banco tace, e il verde di quel giorno
    # dice «verificata» quando nessuno ha verificato niente.
    testo = esito(r)  # dichiara il returncode prima di tutto il resto
    righe = [x for x in testo.splitlines() if x.startswith("DIR=")]
    assert righe, (
        f"la sonda non ha stampato DIR=: il prodotto non ha scelto una "
        f"cartella dati, oppure non si e' importato. stdout={r.stdout[-300:]!r} "
        f"stderr={r.stderr[-300:]!r}")
    return Path(righe[0][4:]).name


def _casa_con(*cartelle: str) -> Path:
    casa = Path(tempfile.mkdtemp(prefix="casa_verimem_"))
    for c in cartelle:
        (casa / c).mkdir()
    return casa


def test_un_installazione_nuova_va_in_verimem():
    """La prima promessa: chi installa oggi trova i dati dove il README dice."""
    assert _dove_finiscono_i_dati(_casa_con()) == ".verimem", (
        "una casa vuota non produce ~/.verimem: il README promette quel percorso "
        "a chi installa per la prima volta")


def test_UNA_ENGRAM_PREESISTENTE_NON_VIENE_ABBANDONATA():
    """⚠️ LA PROMESSA CHE NON PUÒ ROMPERSI — vale più di quella sopra.

    Se questa cade, nessun dato viene perso e nessun errore viene mostrato: il
    prodotto riparte da una cartella nuova e vuota, e chi lo usa conclude che la
    propria memoria è sparita. È anche il caso del sistema su cui giriamo noi.
    """
    assert _dove_finiscono_i_dati(_casa_con(".engram")) == ".engram", (
        "una ~/.engram esistente non viene più riconosciuta: il README promette "
        "che gli store storici continuino a funzionare intatti, e un utente con "
        "anni di fatti vedrebbe una memoria vuota senza un solo messaggio")


def test_con_entrambe_vince_verimem_ed_e_una_DECISIONE_non_una_promessa():
    """⚠️ Il caso che il README NON copre, tenuto sotto misura apposta.

    `_compat` dichiara `~/.verimem` canonica quando entrambe esistono. Se un
    domani questa asserzione cadesse, la precedenza sarebbe stata ribaltata — il
    che è lecito, ma sposta i dati di chiunque abbia fatto la migrazione, e va
    fatto sapendo che li si sta spostando.
    """
    assert _dove_finiscono_i_dati(_casa_con(".engram", ".verimem")) == ".verimem"


def test_IL_README_PROMETTE_ANCORA_ENTRAMBI_I_PERCORSI():
    """⚠️ IL VERSO OPPOSTO: i tre test sopra restano verdi anche se il README
    smettesse di dire dove finiscono i dati. Qui si pretende la promessa scritta.
    """
    testo = (_RADICE / "README.md").read_text(encoding="utf-8", errors="ignore")
    for percorso in ("~/.engram", "~/.verimem"):
        assert percorso in testo, (
            f"il README non nomina più {percorso}: se la riga sui data store è "
            f"stata tolta, il documento ha smesso di dire all'utente dove "
            f"cercare i propri dati")
