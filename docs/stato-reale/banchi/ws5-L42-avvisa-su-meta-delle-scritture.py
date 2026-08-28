r"""`L4.2` avvisa su META' delle scritture, e la «grandezza» che cita e' spesso una lettera.

@ws2 mi ha passato un falso positivo trovato **usando il prodotto**, non con un
banco: claim «*il commit X modifica il file Y con 25 inserzioni*» su una source
`git show --stat` che contiene `mcp_server.py | 25 +++++` e `3 files changed, 67
insertions`. `L4.2` avvisa «*25 qui e' 'inserzioni', nella fonte 'files'*» -
aggancia il 25 alla grandezza di **un'altra riga**. Sua diagnosi: *su fonti
tabellari la grandezza e' data dalla COLONNA, non dalla parola piu' vicina nel
testo appiattito*. **La frequenza non l'aveva misurata nessuno.**

    A  il caso di @ws2, riprodotto:  AVVISA [(25.0, 'inserzioni', 'files')]  ✔

    B  sul corpus vero, 4000 fatti, sola lettura:
       con span TABELLARE               3614   90,3%
       L4.2 AVVISA                      1990   49,8%
       L4.2 avvisa SU span tabellare    1839   50,9% dei tabellari

⇒ **Un avviso su metà delle scritture.**

🪞 **RIDIMENSIONATO alle 23:45, e in favore del prodotto.** Avevo scritto che la
grandezza citata e' «**spesso**» una lettera o una preposizione, sulla base di
**quattro esempi - i primi quattro incontrati, non un campione**. Classificati
**tutti e 3339** gli avvisi (uno per valore, non per fatto)::

    parola di contenuto (dopo)                   2227   66,7%
    parola VUOTA: articolo/preposizione (dopo)    473   14,2%
    una LETTERA sola (dopo)                       302    9,0%
    parola di contenuto (prima)                   272    8,1%
    una LETTERA sola (prima)                       34    1,0%
    parola VUOTA (prima)                           31    0,9%
    ---- parola di contenuto: 2499 su 3339 = 74,8%

⇒ **La spazzatura e' un QUARTO (25,2%), non «spesso»**: tre avvisi su quattro
nominano una parola di contenuto.
⚠️ **MA «parola di contenuto» NON vuol dire «grandezza giusta»**, e il caso di
@ws2 lo dimostra: in «*25 qui e' inserzioni, nella fonte files*» la parola
`files` **e' di contenuto** ed e' comunque **la grandezza di un'altra riga**.
⇒ Quindi il 74,8% **non e' un tasso di correttezza**: e' il tasso di «*almeno
sembra una grandezza*». Il tasso vero richiede di leggere se la colonna e'
quella giusta, e **non l'ho misurato**.

I quattro esempi che mi avevano fuorviato restano veri e sono la coda del 25%::

    99.6    -> 'l'                        una lettera singola
    15134   -> 'prima del numero: su'     una preposizione
    2026    -> 'res'                      un frammento di parola

⇒ Si salda col mio primo banco su questo layer
(`ws5-L42-tace-quando-il-numero-porta-un-unita.py`): li' avevo misurato che il
vicinato e' **una parola per lato**, e che quando quella parola e' un'unita'
condivisa il layer TACE. Qui si vede il costo dall'altro lato: quando il testo
e' tabellare, quella parola e' **spazzatura**, e il layer PARLA.
⇒ ⚖️ **Ma resta un AVVISO e non blocca**, e @ws2 ha ragione a dire che e' la
cosa giusta. Il danno non e' un fatto perso: e' che **un avviso presente su
metà delle scritture, che nomina «l» o «su» come grandezza, addestra a ignorare
gli avvisi** - e fra quelli veri e quelli rumorosi non c'e' modo di distinguere
leggendo la ricevuta.

⚖️ PUNTI DEBOLI: ho misurato la **funzione** `valori_riusati_da_altro_contesto`,
**non la ricevuta**: il numero dice «quante volte la funzione ha qualcosa da
dire», non «quanti avvisi arrivano davvero al chiamante» - il gate potrebbe
filtrarne una parte. **E' esattamente il livello che stasera mi ha ribaltato
tre verdetti**, quindi lo dichiaro invece di scriverlo come se fosse la
ricevuta. E «tabellare» qui e' un'euristica grezza (>=2 newline oppure un `|`).
Dei 1990 avvisi ne ho letti **quattro**.

REGIME: build corrente · **nessun modello caricato** (funzione pura) · sola
lettura `mode=ro`, percorso da `CONFIG.semantic_db` · regime RAM rispettato.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-L42-avvisa-su-meta-delle-scritture.py
"""
import sqlite3, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.config import CONFIG
from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto as L42

# il caso di @ws2, verbatim
CLAIM_WS2 = "Il commit X modifica il file Y con 25 inserzioni."
SRC_WS2 = " verimem/mcp_server.py | 25 +++++\n 3 files changed, 67 insertions(+)\n"
r = L42(CLAIM_WS2, SRC_WS2)
print("=== A: il caso di @ws2, riprodotto ===")
print("  L4.2 dice: %s" % ("AVVISA " + str([(x.valore, x.nel_claim, x.nella_fonte) for x in r]) if r else "tace"))

print("\n=== B: quanto spesso capita sul CORPUS VERO (sola lettura, nessun modello) ===")
p = Path(str(CONFIG.semantic_db))
con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
righe = con.execute(
    "select proposition, grounding_span from facts where grounding_span is not null "
    "and length(grounding_span) > 20 and superseded_by is null "
    "order by created_at desc limit 4000").fetchall()
con.close()
tot = avvisa = tabellare = avvisa_tab = 0
esempi = []
for prop, span in righe:
    tot += 1
    tab = span.count("\n") >= 2 or "|" in span
    if tab:
        tabellare += 1
    a = L42(prop, span)
    if a:
        avvisa += 1
        if tab:
            avvisa_tab += 1
            if len(esempi) < 4:
                esempi.append((prop[:80], [(x.valore, x.nel_claim, x.nella_fonte) for x in a[:1]]))
print("  fatti esaminati                  %4d" % tot)
print("  con span TABELLARE               %4d  (%.1f%%)" % (tabellare, 100.0*tabellare/max(tot,1)))
print("  L4.2 AVVISA                      %4d  (%.1f%%)" % (avvisa, 100.0*avvisa/max(tot,1)))
print("  L4.2 avvisa SU span tabellare    %4d  (%.1f%% dei tabellari)" % (avvisa_tab, 100.0*avvisa_tab/max(tabellare,1)))
print("\n  --- esempi, da leggere a mano (l'avviso e' giusto o e' la colonna sbagliata?) ---")
for prop, det in esempi:
    print("    claim: %s" % " ".join(prop.split()))
    print("      L4.2: %s" % det)
