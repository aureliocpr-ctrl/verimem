"""La cura `c857752e` misurata sulla popolazione che la garanzia PROTEGGEVA.

    python docs/stato-reale/banchi/ws3-la-popolazione-che-la-garanzia-proteggeva.py

⚡ NESSUN MODELLO: `ground_write=False`. La famiglia L1 e' lessicale.
⚠️ Legge lo store vivo in SOLA LETTURA (`mode=ro`) per avere frasi reali.

━━ PERCHE' ESISTE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`c857752e` («e con l'apostrofo e' un marcatore di verbo quanto e' con
l'accento») DICHIARO' il proprio rischio prima di misurarlo — «allargare il
marcatore allarga cio' che il classificatore legge come third-party, quindi L1
escala di meno» — e lo misuro' su 13.662 fatti vivi: **132 diventano DOMAIN, 0
lo perdono, e dei 132 nessuno e' in prima persona**.

Il controllo era serio e guardava la popolazione sbagliata: quella che la cura
CAMBIA, non quella che la garanzia PROTEGGEVA. Questo banco misura la seconda.

━━ IL DISEGNO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Due worktree, un commit di distanza, le STESSE proposizioni vere del corpus:

    braccio A   `ccab08b4` (padre)   -> chi viene trattenuto
    braccio B   `c857752e` (figlio)  -> di quelli, chi passa

⚠️ LIMITE DICHIARATO PRIMA DEI NUMERI: la `source` dei fatti non e' conservata
dal prodotto (il corpus tiene solo una firma), quindi il gate gira qui SENZA
fonte. Non e' un tasso di produzione: e' la DIFFERENZA fra due versioni a
parita' di ingresso, e la fonte mancante e' una costante fra i due bracci.
⚠️ E la colonna `quarantined_by` non poteva servire: dice 'L1' su DUE fatti di
2.736 quarantinati, e in 1.909 (69,8%) e' vuota. Una colonna quasi vuota non e'
una popolazione — la prima versione di questo banco moriva li'.

━━ MISURATO IL 2026-09-03 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    proposizioni valutate            17.428
    trattenute dal padre              4.649   (26,7%)
    trattenute dal figlio             4.634
    LIBERATE dalla cura                  15   (0,32%)

Lo 0,32% dice «piccolo». L'elenco dice un'altra cosa: fra le 15 ci sono

    «La funzionalita' funziona ed e' verificata.»      (due volte, due topic)
    «L'implementazione e' finita e collaudata.»

cioe' **self-claim da manuale**, la classe che i detector L1.x esistono per
fermare. Verificate una per una, con un controllo che deve restare fermato:

    frase                                              padre    figlio/oggi
    La funzionalita' funziona ed e' verificata.        FERMA     PASSA
    L'implementazione e' finita e collaudata.          FERMA     PASSA
    Il comando warmup e' iniziato ... ed e' finito     FERMA     PASSA
    La migrazione e' completata e tutti i test passano FERMA     FERMA  <- controllo

Il controllo resta fermato in entrambi i rami: non e' un guasto generale del
gate, e' questa cura su queste frasi.

━━ IL MECCANISMO DEL FALLIMENTO DEL CONTROLLO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il controllo chiedeva «**sono in prima persona?**». Nessuna delle due lo e':
«la funzionalita' funziona», «l'implementazione e' finita» sono IMPERSONALI —
ed e' la forma NORMALE della self-claim in italiano. Il proxy («prima
persona») non era la grandezza («self-claim»), e un proxy soddisfatto ha
lasciato passare esattamente cio' che doveva escludere.

━━ E IL GATE LO DICE, SENZA FARLO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Nel braccio figlio i layer CONTINUANO ad accendersi — `['L1.10','L1.15',
'L1.20','L1-domain-precision-observe']` — e l'azione diventa `persist`. La
ricevuta nomina gli strati che hanno visto il problema e il fatto entra lo
stesso: chi legge `layers` non vuoti crede di leggere una trattenuta.

🔴 COME MUORE QUESTO BANCO: se qualcuno restringe il marcatore e le due frasi
tornano FERMA al braccio figlio, i numeri qui sopra vanno rifatti — ed e' il
segno che la cura e' stata ripensata, non che il banco era sbagliato.
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"

#: le frasi provate una per una; l'ultima e' il CONTROLLO che deve restare
#: fermato in entrambi i rami, altrimenti si sta misurando un guasto generale
FRASI = [
    "La funzionalita' funziona ed e' verificata.",
    "L'implementazione e' finita e collaudata.",
    "Il comando warmup e' iniziato alle 14:50:24 ed e' finito alle 14:53:19.",
    "La migrazione e' completata e tutti i test passano.",
]


def verdetti(radice: Path) -> list[tuple[str, str, list[str]]]:
    """Chiama il gate DI QUELLA radice in un processo a se'.

    Un processo per commit: importare due versioni di `verimem` nello stesso
    interprete non si puo', e un `sys.path` cambiato a meta' e' il modo piu'
    rapido di misurare il codice sbagliato.
    """
    # I due valori entrano con `repr()`, mai per interpolazione di testo: le
    # frasi contengono apostrofi, e un apostrofo dentro un `-c` costruito a
    # mano rompe il programma in silenzio invece che con un errore.
    r_radice, r_frasi = repr(str(radice)), repr(FRASI)
    codice = (
        "import sys, json\n"
        "sys.path.insert(0, " + r_radice + ")\n"
        "import verimem\n"
        "assert " + r_radice + " in verimem.__file__, verimem.__file__\n"
        "from verimem.anti_confab_gate import run_validation_gate as g\n"
        "out = []\n"
        "for f in " + r_frasi + ":\n"
        "    x = g(proposition=f, verified_by=[], topic=None, agent=None,"
        " source=None, ground_write=False)\n"
        "    out.append((f, str(getattr(x, 'action', None)),"
        " [str((w or {}).get('layer') or '')"
        " for w in (getattr(x, 'warnings', None) or [])]))\n"
        "print(json.dumps(out, ensure_ascii=False))"
    )
    r = subprocess.run([sys.executable, "-c", codice], capture_output=True,
                       text=True, cwd=str(radice), timeout=600)
    import json
    for riga in reversed(r.stdout.strip().splitlines()):
        if riga.startswith("["):
            return json.loads(riga)
    raise SystemExit(f"nessun esito da {radice}: {r.stderr.strip()[-300:]}")


def main() -> None:
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        tot = con.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        vuoti = con.execute(
            "SELECT COUNT(*) FROM facts WHERE status='quarantined' "
            "AND (quarantined_by IS NULL OR TRIM(quarantined_by)='')"
        ).fetchone()[0]
        q = con.execute(
            "SELECT COUNT(*) FROM facts WHERE status='quarantined'").fetchone()[0]
    finally:
        con.close()
    print("LA POPOLAZIONE CHE LA GARANZIA PROTEGGEVA\n")
    print(f"  fatti nel corpus vivo            : {tot}")
    print(f"  quarantinati                     : {q}")
    print(f"  di cui SENZA `quarantined_by`    : {vuoti} "
          f"({100.0 * vuoti / max(1, q):.1f}%)  <- per questo l'A/B non usa la colonna")
    print()
    print("  Per rifare l'A/B completo servono due worktree:")
    print("    git worktree add --detach <A> ccab08b4")
    print("    git worktree add --detach <B> c857752e")
    print("  e il conteggio sulle 17.428 proposizioni (356 s + 67 s).")
    print("  Qui sotto la parte che pesa, provata frase per frase.\n")

    if len(sys.argv) < 3:
        print("  uso: python <questo file> <worktree-padre> <worktree-figlio>")
        print("  (senza argomenti stampa solo il quadro del corpus)")
        return

    padre, figlio = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    a, b = verdetti(padre), verdetti(figlio)
    print(f"  {'frase':52s} {'padre':>8s} {'figlio':>8s}")
    for (f, aa, _la), (_f2, bb, lb) in zip(a, b, strict=True):
        fermo_a = "FERMA" if aa in ("downgrade", "reject") else "PASSA"
        fermo_b = "FERMA" if bb in ("downgrade", "reject") else "PASSA"
        segno = "  <- CONTROLLO" if f == FRASI[-1] else (
            "  🔴 LIBERATA" if fermo_a != fermo_b else "")
        print(f"  {f[:52]:52s} {fermo_a:>8s} {fermo_b:>8s}{segno}")
        if fermo_a != fermo_b:
            print(f"      i layer si accendono ancora: {lb}")


if __name__ == "__main__":
    main()
