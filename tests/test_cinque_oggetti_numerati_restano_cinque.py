"""Cinque oggetti numerati scritti dalla porta devono tornare in cinque.

⚠️ QUESTA CELLA È ROSSA OGGI, ED È IL SUO SCOPO. Tiene il posto della cura che
@ws4 sta scrivendo per T175: finché quella non entra, qui si vede — dalla
porta, con l'output — che cosa riceve davvero l'utente.

IL CASO, misurato il 2026-09-21 dal wheel 0.7.7 di `24e79c97` prima ancora che
esistesse questo file::

    verimem remember "Il capannone 1 misura 400 metri quadri." \
        --source "Perizia del 2026-03-04: il capannone 1 misura 400 metri quadri."
    …e così per i capannoni 2, 3, 4, 5, con cinque perizie diverse

    cinque volte «admitted», cinque volte EXIT=0
    verimem recall "capannone"  ->  store: …t182.db — 1 fatti
                                    - Il capannone 5 misura 400 metri quadri.

Quattro fatti su cinque ritirati a catena come `same-source evolution`, con le
fonti diverse. L'utente non ha nessun segnale: il comando dice cinque volte di
sì e poi la memoria ne contiene uno.

LA CAUSA, isolata sulla funzione pura e passata a @ws4 per la nota di T175:
`extract_quantities("Il capannone 7 misura 400 metri quadri.")` restituisce
`{('misura', 7.0), ('m2', 400.0)}` — **il verbo dopo l'identificatore diventa
la sua unità**, l'identificatore viene consumato come quantità e l'asse che
avrebbe fatto coesistere i due fatti (`_record_numerati_diversi`) non ha più
niente da vedere. L'etichetta sbagliata sul ritiro è T161 (@ws6); questa cella
non riguarda l'etichetta, riguarda **il fatto che sparisce**.

PERCHÉ ALLA PORTA E IN SOTTOPROCESSO, e non con `Memory().add`: ereditando
l'ambiente di pytest l'embedder è uno stub, e senza embedding veri la
supersessione non avviene — **la cella passerebbe, per il motivo sbagliato**.
Misurato il 2026-09-21: le stesse cinque scritture, in un venv senza modello
(«encode delegate unavailable»), lasciano **cinque** fatti nello store. Un
verde ottenuto spegnendo la variabile non è un verde.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

from tests._esito import esito

#: cinque oggetti DIVERSI, cinque fonti DIVERSE, la stessa misura.
#: La misura uguale è il punto: è ciò che rende le frasi simili senza renderle
#: lo stesso fatto. «capannone N» è la forma di «issue N», «fattura N»,
#: «server N» — un'etichetta e un numero che identifica.
CAPANNONI = [1, 2, 3, 4, 5]


def _frase(n: int) -> str:
    return f"Il capannone {n} misura 400 metri quadri."


def _fonte(n: int) -> str:
    return f"Perizia del 2026-03-04: il capannone {n} misura 400 metri quadri."


def _cli(tmp_path, *argomenti: str) -> str:
    """La CLI in un processo pulito, con uno store tutto suo.

    ⚠️ L'AMBIENTE SI RIPULISCE, non si eredita: è la stessa ragione (e quasi
    lo stesso elenco) di `test_la_cli_dice_perche_ha_ammesso`, dove sta
    scritta per esteso — ereditando da pytest il giudice è uno stub.

    ⚠️⚠️ `USERNAME` NON È UN'AGGIUNTA A CASO, ed è il motivo per cui questo
    elenco non è identico all'altro. Senza di lei il comando **stampa la
    ricevuta e poi muore** (T182, misurato il 2026-09-21)::

        env=None (103 variabili)          EXIT=0
        env=le dodici minime (15)         EXIT=1  AssertionError: Artifact of
                                                  type=precompile already
                                                  registered in mega-cache
                                                  artifact factory
        le dodici + USERNAME (16)         EXIT=0
        le dodici + NUMBER_OF_PROCESSORS  EXIT=1   <- non è «una variabile
                                                      qualsiasi»: è lei

    torch costruisce la cartella della sua cache dal nome utente; tolto
    `USERNAME`, due processi ci scrivono sotto lo stesso nome e la
    registrazione dell'artefatto avviene due volte. **Il difetto non è del
    prodotto** — dal wheel, lanciato come lo lancia un utente, 24 esecuzioni
    su 24 escono 0 — **è del modo in cui i banchi lo chiamano.**
    """
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE",
                    "HOMEDRIVE", "HOMEPATH", "PYTHONPATH", "APPDATA",
                    "LOCALAPPDATA", "PATHEXT", "COMSPEC", "USERNAME")}
    for v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        env[v] = str(tmp_path)
    env["ENGRAM_EVENT_LOG"] = str(tmp_path / "eventi.jsonl")
    r = subprocess.run([sys.executable, "-m", "verimem.cli", *argomenti],
                       capture_output=True, text=True, timeout=900, env=env)
    return esito(r)


@pytest.mark.slow
def test_cinque_oggetti_numerati_tornano_in_cinque(tmp_path):
    """Il numero che conta per chi usa il prodotto: quanti me ne ridà.

    ROSSA finché la cura di T175 non entra. Il messaggio dice QUALI mancano,
    non solo quanti: un conteggio non basta a chi deve ripararlo.
    """
    db = str(tmp_path / "accettazione.db")

    # ── le cinque scritture, e il CONTROLLO POSITIVO su ciascuna ────────────
    # Se una fosse TRATTENUTA, il recall corto avrebbe una causa diversa e
    # questa cella accuserebbe la supersessione al posto del gate.
    non_ammesse = []
    for n in CAPANNONI:
        uscita = _cli(tmp_path, "remember", _frase(n),
                      "--source", _fonte(n), "--topic", "accettazione/capannoni",
                      "--db", db)
        if "admitted" not in uscita:
            non_ammesse.append((n, uscita.strip()[-300:]))

    assert not non_ammesse, (
        "il banco non è nella condizione che vuole misurare: queste scritture "
        "NON sono state ammesse, quindi un recall corto non direbbe niente "
        f"sulla supersessione.\n{non_ammesse}")

    # ── la domanda dell'utente: me li ridai tutti e cinque? ─────────────────
    letto = _cli(tmp_path, "recall", "capannone", "--db", db)
    mancanti = [n for n in CAPANNONI if _frase(n) not in letto]

    assert not mancanti, (
        f"cinque scritture ammesse, {len(CAPANNONI) - len(mancanti)} fatti "
        f"serviti dal recall. Mancano i capannoni {mancanti}: sono stati "
        f"ritirati come «same-source evolution» pur avendo cinque fonti "
        f"diverse, perché il verbo che segue l'identificatore viene letto "
        f"come la sua unità e l'identificatore non si vede più.\n"
        f"--- quello che il recall ha risposto ---\n{letto}")
