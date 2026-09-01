r"""Il percorso di chi installa verimem e lo usa per la prima volta: cosa funziona?

Esegue la direttiva di Aurelio (22:04, verbatim via @ws4): «*quando pubblicate qualcosa
voglio che fate backup del nostro attuale stack, disinstallate verimem e installate come
un normale utente se serve a provare che funziona tutto*».

⚠️ **PERCHE' NON PARTO DALLA WSL.** Aurelio ha chiesto «*si replica su una wsl?*» e la
risposta misurata di @ws4 e' «**si', ma prova un'altra cosa — WSL non dice che funzioni
su Windows**»: il pacchetto si dichiara `OS Independent`, ma due moduli portano codice
platform-bound (`_sqlite_pragma.py`, `interactive_judge.py`) e **le trappole che abbiamo
pagato quest'anno sono tutte Windows** (WinError 206, separatori, conhost). ⇒ La prova
che vale per l'utente vero e' **il venv vergine su Windows**; la WSL e' una prova
**diversa**, complementare, e va dichiarata come tale.

🔴 **REPERTO ZERO, trovato costruendo la prova e prima di installare qualunque cosa: UNA
PROVA D'INSTALLAZIONE ESEGUITA DENTRO IL REPO NON PROVA NIENTE.** Un venv appena creato,
interrogato con la CWD dentro `HippoAgent`, importa `verimem` — e importa il **sorgente**::

    cwd = HippoAgent    import verimem  →  C:\\Users\\aurel\\Code\\HippoAgent\\verimem\\__init__.py
    cwd = dir neutra    import verimem  →  ImportError: No module named 'verimem'

⇒ Python mette la CWD in `sys.path[0]` e **il sorgente vince sul pacchetto installato**.
⚠️ E' probabilmente la ragione per cui @ws1 ha dichiarato la sua venv «NON VERGINE».
⇒ **Primo passo obbligatorio della procedura: `cd` FUORI dal repo.** Senza, si misura il
repo credendo di misurare il pacchetto.

⚠️ **DUE SCOSTAMENTI DAL PERCORSO UTENTE PURO, dichiarati perche' cambiano cosa il banco
prova**:
  ① **Non disinstallo verimem dallo stack principale.** Aurelio lo chiede, ed e' la
     prova piu' forte — ma lo stack e' condiviso da otto istanze che lo stanno usando
     adesso: disinstallarlo le fermerebbe tutte. ⇒ **Venv separato**, che copre
     l'installazione e il primo uso; **non copre** «disinstallo e reinstallo sulla
     macchina di chi lavora».
  ② **Uso uno store TEMPORANEO** (`HIPPO_DATA_DIR`). Un utente vero non lo imposta e
     userebbe il default — che qui e' lo store di Aurelio, e il mio vincolo e' di non
     scriverci. ⚠️ **E questo e' gia' un reperto**: chi installa verimem accanto a
     un'installazione esistente **scrive nello stesso store del default**, e il banco
     misura anche se il prodotto lo dice.

IL PERCORSO, nell'ordine in cui lo farebbe chi ha appena installato::

    ①  verimem --help        il comando esiste ed e' sul PATH?
    ②  verimem doctor        la diagnosi che il prodotto offre per prima
    ③  verimem remember      la prima scrittura — «the 2-second quickstart»
    ④  verimem recall        la prima lettura, sulla cosa appena scritta
    ⑤  verimem stats         cosa dice di aver fatto

⇒ Per ognuno: **esce a zero? quanto ci mette? e cosa stampa a un utente che non conosce
il prodotto?** L'ultima colonna e' quella che questo banco esiste per guardare.

🟡 ESITO — **il percorso funziona in tutti e cinque i passi, e nel secondo il prodotto
dichiara la versione SBAGLIATA**::

    INSTALLAZIONE   7m27s (con cache pip) · 74 pacchetti · torch 2.13.0
                    mcp 1.29.1 (il tetto `<2` della 0.7.1 ha retto)
                    comandi installati: verimem.exe, hippo.exe

    passo          exit    durata   cosa vede l'utente
    ① --help        0       2.0s    l'elenco dei comandi, leggibile
    ② doctor        1       6.3s    🔴 «verimem 0.7.0» — ma e' installata la 0.7.1
    ③ remember      0       4.5s    admitted id=7b3f0216b8b2 topic=user
    ④ recall        0       1.6s    ritrova il fatto appena scritto a 0.87
    ⑤ stats         0       1.5s    admitted: 1 · quarantined: 0

✅ **IL PERCORSO REGGE**: si installa, si scrive, si rilegge, e il fatto torna al primo
posto con 0.87. Un utente che segue il quickstart **arriva in fondo**.

🟢 **E `doctor` fa esattamente quello che dichiara**: l'`exit 1` non e' un difetto — sono
i **due avvisi** (`! offline`, `! llm`), e il suo help lo documenta («*0 all-ok · 1
warnings · 2 failures*»). ✅ Nota che vale per il prodotto: «*local CE gate model
installed — the grounding moat is ON with no llm*» ⇒ **chi installa senza chiave API ha
comunque il moat attivo**, che e' il cuore della promessa.

🔴 **IL DIFETTO, ed e' nel comando che si usa per primo**: `doctor` stampa
**`verimem 0.7.0`** su un'installazione **0.7.1**. Isolato su tre fonti::

    pip show / importlib.metadata   0.7.1
    verimem.__version__             0.7.0   ← discordante
    doctor                          0.7.0   (legge __version__)

    wheel                      METADATA   __version__
    0.7.0 PUBBLICATA (PyPI)     0.7.0       0.7.0     OK
    0.7.1 (hotfix branch)       0.7.1       0.7.0     🔴 DISCORDANTI
    0.7.5 (dist, 13/08)         0.7.5       0.7.5     OK
    main adesso                 0.7.6       0.7.6     OK

⇒ Nel branch la versione e' stata alzata in `pyproject.toml` e **non** in
`verimem/__init__.py:38`. **Solo il candidato al rilascio ne soffre.** Se esce cosi',
ogni utente che chiede «che versione ho?» sente il nome della **precedente**.

🔴 **E UN LIMITE GROSSO DELLA PROVA, che dichiaro perche' cambia i numeri**: il venv
"vergine" **si e' agganciato al daemon di encoding gia' caldo sulla macchina** —
`doctor` lo dice: «*shared encode daemon warm on :50296*». ⇒ **I 4.5s del `remember` e
gli 1.6s del `recall` NON sono i tempi di un utente**, che quel daemon non ce l'ha e
paga il caricamento del modello. **Il percorso e' provato; la sua VELOCITA' no.**

🪞 **E un mio errore di misura, sullo stesso tema di ieri**: rieseguendo `doctor` a mano
ho letto `EXIT=0` — ma era l'exit di `grep`, non di `verimem`. **«`| tail` maschera
l'exit code» ce l'ho scritto in memoria**, e l'ho rifatto. Il valore giusto (1) viene
dal banco, che usa `subprocess` e non una pipe.

REGIME: venv vergine su Windows creato con `python -m venv`, wheel **0.7.1** locale da
`dist_hotfix/`, CWD **fuori dal repo**, `HIPPO_DATA_DIR` temporaneo. Nessun modello
pre-scaricato: e' la condizione di un utente al primo avvio.
⚖️ PUNTI DEBOLI: una sola macchina, un solo Python (3.13.12); misuro **con la cache di
pip** (un utente che ha gia' altri pacchetti Python ce l'ha, ma non e' un download da
zero); e il wheel e' quello del branch, **non** quello pubblicato — su PyPI c'e' ancora
la 0.7.0 del 22 luglio (`0f47b779`).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-percorso-di-un-utente-nuovo.py <venv> <store>
"""
import os
import subprocess
import sys
import time

