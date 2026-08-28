r"""La domanda «quante finiscono in quarantena» NON e' rispondibile - e il perche' e' il reperto.

Avevo messo in coda: «*delle 937 segnalazioni di `L4.2` che agganciano un'altra
riga, quante finiscono in QUARANTENA invece che in avviso? E' LA domanda che
cambia la gravita' del trittico*». **Non e' calcolabile dai dati che il prodotto
conserva**, e provarlo vale piu' del numero che cercavo::

    quarantinati totali                        2399
    ... con `quarantined_by` valorizzato        490   20,4%

    chi ha quarantinato, fra quelli registrati:
       moat 315 · L4.1 76 · gate 55 · L4-review 31 · L3-coexistence 10 · L1 2 · store-screen 1

🔴 **`L4.2` NON COMPARE MAI FRA I DECISORI REGISTRATI: zero su 490.** Eppure il
fatto perso il 28/08 a mezzanotte aveva `layers=['L4.1','L4.2']` e
`status=quarantined`: **`L4.2` era li' e ha concorso, ma nel registro non lascia
traccia col proprio nome.** ⇒ Chi cerca l'impatto di `L4.2` interrogando
`quarantined_by` **trova ZERO e conclude che e' innocuo**.
📌 E' la riga 56 di @ws6 in forma acuta: non e' solo che il corpus non conserva
*chi* ha deciso - **conserva UN nome quando i decisori sono due**, e sempre lo
stesso.

🔴 **71 QUARANTINATI CON `L4.1` NELLA FIRMA HANNO IL GIUDICE SOPRA 90** (su 76).
E' il «muro a 99» di @ws6 con la firma **leggibile** invece che anonima: casi in
cui un layer deterministico scavalca un giudice convinto. Di quei 76, in **11**
la grandezza citata sta su un'**altra riga** - il difetto di @ws2.

⚖️ **PERCHE' IL TASSO NON E' CALCOLABILE**: `quarantined_by` e' valorizzato nel
**20,4%**. Gli 11 e i 71 sono **minimi su una popolazione nota a un quinto**; i
1909 senza firma potrebbero contenerne molti altri o nessuno, e **non c'e' modo
di saperlo dai dati conservati**. ⇒ **Non pubblico un tasso: pubblico che il
tasso non e' calcolabile.** E' la riga 58 di @ws6 («*il prodotto documenta cio'
che puo' annullare e non documenta cio' che decide*») vista dal lato di chi
voleva usare quei dati per una misura.

REGIME: build corrente · **nessun modello caricato** · sola lettura `mode=ro`,
percorso da `CONFIG.semantic_db`.
⚖️ ALTRO LIMITE: il ricalcolo di «altra riga» lo faccio con `L4.2` **oggi** su
span salvati **ieri e prima**; se il layer e' cambiato nel frattempo, quel
numero misura il codice corrente su dati vecchi - il che va bene per la
frequenza, non per attribuire la quarantena storica.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-il-tasso-non-e-calcolabile-L42-non-firma-mai.py
"""
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.config import CONFIG
from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto as L42

p = Path(str(CONFIG.semantic_db))
con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
tot_q = con.execute("select count(*) from facts where status='quarantined'").fetchone()[0]
con_by = con.execute("select count(*) from facts where status='quarantined' and quarantined_by is not null and quarantined_by<>''").fetchone()[0]
print("  quarantinati totali                      %6d" % tot_q)
print("  ... con quarantined_by valorizzato       %6d  (%.1f%%)" % (con_by, 100.0*con_by/max(tot_q,1)))
righe = con.execute(
    "select quarantined_by, count(*) from facts where status='quarantined' "
    "and quarantined_by is not null and quarantined_by<>'' group by 1 order by 2 desc limit 12").fetchall()
print("  --- chi ha quarantinato, fra quelli registrati ---")
for k, v in righe:
    print("     %-34s %5d" % (str(k)[:34], v))
# i quarantinati che nominano L4.2 o L4.1, e se la grandezza sta su un'altra riga
q = con.execute(
    "select proposition, grounding_span, quarantined_by, grounding_score from facts "
    "where status='quarantined' and grounding_span is not null and length(grounding_span)>20 "
    "and (quarantined_by like '%L4.2%' or quarantined_by like '%L4.1%') limit 4000").fetchall()
con.close()
print("\n  quarantinati con L4.1/L4.2 nella firma   %6d" % len(q))
alta = sum(1 for _pr, _sp, _by, g in q if (g or 0) >= 90)
print("  ... di cui col GIUDICE sopra 90          %6d  <== il giudice li riteneva sostenuti" % alta)
n_altra = 0
for prop, span, by, g in q:
    if "\n" not in span:
        continue
    for x in (L42(prop, span) or []):
        w = (x.nella_fonte or "").replace("prima del numero:", "").strip().split()
        if not w:
            continue
        import re as _r
        intero = int(x.valore) if float(x.valore).is_integer() else x.valore
        pat = _r.compile(r"(?<![\d.,])%s(?![\d.,])" % _r.escape(str(intero)))
        rr = [r for r in span.splitlines() if pat.search(r)]
        if rr and not any(w[0].lower() in r.lower() for r in rr):
            n_altra += 1
            break
print("  ... e la grandezza sta su un'ALTRA RIGA  %6d" % n_altra)
