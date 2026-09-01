r"""Quanto e' frequente la forma che il gate tratta male — e il numero globale INGANNA.

Paga il limite scritto consegnando `3b4360d7`: «*non ho misurato sul corpus quanti
fatti contengano un orario o una data breve, quindi **non dico quanto sia
frequente***». E poi paga il limite che questo banco stesso aveva dichiarato:
«*nessun controllo sul tempo — non l'ho escluso*».

IL REPERTO DA QUANTIFICARE (`3b4360d7`, cella `W5-11`): `_spans_delle_date` pota le
date **complete** e non gli **orari** ne' le date **senza anno** ⇒ alla porta la stessa
data non sostenuta **passa** se scritta `2026-08-10` e **cade** se scritta `28/08`.

⚠️ **CHE NUMERO E' E CHE NUMERO NON E'**: `L4.1` quarantina per **qualunque** numero
che la fonte non dica. ⇒ Qui si misura **quanti quarantinati PORTANO quella forma** —
un **limite superiore dei candidati**, non quanti siano caduti PER quella causa.
⚠️ **DUE POPOLAZIONI**: la stessa forma si conta anche sugli **ammessi**.
⚠️ **E TRE FINESTRE**: il globale si stratifica per mese, perche' un rapporto che
mescola due ere si legge come un difetto in corso.

🟡 ESITO — **tre verdetti, e i primi due si correggono a vicenda**::

    ① IL GLOBALE
    popolazione                       totale  marca breve   quota   Wilson 95%     data piena
    ammessi (status != quarantined)    14303         2328   16.3%  [15.7, 16.9]          2750
    quarantinati, causa L4.1             142           31   21.8%  [15.8, 29.3]             6
    quarantinati, qualunque causa       2679         1468   54.8%  [52.9, 56.7]          1602

    ② STRATIFICATO PER MESE — la riga che disfa il globale
    mese        AMMESSI n (marca%)   QUARANT. n (marca%)   delta
    2026-05       2065 ( 39.2%)         1579 ( 85.3%)      +46.1 pt   disgiunti
    2026-06       1407 ( 19.8%)           47 ( 72.3%)      +52.6 pt   disgiunti
    2026-07       1393 ( 51.0%)           77 (  5.2%)      -45.8 pt   🔑 SEGNO INVERTITO
    2026-08       9384 (  5.6%)          964 (  8.6%)       +3.0 pt   disgiunti

🪞 **① LA MIA IPOTESI DI PARTENZA CADE.** Sospettavo che la potatura mancante facesse
cadere fatti in massa **via `L4.1`**. Fra i quarantinati con causa `L4.1` la quota e'
**21.8%**, intervallo **[15.8%, 29.3%]**, che **CONTIENE il 16.3% degli ammessi** ⇒
**non sovra-rappresentata**.

🪞 **② E CADE ANCHE LA MIA LETTURA DEL RIPIEGO.** Visto il **54.8%** contro **16.3%**
avevo pubblicato «*i quarantinati la portano tre volte piu' spesso*». **Stratificando,
quel numero e' dominato da MAGGIO**: 1579 dei 2679 quarantinati (59%) sono di maggio, e
li' la quota e' **85.3%**. A **luglio il segno si INVERTE**. E nel regime attuale —
**agosto, 9384 ammessi** — il divario e' **+3.0 punti** (8.6% contro 5.6%): disgiunto,
quindi reale, ma **piccolo**. ⇒ **Il numero da citare e' +3.0 punti, non «tre volte
tanto».**

🔑 **E resta vera una cosa che il globale diceva bene**: cade nella stessa misura anche
la data **COMPLETA** (1602 su 2679), cioe' **la forma che la potatura COPRE** ⇒ se fosse
la potatura, quella dovrebbe restare a terra. **Qualunque sia la causa del divario, non
e' `L4.1`.** Il candidato resta la **forma tabellare** dei fatti di misura (`W5-5`;
`quantity_match.py:676`, 27 falsi positivi su 28) — **nominato, non isolato**.

⇒ **PER LA DECISIONE**: il difetto della potatura e' **reale e riproducibile alla porta**
(`3b4360d7`, sei casi su sei), e sul corpus attuale la forma pesa **+3 punti** sui
quarantinati. **Cura di correttezza, non emergenza di rilascio.**

🪞 **DUE ERRORI MIEI IN QUESTO SINGOLO BANCO, e li lascio scritti perche' sono di due
specie diverse**:
  ① **ESITO scritto prima dell'esecuzione**, con numeri inventati (avevo scritto 26.6% e
     30.7%; i veri sono 16.3% e 21.8%) — **seconda volta in un'ora**. La causa non e'
     distrazione: il formato del banco tiene l'esito nel docstring e scrivendo il file di
     seguito lo compilo insieme al resto. ⇒ **Cura di processo: si scrive senza ESITO, si
     esegue, l'esito si aggiunge dopo.**
  ② **Il misuratore era rotto**: la prima stratificazione faceva `str(created_at)[:7]`, ma
     `created_at` e' un **float epoch** — raggruppava per «1788115», che mese non e'. L'ho
     visto **solo perche' lo script stampa le chiavi**. ⇒ La riga «`chiavi trovate:`» resta
     nel codice: e' il presidio che ha trovato il difetto.

SOLA LETTURA: `sqlite3` con `mode=ro`, percorso chiesto al prodotto
(`CONFIG.semantic_db`) e non all'intuito.
⚖️ PUNTI DEBOLI: ① `quarantined_by` non copre tutti i quarantinati ⇒ la riga `causa
L4.1` vale su **142** casi; ② la regex conta anche `1:2` e `1/2` ⇒ numeratore
**generoso**, il che rende «non sovra-rappresentata» piu' forte e i divari piu' deboli;
③ **settembre e' saltato** (campione < 30 in una delle due popolazioni) ⇒ il mese in
corso non entra; ④ il corpus e' scritto quasi tutto da noi, non da utenti terzi;
⑤ **non ho stratificato ANCHE per forma della source**, che e' il candidato vero: dico
dove guardare, non che sia quello.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-quanti-fatti-portano-una-marca-temporale-breve.py
"""
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path

