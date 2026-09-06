"""LIVELLO: il giudice locale su coppie (grounding_span, proposition) VERE del corpus,
in sola lettura — due popolazioni, ammessi e bocciati dal moat, ciascuna in due
grafie. Un processo, un caricamento, tutto in lotto.

K1 era «indecisa per n=30». Qui n e' quello che il corpus da'.

    python docs/stato-reale/banchi/ws3-la-grafia-sul-corpus-vero-ammessi-e-bocciati.py [N]

⚠️ RICHIEDE UNO SLOT. Store di Aurelio aperto SOLO in lettura (`mode=ro`) per
pescare le coppie; nessuna scrittura. Finestra dichiarata: caricamento ~20 s +
2 x N x 2 coppie in lotto (5 ms l'una): N=400 -> < 30 s; dichiaro 300 s.

━━ PERCHE' QUESTE COPPIE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`grounding_span` e' il pezzo di fonte che il giudice ha guardato quando ha
deciso (N10 del design): la coppia (span, proposition) e' ESATTAMENTE cio' che
il moat ha giudicato, e `status` dice come e' andata — model_claim (ammesso) o
quarantined (bocciato). Non ho etichette di verita'; ho il verdetto del
prodotto, e lo dichiaro: qui si misura se la grafia SPOSTA i punteggi e se li
sposta allo stesso modo sulle due popolazioni. Se alza gli ammessi e non i
bocciati, discrimina; se alza tutti uguale, e' solo un offset.

Popolazione: fatti vivi con span non vuoto che contengono almeno una forma
ASCII («e'», «piu'», «da'», …) nello span o nella proposition — cioe' quelli
che una normalizzazione toccherebbe (8,9% del corpus, d9fba97a). Braccio ASCII
= originale; braccio accentato = conversione.

━━ PREDIZIONI, scritte prima (06/09 01:14) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    L1 sugli AMMESSI il punteggio medio sale con l'accentata di >= +1,5 punti
       (su 100), intervallo appaiato al 95% che esclude lo zero.
       🔴 muore se < +0,5 o se l'intervallo include lo zero: K1 resta indecisa
       anche con n grande, e la cura non ha un numero.
    L2 sui BOCCIATI il punteggio medio sale MENO che sugli ammessi (differenza
       delle differenze >= +1,0): la grafia discrimina, non e' un offset.
       🔴 muore se sale uguale o piu': allora normalizzare alza tutto e non
       cambia nessun verdetto — cura inutile.
    L3 fra gli ammessi in ASCII, quelli SOTTO il cut 40 (che con la grafia
       giusta non cadrebbero) sono >= 2%. 🔴 muore se < 0,5%: il danno della
       grafia e' reale ma non tocca il verdetto.

━━ ESITO, 06/09 01:18, slot 03409903d144 preso e rilasciato, 17 s + 12 s ━━━━━━━━
    coppie con span 7.840 · con una forma ASCII 1.283 · ammessi 400 · bocciati 109
    AMMESSI   media ASCII 97,61 · accentata 97,58 · delta −0,03 [−0,57; +0,47]
              sotto il cut 40: ASCII 7 (1,8%) · accentata 8 (2,0%)
    BOCCIATI  media ASCII 57,12 · accentata 57,56 · delta +0,44 [−3,11; +4,43]
              sotto il cut 40: ASCII 42 (38,5%) · accentata 46 (42,2%)
    L1 ammessi salgono >= +1,5 e intervallo > 0    −0,03    🔴 FALSIFICATA
    L2 ammessi salgono piu' dei bocciati (>= +1,0) −0,47    🔴 FALSIFICATA
    L3 ammessi ASCII sotto il cut >= 2%             1,75%   indeciso (7/400 -> 8/400)

⇒ SUL CORPUS LA GRAFIA NON CAMBIA NESSUN VERDETTO. Il +0,04 di AUROC sulle mie
  30 coppie (b82ebf55) e il +0,03 sulle 30 implicite (da0ed03f) NON si
  trasferiscono alle scritture vere. Due ragioni, entrambe leggibili nei numeri:
  ① SOFFITTO: gli ammessi stanno a 97,6 su 100 — non c'e' dove salire. Le mie
     coppie erano brevi e a punteggio medio, con «e'» come verbo che porta il
     senso del claim; nel corpus «e'» e' una parola fra quaranta.
  ② i 7 ammessi sotto il cut restano 8 con l'accentata: nessuno recuperato,
     uno perso. Il numero che decide una cura di prodotto e' questo, ed e' zero.
⇒ Correggo cio' che ho scritto due volte (27cde06ecc5d8c43, 609f07c849e2300f):
  «normalizzare e'->è prima del giudice e' una cura a costo zero» — VERA sui
  banchi costruiti, FALSA come cura di prodotto. Non entra nel design. Il
  fenomeno resta (il giudice preferisce l'accentata sulle frasi brevi), e resta
  un dato per chi addestra (Nadia): nel corpus non decide niente.
  Classe: un effetto su un banco costruito non e' un tasso sul prodotto — e il
  campione grande che avevo detto servisse l'ha falsificato lui.
"""
from __future__ import annotations

