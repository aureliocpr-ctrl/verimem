"""Il tetto del giudizio: una chiamata alla porta non puo' NON tornare.

⚠️ PERCHE' ESISTE — misurato il 15-16/09 alla porta MCP, quattro volte su quattro:

    initialize                             5.73 s
    tools/list                             0.01 s
    prima chiamata (hippo_remember)      424.06 s  -> {"CHIUSO": "Connection closed"}
    EXIT=124

E la CPU dice che non e' lentezza, e' un ARRESTO::

    t+ 10 s   CPU   4.52 s   RSS  128.5 MB     <- sta lavorando
    t+ 35 s   CPU  21.83 s   RSS  737.9 MB     <- qui finisce il lavoro
    t+246 s   CPU  22.17 s   RSS  737.9 MB     <- 0,34 s di CPU in 236 s (0,1%)

Il gestore gira INLINE sull'anello (`mcp_server.call_tool`: «deliberately NOT a
thread offload; that broke stdio»), quindi quando il giudizio si pianta si pianta
tutto il server: il client non vede un errore, vede la connessione morire.

🔴 LA CAUSA DELL'ARRESTO E' IGNOTA, e questo modulo NON la cura. Sei candidati
sono stati esclusi eseguendo (il lavoro: 14,6 s in-process; il precarico; la gara
a pausa zero; lo scaricamento; due import concorrenti; worker anyio + anello) e
la pila si ferma in `create_module` di `scipy` dentro `sklearn`, sotto Python.
Il passo dopo e' un debugger nativo (T90b), non questo file.

🔑 QUESTO MODULO CURA IL SINTOMO, ed e' il contratto I5/I7: **o il fatto e'
giudicato, o entra DICHIARANDO che non lo e' stato**. Non esiste il terzo caso,
quello di oggi: la chiamata che non torna mai.

IL TETTO STA QUI E SOLO QUI. Chi lo vuole diverso passa da `VERIMEM_JUDGE_BUDGET_S`;
`doctor` lo stampa, cosi' il numero non e' una costante nascosta in un file che
nessuno legge (e' la classe «il numero dichiarato non e' quello applicato», gia'
pagata due volte in questa casa).

⚠️ LO STATO DEGRADATO STA SU UN FILE, NON IN UNA VARIABILE, e la ragione e'
banale: `doctor` e' un ALTRO PROCESSO. Un flag di modulo sarebbe invisibile
proprio a chi deve vederlo. Stessa forma della scoperta del daemon, che per la
stessa ragione e' un file.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

#: Il tetto, in secondi. Il lavoro vero misurato dura ~35 s (CPU e RSS salgono
#: fino a li' e poi si fermano): 60 s e' il doppio, quindi non taglia un
#: giudizio lento — taglia un giudizio FERMO.
TETTO_S = float(os.environ.get("VERIMEM_JUDGE_BUDGET_S") or 60.0)

#: Nome del livello che salta quando il tetto scade. La ricevuta deve dire
#: QUALE, non un generico «non giudicato» (specifica della ricevuta, 16/09).
LIVELLO = "L4"


def _cartella() -> Path:
    """La cartella dei marcatori: la data dir in vigore ADESSO.

    Risolta a ogni accesso e non all'import: un path che dipende dall'ambiente
    non e' una costante (lezione gia' pagata su `DISCOVERY_PATH` e su
    `EVENT_LOG_PATH`, che si fissano all'import e restano indietro).
    """
    try:
        from ._compat import _env_data_dir
        override = _env_data_dir()
    except Exception:  # noqa: BLE001 — il marcatore non deve mai rompere una scrittura
        override = None
    return Path(override).expanduser() if override else Path.home() / ".engram"


def percorso_del_marcatore() -> Path:
    return _cartella() / "giudizio-degradato.json"


def ragione_del_salto(secondi: float | None = None) -> str:
    """La frase che finisce nella ricevuta. Una sola forma, in un posto solo."""
    return f"{LIVELLO}: non ha girato: tetto {secondi if secondi is not None else TETTO_S:.0f} s"


def segna_degradato(motivo: str) -> None:
    """Questo processo non riesce piu' a giudicare: si scrive, non si stampa.

    Best-effort per disegno: se il disco non collabora, la scrittura del FATTO
    non deve fallire per colpa del marcatore.
    """
    try:
        p = percorso_del_marcatore()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "pid": os.getpid(),
            "quando": time.time(),
            "motivo": motivo,
            "tetto_s": TETTO_S,
        }), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def stato_degradato() -> dict | None:
    """Il marcatore, se c'e' e se il processo che l'ha scritto e' ancora vivo.

    ⚠️ Il pid si controlla: un marcatore di un processo morto racconterebbe un
    guasto che non c'e' piu', e un allarme che mente si smette di leggerlo.
    """
    try:
        dati = json.loads(percorso_del_marcatore().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    pid = dati.get("pid")
    if isinstance(pid, int):
        try:
            import psutil
            if not psutil.pid_exists(pid):
                return None
        except ImportError:
            pass
    return dati


def questo_processo_e_degradato() -> bool:
    """Vero se e' QUESTO processo ad aver gia' sbattuto contro il tetto.

    Serve alla seconda scrittura: aspettare di nuovo sessanta secondi per
    scoprire la stessa cosa e' tempo dell'utente buttato.
    """
    dati = stato_degradato()
    return bool(dati and dati.get("pid") == os.getpid())
