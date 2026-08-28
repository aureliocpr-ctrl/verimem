r"""`L4.2`: **un avviso su quattro cita la grandezza di un'ALTRA RIGA** (28,7%).

Chiude il numero che avevo dichiarato non misurato. Nel banco precedente
(`ws5-L42-avvisa-su-meta-delle-scritture.py`) avevo classificato i 3339 avvisi e
trovato che il **74,8%** nomina una «parola di contenuto» - **avvertendo che non
e' un tasso di correttezza**, perche' nel caso di @ws2 («*25 qui e' inserzioni,
nella fonte files*») la parola `files` **e' di contenuto** ed e' comunque la
grandezza di **un'altra riga**. Qui quel «quanto» c'e'::

    avvisi su span MULTILINEA                 3264
    la grandezza citata e' sulla STESSA riga   2327   71,3%
    ... su un'ALTRA riga                        937   28,7%   <- il caso di @ws2
    indecidibile                                  0    0,0%

⇒ **Il difetto che @ws2 ha trovato usando il prodotto vale 937 avvisi su 3264.**
Non e' un caso limite: e' **un avviso su quattro** fra quelli su fonte
multilinea - e le nostre source sono multilinea per costruzione (`git --stat`,
`pytest`, `sqlite`, i nostri stessi referti).

🔑 E GLI ESEMPI DICONO QUALCOSA DI PEGGIO di «prende la colonna sbagliata»::

    valore 4000   claim dice 'fatti' · fonte dice 'con'
        ma la riga col valore e':  «fatti esaminati                  4000»

**La grandezza giusta e' li', sulla stessa riga** - `fatti` - e `L4.2` va a
pescare `con` da un'altra. Su una riga allineata a colonne il token adiacente
nel testo appiattito e' spazio o punteggiatura, e il vicinato «una parola per
lato» scavalca la riga.
📌 Nota di dogfooding: **il campione include i miei stessi referti** (`fatti
esaminati 4000` e' l'output di un mio banco). Il prodotto sta giudicando le
nostre misure, e su quelle sbaglia con la stessa frequenza.

⚖️ PUNTI DEBOLI: **«stessa riga» non garantisce «grandezza giusta»** - una riga
puo' contenere due colonne e il layer puo' prendere quella sbagliata restando
sulla riga. ⇒ **28,7% e' un MINIMO**, non il tasso di errore. E qui misuro la
**funzione**, non la ricevuta (il gate potrebbe filtrare parte degli avvisi):
e' la distinzione che stasera mi ha ribaltato tre verdetti, quindi la dichiaro.
Restano **avvisi** e non bloccano.

REGIME: build corrente · **nessun modello caricato** · sola lettura `mode=ro`,
percorso da `CONFIG.semantic_db` · regime RAM rispettato.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-L42-un-avviso-su-quattro-cita-la-riga-sbagliata.py
"""
import re, sqlite3, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.config import CONFIG
from verimem.vicinato_del_valore import valori_riusati_da_altro_contesto as L42

def righe_col_valore(span, v):
    """le righe dello span che contengono il valore."""
    intero = int(v) if float(v).is_integer() else v
    pat = re.compile(r"(?<![\d.,])%s(?![\d.,])" % re.escape(str(intero)))
    return [r for r in span.splitlines() if pat.search(r)]

def stessa_riga(span, v, parola):
    """la parola citata compare su una riga che contiene anche il valore?"""
    p = (parola or "").replace("prima del numero:", "").strip().split()
    if not p:
        return None
    w = p[0].lower()
    rr = righe_col_valore(span, v)
    if not rr:
        return None
    return any(w in r.lower() for r in rr)

p = Path(str(CONFIG.semantic_db))
con = sqlite3.connect(p.as_uri() + "?mode=ro", uri=True)
righe = con.execute(
    "select proposition, grounding_span from facts where grounding_span is not null "
    "and length(grounding_span) > 20 and superseded_by is null "
    "order by created_at desc limit 4000").fetchall()
con.close()

tot = stessa = altra = indecidibile = 0
esempi = []
for prop, span in righe:
    if "\n" not in span:
        continue                      # solo span MULTILINEA: e' li' che la colonna conta
    for x in (L42(prop, span) or []):
        tot += 1
        s = stessa_riga(span, x.valore, x.nella_fonte)
        if s is None:
            indecidibile += 1
        elif s:
            stessa += 1
        else:
            altra += 1
            if len(esempi) < 3:
                esempi.append((x.valore, x.nel_claim, x.nella_fonte,
                               (righe_col_valore(span, x.valore) or [""])[0][:70]))
print("  avvisi su span MULTILINEA               %5d" % tot)
print("  la grandezza citata e' sulla STESSA riga %5d  %5.1f%%" % (stessa, 100.0*stessa/max(tot,1)))
print("  ... su un'ALTRA riga                     %5d  %5.1f%%  <== il caso di @ws2" % (altra, 100.0*altra/max(tot,1)))
print("  indecidibile (valore non trovato a riga) %5d  %5.1f%%" % (indecidibile, 100.0*indecidibile/max(tot,1)))
print("\n  --- esempi di aggancio a un'ALTRA riga ---")
for v, nc, nf, riga in esempi:
    print("    valore %-10s claim dice '%s' · fonte dice '%s'" % (v, nc, nf))
    print("      ma la riga col valore e': %s" % riga.strip())
