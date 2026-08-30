"""`_have_judge` elenca tre vie al giudizio, e il daemon e' la quarta.

LA RIGA. `anti_confab_gate.py:2350`::

    _have_judge = (grounding_llm is not None
                   or _resolve_backend() == "local"
                   or local_ce_available())

⇒ Tre criteri: un llm iniettato, il backend dichiarato `local`, il modello CE su
disco. **Il daemon condiviso non e' nell'elenco** — ed e' un giudice a tutti gli
effetti: `try_local_score` gli chiede per primo, e il docstring di
`_gate_via_daemon` spiega perche' *«e' cio' che rende giudicata la PRIMA
scrittura invece di ammetterla al buio»*.

⚠️ E `local_ce_available` risponde alla domanda «c'e' un modello IN CASA?»
mentre il chiamante chiede «c'e' un GIUDICE?». Le due domande hanno smesso di
coincidere quando e' nato il daemon. Tre dei suoi cinque chiamanti portano gia'
una nota di cautela; questo no.

🔑 IL PRECEDENTE, di due ore fa: la clausola `and not judge._load_failed` in
`try_local_score` faceva **lo stesso errore** — un predicato che descrive QUESTO
processo usato per decidere di un ALTRO. Misurata e tolta il 2026-08-30 alle
22:16. **Questa guardia e' la stessa forma, un livello piu' su.**

LE DUE POPOLAZIONI, e servono entrambe:

  [BENEFICIO]  modello locale ASSENTE + daemon VIVO
               la guardia dice «nessun giudice» e il daemon giudicherebbe.
               Quanto si perde: un verdetto per ogni write con fonte.

  [COSTO]      modello locale ASSENTE + daemon SPENTO (nessun giudice DAVVERO)
               togliere la guardia farebbe TENTARE il giudizio a ogni write.
               `local_ce_available` esiste apposta — «cheap by design: it NEVER
               loads the model, so the gate can ask "is there a judge?" on the
               hot write path without paying the cold-start». Quanto costa il
               tentativo, in millisecondi, e' cio' che decide se la cura si puo'
               fare.

⚠️ Con la sola [BENEFICIO] si «cura» aprendo un costo che nessuno ha misurato;
con la sola [COSTO] non si vede cosa si guadagna.

LA PREDIZIONE, scritta prima di eseguire: **[BENEFICIO] il write esce senza
verdetto mentre `try_local_score` nello stesso processo ne produce uno**;
**[COSTO] il tentativo fallito costa pochi millisecondi**, perche' il ramo
`except (FileNotFoundError, OSError, ImportError, NoGroundingJudge)` intercetta
un modello assente **senza caricare nulla**.

CONDIZIONE DI FALSIFICAZIONE: se in [COSTO] il write senza giudice pagasse
secondi invece di millisecondi, la guardia guadagnerebbe cio' che costa e la
cura andrebbe pensata diversamente (per esempio aggiungendo una quarta via
economica invece di togliere il predicato).

═══════════════════════════════════════════════════════════════════════════════
🔑 IL CONTROLLO CHE DEVE POTER FALLIRE: nel regime [BENEFICIO], `try_local_score`
DEVE dare un punteggio. Se non lo desse, il daemon non starebbe giudicando e il
`grounding_score=None` del write non direbbe nulla sulla guardia — misurerei un
daemon spento e lo chiamerei difetto.
═══════════════════════════════════════════════════════════════════════════════

REGIME: processi separati, store TEMPORANEO ciascuno. Il modello locale si rende
assente puntando `ENGRAM_LOCAL_GATE_MODEL` a una cartella vuota (nessun
download, ⛔ nessun `warmup`). Il daemon si rende irraggiungibile **solo per quel
processo** con `ENGRAM_ENCODE_SERVICE=0`, che `_gate_via_daemon` legge alla
prima riga: il servizio condiviso resta acceso per tutte le altre. Lo store di
Aurelio non e' toccato.

    python docs/stato-reale/banchi/ws3-la-guardia-che-decide-se-c-e-un-giudice-non-conosce-il-daemon.py
"""

from __future__ import annotations

import json
import subprocess
import sys

CLAIM = "La penale e' di 500 euro al giorno."
FONTE = "Il contratto fissa la penale in 120 euro al giorno."

