"""LIVELLO: `run_validation_gate` (proxy lessicale, validato ieri 4/4 contro la porta)
— piu' una cella ALLA PORTA `Memory.add(ground=False)` sul caso che decide.

MURO 1, fase 2: la decomposizione del lead scarta i pezzi sotto le tre parole —
e «ed e' verificata» ha due parole. La self-claim in coda, che e' il bersaglio
del muro, sparisce PRIMA di arrivare al gate.

    python docs/stato-reale/banchi/ws3-muro1-fase2-la-soglia-di-tre-parole-perde-la-coda.py [N]

⚡ COSTO ZERO. Store di Aurelio in SOLA LETTURA (serve solo a pescare fatti veri).
Finestra dichiarata: proxy lessicale sotto i 120 s; la cella alla porta ~30 s.

━━ COME L'HO TROVATO: guardando QUALI, non quanti ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sui 5 falsi di ws7 l'atomico fermava 5/5 e il numero sembrava un guadagno.
Pezzo per pezzo (scratchpad/quale_falso_esenta.py, 05/09 21:16):
    «La funzionalita' funziona ed e' verificata.»   pezzi=1
        -> «La funzionalita' funziona.»                 FERMATO (L1.10/L1.15)
        -> «e' verificata»                              SCARTATO: 2 parole < 3
    «L'implementazione e' finita e collaudata.»      pezzi=1
        -> «L'implementazione e' finita.»               FERMATO (L1.13)
        -> «collaudata»                                 SCARTATO: 1 parola
Il falso viene fermato SOLO perche' il primo pezzo e' a sua volta una self-claim.
La coda — «e' verificata», «collaudata» — non arriva mai al gate. Quando il primo
pezzo e' un fatto VERO, l'atomico non ha piu' niente da fermare, e l'intero si'.

━━ LA TESI, e come muore ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sulla forma «<fatto vero composto> ed e' verificata.» la decomposizione REGREDISCE
rispetto al giudizio intero: l'intero ferma (la cura di ws7 legge la coda),
l'atomico ammette (la coda e' stata scartata).
    U1  su N fatti veri del corpus con la coda «ed e' verificata.» aggiunta, il
        gate INTERO ne ferma >= 80%. 🔴 muore sotto 80%: la cura di ws7 non legge
        la coda come credo, e allora il confronto non ha un lato buono.
    U2  sugli stessi, l'ATOMICO ne ferma <= 20% — cioe' la decomposizione perde
        almeno 60 punti di richiamo sui falsi proprio sulla forma per cui esiste.
        🔴 muore se ferma >= 50%: la coda arriva al gate per un'altra via.
    U3  alzando la soglia a 1 parola, l'atomico torna >= 80%: e' la soglia, non
        l'idea. 🔴 muore se resta basso: allora il pezzo corto arriva al gate e
        NON viene fermato — un altro difetto, di L1, non dello splitter.
Predizioni scritte nel file alle 21:20, prima dell'esecuzione (mtime del file).

━━ PERCHE' CONTA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il muro 1 nasce dalla self-claim in coda: ws7 l'ha trovata da utente in 7 forme
su 3 porte. Una decomposizione che scarta la coda cura il sintomo sui casi
costruiti (dove ogni pezzo e' una self-claim) e lo riapre sui casi veri (dove
la coda e' l'UNICO pezzo falso). E' la classe «un banco ritagliato sulla cura».
"""
from __future__ import annotations

import pathlib
import random
import re
import sqlite3
import sys
import tempfile

ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
sys.path.insert(0, str(ALBERO))

import verimem  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.subject_extract import subject_of  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
SEED = 20260905
CODE = (" ed e' verificata.", " ed e' collaudata.", " e funziona.", " ed e' completata.")

_COORD = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
_VERBI = r"(ha|è|e'|sono|hanno|era|fu|has|is|are|was|signed|tested|were)"
_VERBO_INIZIALE = re.compile(rf"^{_VERBI}(?=\s|$)", re.I)


