# -*- coding: utf-8 -*-
r"""`L4.2` e' cieco per costruzione su ogni testo che usa UNITA' DI MISURA.

    CTRL+ 14 valvole / 14 operai (il caso del suo docstring)   SEGNALA  atteso SEGNALA
    unita' condivisa 'pezzi'                                   tace     atteso SEGNALA
    unita' condivisa 'euro'                                    tace     atteso SEGNALA
    unita' condivisa '%'                                       tace     atteso SEGNALA
    CTRL- claim VERO                                           tace     atteso tace

⇒ **Il banco separa**: il controllo positivo parla, il negativo tace. I tre
mancati non sono rumore.

IL MECCANISMO, letto e poi misurato. `_intorno()` prende **UNA parola per lato**
del numero. `valori_riusati_da_altro_contesto` tace quando quel vicinato
coincide fra claim e fonte. Ma la parola che segue un numero e' l'**unita' di
misura**, e chi scrive usa la stessa unita' per grandezze diverse::

    claim dopo=['pezzi']   fonte dopo=['pezzi']   -> IDENTICO -> tace
    claim dopo=['euro']    fonte dopo=['euro']    -> IDENTICO -> tace

Il discriminante («ordine» / «reso», «canone» / «deposito») sta **oltre la
finestra**. `L4.2` funziona quando il sostantivo dopo il numero **e'** la cosa
(«14 valvole»), e non puo' funzionare quando e' un'unita'.
⇒ **Cio' che resta scoperto non e' un caso limite: sono contratti, fatture,
referti e specifiche tecniche** — i documenti in cui i numeri contano.

📌 QUESTO SERVE A F1 (`L4.3`, doc `d809a433` di @ws3): misura il territorio che
il suo strato deve coprire, e conferma con un numero che allargare la finestra
alla FRASE non e' una preferenza ma il minimo necessario. Va letto insieme a
`ws5-review-F1-il-passo-3-assolve-lo-scambio.py`, che mostra il difetto opposto:
la finestra piu' larga assolve troppo.

🔎 REPERTO SECONDARIO, indipendente: **`_intorno` attraversa i confini di riga.**
Su una fonte tabellare — e le nostre source sono quasi tutte output di
strumenti — il vicinato di un numero a fine riga e' la **prima cella della riga
successiva**::

    99.3  dopo=['mese']    <- 'mese' e' la riga SOTTO, non il contesto di 99.3
    1.1   dopo=['colore']

Non produce un avviso falso (il layer *descrive* dove sta il numero), ma la
ricevuta mostra a chi legge un accostamento che nel documento non esiste. E'
il reperto che avevo pubblicato il 28/08 come «sospetto quarto avviso che
mente»: **non e' un avviso che mente, e' una finestra che salta riga.**

⚖️ PUNTO DEBOLE: un caso per unita' (`pezzi`, `euro`, `%`), fonti costruite. So
che questi tre mancano, non che **ogni** testo con unita' manchi — la
generalizzazione «per costruzione» viene dal MECCANISMO letto al sorgente
(`vicinato_del_valore._intorno`, una parola per lato), non dai tre casi. Chi
vuole falsificarla cerchi un testo dove il vicinato dell'unita' NON coincide.
Sul caso `%` il vicinato SEGUENTE e' vuoto su entrambi i lati e a decidere e'
quello precedente: la riga di dettaglio lo stampa.

REGIME: build corrente · python 3.13.12 · nessun modello caricato (funzione
pura) · chiamata la porta `valori_riusati_da_altro_contesto`, quella che il
gate usa a `anti_confab_gate.py:2513`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-L42-tace-quando-il-numero-porta-un-unita.py
"""
import sys
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.vicinato_del_valore import _intorno, valori_riusati_da_altro_contesto as L42

CASI = [
 # (nome, claim, fonte, atteso)
 ("CTRL+ il caso del suo docstring: 14 valvole / 14 operai",
  "Il fornitore Gatti ha consegnato 14 valvole.",
  "Il fornitore Gatti ha inviato 14 operai in cantiere.", "SEGNALA"),
 ("unita' di misura condivisa: 'pezzi' su entrambi i lati",
  "Il reso e' di 250 pezzi.",
  "L'ordine e' di 250 pezzi. Il reso e' di 12 pezzi.", "SEGNALA"),
 ("unita' condivisa: 'euro'",
  "Il deposito e' di 1200 euro.",
  "Il canone e' di 1200 euro. Il deposito e' di 2400 euro.", "SEGNALA"),
 ("unita' condivisa: '%' (formula burocratica)",
  "La penale per il ritardo e' pari al 5%.",
  "Penale per il ritardo pari al 2%. Penale per difformita' pari al 5%.", "SEGNALA"),
 ("CTRL- claim VERO (non deve segnalare)",
  "L'ordine e' di 250 pezzi.",
  "L'ordine e' di 250 pezzi. Il reso e' di 12 pezzi.", "tace"),
]
print("  %-56s %-9s %s" % ("caso", "L4.2", "atteso"))
ok = 0
for nome, c, f, atteso in CASI:
    r = L42(c, f)
    e = "SEGNALA" if r else "tace"
    mark = "OK" if e == atteso else "<== MANCATO"
    if e == atteso: ok += 1
    print("  %-56s %-9s %-9s %s" % (nome[:56], e, atteso, mark))
    if e != atteso:
        for v in sorted({vv for vv in [None]} ) : pass
print("\n  corrette: %d su %d" % (ok, len(CASI)))
print("\n=== il vicinato che decide, nei casi mancati ===")
for nome, c, f, atteso in CASI[1:4]:
    import re
    n = float(re.search(r"\d+", c).group())
    dc, pc = _intorno(c, n); df, pf = _intorno(f, n)
    print("  %-28s claim dopo=%-9s prima=%-7s | fonte dopo=%-9s prima=%-7s  %s"
          % (nome[:28], sorted(dc), sorted(pc), sorted(df), sorted(pf),
             "vicinato COINCIDE -> tace" if (dc & df) or (pc & pf) else "diverso"))
