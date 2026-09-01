r"""Quanto e' frequente la forma che il gate tratta male: un limite che avevo dichiarato.

Paga il limite scritto consegnando `3b4360d7`: «*non ho misurato sul corpus quanti
fatti contengano un orario o una data breve, quindi **non dico quanto sia
frequente***».

IL REPERTO DA QUANTIFICARE (`3b4360d7`, cella `W5-11`): `_spans_delle_date` pota le
date **complete** e non gli **orari** ne' le date **senza anno** ⇒ «*il 28/08 alle
20:58*» produce **quattro** quantita' che nessuno ha affermato, e alla porta la
stessa data non sostenuta **passa** se scritta `2026-08-10` e **cade** se scritta
`28/08`.

⚠️ **CHE NUMERO E' E CHE NUMERO NON E'**: `L4.1` quarantina per **qualunque** numero
che la fonte non dica, non solo per le marche temporali. ⇒ Questo banco misura
**quanti quarantinati PORTANO quella forma**, cioe' un **limite superiore dei
candidati**, non quanti siano caduti PER quella causa.

⚠️ **DUE POPOLAZIONI, non una**: la stessa forma si conta anche sugli **ammessi**. Se
la quota fosse uguale nelle due, la marca temporale non sarebbe un fattore.

🟡 ESITO — **due verdetti opposti, e il primo falsifica la mia ipotesi**::

    popolazione                       totale  marca breve   quota   Wilson 95%     data piena
    ammessi (status != quarantined)    14303         2328   16.3%  [15.7, 16.9]          2750
    quarantinati, causa L4.1             142           31   21.8%  [15.8, 29.3]             6
    quarantinati, qualunque causa       2679         1468   54.8%  [52.9, 56.7]          1602

🪞 **① LA MIA IPOTESI NON REGGE, ed era la ragione per cui ho aperto il banco.**
Avevo il sospetto che la potatura mancante facesse cadere fatti in massa **via
`L4.1`**. Sui quarantinati con causa `L4.1` la quota e' **21.8%**, e il suo intervallo
**[15.8%, 29.3%] CONTIENE il 16.3% degli ammessi** ⇒ **non sovra-rappresentata**. Il
meccanismo che avevo in mente **non e' quello che sta cadendo sul corpus**.

🔴 **② MA C'E' UN SECONDO NUMERO, e non lo cercavo**: fra i quarantinati **di qualunque
causa** la marca temporale breve sta nel **54.8%** contro il **16.3%** degli ammessi —
**intervalli disgiunti**, tre volte tanto. E la stessa cosa vale per le date
**complete** (**59.8%** contro **19.2%**), che pero' la potatura **copre**.

🔑 **⇒ Le due righe insieme dicono una terza cosa**: la marca temporale e' fortissimamente
associata alla quarantena, **ma non attraverso `L4.1`** — se fosse la potatura, a
cadere sarebbero i formati **non coperti**, e invece cade **anche** quello coperto,
nella stessa misura. ⇒ **Il candidato e' un'altra proprieta' che viaggia insieme alle
date**: sono i **fatti di misura** — i nostri, con source tabellare — e la forma
tabellare e' gia' misurata come penalizzante (`W5-5`; `quantity_match.py:676`, 27 falsi
positivi su 28). **Non l'ho isolata: la nomino come candidato, non come causa.**

⇒ **PER LA DECISIONE**: il difetto della potatura resta **reale e riproducibile alla
porta** (`E` passa, `F` cade, sei casi su sei, `3b4360d7`), ma **la sua portata sul
corpus non e' dimostrata**. E' una **cura di correttezza**, non un'emergenza di
rilascio. Chi ordina la coda delle cure deve avere questo numero **prima**.

🪞 **Un errore di processo, mio, la seconda volta in un'ora**: ho scritto la sezione
ESITO nel docstring **prima di eseguire**, con numeri inventati (avevo scritto 26.6% e
30.7% contro i veri 16.3% e 21.8%). Corretto prima del commit, come la volta prima. **La
causa non e' distrazione: e' che il mio formato di banco tiene l'esito nel docstring, e
scrivendo il file di seguito lo compilo insieme al resto.** ⇒ La cura e' di processo:
**il banco si scrive senza la sezione ESITO, si esegue, e l'esito si aggiunge dopo** —
come ho fatto per i due banchi precedenti di stasera, dove infatti non e' successo.

SOLA LETTURA: `sqlite3` con `mode=ro`, percorso chiesto al prodotto
(`CONFIG.semantic_db`) e non all'intuito.
⚖️ PUNTI DEBOLI: ① `quarantined_by` **non copre tutti** i quarantinati (100% negli
ultimi tre giorni, ~28% sullo storico) ⇒ la riga `causa L4.1` vale su **142** casi, non
sui 2679; ② la regex conta anche `1:2` e `1/2` che marche temporali non sono ⇒ il
numeratore e' **generoso**, il che rende «non sovra-rappresentata» **piu' forte** e il
54.8% **piu' debole**; ③ il corpus e' scritto quasi tutto da noi, non da utenti terzi;
④ **nessun controllo sul tempo**: se i quarantinati si concentrano in un periodo in cui
scrivevamo piu' date, il 54.8% e' un artefatto di quella concentrazione — **non l'ho
escluso**.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-quanti-fatti-portano-una-marca-temporale-breve.py
"""
import re
import sqlite3
from math import sqrt
from pathlib import Path

