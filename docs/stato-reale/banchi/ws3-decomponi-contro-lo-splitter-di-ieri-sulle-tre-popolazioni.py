"""LIVELLO: `run_validation_gate` del WORKTREE (proxy lessicale, validato il 04/09 4/4
contro la porta), con DUE decompositori nello stesso processo sulle stesse popolazioni.

`decomponi()` (verimem/atomic_claims.py) contro lo splitter del 04/09 (regex del
lead con le due cure di ieri, soglia 3): fa cio' che il design promette?

    python docs/stato-reale/banchi/ws3-decomponi-contro-lo-splitter-di-ieri-sulle-tre-popolazioni.py [N]

⚡ COSTO ZERO: nessun giudice, nessuno slot. Store di Aurelio in SOLA LETTURA.
Finestra dichiarata: proxy lessicale, < 180 s per N=800.

━━ PERCHE' PRIMA DI CONSEGNARE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
22 celle verdi dicono che `decomponi()` fa quello che le celle chiedono. Non
dicono che sulle popolazioni VERE il danno scenda e il guadagno salga. Questo
banco lo misura con un A/B nello stesso impianto: stesso gate, stesse frasi,
cambia solo il decompositore. Immune ai confondenti d'ambiente, e lo dichiaro.
⚠️ Il gate e' quello del worktree (base 04911425 + i miei docs), non main di
oggi: per questo il braccio «splitter di ieri» e' il controllo — se i suoi numeri
coincidono con quelli del 04/09-05/09, il gate non e' cambiato per cio' che conta.

━━ LE TRE POPOLAZIONI, e le predizioni scritte PRIMA (05/09 23:05) ━━━━━━━━━━━━
  A  le 15 di ws7 — 5 falsi da fermare, 10 veri da ammettere.
     V1 decomponi(): falsi 5/5 (come ieri) e veri fermati <= 2/10 (ieri 2-3).
        🔴 muore se i falsi scendono sotto 5 o i veri fermati salgono sopra 3.
  B  i 200 «<vero> + coda di completamento» — falsi che l'INTERO ferma 115/200.
     V2 decomponi() ne ferma >= 135/200 (la soglia 1 di ieri) — cioe' almeno
        quanto lo splitter di ieri a soglia 1 e piu' dell'intero.
        🔴 muore sotto 115: la cura e' peggio dell'intero e non entra.
  C  campione casuale n=800 di veri composti ammessi (seed 20260904).
     V3 decomponi() cambia verdetto a <= 2,4% (P-A del design; ieri 2,12-2,38%
        con lo splitter di ieri).
        🔴 muore sopra 2,4%: la fusione dei nudi non basta e serve il tempo 2.

━━ ESITO del primo giro (05/09 22:55) — V1 regge, V2 CADE, V3 regge ━━━━━━━━━━━━
    A  falsi 5/5 · veri fermati 2/10 (intero 0/10)                     V1 REGGE
    B  intero 114 · ieri(3) 0 · ieri(1) 120 · decomponi() 101 /200     V2 🔴 CADE
    C  ieri(3) 14 · ieri(1) 14 · decomponi() 12 /800 = 1,50%           V3 REGGE

━━ LA DIAGNOSI DI V2, letta nei LAYER e non nei conteggi ━━━━━━━━━━━━━━━━━━━━━━
(scratchpad/diagnosi_v2.py, 24 persi su 200). Lo stesso pezzo, due grafie:
    «E' completata.»                 -> L1.13, L1.20            FERMATO
    «Una directory VUOTA e' completata.» -> L1.13, L1-domain-precision-observe  passa
L1.20 e' il rilevatore SEMANTICO di self-claim (anti_confab_gate.py:1623): con
un soggetto davanti la frase si allontana dal prototipo e la carve-out di terzi
la esenta. L'eredita' del soggetto — la cura che il design chiedeva — DISATTIVA
il rilevatore. E il 120 dello splitter di ieri era un effetto della cecita' di
subject_of: lasciava la coda nuda, e L1.20 la fermava. La cura di un difetto ha
scoperto cio' che il difetto mascherava.
    per coda (50 l'una): «ed e' verificata» 39 -> 28 · «e funziona» 50 -> 46 ·
    «ed e' completata» 31 -> 27 · «ed e' collaudata» 0 -> 0 (!)
«collaudata» e' 0/50 in ENTRAMBI i bracci: L1 non conosce il verbo. Buco del
gate, non del decompositore — segnalato.

━━ LA TESI CHE NE SEGUE, e la sua verifica (scratchpad/forma_nuda_per_l1.py) ━━
Due forme per claim: NUDA per L1 (la forma che L1.20 riconosce), AUTO-CONTENUTA
per il moat (un giudice NLI vuole il soggetto). Predetto >= 120 nuda; misurato:
    200 con coda: intero 114 · decomponi() 101 · decomponi() NUDA **145**
    le 15, forma nuda: falsi 5/5 · veri fermati 3/10 (controllo <= 3: regge)
Da qui il quarto braccio sotto e il parametro `eredita_soggetto` nel modulo.

━━ SECONDO GIRO (05/09 23:05), quattro bracci nello STESSO processo ━━━━━━━━━━━━
    A  falsi 5/5 per tutti · veri fermati: ieri 2, decomponi() 2, NUDA 3, intero 0
    B  intero 114 · ieri(3) 0 · ieri(1) 124 · decomponi() 103 · NUDA **145**
       V2 (con soggetto) resta CADUTA · V2' (forma nuda, >= 120) REGGE
    C  ieri 14/800 · decomponi() 12/800 · NUDA 12/800 = 1,50%          V3 REGGE
⚠️ ieri(1) 120->124 e decomponi() 101->103 fra i due giri: il corpus e' passato da
15.367 a 15.368 fatti e il campione dei 200 con seed cambia con lui. Il
denominatore si muove; il rapporto fra i bracci no.

━━ UN ALTRO BUCO ORTOGRAFICO, visto nei QUALI di C ━━━━━━━━━━━━━━━━━━━━━━━━━━━━
«La frase che dice che non e chiaro se il modulo…» -> spezzato su « e chiaro »:
la «e» copula scritta senza accento ne' apostrofo viene letta come congiunzione.
Non curato qui (la memoria dice che «e» copula e' gia' una strada falsificata
altrove): la frequenza sul corpus va misurata prima di toccare la regex.

━━ COSA NON DECIDE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Solo L1 (proxy senza store: niente L3); solo il lato claim (il MAX sulle frasi
della fonte e' un'altra cella, P-E, col giudice). I 12 di C che cambiano
verdetto restano da classificare uno per uno (condizione 1 del lead).
"""
from __future__ import annotations

