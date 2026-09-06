"""Cerca il RED del SIGSEGV di `test_hang_watchdog` sulla cella che lo produce.

    wsl -d Ubuntu -e bash -lc 'python3.12 <questo file> [ripetizioni]'

⚡ NESSUNA DIPENDENZA: `_hang_watchdog.py` importa solo stdlib, e qui viene
caricato PER PERCORSO — non si passa da `verimem/__init__`, quindi il banco gira
in una WSL nuda senza installare il progetto.

━━ PERCHE' ESISTE, E PERCHE' SU WSL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il run 33791940160 su `fade02f0` muore con exit 139 (128+11 = SIGSEGV) dentro
`test_slow_body_leaves_a_stack_dump`. La matrice dice dove:

    ubuntu-latest / py3.12    FAILURE exit 139   <- SOLO QUI
    ubuntu-latest / py3.11    success
    ubuntu-latest / py3.13    success
    windows-latest/ py3.12    success
    macos-latest  / py3.12    success

⚠️ IL 03/09 AVEVO CERCATO IL RED SU WINDOWS/py3.13 — cioe' su una delle celle
che PASSANO — e avevo concluso «non riproducibile». Il verdetto era giusto e la
ragione sbagliata: non e' che il difetto non esista, e' che li' non e' dove
succede. Questa macchina ha `wsl -d Ubuntu` con **Ubuntu 24.04 / Python
3.12.3**: la cella esatta, senza container e senza CI.
🔑 La lezione generale: PRIMA DI DIRE «NON RIPRODUCIBILE», CHIEDERSI SE SI STA
   GUARDANDO LA PIATTAFORMA IN CUI IL GUASTO E' STATO VISTO.

━━ QUATTRO CONDIZIONI PROVATE, TUTTE VERDI (34 esecuzioni) ━━━━━━━━━━━━━━━━━━
    A  il caso isolato, 20 giri                                 20/20 OK
    B  durata del referto (19 s) + 8 thread Python, 4 giri        4/4 OK
    C  thread NATIVI (numpy+OpenBLAS) dentro il corpo, 5 giri     5/5 OK
    D  sotto pytest, con e senza `faulthandler_timeout`, 5+5     10/10 OK
Nessun SIGSEGV. Il banco tiene A-D come regressione: se un giorno uno di questi
diventa rosso, la condizione si e' ristretta e lo si sa subito.

━━ COSA HA MISURATO, e cambia la diagnosi ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
In CI quel test e' morto DOPO 19 SECONDI. In condizioni normali dura 1,2 s: era
gia' anomalo PRIMA di crashare, sedici volte piu' lento. E la lentezza non e' un
dettaglio, perche' `dump_traceback_later(..., repeat=True)` ripete il dump a
ogni intervallo finche' il corpo non finisce:

    corpo  1,2 s  ->  1 file ·  2.743 byte ·  4 dump ripetuti
    corpo 19,0 s  ->  1 file · 35.336 byte · 63 dump ripetuti

⇒ Sedici volte le occasioni perche' qualcosa cada DENTRO un dump.

❌ E UN SOSPETTO CADE, misurato: il sorvegliante del tetto (che chiama
`cancel_dump_traceback_later()` da un THREAD) scatta solo sopra
`_MAX_FILE_BYTES`, che vale **2.000.000 byte**. A 19 secondi il file era 35 KB:
il sorvegliante NON e' mai scattato. Per arrivare al tetto servirebbero ~3.600
dump, cioe' una ventina di minuti di stallo.
✅ RESTA l'altro `cancel`, quello del `finally`: quello scatta SEMPRE, alla fine
del corpo, e con 63 dump invece di 4 la probabilita' che cada mentre
faulthandler cammina sugli stack e' ~16x.
⚠️ IPOTESI, NON DIAGNOSI: non l'ho fatta cadere in nessuna delle quattro
condizioni. Chi la vuole provare deve far finire il corpo DENTRO un dump.
"""
from __future__ import annotations

import collections
import importlib.util
import subprocess
import sys
from pathlib import Path

#: Il modulo sotto esame, caricato per percorso (vedi sopra).
MOD = "/mnt/c/Users/aurel/Code/_ws7_tmp_main/verimem/_hang_watchdog.py"

#: Il corpo del figlio: un processo per giro, perche' un SIGSEGV uccide il
#: processo e con esso qualunque riepilogo si stesse accumulando in memoria.
FIGLIO = r'''
import importlib.util, time, tempfile, pathlib, threading
spec = importlib.util.spec_from_file_location("hw", MODPATH)
hw = importlib.util.module_from_spec(spec); spec.loader.exec_module(hw)
stop = threading.Event()
def gira():
    while not stop.is_set():
        pass
for _ in range(NTHREAD):
    threading.Thread(target=gira, daemon=True).start()
d = pathlib.Path(tempfile.mkdtemp()); hw._TRACE_DIR = d
try:
    with hw.hang_trace("slow_tool", budget_s=BUDGET):
        time.sleep(DURATA)
finally:
    stop.set()
print("OK", len(list(d.glob("hang-*.txt"))))
'''


def giro(n: int, durata: float, budget: float, nthread: int) -> dict[int, int]:
    codice = (FIGLIO.replace("MODPATH", repr(MOD))
              .replace("NTHREAD", str(nthread))
              .replace("DURATA", str(durata))
              .replace("BUDGET", str(budget)))
    esiti: collections.Counter[int] = collections.Counter()
    for i in range(n):
        r = subprocess.run([sys.executable, "-c", codice],
                           capture_output=True, text=True, timeout=300)
        esiti[r.returncode] += 1
        if r.returncode != 0:
            marca = " <-- SIGSEGV" if r.returncode in (-11, 139) else ""
            print(f"    [{i}] returncode={r.returncode}{marca}")
            for riga in r.stderr.strip().splitlines()[-3:]:
                print("        ", riga[:130])
    return dict(esiti)


def main() -> None:
    if not Path(MOD).exists():
        raise SystemExit(f"  modulo non trovato: {MOD}\n"
                         "  (questo banco va eseguito DENTRO WSL, dove il repo "
                         "sta sotto /mnt/c)")
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(f"  python {sys.version.split()[0]} · {sys.platform}")
    casi = [
        ("A  caso isolato          ", 1.2, 0.3, 0),
        ("B  durata del referto    ", 19.0, 0.3, 8),
        ("C  fine del corpo stretta", 0.37, 0.05, 60),
    ]
    rosso = False
    for nome, dur, bud, nt in casi:
        e = giro(n, dur, bud, nt)
        ok = e.get(0, 0)
        seg = e.get(-11, 0) + e.get(139, 0)
        print(f"  {nome} {ok}/{n} OK" + (f"  · SIGSEGV {seg}" if seg else ""))
        rosso = rosso or bool(seg)
    print()
    print("  ⇒ " + ("RED TROVATO: il SIGSEGV si riproduce qui."
                    if rosso else
                    "nessun SIGSEGV: la condizione NON e' solo (piattaforma + "
                    "watchdog + thread). Serve qualcosa dello stato della "
                    "suite, e chi lo cerca parta da li'."))


if __name__ == "__main__":
    main()