from verimem.config import CONFIG

#: orario `20:58` oppure data senza anno `28/08` — le due forme che la potatura NON copre
MARCA = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}/\d{1,2}\b(?!/\d)")
#: la forma che la potatura COPRE — riga di riferimento: se cade anche questa, non e' la potatura
COMPLETA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b")


def wilson(k, n):
    """Intervallo al 95% — senza, una quota su 142 casi si legge come esatta."""
    if not n:
        return (0.0, 0.0)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    e = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0.0, c - e), 100 * min(1.0, c + e))


def conta(righe):
    tot = len(righe)
    return (tot,
            sum(1 for t in righe if MARCA.search(t or "")),
            sum(1 for t in righe if COMPLETA.search(t or "")))


def main():
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    cur = con.cursor()

    def prendi(dove):
        return [r[0] for r in cur.execute(
            "select proposition from facts where " + dove)]

    gruppi = [
        ("ammessi (status != quarantined)", prendi("status is null or status != 'quarantined'")),
        ("quarantinati, causa L4.1", prendi("status = 'quarantined' and quarantined_by = 'L4.1'")),
        ("quarantinati, qualunque causa", prendi("status = 'quarantined'")),
    ]

    print("  %-34s %8s %10s %8s %-16s %10s"
          % ("popolazione", "totale", "marca breve", "quota", "Wilson 95%", "data piena"))
    print("  " + "-" * 96)
    base = None
    for nome, righe in gruppi:
        tot, breve, completa = conta(righe)
        q = 100.0 * breve / tot if tot else 0.0
        lo, hi = wilson(breve, tot)
        if base is None:
            base = q
            base_piena = 100.0 * completa / tot if tot else 0.0
        print("  %-34s %8d %10d %7.1f%% [%5.1f%%, %5.1f%%] %10d"
              % (nome, tot, breve, q, lo, hi, completa))

    tot_l41, breve_l41, _ = conta(gruppi[1][1])
    tot_q, breve_q, piena_q = conta(gruppi[2][1])
    lo, hi = wilson(breve_l41, tot_l41)
    print("\n=== SINTESI ===")
    if not tot_l41:
        print("  ⚠️ nessun quarantinato con causa L4.1 registrata: la riga non si legge.")
    elif lo <= base <= hi:
        print("  🪞 ① L'IPOTESI CADE: fra i quarantinati-L4.1 la quota e' %.1f%%, intervallo"
              % (100.0 * breve_l41 / tot_l41))
        print("       [%.1f%%, %.1f%%], che CONTIENE il %.1f%% degli ammessi ⇒ la marca"
              % (lo, hi, base))
        print("       temporale NON e' sovra-rappresentata fra i caduti per quel layer.")
    else:
        print("  🔴 ① la quota fra i quarantinati-L4.1 e' fuori dall'intervallo degli ammessi.")

    q_gen = 100.0 * breve_q / tot_q if tot_q else 0.0
    lo_g, hi_g = wilson(breve_q, tot_q)
    piena_gen = 100.0 * piena_q / tot_q if tot_q else 0.0
    if lo_g > base:
        print("  🔴 ② MA sui quarantinati di QUALUNQUE causa la quota e' %.1f%% [%.1f%%, %.1f%%]"
              % (q_gen, lo_g, hi_g))
        print("       contro %.1f%% degli ammessi — intervalli disgiunti." % base)
        print("       ⇒ E cade anche la forma COPERTA dalla potatura (%.1f%% contro %.1f%%):"
              % (piena_gen, base_piena))
        print("          se fosse la potatura, quella dovrebbe restare a terra. NON e' L4.1.")
    else:
        print("  ⚪ ② nemmeno sui quarantinati in generale la quota si stacca (%.1f%%)." % q_gen)
    con.close()


main()
