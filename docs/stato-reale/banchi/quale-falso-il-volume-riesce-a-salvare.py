"""QUALE FALSO il volume riesce a SALVARE — la tensione fra due dati che abbiamo già.

Il quadro consolidato di stasera dice: **il volume salva i falsi**. Un'altra
istanza l'ha misurato su fonte costruita: **160 caratteri di pseudo-parole
portano un falso da 72,1 a 99,7**.

⚠️ **Ma un mio dato, sulla stessa serata, dice il contrario su fonte REALE.**
`W7-54` misura tre popolazioni su un `git log` ancorato, a quattro lunghezze
crescenti — **28237 · 48822 · 56474 · 112948 caratteri** — e il claim con la
cifra **ASSENTE** e' fermato **4 volte su 4**, fino a **112 mila caratteri**.

⇒ **I due dati non si contraddicono: parlano di due falsi DIVERSI**, e questa e'
l'ipotesi che il banco mette alla prova.

  · **ASSENTE** (cifra inventata) e' fermato da **`L4.1`**, un layer LESSICALE
    che verifica se il numero c'e' nella fonte. **Il volume non lo tocca**:
    aggiungere testo non fa comparire una cifra che non c'e'.
  · **SCAMBIO** (numero vero, soggetto sbagliato) **non ha nessun layer**
    (`W7-55`): lo decide **solo il moat**, ed e' il moat che risponde al volume.

🔑 **PREVISIONE DICHIARATA PRIMA**: se l'ipotesi regge, allora **accorciando** la
fonte reale lo SCAMBIO deve **scendere** (e' il moat a deciderlo, e il moat
risponde alla taglia), mentre l'ASSENTE deve restare **fermato a ogni
lunghezza** (lo decide `L4.1`, che alla taglia e' indifferente).

  · se lo SCAMBIO scende sotto 80 accorciando -> **il volume e' cio' che lo
    salva**, e la famiglia a rischio e' esattamente quella senza layer.
  · se lo SCAMBIO resta alto a ogni lunghezza -> **la mia ipotesi cade**, e il
    volume non spiega perche' entra.

CONTROLLI CHE POSSONO FALLIRE:
 (1) la fonte piu' corta deve contenere il soggetto e i due conteggi: se non li
     contiene non sto misurando lo scambio, sto misurando un claim monco.
 (2) l'ASSENTE dev'essere fermato a OGNI lunghezza: e' il controllo che tiene
     in piedi la distinzione fra i due falsi. Se cede, cade tutto.
 (3) il VERO dev'essere ammesso a ogni lunghezza (popolazione di riferimento).

    python -u docs/stato-reale/banchi/quale-falso-il-volume-riesce-a-salvare.py
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ANCORA = "d7f4b611"  # la stessa di W7-54, cosi' la fonte e' confrontabile
CIFRA_ASSENTE = "91234"
# lunghezze CORTE, scelte prima: W7-54 partiva da 28237 e saliva.
LUNGHEZZE = [1500, 3000, 6000, 12000, 28237]


def main() -> int:
    try:
        from verimem.client import Memory
    except Exception as e:  # noqa: BLE001
        print(f"NON RIUSCITO: import fallito - {type(e).__name__}: {e}")
        return 1

    out = subprocess.run(
        ["git", "log", "--shortstat", "--format=@@%h|%s", "-n", "400", ANCORA],
        capture_output=True, text=True, timeout=60, encoding="utf-8",
        errors="replace")
    if out.returncode != 0:
        print(f"NON RIUSCITO: git log returncode {out.returncode}")
        return 1
    commit, corrente = [], None
    for riga in out.stdout.splitlines():
        r = riga.strip()
        if r.startswith("@@"):
            corrente = r[2:].split("|", 1)[-1]
        elif "insertion" in r and corrente:
            m = re.search(r"(\d+) insertion", r)
            if m:
                commit.append((corrente, m.group(1)))
            corrente = None
    log = " ".join(x.strip() for x in out.stdout.splitlines() if x.strip()).replace("@@", "")
    conteggi = [c for _s, c in commit]
    buoni = [(s, c) for s, c in commit
             if conteggi.count(c) == 1 and len(re.findall(r"\b%s\b" % c, log)) == 1
             and len(s) < 60]
    dentro = [(s, c) for s, c in buoni if log.find(s[:40]) >= 0]
    dentro.sort(key=lambda sc: log.find(sc[0][:40]))
    if len(dentro) < 2:
        print(f"NON RIUSCITO: servono due commit univoci, trovati {len(dentro)}")
        return 1
    (sog_a, ins_a), (_sog_b, ins_b) = dentro[0], dentro[1]
    print(f"  fonte: git log ancorato a {ANCORA}, {len(log)} caratteri")
    print(f"  A: {ins_a} inserzioni — {sog_a[:50]}")
    print(f"  B: {ins_b} inserzioni (il conteggio che lo SCAMBIO ruba)")

    CLAIM = {
        "VERO": f"Il commit «{sog_a}» ha aggiunto {ins_a} inserzioni.",
        "SCAMBIO": f"Il commit «{sog_a}» ha aggiunto {ins_b} inserzioni.",
        "ASSENTE": f"Il commit «{sog_a}» ha aggiunto {CIFRA_ASSENTE} inserzioni.",
    }
    if CIFRA_ASSENTE in log:
        print(f"CONTROLLO CADUTO: {CIFRA_ASSENTE} e' nel log")
        return 1

    print("\n  -- CONTROLLO (1): quali lunghezze contengono soggetto e i due conteggi?")
    fonti = {}
    for n in LUNGHEZZE:
        f = log[:n]
        if sog_a[:40] in f and ins_a in f and ins_b in f:
            fonti[n] = f
    print(f"     {sorted(fonti)}  (scartate: {sorted(set(LUNGHEZZE) - set(fonti))})")
    if not fonti:
        print("     CADUTO - nessuna lunghezza utile: non misuro un claim monco.")
        return 1
    # 🪞 GUARDIA aggiunta dopo la prima esecuzione, ed e' la lezione del banco.
    # La prima stesura arrivava in fondo con UNA sola lunghezza utile e stampava
    # «la mia ipotesi CADE»: una conclusione tratta da n=1, cioe' esattamente
    # «una misura che non c'e' letta come un verdetto».
    if len(fonti) < 3:
        print(f"\n  🛑 NON RIUSCITO, e il MOTIVO e' il reperto: {len(fonti)} lunghezza")
        print("  utile su 5. Le corte cadono perche' **sotto una certa taglia la")
        print("  fonte non contiene piu' i due conteggi** — e senza il conteggio")
        print("  rubato lo SCAMBIO non e' piu' uno scambio: degenera in un")
        print("  ASSENTE, che e' un'altra popolazione.")
        print("  🔑 ⇒ SU FONTE REALE IL VOLUME NON E' MANIPOLABILE")
        print("  INDIPENDENTEMENTE DAL CONTENUTO: accorciare cambia *cosa* la")
        print("  fonte dice, non solo *quanto*. Su fonte COSTRUITA si aggiungono")
        print("  pseudo-parole senza toccare il resto; qui no.")
        print("  ⇒ **La domanda era mal posta**, e con questo disegno non e'")
        print("  misurabile. Chi conclude sul volume dichiari su QUALE delle due")
        print("  popolazioni sta concludendo: non permettono lo stesso esperimento.")
        return 1

    mem = Memory(str(Path(tempfile.mkdtemp()) / "volume.db"))
    print(f"\n  {'lunghezza':>10}   " + "".join(f"{k:>22}" for k in CLAIM))
    print("  " + "-" * 78)
    esiti = {k: [] for k in CLAIM}
    for n in sorted(fonti):
        celle = []
        for nome, prop in CLAIM.items():
            ric = mem.add(prop, topic=f"vol/{nome}/{n}", source=fonti[n],
                          validate="full")
            g = float(ric.get("grounding_score") or -1)
            st = str(ric.get("status"))
            esiti[nome].append((n, st != "quarantined", g))
            celle.append(f"{'ENTRA' if st != 'quarantined' else 'ferma'} {g:6.1f}")
        print(f"  {n:>10}   " + "".join(f"{c:>22}" for c in celle))

    print("\n  -- CONTROLLO (2): l'ASSENTE e' fermato a OGNI lunghezza?")
    ass = [(n, e) for n, e, _g in esiti["ASSENTE"]]
    if any(e for _n, e in ass):
        print(f"     🚨 CEDE: entra a {[n for n, e in ass if e]} ⇒ la distinzione")
        print("     fra i due falsi CADE, e con essa tutta l'ipotesi.")
    else:
        print(f"     retto - fermato a tutte e {len(ass)} le lunghezze")

    print("\n  -- CONTROLLO (3): il VERO e' ammesso a ogni lunghezza?")
    ver = [(n, e, g) for n, e, g in esiti["VERO"]]
    print(f"     {[(n, 'ENTRA' if e else 'ferma') for n, e, _g in ver]}")

    print("\n  == LA RISPOSTA: lo SCAMBIO scende accorciando?")
    sc = [(n, g) for n, _e, g in esiti["SCAMBIO"]]
    print(f"     {[(n, round(g, 1)) for n, g in sc]}")
    minimo = min(g for _n, g in sc)
    massimo = max(g for _n, g in sc)
    if minimo < 80.0:
        print(f"     🔴 SI: il minimo e' {minimo:.1f} (sotto tau_hi=80) ⇒ **il")
        print("     volume e' cio' che salva lo scambio**, e la famiglia a")
        print("     rischio e' quella senza layer lessicale (W7-55).")
    else:
        print(f"     🟡 NO: resta fra {minimo:.1f} e {massimo:.1f}, sempre sopra 80.")
        print("     ⇒ **La mia ipotesi CADE**: il volume non spiega perche' lo")
        print("     scambio entra, e la causa e' un'altra che non conosco.")
    print(f"     escursione totale: {massimo - minimo:.1f} punti")

    print("\n  ⚠️ COSA NON DICE: una fonte, una coppia di commit, un'ancora sola.")
    print("  E le lunghezze corte tagliano il log in un punto arbitrario: il")
    print("  contenuto cambia insieme alla taglia, come in W7-11.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