#: ⚠️ Il figlio RICALCOLA `_have_judge` invece di importarlo: nel prodotto e'
#: una variabile locale dentro il write path, non una funzione. Ricalcolarla
#: qui e' una COPIA della condizione — se un giorno il prodotto la cambia,
#: questo banco misura la vecchia e va riletto. E' un limite, ed e' scritto.
FIGLIO = r'''
import json, os, sys, tempfile, time
os.environ["HIPPO_DATA_DIR"] = tempfile.mkdtemp()
os.environ["ENGRAM_LOCAL_GATE_MODEL"] = tempfile.mkdtemp()   # cartella VUOTA
os.environ["HIPPO_ENCODE_DELEGATE_ONLY"] = "1"
if sys.argv[1] == "senza_daemon":
    os.environ["ENGRAM_ENCODE_SERVICE"] = "0"                # solo per QUESTO processo
claim, fonte = sys.argv[2], sys.argv[3]

from verimem.grounding_gate import _resolve_backend
from verimem.local_grounding import local_ce_available, try_local_score

# ⚠️ LA COPIA VA TENUTA ALLINEATA, e il 30/08 alle 22:37 non lo era: dopo aver
# aggiunto la quarta via al prodotto, il banco continuava a calcolare i soli
# TRE criteri e stampava `have_judge=False` mentre nel prodotto era True —
# cioe' il banco mentiva sul proprio regime per la terza volta in una notte.
try:
    from verimem.local_grounding import daemon_del_giudice_annunciato
except ImportError:                      # prodotto senza la quarta via
    def daemon_del_giudice_annunciato():
        return False

have_judge = ((_resolve_backend() == "local") or local_ce_available()
              or daemon_del_giudice_annunciato())

# ⚠️ L'ORDINE INQUINA IL COSTO, e la prima stesura ci è caduta: chiamare
# `try_local_score` PRIMA del write mette in cache il fallimento di
# caricamento, e il write che segue paga 187 ms invece dei secondi veri.
# Il figlio fa UNA cosa sola, scelta dal chiamante.
if sys.argv[4] == "diretto":
    t0 = time.perf_counter()
    diretto = try_local_score(fonte, claim)
    ms_diretto = round((time.perf_counter() - t0) * 1000)
    r, ms_write = {}, None
else:
    diretto, ms_diretto = None, None
    from verimem.client import Memory
    t1 = time.perf_counter()
    r = Memory().add(claim, topic="hj/x", source=fonte, validate="full")
    ms_write = round((time.perf_counter() - t1) * 1000)

lay = [str(w.get("layer")) for w in (r.get("warnings") or []) if isinstance(w, dict)]
print(json.dumps({
    "have_judge": bool(have_judge),
    "diretto": None if diretto is None else round(float(diretto[0]), 4),
    "ms_diretto": ms_diretto,
    "status": r.get("status"),
    "gs": r.get("grounding_score"),
    "ms_write": ms_write,
    "lay": lay,
}, default=str, ensure_ascii=False))
'''

REGIMI = [
    ("BENEFICIO  daemon VIVO", "con_daemon"),
    ("COSTO      daemon SPENTO", "senza_daemon"),
]


