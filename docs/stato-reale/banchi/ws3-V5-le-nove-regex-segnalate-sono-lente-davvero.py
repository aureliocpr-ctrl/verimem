# -*- coding: utf-8 -*-
"""V5 — i 9 alert `py/polynomial-redos` sulle regex: sono lente DAVVERO?

    python docs/stato-reale/banchi/ws3-V5-le-nove-regex-segnalate-sono-lente-davvero.py

CodeQL segnala 9 alert su queste regex (1265, 1309, 1310, 1275, 1236, 1329,
1269, 1316, 1306). L'analisi e' STATICA: guarda la forma del pattern, non
quanto tempo impiega ne' quanto e' lungo l'input che riceve davvero. Prima di
curare o dismettere, il passo ① del mandato: **riprodurre e misurare**.

DUE COSE CHE L'ANALISI STATICA NON PUO' VEDERE, e che decidono il verdetto:
  ① **i quantificatori LIMITATI**. `\\s{0,3}-?\\s{0,3}` e' ambiguo — una sequenza
     di spazi si puo' spartire in piu' modi fra i due gruppi — ma i modi sono
     al piu' 4x2x4: un fattore COSTANTE per posizione, non una crescita in n.
  ② **la lunghezza dell'input al SITO DI CHIAMATA**. `_NOME_DI_PARAMETRO` viene
     applicata a `testo[max(0, inizio - 40):inizio]`: **quaranta caratteri**,
     per costruzione. Una regex quadratica su 40 caratteri costa 1600 passi.

⇒ Il criterio, dichiarato prima di misurare: **una regex e' da curare se il
tempo cresce PIU' CHE LINEARMENTE fra 10 KB e 100 KB** (10x l'input ⇒ molto
piu' di 10x il tempo). Se cresce ~10x, il pattern e' lineare in pratica e
l'alert va **dismesso con la misura come rationale**, non curato a caso.

⚠️ Ogni input e' costruito per essere il PEGGIORE di quella regex: prefissi
che il motore deve provare e far fallire il piu' tardi possibile. Un banco che
usasse testo normale non misurerebbe il ReDoS.

⚠️ Le regex si leggono dal prodotto, non si ricopiano: se qualcuno le cambia,
questo banco misura la versione nuova.
"""
import re
import time

from verimem.l1_tested_detector import _NOME_DI_PARAMETRO
from verimem.quantity_match import _APRE_LA_FRASE_RE, _LABEL_RE, _QUANT_RE
from verimem.valore_non_nella_fonte import _DECIMALI_RE, _TOKEN_CON_VERSIONE

KB = 1024

#: (nome, regex, come_si_usa, costruttore del caso PEGGIORE, alert CodeQL)
CASI = [
    ("_LABEL_RE", _LABEL_RE, "search",
     lambda n: "A" * n,                       # maiuscole senza fine riga: `$` fallisce sempre
     "1265"),
    ("_QUANT_RE", _QUANT_RE, "finditer",
     lambda n: "1   -   " * (n // 8),         # spazi spartibili fra i due \s{0,3}
     "1309/1310/1275/1236"),
    ("_APRE_LA_FRASE_RE", _APRE_LA_FRASE_RE, "finditer",
     lambda n: ". " * (n // 2),               # separatori a raffica, mai una maiuscola
     "1329"),
    ("_DECIMALI_RE", _DECIMALI_RE, "finditer",
     lambda n: "1" * n,                       # cifre senza mai il separatore
     "1269"),
    ("_TOKEN_CON_VERSIONE", _TOKEN_CON_VERSIONE, "finditer",
     lambda n: "a" + "b." * (n // 2),         # [\w.]* lunghissimo, il `-` non arriva mai
     "1316"),
    ("_NOME_DI_PARAMETRO", _NOME_DI_PARAMETRO, "search",
     lambda n: "-" + "a" * (n - 1),           # --?\w+ lunghissimo, `\s+$` fallisce
     "1306"),
]

TAGLIE = [10 * KB, 100 * KB]


def misura(regex, come, testo):
    t0 = time.perf_counter()
    if come == "search":
        regex.search(testo)
    else:
        for _ in regex.finditer(testo):
            pass
    return time.perf_counter() - t0


print("V5 — le regex segnalate, sul loro caso PEGGIORE\n")
print("%-22s %10s %10s %8s  %s"
      % ("regex", "10 KB", "100 KB", "x10?", "verdetto"))
print("-" * 76)

verdetti = {}
for nome, regex, come, costruisci, alert in CASI:
    tempi = []
    for n in TAGLIE:
        t = misura(regex, come, costruisci(n))
        tempi.append(t)
    rapporto = tempi[1] / tempi[0] if tempi[0] > 0 else float("inf")
    # 10x input: lineare ~10x, quadratico ~100x. La soglia sta in mezzo,
    # larga per non chiamare quadratico un rumore di misura.
    quadratico = rapporto > 30
    verdetti[nome] = (tempi, rapporto, quadratico, alert)
    print("%-22s %9.1fms %9.1fms %7.1fx  %s"
          % (nome, tempi[0] * 1000, tempi[1] * 1000, rapporto,
             "🔴 CURARE" if quadratico else "✅ lineare in pratica"))

print("\n" + "=" * 76)
print("IL SITO DI CHIAMATA — la lunghezza che la regex riceve DAVVERO\n")
# `_NOME_DI_PARAMETRO` non vede mai piu' di 40 caratteri: l1_tested_detector.py
# la chiama su `testo[max(0, inizio - 40):inizio]`.
reale = "-" + "a" * 39
t_reale = min(misura(_NOME_DI_PARAMETRO, "search", reale) for _ in range(50))
print(f"  _NOME_DI_PARAMETRO sui suoi 40 caratteri reali: "
      f"{t_reale * 1e6:.1f} microsecondi")
print("  (l1_tested_detector.py:79 -> testo[max(0, inizio - 40):inizio])")

print("\n" + "=" * 76)
print("COSA FARNE, secondo il criterio dichiarato prima di misurare:")
for nome, (tempi, rapporto, quadratico, alert) in verdetti.items():
    if quadratico:
        print(f"  🔴 {nome:22s} alert {alert:20s} CURA con RED-GREEN")
    else:
        print(f"  ✅ {nome:22s} alert {alert:20s} dismissione, rationale = "
              f"{rapporto:.1f}x su 10x input")
print("\nrifallo con:")
print("  python docs/stato-reale/banchi/"
      "ws3-V5-le-nove-regex-segnalate-sono-lente-davvero.py")