PASSI = [
    ("① --help", ["--help"], 30),
    ("② doctor", ["doctor"], 180),
    ("③ remember", ["remember",
                    "La coda della CI contiene 149 run in attesa.",
                    "--source", "coda: completed=2557 · queued=149 · in_progress=3"], 600),
    ("④ recall", ["recall", "quanti run ci sono in attesa nella coda?"], 600),
    ("⑤ stats", ["stats"], 180),
]


def main():
    if len(sys.argv) < 3:
        print("uso: python %s <venv> <store>" % sys.argv[0])
        raise SystemExit(2)
    venv, store = sys.argv[1], sys.argv[2]
    exe = os.path.join(venv, "Scripts", "verimem.exe")
    if not os.path.exists(exe):
        print("  🔴 `verimem` NON e' sul PATH del venv: %s" % exe)
        print("     ⇒ gia' questo e' un esito: l'utente installa e non trova il comando.")
        return
    # 🔴 PULIRE L'AMBIENTE E' OBBLIGATORIO QUANTO CREARE IL VENV, e l'ho imparato
    # sbagliando: la prima versione ereditava l'environment della sessione, dove
    # ci sono NOVE variabili del prodotto — fra cui `HIPPO_ENCODE_DELEGATE_ONLY=1`
    # (che faceva CRASHARE `remember` con un traceback) e `HIPPO_DATA_DIR` puntato
    # allo store principale. ⇒ Un venv vergine con l'ambiente di chi lo lancia NON
    # e' l'ambiente di un utente.
    # ⚠️ UNA sola variabile sopravvive alla pulizia, ed e' quella che sceglie il
    # REGIME da misurare: senza questa eccezione il banco toglieva anche
    # `ENGRAM_ENCODE_SERVICE=0` e girava col daemon acceso mentre credevo di
    # misurarlo spento. Se ne e' accorta la riga «REGIME:» qui sotto.
    DI_REGIME = {"ENGRAM_ENCODE_SERVICE"}
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_")) or k in DI_REGIME}
    ereditate = sorted(k for k in os.environ
                       if k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_")) and k not in DI_REGIME)
    if ereditate:
        print("  ⚠️ TOLTE dall'ambiente %d variabili del prodotto che un utente non ha:"
              % len(ereditate))
        print("     %s" % ", ".join(ereditate))
    env["HIPPO_DATA_DIR"] = store
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    # ⚠️ IL REGIME VA DICHIARATO, non lasciato all'ambiente: un giro col daemon
    # condiviso caldo e uno senza differiscono di un caricamento del modello, e
    # il prodotto stesso lo quantifica in `embedding.py` («pay ~20-32s»). Senza
    # questa riga i due giri sono indistinguibili nell'output.
    daemon = env.get("ENGRAM_ENCODE_SERVICE", "1").strip().lower()
    spento = daemon in {"0", "false", "no", "off"}
    print("  REGIME: daemon condiviso %s  ·  store %s"
          % ("DISABILITATO (ENGRAM_ENCODE_SERVICE=%s)" % daemon if spento
             else "ABILITATO (default)", os.path.basename(store)))
    print()

    print("  %-14s %-7s %9s  %s" % ("passo", "exit", "durata", "cosa vede l'utente"))
    print("  " + "-" * 92)
    esiti = []
    for nome, args, tmo in PASSI:
        t = time.time()
        try:
            r = subprocess.run([exe] + args, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=tmo, env=env,
                               cwd=os.path.dirname(venv))
            code, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            code, out = "TIMEOUT", "(nessuna risposta entro %ds)" % tmo
        dur = time.time() - t
        utili = [x.strip() for x in out.splitlines()
                 if x.strip() and "RuntimeWarning" not in x and not x.startswith("W0")
                 and "_threshold_of_record" not in x and "triton" not in x]
        prima = " ".join(" ".join(utili[:3]).split())[:60] if utili else "(nessun output)"
        esiti.append((nome, code, dur, utili))
        print("  %-14s %-7s %8.1fs  %s" % (nome, code, dur, prima))

    print("\n=== COSA VEDE DAVVERO, per esteso ===")
    for nome, code, dur, utili in esiti:
        print("\n  --- %s (exit %s, %.1fs) ---" % (nome, code, dur))
        for r in utili[:8]:
            print("    %s" % r[:110])
        if len(utili) > 8:
            print("    …e altre %d righe" % (len(utili) - 8))

    print("\n=== SINTESI ===")
    falliti = [n for n, c, _, _ in esiti if c != 0]
    lenti = [(n, d) for n, _, d, _ in esiti if d > 30]
    if falliti:
        print("  🔴 %d passi su %d NON escono a zero: %s"
              % (len(falliti), len(esiti), ", ".join(falliti)))
    else:
        print("  🟢 tutti e %d i passi escono a zero." % len(esiti))
    if lenti:
        print("  ⏱️ sopra i 30 secondi: %s"
              % ", ".join("%s %.0fs" % (n, d) for n, d in lenti))


main()
