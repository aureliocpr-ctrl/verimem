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


def test_chi_non_ha_chiesto_il_daemon_non_riceve_l_avviso(tmp_path):
    """LA CURA (C): un avviso che esce SEMPRE non informa, riempie.

    Prima stesura di questa PR: l'avviso usciva su ogni giudizio in casa — il
    caso normale — e in CI ha fatto cadere SEI celle di altri su tre sistemi
    (run 35650184556): chi conta gli avvisi (`assert n_avvisi == 0`), chi
    garantisce che un fatto ammesso non riceva la seconda voce
    (`assert "giudice era d" not in out`) e chi legge col parser la riga che
    parla di delega. Nessuna di quelle celle era sbagliata: era sbagliato
    l'avviso.
    ⇒ Qui la delega NON e' richiesta: chi scrive non ha mai chiesto il daemon,
    e la ricevuta non deve dirgli niente.
    """
    r = _ricevuta(_cli(tmp_path, "remember", CLAIM, "--source", FONTE,
                       "--topic", "prova/t179", "--json", delega=False))
    avvisi = [w for w in (r.get("warnings") or [])
              if str(w.get("layer")) == "giudice_in_processo"]
    assert not avvisi, (
        "la ricevuta avvisa chi non ha chiesto il daemon: e' il rumore che ha "
        f"fatto cadere sei celle altrui. {json.dumps(avvisi, ensure_ascii=False)[:300]}")


def test_se_avevi_chiesto_il_daemon_e_ha_giudicato_il_processo_lo_dice(tmp_path, monkeypatch):
    """IL CASO (ii), quello che ha aperto T179: la promessa disattesa.

    Delega richiesta E scorer gia' caricato in questo processo: la riga 1038
    non entra nel ramo del daemon, il giudizio resta in casa, e il daemon non
    viene interrogato nemmeno se risponde. E' l'unico caso in cui la ricevuta
    deve parlare.

    ⛔ NON si misura dalla CLI: ogni comando e' un processo nuovo, e il
    presupposto («scorer gia' in casa») nasce solo DENTRO un processo che ha
    gia' giudicato una volta. Qui lo si costruisce esplicitamente, invece di
    sperare che la seconda scrittura lo trovi caldo.
    """
    monkeypatch.setenv("HIPPO_ENCODE_DELEGATE_ONLY", "1")
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from verimem import local_grounding as lg
    from verimem.client import Memory

    # ⚠️ IL GIUDICE E' UN SINGLETON DI MODULO: caricarlo qui e non spegnerlo
    # lascerebbe uno scorer CALDO alle celle che vengono dopo, e una che
    # presuppone il giudice freddo cadrebbe per colpa mia, lontano da qui.
    # `test_flow_warmup_dichiarato.py` lo resetta PRIMA e DOPO con una
    # fixture: qui il `finally` fa lo stesso lavoro senza aggiungere fixture.
    lg.reset_local_judge()
    try:
        giudice = lg.get_local_judge()
        giudice._ensure_scorer()   # ⇐ il presupposto, costruito e non sperato
        assert giudice._scorer is not None, (
            "lo scorer non si e' caricato: la cella non puo' misurare il caso "
            "(ii), e questo e' un guasto del banco, non un motivo per passare")

        m = Memory(tmp_path / "m.db")
        r = m.add(CLAIM, topic="prova/t179c", source=FONTE)
    finally:
        lg.reset_local_judge()

    chi = str(r.get("judged_by") or "")
    assert "process" in chi, (
        f"non ha giudicato il processo, la cella non misura: judged_by={chi!r}")
    avvisi = [w for w in (r.get("warnings") or [])
              if str(w.get("layer")) == "giudice_in_processo"]
    assert avvisi, (
        "avevi chiesto il daemon, ha giudicato il processo, e la ricevuta tace: "
        f"{json.dumps(r.get('warnings'), ensure_ascii=False)[:300]}")
    assert "avevi chiesto il daemon" in str(avvisi[0].get("reason")), avvisi[0]


def test_il_giudizio_non_cambia(tmp_path):
    """NON-REGRESSIONE: la PR fa parlare la ricevuta, non sposta il verdetto."""
    r = _ricevuta(_cli(tmp_path, "remember", CLAIM, "--source", FONTE,
                       "--topic", "prova/t179b", "--json", delega=False))
    assert r.get("esito") in ("ammesso", "quarantinato", "respinto"), r
    assert "id" in r, r
