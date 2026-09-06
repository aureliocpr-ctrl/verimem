"""LIVELLO: il giudice locale (`get_local_judge`), un processo solo, un caricamento
solo — due regimi sulle stesse coppie: il FOCUS di oggi (`judge.score`, che passa
da `select_relevant_span` a budget) contro il MAX PER FRASE del design (ogni
frase della fonte giudicata da sola, si tiene la migliore).

Cella P-E del design (docs/ricerca/2026-09-05-design-write-n-claim-atomici.md,
sezione 2.2): il secondo selettore paga sulla zavorra?

    python docs/stato-reale/banchi/ws3-P-E-il-max-per-frase-contro-il-focus-sulla-zavorra.py

⚠️ RICHIEDE UNO SLOT (carica il giudice). Store di Aurelio non aperto: le coppie
sono i 5 casi zavorra del lead (7321c7b118e641a3) e le mie 30 coppie dirette.
Finestra dichiarata: caricamento ~27 s + (5+60+60) coppie x ~4 frasi x 65 ms
< 60 s; dichiaro 300 s.

━━ LA DOMANDA, e perche' non e' gia' risolta ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il lead ha misurato (a05dd7a6d6fa2458) che il MAX per frase ferma 4/4 falsi
zavorra contro 2/4 dell'intero: R2 e P-b passano da 99,9 a 1,84 «perche' il CE
non vede mai la frase estranea accanto alla decisiva». Ma il giudice di oggi
NON giudica l'intero: passa dal focus (N10: nel 69,5% dei casi UNA frase). Il
confronto che decide non e' MAX-contro-intero, e' MAX-contro-FOCUS: se il focus
gia' isola la frase giusta, il MAX non aggiunge niente; se il focus tiene la
zavorra dentro il budget (fonti corte: 2 frasi stanno in 1500 caratteri), il
CE le vede insieme e ribalta — e il MAX lo cura.
Ieri (P1/P2, c02a0f85): sulle mie 30 coppie la zavorra su R vale −0,0633 di
AUROC, cioe' NON ribalta in media: la zavorra del lead e' un caso costruito, e
sui miei 30 il MAX non dovrebbe cambiare quasi nulla.

━━ PREDIZIONI, scritte prima (05/09 23:30) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    E1 sui 5 casi zavorra del lead: FOCUS ferma <= 2/4 falsi (la fonte D+Z entra
       intera nel budget e il CE ribalta come sull'intero); MAX per frase 4/4,
       veri persi 0/1. 🔴 muore se il focus ferma gia' 4/4: allora il focus gia'
       cura la zavorra e il MAX e' ridondante su questa popolazione.
    E2 sulle mie 30 coppie con zavorra in coda (D+Z) e in testa (Z+D): la
       differenza di AUROC fra FOCUS e MAX e' < 0,02 in valore assoluto.
       🔴 muore sopra 0,05: la zavorra morde anche qui e ieri non l'avevo vista.
    E3 costo: le coppie giudicate col MAX sono M = frasi della fonte (2 sui casi
       zavorra) — e in lotto costano ~0,8x l'intero (P6c). Qui si stampa M.

━━ COME SI LEGGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se E1 regge e E2 regge: il MAX paga SOLO dove la zavorra sta dentro il budget
del focus — cioe' sulle fonti corte — e il design lo tiene come cura mirata.
Se E1 muore: il focus basta e il MAX si toglie dal design (sezione 2.2).

━━ ESITO, 05/09 23:33, slot 1c5e3df92ade preso e rilasciato, caricamento 17,7 s ━━
    E1 · i 5 del lead                 FOCUS     MAX    M
       R1 corta        falso           1,84    1,84   1   FERMATO / FERMATO
       R2 +zav coda    falso          99,94    1,84   2   passa   / FERMATO
       P-a sola zav    falso           0,19    0,19   1   FERMATO / FERMATO
       P-b zav testa   falso          99,87    1,84   2   passa   / FERMATO
       P-c vero +zav   vero           99,94   99,75   2   passa   / passa
       falsi fermati: focus 2/4 · max 4/4 · veri persi 0/1 · 0/1     E1 REGGE
    E2 · le mie 30, zavorra in coda:  AUROC focus 0,8067 · max 0,8500 · +0,0433
         zavorra in testa:            AUROC focus 0,8333 · max 0,8500 · +0,0167
         M medio 2,00                                          E2 INDECISO
⇒ Il focus di oggi NON cura la zavorra: tiene le due frasi nel budget e il CE
  le vede insieme (99,94 come sull'intero). Il MAX per frase la cura (1,84) senza
  perdere il vero. Sui miei 30 la direzione e' la stessa (+0,04 e +0,02) ma fra le
  due soglie che avevo scritto: con n=30 serve il bootstrap appaiato (P3) prima
  di chiamarlo guadagno. Costo: M = 2 coppie per claim, in lotto ~0,8x (P6c).
⇒ Per il design (2.2): il MAX resta, come cura mirata dove la zavorra sta dentro
  il budget del focus — le fonti corte, che sono il 69,5% degli span (N10).
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
import time

ALBERO = pathlib.Path(r"C:\Users\aurel\Code\HippoAgent")
QUI = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(ALBERO))

import verimem  # noqa: E402
from verimem.local_grounding import get_local_judge  # noqa: E402

_FRASI = re.compile(r"(?<=[.!?])\s+")
CUT = 40.0

# ── i 5 casi zavorra del lead, verbatim ──────────────────────────────────────
CLAIM_FALSO = "Il direttore e' stato confermato nell'incarico il 4 maggio."
CLAIM_VERO = "Il direttore ha rassegnato le dimissioni il 4 maggio."
D = "Verbale: il direttore ha rassegnato le dimissioni il 4 maggio."
Z = "La mensa aziendale resta chiusa il primo maggio."
ZAVORRA = [("R1 corta", CLAIM_FALSO, D, "falso"), ("R2 +zav coda", CLAIM_FALSO, D + " " + Z, "falso"),
           ("P-a sola zav", CLAIM_FALSO, Z, "falso"), ("P-b zav testa", CLAIM_FALSO, Z + " " + D, "falso"),
           ("P-c vero +zav", CLAIM_VERO, D + " " + Z, "vero")]


def frasi(testo: str) -> list[str]:
    return [f.strip() for f in _FRASI.split(testo) if f.strip()] or [testo]


def auroc(pos: list[float], neg: list[float]) -> float:
    """P(score_vero > score_falso): senza dipendenze, con i pareggi a meta'."""
    if not pos or not neg:
        return float("nan")
    tot = 0.0
    for p in pos:
        for n in neg:
            tot += 1.0 if p > n else (0.5 if p == n else 0.0)
    return tot / (len(pos) * len(neg))


