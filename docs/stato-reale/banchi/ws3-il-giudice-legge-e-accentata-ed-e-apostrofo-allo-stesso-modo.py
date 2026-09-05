"""LIVELLO: il giudice locale (`get_local_judge`), un processo, un caricamento —
le STESSE 30 coppie in DUE GRAFIE, «è» accentata e «e'» con l'apostrofo, con e
senza la frase estranea. Una variabile per volta.

Il giudice legge «è» ed «e'» allo stesso modo? Il corpus scrive «e'» 976 volte
contro 357 «è» (test_e_apostrofo_e_un_marcatore_di_verbo, W7-73): se il CE e'
piu' debole su una grafia, quella e' la grafia del 73% delle scritture.

    python docs/stato-reale/banchi/ws3-il-giudice-legge-e-accentata-ed-e-apostrofo-allo-stesso-modo.py

⚠️ RICHIEDE UNO SLOT. Store di Aurelio non aperto: le 30 coppie sono mie.
Finestra dichiarata: caricamento ~20 s + 30 x 2 x 2 x 2 coppie x 65 ms < 30 s;
dichiaro 300 s.

━━ DA DOVE VIENE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Il 03/09 la zavorra cambiava effetto da +31 a +99 punti a seconda che il testo
avesse «e» o «e'» — segnato come NON MISURATO da allora. Stasera l'apostrofo si
e' rivelato una faglia in due regex (\\b dopo `e'` non si accende) e il prodotto
lo sapeva (subject_extract.py:37). Il giudice pero' non e' una regex: e' un
tokenizzatore piu' un CE fine-tuned su HaluMem. Se HaluMem scrive «è», il CE ha
visto «e'» raramente — e «e'» si tokenizza in DUE pezzi («e», «'»), non in uno.

━━ PREDIZIONI, scritte prima (05/09 23:45) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    G1 senza zavorra: AUROC in grafia «è» supera quella in «e'» di ALMENO 0,03.
       🔴 muore se |differenza| < 0,02: il giudice e' indifferente alla grafia e
       il +31/+99 del 03/09 veniva da altro.
    G2 con zavorra in coda: il ribaltamento (calo di AUROC fra senza e con) e'
       PIU' GRANDE in grafia «e'» che in «è», di almeno 0,03.
       🔴 muore se e' uguale o rovesciato.
    G3 col MAX per frase la differenza fra grafie si riduce sotto 0,02 (il MAX
       toglie la zavorra, non la grafia: se la differenza resta, e' la grafia).
       🔴 muore se resta >= 0,03: allora la grafia pesa da sola, senza zavorra.

━━ COME SI LEGGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se G1 regge: normalizzare «e'» -> «è» PRIMA del giudice e' una cura a costo
zero che il design deve prendere (una riga in `coppia()`), e la misura di
ieri sulle implicite (A/B/C/R) va rifatta in grafia accentata prima di
confrontare i modelli. Se G1 muore: la grafia non e' una variabile e si chiude.

━━ ESITO, 05/09 23:48, slot preso e rilasciato, caricamento 19,4 s ━━━━━━━━━━━━━
Le 30 coppie sono in ASCII di partenza (21 «e'», 0 «è»): il braccio accentato
e' la conversione, l'ASCII e' l'originale.
    grafia          regime      senza zav   con zav     calo
    e' (ASCII)      focus         0,8700    0,8067   −0,0633
    e' (ASCII)      max/frase     0,8700    0,8500   −0,0200
    è (accentata)   focus         0,9111    0,8722   −0,0389
    è (accentata)   max/frase     0,9111    0,8878   −0,0233
    G1 accentata − ASCII, senza zavorra, focus   +0,0411   REGGE
    G2 calo ASCII − calo accentata, focus        +0,0244   indeciso
    G3 accentata − ASCII col MAX, con zavorra    +0,0378   🔴 FALSIFICATA
⇒ G3 e' caduta nel verso che conta: la grafia pesa DA SOLA, anche quando il MAX
  ha tolto la zavorra. Su quattro celle su quattro l'accentata batte l'ASCII di
  +0,04 / +0,04 / +0,07 / +0,04. Il corpus scrive «e'» 976 volte contro 357 «è»:
  il giudice lavora sul lato debole nel 73% delle scritture.
⇒ Cura a costo zero, per il design (2.2 / `coppia()`): normalizzare «e'»->«è»
  (e puo'/da'/sara'/cosi'/piu'/perche') PRIMA del giudice, su fonte e claim
  insieme — una variabile sola, entrambi i lati. E la misura di ieri sui quattro
  scorer (P3, implicite) va rifatta in grafia accentata prima di confrontare i
  modelli: B/C/A sono addestrati su testi accentati e potrebbero soffrirne meno.
⚠️ n=30: +0,04 va letto con il bootstrap appaiato (P3) prima di diventare una
  cura di prodotto. Qui e' la direzione, coerente su 4 celle su 4.
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
Z = "La mensa aziendale resta chiusa il primo maggio."
Z_ASCII = Z  # la zavorra non contiene «è»: identica nelle due grafie


def accentata(t: str) -> str:
    """«e'» -> «è», «E'» -> «È», «puo'» -> «può», «da'» -> «dà», «sara'» -> «sarà»."""
    t = re.sub(r"\bE'", "È", t)
    t = re.sub(r"\be'", "è", t)
    t = re.sub(r"\bpuo'", "può", t)
    t = re.sub(r"\bda'", "dà", t)
    t = re.sub(r"\bsara'", "sarà", t)
    t = re.sub(r"\bcosi'", "così", t)
    t = re.sub(r"\bpiu'", "più", t)
    t = re.sub(r"\bperche'", "perché", t)
    return t