import json
import pathlib
import random
import re
import sqlite3
import sys

WT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WT))

import verimem  # noqa: E402
from verimem.anti_confab_gate import run_validation_gate  # noqa: E402
from verimem.atomic_claims import decomponi  # noqa: E402
from verimem.subject_extract import subject_of  # noqa: E402

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
QUINDICI = WT / "docs/stato-reale/banchi/ws7-le-quindici-liberate-tornano-fermate.json"
SEED = 20260904
CODE = (" ed e' verificata.", " ed e' collaudata.", " e funziona.", " ed e' completata.")

# ── lo splitter del 04/09, verbatim con le due cure di ieri (« ed », guardia senza \b)
_COORD = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|;\s+)", re.I)
_VERBI = r"(ha|è|e'|sono|hanno|era|fu|has|is|are|was|signed|tested|were)"
_VERBO_INIZIALE = re.compile(rf"^{_VERBI}(?=\s|$)", re.I)


def splitter_di_ieri(testo: str, min_parole: int = 3) -> list[str]:
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


def atomico(t: str, decomp) -> bool:
    return any(fermato(p) for p in decomp(t))


BRACCI = (("splitter di ieri (soglia 3)", lambda t: splitter_di_ieri(t, 3)),
          ("splitter di ieri (soglia 1)", lambda t: splitter_di_ieri(t, 1)),
          ("decomponi()", decomponi),
          ("decomponi() forma NUDA", lambda t: decomponi(t, eredita_soggetto=False)))


