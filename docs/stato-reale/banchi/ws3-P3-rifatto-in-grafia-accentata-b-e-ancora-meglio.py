"""LIVELLO: i quattro scorer di P3 (nostro giudice R, A, B, C) piu' il conta-parole,
sulle STESSE 30 contraddizioni implicite in DUE grafie — ASCII (l'originale di
ieri) e accentata. Un processo, tutti i modelli caricati una volta.

Ieri (f3907dd9): «B e' l'unico decidibilmente migliore del nostro giudice sulle
implicite, +0,2856 [+0,160; +0,420]». Stanotte (b82ebf55): il nostro giudice
legge «è» meglio di «e'» di +0,04. Le 30 implicite erano in ASCII; A, B e C sono
addestrati su testi accentati. Quindi ieri il confronto era A/B/C sul loro
terreno contro R sul suo terreno debole: un confondente. Questo banco lo toglie.

    python docs/stato-reale/banchi/ws3-P3-rifatto-in-grafia-accentata-b-e-ancora-meglio.py

⚠️ RICHIEDE UNO SLOT (quattro modelli, ~1,5 GB). Store di Aurelio non aperto.
Finestra dichiarata: caricamenti ~2 min + 30 x 2 x 2 x 4 coppie: dichiaro 600 s.

━━ PREDIZIONI, scritte prima (06/09 00:52) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    K1 il nostro giudice R guadagna con l'accentata >= +0,03 di AUROC (come
       sulle dirette). 🔴 muore se < +0,01: allora sulle implicite la grafia
       non conta e il +0,04 di stanotte era della popolazione, non del giudice.
    K2 B NON guadagna: |differenza| < 0,02 (e' gia' sul suo terreno).
       🔴 muore se guadagna >= 0,03: anche B soffriva l'ASCII, e il divario di
       ieri era sottostimato, non sovrastimato.
    K3 B − R in grafia ACCENTATA resta > 0 con l'intervallo appaiato che esclude
       lo zero: la grafia spiega al massimo 0,05 dei +0,2856 di ieri.
       🔴 muore se l'intervallo include lo zero: «B e' meglio» era un
       confondente di grafia, e la scelta del modello si riapre.

━━ COME SI LEGGE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Se K3 regge, il confronto di ieri e' confermato su terreno pari e la
normalizzazione della grafia e' una cura al nostro giudice, non un argomento
contro B. Se K3 muore, la pagina del giudice 0.8.0 non puo' citare +0,2856.

━━ ESITO, 06/09 01:01, slot 32c9f1079258 preso e rilasciato, 519 s (finestra 600) ━━
    scorer                        AUROC ASCII  accentata   diff appaiata [95%]
    conta-parole                       0,6017     0,6017   +0,0000 [+0,000; +0,000]
    R nostro giudice                   0,6589     0,6878   +0,0289 [−0,010; +0,074]
    A nli-deberta-v3-base              0,6700     0,6956   +0,0256 [−0,012; +0,071]
    B deberta-large-mnli-fever         0,9444     0,9500   +0,0056 [−0,004; +0,020]
    C MiniCheck-DeBERTa-large          0,7656     0,7700   +0,0044 [−0,022; +0,032]
    K1 R guadagna >= +0,03        +0,0289   INDECISO (direzione si', intervallo con lo zero)
    K2 B non guadagna (|d|<0,02)  +0,0056   REGGE
    B − R in ASCII (ieri)         +0,2856 [+0,160; +0,420]
    B − R in ACCENTATA            +0,2622 [+0,143; +0,391]
    la grafia spiega              +0,0233 del divario
    K3 B resta meglio, grafia <= 0,05 del divario          REGGE
⇒ Il confronto di ieri e' CONFERMATO su terreno pari: B batte il nostro giudice
  anche quando il nostro legge la grafia che preferisce; la grafia vale +0,02 dei
  +0,29. La normalizzazione «e'»->«è» resta una cura al NOSTRO giudice (e al base
  A, che guadagna quanto R: +0,026 — R l'ha ereditato), non un argomento contro B.
⚠️ K1 e' indeciso per n=30, non per direzione: sulle 30 dirette era +0,04 su 4
  celle su 4, qui +0,03 con l'intervallo che sfiora lo zero. Il numero che
  decide la cura di prodotto e' su un campione piu' grande, non su queste 30.
🔴 E su quel campione (06/09 01:18, ws3-la-grafia-sul-corpus-vero-ammessi-e-
  bocciati: 400 ammessi + 109 bocciati) la grafia NON sposta nulla: −0,03 e
  +0,44 con intervalli che includono lo zero, nessun verdetto cambiato. K1 si
  chiude in negativo per il prodotto; K3 (B resta meglio) non ne e' toccata.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import time

QUI = pathlib.Path(__file__).resolve()
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")


def carica(nome: str):
    spec = importlib.util.spec_from_file_location(nome.replace("-", "_"), QUI.parent / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    import verimem
    print("IMPORT DA", verimem.__file__)
    p3 = carica("ws3-P3-la-popolazione-implicita-contro-quattro-scorer")
    grafie = carica("ws3-il-giudice-legge-e-accentata-ed-e-apostrofo-allo-stesso-modo")

    ascii_ = p3.casi()
    acc = [(grafie.accentata(f), grafie.accentata(x), grafie.accentata(v)) for f, x, v in ascii_]
    n_ap = sum(t.count("e'") for c in ascii_ for t in c)
    n_ac = sum(t.count("è") for c in acc for t in c)
    print(f"30 implicite: «e'» in ASCII {n_ap} · «è» dopo la conversione {n_ac}\n")

    t0 = time.perf_counter()
    punti: dict[str, dict[str, tuple[list[float], list[float]]]] = {}
    for nome, fn in (("conta-parole", p3.punteggi_baseline), ("R nostro giudice", p3.punteggi_nostro)):
        punti[nome] = {"ASCII": fn(ascii_), "accentata": fn(acc)}
    for nome, hf in p3.MODELLI.items():
        punti[nome] = {"ASCII": p3.punteggi_hf(hf, ascii_), "accentata": p3.punteggi_hf(hf, acc)}
    print(f"\ncaricamenti e punteggi: {time.perf_counter() - t0:.0f} s\n")

    print(f"   {'scorer':28s} {'AUROC ASCII':>12s} {'accentata':>10s} {'diff appaiata [95%]':>24s}")
    diff: dict[str, tuple[float, float, float]] = {}
    for nome, d in punti.items():
        a = p3.auroc(*d["ASCII"])
        b = p3.auroc(*d["accentata"])
        lo, hi = p3.differenza(d["accentata"], d["ASCII"])
        diff[nome] = (b - a, lo, hi)
        print(f"   {nome:28s} {a:12.4f} {b:10.4f}   {b - a:+.4f} [{lo:+.3f}; {hi:+.3f}]")

    k1 = diff["R nostro giudice"][0]
    k2 = diff["B deberta-large-mnli-fever"][0]
    print(f"\n   K1 R guadagna >= +0,03      : {k1:+.4f}  {'REGGE' if k1 >= 0.03 else ('🔴 FALSIFICATA' if k1 < 0.01 else 'indeciso')}")
    print(f"   K2 B non guadagna (|d|<0,02): {k2:+.4f}  {'REGGE' if abs(k2) < 0.02 else ('🔴 FALSIFICATA' if k2 >= 0.03 else 'indeciso')}")

    b_acc = punti["B deberta-large-mnli-fever"]["accentata"]
    r_acc = punti["R nostro giudice"]["accentata"]
    b_asc = punti["B deberta-large-mnli-fever"]["ASCII"]
    r_asc = punti["R nostro giudice"]["ASCII"]
    d_acc = p3.auroc(*b_acc) - p3.auroc(*r_acc)
    lo, hi = p3.differenza(b_acc, r_acc)
    d_asc = p3.auroc(*b_asc) - p3.auroc(*r_asc)
    lo0, hi0 = p3.differenza(b_asc, r_asc)
    print(f"\n   B − R in ASCII (ieri)       : {d_asc:+.4f} [{lo0:+.3f}; {hi0:+.3f}]")
    print(f"   B − R in ACCENTATA          : {d_acc:+.4f} [{lo:+.3f}; {hi:+.3f}]")
    print(f"   la grafia spiega            : {d_asc - d_acc:+.4f} del divario")
    k3 = lo > 0 and (d_asc - d_acc) <= 0.05
    print(f"   K3 B resta meglio, grafia <= 0,05 del divario: "
          f"{'REGGE' if k3 else ('🔴 FALSIFICATA: intervallo con lo zero' if lo <= 0 else 'indeciso: B resta meglio ma la grafia pesa piu di 0,05')}")


if __name__ == "__main__":
    main()