def main() -> int:
    print("  LA RIGA: `_have_judge = grounding_llm is not None or "
          "_resolve_backend()=='local' or local_ce_available()`")
    print("  Il daemon condiviso NON e' fra i tre criteri.\n")
    print(f"  {'regime':<28} {'have_judge':<11} {'try_local_score':<16} "
          f"{'gs del write':<13} {'ms write':<9} strati")
    print("  " + "-" * 96)

    def _figlio(modo: str, cosa: str) -> dict:
        p = subprocess.run([sys.executable, "-c", FIGLIO, modo, CLAIM, FONTE, cosa],
                           capture_output=True, text=True, timeout=1800)
        if p.returncode != 0:
            raise RuntimeError(f"exit={p.returncode}: {p.stderr.strip()[-160:]}")
        return json.loads(p.stdout.strip().splitlines()[-1])

    letto: dict[str, dict] = {}
    for etichetta, modo in REGIMI:
        try:
            # DUE processi FRESCHI: il tentativo diretto mette in cache il
            # fallimento di caricamento e falserebbe il costo del write.
            w = _figlio(modo, "write")
            dd = _figlio(modo, "diretto")
        except RuntimeError as exc:
            print(f"  {etichetta:<28} PROCESSO MORTO {exc}")
            return 1
        d = {**w, "diretto": dd["diretto"], "ms_diretto": dd["ms_diretto"]}
        letto[modo] = d
        print(f"  {etichetta:<28} {str(d['have_judge']):<11} "
              f"{str(d['diretto']):<16} {str(d['gs']):<13} "
              f"{d['ms_write']:<9} {','.join(d['lay']) or '-'}")

    ben, cos = letto["con_daemon"], letto["senza_daemon"]

    print("\n  [1] CONTROLLO — col daemon vivo `try_local_score` DEVE giudicare: "
          f"{'SI' if ben['diretto'] is not None else 'NO'}")
    if ben["diretto"] is None:
        print("      CONTROLLO CADUTO: il daemon non sta giudicando ⇒ un write")
        print("      senza punteggio non dice niente sulla guardia. Misurerei un")
        print("      daemon spento e lo chiamerei difetto. NESSUN VERDETTO.")
        return 1

    print("\n  ══ VERDETTO ══")
    if not ben["have_judge"] and ben["gs"] is None:
        print("     🔴 [BENEFICIO] LA GUARDIA COSTA UN VERDETTO: `_have_judge` e'")
        print(f"     False, il write esce con gs={ben['gs']}, e nello STESSO")
        print(f"     processo il daemon risponde {ben['diretto']}.")
        print("     ⇒ E' la stessa forma della clausola `_load_failed` tolta alle")
        print("     22:16: un predicato locale che decide di un processo remoto.")
    elif ben["gs"] is not None and ben["have_judge"]:
        print("     🟢 LA QUARTA VIA E' IN SERVIZIO: `_have_judge` e' True perche'")
        print("     il daemon si e' annunciato, e il write ottiene il punteggio")
        print(f"     ({ben['gs']}) invece di uscire al buio. ⇒ RED->GREEN")
        print("     falsificato dal banco stesso: la stessa cella dava gs=None.")
    elif ben["gs"] is not None:
        print("     🟢 il write E' giudicato mentre `_have_judge` resta False ⇒ la")
        print("     mia lettura della guardia era incompleta e lo dico.")
    else:
        print(f"     ⚪ have_judge={ben['have_judge']}: il regime non isola la")
        print("     guardia. NESSUN VERDETTO sul beneficio.")

    # ⚠️⚠️ DUE COSTI DIVERSI, E LA PRIMA STESURA LI CONFONDEVA. `ms_write` e' il
    # costo CON la guardia: `_have_judge` e' False, quindi il write NON tenta
    # nemmeno il giudizio ed esce subito. Il costo di TOGLIERE la guardia e'
    # quello del tentativo, che si legge nella colonna accanto. Leggere il
    # primo come «il costo della cura» dice millisecondi dove sono secondi.
    print(f"\n     [COSTO] con la guardia il write senza giudice costa "
          f"{cos['ms_write']} ms — ed e' il costo di NON tentare:")
    print("     `_have_judge` e' False, quindi il write esce senza provarci.")
    print(f"     Il tentativo, in un processo fresco, costa "
          f"{cos['ms_diretto']} ms.")
    if (cos["ms_diretto"] or 0) < 1000:
        print("     ⇒ togliere il predicato costerebbe millisecondi: la cura")
        print("     puo' essere la rimozione.")
    else:
        print("     ⇒ 🟡 TOGLIERE IL PREDICATO COSTEREBBE SECONDI a ogni write")
        print("     senza giudice. La guardia guadagna cio' che costa, e la cura")
        print("     NON e' rimuoverla: e' aggiungerle una QUARTA VIA economica")
        print("     che sappia del daemon — `read_discovery()` e' una lettura di")
        print("     file, come `local_ce_available()` e' un `os.path`.")

    print("\n  ⚠️ LIMITI: un claim, una fonte, italiano, porta SDK, una macchina.")
    print("     Il costo e' quello di un modello ASSENTE (cartella vuota), non")
    print("     di un modello presente ma lento a caricare.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