from verimem.config import CONFIG

#: orario `20:58` oppure data senza anno `28/08` — le due forme che la potatura NON copre
MARCA = re.compile(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}/\d{1,2}\b(?!/\d)")
#: la forma che la potatura COPRE — se cade anche questa, la causa non e' la potatura
COMPLETA = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b")
#: sotto questa soglia una quota mensile non si legge
MIN_CAMPIONE = 30


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


def globale(cur):
    def prendi(dove):
        return [r[0] for r in cur.execute("select proposition from facts where " + dove)]

    gruppi = [
        ("ammessi (status != quarantined)", prendi("status is null or status != 'quarantined'")),
        ("quarantinati, causa L4.1", prendi("status = 'quarantined' and quarantined_by = 'L4.1'")),
        ("quarantinati, qualunque causa", prendi("status = 'quarantined'")),
    ]
    print("① IL GLOBALE\n")
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
        print("  %-34s %8d %10d %7.1f%% [%5.1f%%, %5.1f%%] %10d"
              % (nome, tot, breve, q, lo, hi, completa))
    tot_l41, breve_l41, _ = conta(gruppi[1][1])
    return base, tot_l41, breve_l41


def per_mese(cur):
    """⚠️ `created_at` e' un FLOAT epoch, non una stringa ISO: la prima versione di
    questo banco faceva `str(created_at)[:7]` e raggruppava per «1788115». La riga
    che stampa le chiavi non e' decorativa — e' cio' che ha trovato il difetto."""
    tab = defaultdict(lambda: {"amm": [0, 0], "qua": [0, 0]})
    for prop, status, creato in cur.execute(
            "select proposition, status, created_at from facts where created_at is not null"):
        try:
            mese = datetime.fromtimestamp(float(creato), tz=timezone.utc).strftime("%Y-%m")
        except (TypeError, ValueError, OSError):
            continue
        d = tab[mese]["qua" if status == "quarantined" else "amm"]
        d[0] += 1
        if MARCA.search(prop or ""):
            d[1] += 1

    print("\n② STRATIFICATO PER MESE\n")
    print("  chiavi trovate: %s\n" % ", ".join(sorted(tab)))
    print("  %-9s %20s %20s   %s"
          % ("mese", "AMMESSI n (marca%)", "QUARANT. n (marca%)", "delta"))
    print("  " + "-" * 76)
    concordi = discordi = saltati = 0
    for mese in sorted(tab):
        a, q = tab[mese]["amm"], tab[mese]["qua"]
        if a[0] < MIN_CAMPIONE or q[0] < MIN_CAMPIONE:
            saltati += 1
            continue
        qa, qq = 100.0 * a[1] / a[0], 100.0 * q[1] / q[0]
        lo_a, hi_a = wilson(a[1], a[0])
        lo_q, hi_q = wilson(q[1], q[0])
        disgiunti = lo_q > hi_a or lo_a > hi_q
        if qq > qa:
            concordi += 1
        else:
            discordi += 1
        print("  %-9s %8d (%5.1f%%)      %8d (%5.1f%%)   %+6.1f pt %s"
              % (mese, a[0], qa, q[0], qq, qq - qa,
                 "disgiunti" if disgiunti else "si sovrappongono"))
    return concordi, discordi, saltati


def main():
    p = Path(str(CONFIG.semantic_db))
    con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
    cur = con.cursor()
    base, tot_l41, breve_l41 = globale(cur)
    concordi, discordi, saltati = per_mese(cur)
    con.close()

    print("\n=== SINTESI ===")
    lo, hi = wilson(breve_l41, tot_l41)
    if tot_l41 and lo <= base <= hi:
        print("  🪞 ① L'IPOTESI CADE: fra i quarantinati-L4.1 la quota e' %.1f%% [%.1f%%, %.1f%%],"
              % (100.0 * breve_l41 / tot_l41, lo, hi))
        print("       che CONTIENE il %.1f%% degli ammessi ⇒ non sovra-rappresentata." % base)
    else:
        print("  🔴 ① la quota fra i quarantinati-L4.1 e' fuori dall'intervallo degli ammessi.")

    if discordi:
        print("  🪞 ② E CADE LA LETTURA DEL GLOBALE: %d mesi concordi su %d (%d saltati)."
              % (concordi, concordi + discordi, saltati))
        print("       Il segno NON e' costante ⇒ il divario globale e' in parte")
        print("       composizione temporale. Si cita il mese in corso, non il totale.")
    else:
        print("  🔴 ② il segno e' costante in tutti i mesi leggibili (%d): il divario" % concordi)
        print("       NON e' spiegato dalla composizione temporale.")


main()