def claim_atomici(testo: str, min_parole: int = 3) -> list[str]:
    """Lo splitter del lead con le due cure di ieri; `min_parole` e' la soglia."""
    pezzi = [p.strip(" .") for p in _COORD.split(testo) if p and len(p.split()) >= min_parole]
    out: list[str] = []
    soggetto = ""
    for p in pezzi:
        if _VERBO_INIZIALE.match(p) and soggetto:
            p = f"{soggetto} {p[0].lower() + p[1:]}"
        else:
            s = subject_of(p)
            if not s:
                m_ = re.match(rf"^(.*?)\s+{_VERBI}\b", p, re.I)
                s = m_.group(1) if m_ else ""
            soggetto = s.strip() or soggetto
        out.append(p[0].upper() + p[1:] + ".")
    return out or [testo]


def fermato(t: str) -> bool:
    g = run_validation_gate(proposition=t, verified_by=[], topic=None, agent=None)
    return getattr(g, "action", "persist") in ("downgrade", "reject")


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    print("IMPORT DA", verimem.__file__, "\n")

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL AND proposition IS NOT NULL "
            "AND LENGTH(proposition) BETWEEN 40 AND 220") if r[0]]
    finally:
        con.close()
    random.Random(SEED).shuffle(righe)

    # veri: ammessi interi, di UNA frase, senza gia' una coda di completamento
    veri = []
    for t in righe:
        if len(veri) >= n:
            break
        t1 = t.strip().rstrip(".")
        if "." in t1 or "\n" in t1 or fermato(t1 + "."):
            continue
        veri.append(t1)
    falsi = [v + CODE[i % len(CODE)] for i, v in enumerate(veri)]
    print(f"popolazione: {len(veri)} fatti VERI ammessi interi, + una coda di completamento\n")
    print(f"  esempio: «{falsi[0][:110]}»\n")

    f_int = sum(fermato(f) for f in falsi)
    f_atm3 = sum(any(fermato(p) for p in claim_atomici(f, 3)) for f in falsi)
    f_atm1 = sum(any(fermato(p) for p in claim_atomici(f, 1)) for f in falsi)
    n_pezzi3 = sum(len(claim_atomici(f, 3)) for f in falsi) / max(1, len(falsi))
    n_pezzi1 = sum(len(claim_atomici(f, 1)) for f in falsi) / max(1, len(falsi))

    print(f"  INTERO                 ferma {f_int:4d}/{len(falsi)} = {100 * f_int / len(falsi):5.1f}%")
    print(f"  ATOMICO soglia 3 parole ferma {f_atm3:4d}/{len(falsi)} = {100 * f_atm3 / len(falsi):5.1f}%"
          f"   (pezzi medi {n_pezzi3:.2f})")
    print(f"  ATOMICO soglia 1 parola ferma {f_atm1:4d}/{len(falsi)} = {100 * f_atm1 / len(falsi):5.1f}%"
          f"   (pezzi medi {n_pezzi1:.2f})")
    p_int, p3, p1 = (100 * x / len(falsi) for x in (f_int, f_atm3, f_atm1))
    print(f"\n  U1 intero >= 80%          : {'REGGE' if p_int >= 80 else '🔴 FALSIFICATA'}")
    print(f"  U2 atomico(3) <= 20%      : {'REGGE' if p3 <= 20 else ('🔴 FALSIFICATA' if p3 >= 50 else 'indeciso')}")
    print(f"  U3 atomico(1) >= 80%      : {'REGGE' if p1 >= 80 else '🔴 FALSIFICATA'}")

    # la cella ALLA PORTA sul caso che decide, per non fidarsi solo del proxy
    print("\n  CELLA ALLA PORTA (Memory.add ground=False) sul primo caso:")
    m = Memory(pathlib.Path(tempfile.mkdtemp()) / "coda.db")
    caso = falsi[0]
    ri = m.add(caso, ground=False).get("status")
    pz = claim_atomici(caso, 3)
    ra = [m.add(p, ground=False).get("status") for p in pz]
    print(f"    intero  -> {ri}")
    coda = caso[caso.rfind(" e"):]
    coda_presente = any(k in p for p in pz for k in ("verificat", "collaudat", "funziona", "completat"))
    dove = "nei pezzi" if coda_presente else "NON nei pezzi"
    print(f"    atomico -> pezzi {len(pz)}: {ra}   (la coda «{coda}» {dove})")

    # e la coda da sola, per U3: se arriva al gate, viene fermata?
    print("\n  LA CODA DA SOLA al gate (proxy): "
          + " · ".join(f"«{c.strip()}» -> {'FERMATA' if fermato(c.strip()) else 'passa'}" for c in CODE))


if __name__ == "__main__":
    main()
