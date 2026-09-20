"""Un fatto ammesso deve dire PERCHE', non solo che e' entrato.

MISURATO il 2026-09-20 sul tronco a5a9ac0a, stesso claim, stesse due uscite:

    testo    admitted id=0217fdf427bd topic=prova/t174
    --json   esito ammesso · punteggio 99.77965545654297 · soglia 40.0 ·
             scala moat-0-100 · margine 59.77965545654297 · giudice local ·
             modello local_gate_ce_v2 · moat passed

Nove parole contro ventidue chiavi. E per un NO la stessa CLI stampa ventidue
righe: layer, advice, «il giudice era d'accordo», il suggerimento su
writer_role. ⇒ Il prodotto argomenta i suoi no e non i suoi si'.

⚠️ QUESTO NON E' UN CALCOLO, E' UNA STAMPA: punteggio, soglia e giudice sono
gia' nella ricevuta che la CLI ha in mano mentre stampa quella riga. La cella
lo fissa nel modo piu' duro possibile — i numeri della riga di testo devono
essere gli STESSI del json, carattere per carattere dove sono stringhe e senza
ricalcoli dove sono numeri. Se un giorno qualcuno li riformattasse a mano, qui
si vedrebbe.

⚠️ Il NO non si tocca: una cella lo tiene fermo.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

from tests._esito import esito

CLAIM = "Il collaudo della linea 3 e' stato ultimato il 12 marzo."
FONTE = ("Il collaudo della linea 3 si e' ultimato il 12 marzo con esito "
         "positivo e la linea e' stata approvata dalla commissione.")


def _cli(tmp_path, *argomenti: str) -> str:
    """La CLI in un processo pulito, con uno store tutto suo.

    ⚠️ L'AMBIENTE SI RIPULISCE, non si eredita. Ereditando `os.environ` da
    pytest il sottoprocesso si porta dietro le variabili che il conftest
    impone, e con quelle il giudice e' uno stub: la ricevuta torna con
    `punteggio: None` e questa cella misurerebbe l'ambiente di test invece
    del prodotto. Misurato il 2026-09-20: stesso claim, stesso store nuovo —
    dalla shell `punteggio 99.86578369140625`, ereditando da pytest `None`.
    Qui si simula un UTENTE, quindi si tengono solo le variabili di sistema
    piu' quelle dello store.
    """
    import os
    env = {k: v for k, v in os.environ.items()
           if k in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE",
                    "HOMEDRIVE", "HOMEPATH", "PYTHONPATH", "APPDATA",
                    "LOCALAPPDATA", "PATHEXT", "COMSPEC")}
    for v in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        env[v] = str(tmp_path)
    env["ENGRAM_EVENT_LOG"] = str(tmp_path / "eventi.jsonl")
    r = subprocess.run([sys.executable, "-m", "verimem.cli", *argomenti],
                       capture_output=True, text=True, timeout=900, env=env)
    return esito(r)


def _ricevuta_json(tmp_path, suffisso: str) -> dict:
    testo = _cli(tmp_path, "remember", CLAIM + suffisso, "--source", FONTE,
                 "--topic", "prova/t174", "--json")
    return json.loads(testo[testo.index("{"):testo.rindex("}") + 1])


def test_la_riga_dell_ammissione_dice_cio_che_la_ricevuta_sa(tmp_path):
    """La riga di un SI' deve dire perche', e distinguere DUE sì diversi.

    ⚠️ IL CASO CHE MI MANCAVA quando ho scritto la nota, e l'ha trovato il
    banco: un fatto puo' entrare AMMESSO con `moat: not_run:no_judge`, cioe'
    senza che nessuno abbia giudicato. Oggi la CLI scrive
    «admitted id=… topic=…» IDENTICO nei due casi — giudicato 99.87 e non
    giudicato affatto. Sono due sì diversissimi.
    """
    d = _ricevuta_json(tmp_path, " (a)")
    assert d.get("esito") == "ammesso", d

    testo = _cli(tmp_path, "remember", CLAIM + " (b)", "--source", FONTE,
                 "--topic", "prova/t174")
    tutto = " ".join(testo.splitlines())
    assert "admitted" in tutto, f"non c'e' piu' la riga di ammissione: {tutto[-300:]}"

    if d.get("punteggio") is None:
        # Nessun giudizio: la riga deve DIRLO, non tacere.
        assert ("non giudicat" in tutto.lower()
                or "not_run" in tutto
                or "no_judge" in tutto), (
            "il fatto e' entrato SENZA giudizio e la riga non lo dice: chi "
            f"legge crede che qualcuno abbia controllato. {tutto[-300:]}")
    else:
        for campo, atteso in (("punteggio", f"{d['punteggio']:.2f}"),
                              ("soglia", f"{d['soglia']:.0f}"),
                              ("giudice", str(d["giudice"])),
                              ("modello", str(d["modello"]))):
            assert atteso in tutto, (
                f"la riga non dice {campo}={atteso}: {tutto[-300:]}")


def test_i_numeri_della_riga_sono_quelli_della_ricevuta(tmp_path):
    """Non ricalcolati: gli STESSI. Una riformattazione a mano si vedrebbe."""
    d = _ricevuta_json(tmp_path, " (c)")
    testo = _cli(tmp_path, "remember", CLAIM + " (d)", "--source", FONTE,
                 "--topic", "prova/t174")
    tutto = " ".join(testo.splitlines())
    if d.get("punteggio") is None:
        assert not re.search(r"\d+\.\d+/100", tutto), (
            f"la riga inventa un punteggio che la ricevuta non ha: {tutto[-300:]}")
    else:
        assert f"{d['punteggio']:.2f}" in tutto, (
            f"il punteggio stampato non e' quello della ricevuta "
            f"({d['punteggio']:.2f}): {tutto[-300:]}")


def test_il_no_resta_com_e(tmp_path):
    """NON-REGRESSIONE: la spiegazione dei rifiuti non si tocca."""
    testo = _cli(tmp_path, "remember",
                 "Ho verificato che il sistema funziona correttamente.",
                 "--topic", "prova/t174no")
    assert "advice" in testo.lower() or "quarantined" in testo.lower(), (
        f"il NO ha perso la sua spiegazione: {testo[-400:]}")
