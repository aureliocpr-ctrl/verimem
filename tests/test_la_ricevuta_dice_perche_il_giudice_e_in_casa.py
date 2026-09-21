"""Quando giudica il processo stesso, la ricevuta deve dire PERCHE'.

La ricevuta dice CHI ha giudicato (`judged_by: "in-process"`) e non perche'
non l'abbia fatto il daemon. Per chi usa il prodotto sono due cose diverse:
la prima e' un'etichetta, la seconda e' la sola che dica se l'installazione
sta lavorando come crede.

⚖️ QUESTA CELLA NON CAMBIA IL COMPORTAMENTO DEL RIPIEGO, e la PR nemmeno: il
giudizio resta quello di prima, cambia solo cio' che la ricevuta ne racconta.
La causa del ripiego si cura dopo (T179-b) con questa riga gia' accesa.

📌 IL FORMATO NON E' NUOVO: `layer` / `reason` / `advice` e' gia' quello di
`duplicate_check_skipped` (client.py) e di «encode delegate unavailable»
(memory.py, semantic.py); e `local_grounding.py` riporta gia' la ragione DEL
DAEMON con le sue parole («Motivo dal daemon: …»). Qui si applica la stessa
forma a un caso che oggi tace.

⚠️ E IL RAMO NON E' QUELLO CHE SEMBRA, letto nel sorgente: dentro il blocco
`if judge._scorer is None and _delegate_only():` un daemon muto fa uscire con
`return None` — NON si ripiega in casa. In-process si raggiunge SOLO non
entrando in quel blocco, cioe' con almeno una delle due condizioni falsa
NELL'ISTANTE della chiamata. E' l'ipotesi della nota, e la ricevuta deve
dire quale delle due ha deciso: e' il solo modo di falsificarla.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from tests._esito import esito

CLAIM = "Il collaudo della linea 3 e' stato ultimato il 12 marzo."
FONTE = ("Il collaudo della linea 3 si e' ultimato il 12 marzo con esito "
         "positivo e la linea e' stata approvata dalla commissione.")


# ⛔ NIENTE «SCOPERTA A PORTA CHIUSA»: NON FUNZIONA, e la prima stesura di
# questo banco credeva di si'. `encode_service.DISCOVERY_PATH` e' FISSO nella
# home — `Path.home() / ".engram" / "encode_service.json"` — e NON segue
# `HIPPO_DATA_DIR`: un file scritto nello store di prova non viene mai letto,
# e la cella misurava un regime che non aveva prodotto lei.
# Misurato il 2026-09-21: con delega richiesta e «porta chiusa» scritta nello
# store, la ricevuta torna `judged_by=daemon, moat=passed` — cioe' ha parlato
# col daemon VERO, non con la porta finta.
# ⇒ Qui il regime si forza con l'unica leva che agisce davvero e che non tocca
# il daemon di nessuno: `HIPPO_ENCODE_DELEGATE_ONLY`. Scrivere nel file della
# home sarebbe l'altra strada, ed e' esclusa: quel file e' del daemon condiviso
# di tutti.
# 📌 E il fatto che la scoperta non sia isolata per store e' un reperto suo,
# gemello di T91 («le variabili dello store non isolano tutto»).


def _cli(tmp_path, *argomenti: str, delega: bool) -> str:
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE",
                    "HOMEDRIVE", "HOMEPATH", "PYTHONPATH", "APPDATA",
                    "LOCALAPPDATA", "PATHEXT", "COMSPEC", "USERNAME")}
    for v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        env[v] = str(tmp_path)
    env["ENGRAM_EVENT_LOG"] = str(tmp_path / "eventi.jsonl")
    env["HIPPO_ENCODE_DELEGATE_ONLY"] = "1" if delega else "0"
    r = subprocess.run([sys.executable, "-m", "verimem.cli", *argomenti],
                       capture_output=True, text=True, timeout=900, env=env)
    return esito(r, atteso=None)


def _ricevuta(testo: str) -> dict:
    d = json.JSONDecoder()
    for i, c in enumerate(testo):
        if c != "{":
            continue
        try:
            oggetto, _ = d.raw_decode(testo[i:])
        except ValueError:
            continue
        if isinstance(oggetto, dict) and "esito" in oggetto:
            return oggetto
    raise AssertionError(f"nessuna ricevuta nell'uscita: {testo[-400:]}")


def test_se_giudica_il_processo_la_ricevuta_dice_perche(tmp_path):
    """RED: oggi `judged_by` dice «in-process» e nient'altro.

    Il regime si forza con `HIPPO_ENCODE_DELEGATE_ONLY=0`: la delega non
    e' richiesta, quindi giudica il processo. E' l'unica leva che agisce
    senza toccare il file di scoperta condiviso.
    """
    r = _ricevuta(_cli(tmp_path, "remember", CLAIM, "--source", FONTE,
                       "--topic", "prova/t179", "--json", delega=False))
    chi = str(r.get("judged_by") or "")
    if "process" not in chi:
        raise AssertionError(
            f"non ha giudicato il processo, la cella non misura: judged_by={chi!r}")

    testo = json.dumps(r, ensure_ascii=False).lower()
    assert ("delegate" in testo or "delega" in testo or "daemon" in testo), (
        "la ricevuta dice CHI ha giudicato e non PERCHE' non l'ha fatto il "
        f"daemon: {json.dumps(r, ensure_ascii=False)[:400]}")


def test_il_giudizio_non_cambia(tmp_path):
    """NON-REGRESSIONE: la PR fa parlare la ricevuta, non sposta il verdetto."""
    r = _ricevuta(_cli(tmp_path, "remember", CLAIM, "--source", FONTE,
                       "--topic", "prova/t179b", "--json", delega=False))
    assert r.get("esito") in ("ammesso", "quarantinato", "respinto"), r
    assert "id" in r, r