def ascii_(t: str) -> str:
    """Il verso opposto, per le coppie che fossero gia' accentate."""
    t = t.replace("È", "E'").replace("è", "e'").replace("può", "puo'").replace("dà", "da'")
    return t.replace("sarà", "sara'").replace("così", "cosi'").replace("più", "piu'").replace("perché", "perche'")


def auroc(pos: list[float], neg: list[float]) -> float:
    tot = 0.0
    for p in pos:
        for n in neg:
            tot += 1.0 if p > n else (0.5 if p == n else 0.0)
    return tot / (len(pos) * len(neg))


def main() -> None:
    print("IMPORT DA", verimem.__file__)
    t0 = time.perf_counter()
    judge = get_local_judge()
    scorer = judge._ensure_scorer()  # noqa: SLF001
    print(f"caricamento {time.perf_counter() - t0:.1f} s")

    spec = importlib.util.spec_from_file_location(
        "trenta", QUI.parent / "ws3-trenta-coppie-con-e-senza-frase-estranea.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    coppie = mod.coppie()  # (fonte, falso, vero)
    n_apostrofi = sum(t.count("e'") for c in coppie for t in c)
    n_accenti = sum(t.count("è") for c in coppie for t in c)
    print(f"30 coppie: occorrenze di «e'» {n_apostrofi} · di «è» {n_accenti}"
          f"  -> la grafia di partenza e' {'ASCII' if n_apostrofi >= n_accenti else 'accentata'}\n")

    def focus(src: str, claim: str) -> float:
        return judge.score(src, claim)

    def max_frase(src: str, claim: str) -> float:
        fr = [f.strip() for f in _FRASI.split(src) if f.strip()] or [src]
        return max(judge.normalizza(p) for p in scorer([judge.coppia(f, claim) for f in fr]))

    grafie = {"e' (ASCII)": ascii_, "è (accentata)": accentata}
    ris: dict[tuple[str, str, str], float] = {}
    print(f"   {'grafia':14s} {'regime':10s} {'senza zav':>10s} {'con zav':>10s} {'calo':>8s}")
    for nome_g, conv in grafie.items():
        for regime, fn in (("focus", focus), ("max/frase", max_frase)):
            for zav in (False, True):
                pos, neg = [], []
                for fonte, falso, vero in coppie:
                    src = conv(fonte) + (" " + Z if zav else "")
                    pos.append(fn(src, conv(vero)))
                    neg.append(fn(src, conv(falso)))
                ris[(nome_g, regime, "con" if zav else "senza")] = auroc(pos, neg)
            s, c = ris[(nome_g, regime, "senza")], ris[(nome_g, regime, "con")]
            print(f"   {nome_g:14s} {regime:10s} {s:10.4f} {c:10.4f} {c - s:+8.4f}")

    g1 = ris[("è (accentata)", "focus", "senza")] - ris[("e' (ASCII)", "focus", "senza")]
    calo_ascii = ris[("e' (ASCII)", "focus", "senza")] - ris[("e' (ASCII)", "focus", "con")]
    calo_acc = ris[("è (accentata)", "focus", "senza")] - ris[("è (accentata)", "focus", "con")]
    g2 = calo_ascii - calo_acc
    g3 = ris[("è (accentata)", "max/frase", "con")] - ris[("e' (ASCII)", "max/frase", "con")]
    print(f"\n   G1 accentata − ASCII, senza zavorra, focus : {g1:+.4f}"
          f"   {'REGGE' if g1 >= 0.03 else ('🔴 FALSIFICATA' if abs(g1) < 0.02 else 'indeciso')}")
    print(f"   G2 calo ASCII − calo accentata, focus      : {g2:+.4f}"
          f"   {'REGGE' if g2 >= 0.03 else ('🔴 FALSIFICATA' if g2 <= 0 else 'indeciso')}")
    print(f"   G3 accentata − ASCII col MAX, con zavorra  : {g3:+.4f}"
          f"   {'REGGE' if abs(g3) < 0.02 else ('🔴 FALSIFICATA: la grafia pesa da sola' if abs(g3) >= 0.03 else 'indeciso')}")
    print("\n   ⚠️ n=30: le differenze sotto ~0,05 vanno lette con l'intervallo (bootstrap")
    print("      appaiato, P3) prima di diventare una cura. Qui si misura la direzione.")


if __name__ == "__main__":
    main()