def main() -> None:
    n_camp = int(sys.argv[1]) if len(sys.argv) > 1 else 800
    print("IMPORT DA", verimem.__file__, "\n")

    # ── A: le 15 ───────────────────────────────────────────────────────────
    d = json.loads(QUINDICI.read_text(encoding="utf-8"))
    print("A · LE 15 di ws7 (proxy)")
    print(f"   {'decompositore':30s} falsi fermati /5   veri fermati /10")
    esiti_a = {}
    for nome, dec in BRACCI:
        f = sum(atomico(t, dec) for t in d["elenco_tornate"])
        v = sum(atomico(t, dec) for t in d["elenco_restano"])
        esiti_a[nome] = (f, v)
        print(f"   {nome:30s} {f:>8}            {v:>8}")
    f_int = sum(fermato(t) for t in d["elenco_tornate"])
    v_int = sum(fermato(t) for t in d["elenco_restano"])
    print(f"   {'(intero)':30s} {f_int:>8}            {v_int:>8}")
    fa, va = esiti_a["decomponi()"]
    print(f"   ⇒ V1 (5/5 e <= 2/10): {'REGGE' if fa == 5 and va <= 2 else ('🔴 FALSIFICATA' if fa < 5 or va > 3 else 'indeciso (3/10)')}")
    for t in d["elenco_restano"]:
        if atomico(t, decomponi):
            caduti = [p for p in decomponi(t) if fermato(p)]
            print(f"      resta fermato: «{caduti[0][:72]}»")

    # ── corpus per B e C ───────────────────────────────────────────────────
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL AND proposition IS NOT NULL "
            "AND LENGTH(proposition) BETWEEN 40 AND 220") if r[0]]
        tutte = [r[0] for r in con.execute(
            "SELECT proposition FROM facts WHERE superseded_by IS NULL AND proposition IS NOT NULL") if r[0]]
    finally:
        con.close()

    # ── B: i 200 con coda ──────────────────────────────────────────────────
    rnd = random.Random(20260905)
    rnd.shuffle(righe)
    veri = []
    for t in righe:
        if len(veri) >= 200:
            break
        t1 = t.strip().rstrip(".")
        if "." in t1 or "\n" in t1 or fermato(t1 + "."):
            continue
        veri.append(t1)
    falsi = [v + CODE[i % len(CODE)] for i, v in enumerate(veri)]
    print(f"\nB · {len(falsi)} «<vero> + coda» (proxy)")
    b_int = sum(fermato(f) for f in falsi)
    print(f"   {'(intero)':30s} ferma {b_int:>4}/{len(falsi)}")
    esiti_b = {}
    for nome, dec in BRACCI:
        k = sum(atomico(f, dec) for f in falsi)
        esiti_b[nome] = k
        print(f"   {nome:30s} ferma {k:>4}/{len(falsi)}")
    kb = esiti_b["decomponi()"]
    if kb >= 135:
        v2 = "REGGE"
    elif kb < b_int:
        v2 = "🔴 FALSIFICATA (peggio dell'intero)"
    else:
        v2 = "indeciso: sopra l'intero, sotto 135"
    print(f"   ⇒ V2 (>= 135), decomponi() con soggetto: {v2}")
    kn = esiti_b["decomponi() forma NUDA"]
    print(f"   ⇒ V2' (>= 120), decomponi() forma NUDA: "
          f"{'REGGE' if kn >= 120 else ('🔴 FALSIFICATA' if kn < b_int else 'indeciso')}"
          f"   ({kn} contro {b_int} dell'intero)")

    # ── C: campione casuale di veri composti ───────────────────────────────
    composti = [t for t in tutte if len(decomponi(t)) >= 2 or len(splitter_di_ieri(t, 1)) >= 2]
    random.Random(SEED).shuffle(composti)
    ammessi = 0
    cambia = {n: 0 for n, _ in BRACCI}
    quali: list[tuple[str, str]] = []
    for t in composti:
        if ammessi >= n_camp:
            break
        if fermato(t):
            continue
        ammessi += 1
        for nome, dec in BRACCI:
            if atomico(t, dec):
                cambia[nome] += 1
                if nome == "decomponi()":
                    quali.append((t, [p for p in dec(t) if fermato(p)][0]))
    print(f"\nC · campione casuale di {ammessi} veri composti ammessi (seed {SEED}, corpus {len(tutte)})")
    for nome, _ in BRACCI:
        print(f"   {nome:30s} cambiano verdetto {cambia[nome]:>3}/{ammessi} = {100 * cambia[nome] / max(1, ammessi):.2f}%")
    pc = 100 * cambia["decomponi()"] / max(1, ammessi)
    print(f"   ⇒ V3 (<= 2,4%): {'REGGE' if pc <= 2.4 else '🔴 FALSIFICATA'}")
    print("   QUALI cadono con decomponi(), i primi 8 (da classificare uno per uno, condizione 1 del lead):")
    for t, p in quali[:8]:
        print(f"     · «{p[:70]}»   ← «{t[:48].replace(chr(10), ' ')}…»")


if __name__ == "__main__":
    main()