def main() -> None:
    print("IMPORT DA", verimem.__file__)
    t0 = time.perf_counter()
    judge = get_local_judge()
    scorer = judge._ensure_scorer()  # noqa: SLF001 — lo stesso percorso di `score`
    print(f"caricamento {time.perf_counter() - t0:.1f} s\n")

    def focus(src: str, claim: str) -> float:
        return judge.score(src, claim)

    def max_per_frase(src: str, claim: str) -> tuple[float, int]:
        fr = frasi(src)
        punti = scorer([judge.coppia(f, claim) for f in fr])
        return max(judge.normalizza(p) for p in punti), len(fr)

    # ── E1: i 5 del lead ──────────────────────────────────────────────────
    print("E1 · I 5 CASI ZAVORRA DEL LEAD   [cut 40]")
    print(f"   {'caso':14s} atteso  {'FOCUS':>7}  {'MAX':>7}  M   verdetto focus / max")
    f_focus = f_max = 0
    v_persi_focus = v_persi_max = 0
    for nome, claim, src, atteso in ZAVORRA:
        a = focus(src, claim)
        b, m = max_per_frase(src, claim)
        vf, vm = a < CUT, b < CUT
        if atteso == "falso":
            f_focus += vf
            f_max += vm
        else:
            v_persi_focus += vf
            v_persi_max += vm
        print(f"   {nome:14s} {atteso:6s} {a:7.2f}  {b:7.2f}  {m}   "
              f"{'FERMATO' if vf else 'passa':7s} / {'FERMATO' if vm else 'passa'}")
    print(f"   falsi fermati: focus {f_focus}/4 · max {f_max}/4 · veri persi: focus {v_persi_focus}/1 · max {v_persi_max}/1")
    e1 = f_focus <= 2 and f_max == 4 and v_persi_max == 0
    if e1:
        v_e1 = "REGGE"
    elif f_focus > 2:
        v_e1 = f"🔴 FALSIFICATA: il focus ferma gia' {f_focus}/4, il MAX e' ridondante qui"
    else:
        v_e1 = "🔴 FALSIFICATA"
    print(f"   ⇒ E1 {v_e1}")

    # ── E2: le mie 30 con zavorra in coda e in testa ──────────────────────
    spec = importlib.util.spec_from_file_location(
        "trenta", QUI.parent / "ws3-trenta-coppie-con-e-senza-frase-estranea.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    coppie = mod.coppie()  # (fonte, falso, vero)
    print(f"\nE2 · LE MIE 30 COPPIE, zavorra «{Z}» in CODA e in TESTA")
    esiti = {}
    for dove in ("coda", "testa"):
        pos_f, neg_f, pos_m, neg_m, emme = [], [], [], [], []
        for fonte, falso, vero in coppie:
            src = fonte + " " + Z if dove == "coda" else Z + " " + fonte
            pos_f.append(focus(src, vero))
            neg_f.append(focus(src, falso))
            bv, m = max_per_frase(src, vero)
            bf, _ = max_per_frase(src, falso)
            pos_m.append(bv)
            neg_m.append(bf)
            emme.append(m)
        af, am = auroc(pos_f, neg_f), auroc(pos_m, neg_m)
        esiti[dove] = (af, am)
        print(f"   zavorra in {dove:5s}: AUROC focus {af:.4f} · max per frase {am:.4f} · differenza {am - af:+.4f}"
              f" · M medio {sum(emme) / len(emme):.2f}")
    d_max = max(abs(am - af) for af, am in esiti.values())
    print(f"   ⇒ E2 (|differenza| < 0,02): {'REGGE' if d_max < 0.02 else ('🔴 FALSIFICATA' if d_max > 0.05 else 'indeciso (fra 0,02 e 0,05)')}")


if __name__ == "__main__":
    main()