import importlib.util
import pathlib
import random
import sqlite3
import sys
import time

QUI = pathlib.Path(__file__).resolve()
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")

DB = r"C:\Users\aurel\.engram\semantic\semantic.db"
SEED = 20260906
CUT = 40.0


def carica(nome: str):
    spec = importlib.util.spec_from_file_location(nome.replace("-", "_"), QUI.parent / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def media(x: list[float]) -> float:
    return sum(x) / len(x) if x else float("nan")


def intervallo_appaiato(delta: list[float], giri: int = 2000) -> tuple[float, float]:
    r = random.Random(SEED)
    n = len(delta)
    medie = []
    for _ in range(giri):
        campione = [delta[r.randrange(n)] for _ in range(n)]
        medie.append(sum(campione) / n)
    medie.sort()
    return medie[int(0.025 * giri)], medie[int(0.975 * giri)]


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    import verimem
    from verimem.local_grounding import get_local_judge
    print("IMPORT DA", verimem.__file__)
    grafie = carica("ws3-il-giudice-legge-e-accentata-ed-e-apostrofo-allo-stesso-modo")
    orto = carica("ws3-quanto-corpus-e-scritto-in-ascii-e-quanta-copula-e-nuda")

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        righe = con.execute(
            "SELECT grounding_span, proposition, status FROM facts WHERE superseded_by IS NULL "
            "AND grounding_span IS NOT NULL AND LENGTH(grounding_span) > 0 "
            "AND proposition IS NOT NULL").fetchall()
    finally:
        con.close()
    con_ascii = [(s, p, st) for s, p, st in righe if orto._ASCII.search(s) or orto._ASCII.search(p)]
    amm = [(s, p) for s, p, st in con_ascii if st != "quarantined"]
    boc = [(s, p) for s, p, st in con_ascii if st == "quarantined"]
    random.Random(SEED).shuffle(amm)
    random.Random(SEED).shuffle(boc)
    amm, boc = amm[:n], boc[:n]
    print(f"coppie con span: {len(righe)} · con una forma ASCII: {len(con_ascii)}"
          f" · ammessi usati {len(amm)} · bocciati usati {len(boc)}\n")

    t0 = time.perf_counter()
    judge = get_local_judge()
    scorer = judge._ensure_scorer()  # noqa: SLF001
    print(f"caricamento {time.perf_counter() - t0:.1f} s")

    def punteggi(coppie: list[tuple[str, str]], conv) -> list[float]:
        prep = [judge.coppia(conv(s), conv(p)) for s, p in coppie]
        return [judge.normalizza(x) for x in scorer(prep)]

    t0 = time.perf_counter()
    ris = {}
    for nome, coppie in (("AMMESSI", amm), ("BOCCIATI", boc)):
        if not coppie:
            continue
        a = punteggi(coppie, lambda t: t)
        b = punteggi(coppie, grafie.accentata)
        delta = [y - x for x, y in zip(a, b, strict=True)]
        lo, hi = intervallo_appaiato(delta)
        sotto_a = sum(1 for x in a if x < CUT)
        sotto_b = sum(1 for x in b if x < CUT)
        ris[nome] = (media(a), media(b), media(delta), lo, hi, sotto_a, sotto_b, len(a))
        print(f"\n  {nome:9s} n={len(a)}  media ASCII {media(a):6.2f} · accentata {media(b):6.2f}"
              f" · delta {media(delta):+6.2f} [{lo:+.2f}; {hi:+.2f}]")
        print(f"            sotto il cut {CUT:.0f}: ASCII {sotto_a} ({100 * sotto_a / len(a):.1f}%)"
              f" · accentata {sotto_b} ({100 * sotto_b / len(a):.1f}%)")
    print(f"\n  punteggi in {time.perf_counter() - t0:.1f} s (4 lotti)")

    if "AMMESSI" in ris:
        _, _, d_a, lo_a, hi_a, sotto_a, _, n_a = ris["AMMESSI"]
        print(f"\n  L1 ammessi salgono >= +1,5 e intervallo > 0 : {d_a:+.2f} [{lo_a:+.2f}; {hi_a:+.2f}]"
              f"  {'REGGE' if d_a >= 1.5 and lo_a > 0 else ('🔴 FALSIFICATA' if d_a < 0.5 or lo_a <= 0 else 'indeciso')}")
        q = 100 * sotto_a / n_a
        print(f"  L3 ammessi ASCII sotto il cut >= 2%           : {q:.2f}%"
              f"  {'REGGE' if q >= 2 else ('🔴 FALSIFICATA' if q < 0.5 else 'indeciso')}")
    if "AMMESSI" in ris and "BOCCIATI" in ris:
        dd = ris["AMMESSI"][2] - ris["BOCCIATI"][2]
        print(f"  L2 ammessi salgono piu' dei bocciati (>= +1,0): {dd:+.2f}"
              f"  {'REGGE' if dd >= 1.0 else ('🔴 FALSIFICATA' if dd <= 0 else 'indeciso')}")


if __name__ == "__main__":
    main()
