"""Le variabili d'ambiente che il README insegna devono CAMBIARE il comportamento.

Il README documenta undici variabili. Sei le legge il codice col nome esatto;
le altre cinque il codice le legge con un prefisso diverso (`ENGRAM_`), e a
tradurle è il mirror di compatibilità che gira all'import. Misurato oggi::

    documentate dal README        11
    lette col nome ESATTO          6
    lette con ALTRO prefisso       5   ← passano dal mirror
    mai lette da nessuno           0   ✅

⇒ Nessuna promessa vuota: **una variabile documentata e non letta sarebbe una
leva scollegata** — l'utente la imposta, non succede niente, e non ha modo di
accorgersene. Questo file blinda uno stato che oggi è sano, perché il README e
i nomi nel codice cambiano in momenti diversi.

═══ ⚠️⚠️ IL TEST OVVIO QUI È VERDE PER COSTRUZIONE — NON SCRIVERLO ═══

La verifica che viene in mente per prima è: imposta `VERIMEM_X`, importa
`verimem`, guarda se in `os.environ` compare `ENGRAM_X`. **Passa sempre**, e non
misura niente::

    VERIMEM_QUESTA_NON_ESISTE_DAVVERO=7777
      →  ENGRAM_QUESTA_NON_ESISTE_DAVVERO = 7777

Il mirror copia **qualunque** nome che porti il prefisso: non sa quali variabili
esistano, e non deve saperlo. Un test costruito su quella osservazione
promuoverebbe anche una variabile inventata, cioè **esattamente il difetto che
dovrebbe trovare**.

🔑 La misura giusta guarda l'**effetto**, non l'ambiente: si chiama il codice che
la variabile governa e si controlla che il valore *usato* sia cambiato. Le
quattro celle qui sotto — leva del README, leva del codice, niente, nome
inventato — sono la differenza fra un presidio e una decorazione.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from tests._esito import esito

_RADICE = Path(__file__).resolve().parents[1]

#: La leva scelta come sonda: `_mode()` restituisce `"off"` solo se la variabile
#: vale 0/off/false/no, `"auto"` altrimenti. Una porta piccola, deterministica e
#: che non carica modelli — perciò misurabile in un processo separato.
_SONDA = "import verimem, verimem.band_escalation as b; print('MODE=' + b._mode())"


def _mode_con(**variabili: str) -> str:
    """Il comportamento osservato in un processo pulito, con quelle variabili.

    ⚠️ Ogni `*_BAND_LLM` ereditata viene tolta: se l'ambiente di chi lancia i
    test ne portasse una, il controllo negativo misurerebbe quella e il file
    sembrerebbe sano per la ragione sbagliata.
    """
    env = {k: v for k, v in os.environ.items() if not k.endswith("_BAND_LLM")}
    env["ENGRAM_SKIP_HEAVY"] = "1"
    env.update(variabili)
    r = subprocess.run(
        [sys.executable, "-c", _SONDA], capture_output=True, text=True,
        env=env, cwd=str(_RADICE), timeout=300,
    )
    # ⚠️ 2026-08-14: era `pytest.skip(...)`. Il commento diceva gia' la verita'
    # — «(import fallito?)» — e saltava lo stesso: un import fallito e' un
    # difetto, non un ambiente mancante. Su un banco che verifica che le LEVE
    # INSEGNATE DAL README abbiano effetto, saltare significa dire «la leva
    # funziona» ogni volta che il prodotto non parte.
    testo = esito(r)
    righe = [x for x in testo.splitlines() if x.startswith("MODE=")]
    assert righe, (
        f"la sonda non ha stampato MODE=: la leva non ha prodotto un modo, "
        f"oppure il prodotto non si e' importato. stdout={r.stdout[-300:]!r} "
        f"stderr={r.stderr[-300:]!r}")
    return righe[0].split("=", 1)[1]


def test_la_leva_col_nome_del_readme_cambia_il_comportamento():
    """Il cuore: chi copia il nome dal README deve ottenere l'effetto promesso."""
    assert _mode_con(VERIMEM_BAND_LLM="0") == "off", (
        "`VERIMEM_BAND_LLM=0` è il nome che il README insegna e non spegne "
        "niente: o il mirror di compatibilità non traduce più, o il codice ha "
        "cambiato il nome che legge — in entrambi i casi il README documenta "
        "una leva scollegata")


def test_il_nome_che_il_codice_legge_resta_valido():
    """Controllo positivo: la strada storica (`ENGRAM_`) non deve rompersi.

    Chi ha già `ENGRAM_BAND_LLM` negli script — noi compresi — non deve
    scoprire che una pulizia dei nomi gli ha spento la leva sotto i piedi.
    """
    assert _mode_con(ENGRAM_BAND_LLM="0") == "off"


def test_SENZA_VARIABILE_il_default_resta_acceso():
    """⚠️ Controllo negativo, e senza questo i due sopra non provano nulla.

    Se `_mode()` restituisse `"off"` sempre — per un refuso, per un default
    ribaltato — i due test qui sopra sarebbero verdi con la leva rotta. Qui si
    misura la popolazione opposta: niente variabile, comportamento acceso.
    """
    assert _mode_con() == "auto", (
        "senza variabile il comportamento non è quello di default: i test sulla "
        "leva non stanno più distinguendo il caso acceso dal caso spento")


def test_UN_NOME_INVENTATO_NON_DEVE_CAMBIARE_NIENTE():
    """⚠️⚠️ IL TEST CHE VALE PIÙ DEGLI ALTRI TRE — leggi il docstring in cima.

    Il mirror copia ogni nome col prefisso, anche uno che non esiste. Quindi
    una verifica fatta su `os.environ` promuove pure `VERIMEM_QUESTA_NON_ESISTE`
    e dichiara sano qualunque stato. Qui si pretende che la sonda **discrimini**:
    se un giorno anche questa asserzione dovesse cadere, il file avrebbe smesso
    di misurare l'effetto e sarebbe tornato a misurare la copia.
    """
    assert _mode_con(VERIMEM_QUESTA_NON_ESISTE="0") == "auto", (
        "un nome inventato cambia il comportamento: la sonda non sta misurando "
        "l'effetto della variabile ma qualcos'altro — un presidio così è verde "
        "per costruzione")


def test_IL_README_DOCUMENTA_ANCORA_LE_SUE_LEVE():
    """⚠️ IL VERSO OPPOSTO sul documento: senza, si «supera» cancellando.

    Il modo più facile di rendere vera «ogni variabile documentata funziona» è
    smettere di documentarne. Qui si pretende che il README continui a insegnare
    le sue leve — la promessa va mantenuta, non ritirata.
    """
    testo = (_RADICE / "README.md").read_text(encoding="utf-8", errors="ignore")
    documentate = set(re.findall(r"\b((?:VERIMEM|ENGRAM|HIPPO)_[A-Z0-9_]{2,})\b", testo))
    assert len(documentate) >= 8, (
        f"il README documenta solo {len(documentate)} variabili "
        f"({sorted(documentate)}): erano 11 — se sono state tolte invece che "
        f"corrette, il documento è peggiorato")
