r"""Due sinonimi a 78 punti: e' una legge o era quella fonte?

Paga il limite che ho dichiarato io consegnando il reperto venti minuti fa:
«*una fonte sola - la coppia sinonima andrebbe rifatta su altre fonti prima di
chiamarla una legge*».

Il reperto da mettere alla prova: su una fonte che dice «*il collaudo si e'
concluso... approvato*», il claim con `rinviato` e' **fermato a 15.67** e quello
con `rimandato` e' **ammesso a 93.74** - **78 punti fra due sinonimi**, entrambi
falsi allo stesso modo.

⚠️ **E LA MISURA GIUSTA NON E' QUELLA COPPIA: sono TUTTE le coppie.** Guardando
i dati di quel banco, tre altre coppie sinonime **non divergono affatto**
(`annullato` 0.77 / `revocato` 1.16 · `respinto` 0.54 / `rifiutato` 0.62 ·
`bloccato` 1.41 / `interrotto` 8.06). ⇒ Il fenomeno **non e' «i sinonimi
divergono»**: e' che **una coppia su quattro** diverge, e quando lo fa il salto
e' enorme. Questo banco misura quella frazione **su cinque fonti diverse**.

    per ogni fonte:  4 coppie di sinonimi, entrambi i membri FALSI sulla fonte
    diverge = i due membri hanno ESITO diverso (uno passa, l'altro no)

⚠️ **POPOLAZIONE DI CONTROLLO**: su ogni fonte c'e' anche **un claim VERO**. Se
su una fonte cadesse anche il vero, quella fonte non direbbe niente sui falsi -
il gate starebbe rifiutando tutto, e le coppie sarebbero «concordi» per il
motivo sbagliato.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: le cinque fonti e le quattro coppie sono **mie**; «sinonimi»
e' un giudizio mio (in italiano `rinviare`/`rimandare` sono intercambiabili in
questo contesto, ma un linguista potrebbe distinguerli); guardo l'**esito**,
non il punteggio, perche' e' l'esito che l'utente vede.

ESITO - **non e' quella fonte, ma non e' nemmeno una legge: 3 divergenze su 20
celle, e NON appartengono a una parola**::

    fonte       coppia                   esiti                     verdetto
    collaudo    rinviato / rimandato     ferm 15.7  |  PASSA 93.7  🔴 DIVERGONO
    consegna    rinviato / rimandato     PASSA 99.9 |  PASSA 99.7  ✔ concordi
    riunione    rinviato / rimandato     PASSA 99.2 |  PASSA 99.2  ✔ concordi
    riunione    bloccato / interrotto    PASSA 99.6 |  ferm 1.4    🔴 DIVERGONO
    pagamento   rinviato / rimandato     ferm 1.9   |  ferm 6.5    ✔ concordi
    pratica     rinviato / rimandato     ferm 40.8  |  PASSA 99.8  🔴 DIVERGONO
    (le altre 14 celle: concordi, tutte fermate sotto 8.1)
    CONTROLLO: il claim VERO passa su 5 fonti su 5.

🔑 **IL REPERTO CAMBIA FORMA, E DIVENTA PIU' GENERALE.** Ieri avevo consegnato
«*due sinonimi a 78 punti*» come un fatto su **una coppia di parole**. Non lo e':

① **`rinviato`/`rimandato` diverge su 2 fonti su 5** - quindi non era «quella
   fonte», ma **non e' una proprieta' della coppia**: su `pagamento` sono
   fermati entrambi, su `consegna` e `riunione` passano entrambi.
② **DIVERGE ANCHE UNA COPPIA DI CONTROLLO**: `bloccato`/`interrotto`, che sulla
   prima fonte erano concordi (1.4 e 8.1), su `riunione` fanno **99.6 contro
   1.4 - 98 punti**.
⇒ **Non esiste una parola cattiva: esiste instabilita' fra sinonimi**, e tocca
**coppie diverse su fonti diverse**. Chi cercasse la cura in una lista di
parole non troverebbe niente da mettere in lista.

🪞 **E DICHIARO UN DIFETTO DEL MIO DISEGNO, che vale su tre fonti su cinque.**
Le mie frasi-claim **non hanno lo stesso soggetto della fonte** ovunque:

    collaudo    fonte «il collaudo della linea 3»    claim «il collaudo...»   IDENTICO
    pagamento   fonte «il pagamento della fattura»   claim «il pagamento...»  IDENTICO
    consegna    fonte «la fornitura»                 claim «l'ordine di...»   diverso
    riunione    fonte «il consiglio ha deliberato»   claim «il punto tre»     diverso
    pratica     fonte «la pratica e' stata definita» claim «il provvedimento» diverso

⇒ Sulle tre fonti a soggetto diverso, un «passa» puo' essere **il gate che non
riconosce di cosa si parla**, non il gate che sbaglia sulla contraddizione.
**Le fonti pulite sono due**, e li' la divergenza e' **1 su 2**: esattamente
com'e' finita ieri sul banco delle coppie. Sostengo 1 su 2, non 3 su 20.

✅ **MA IL CONFRONTO DENTRO UNA COPPIA E' IMMUNE A QUEL DIFETTO**, ed e' la
parte che regge: i due membri di una coppia condividono **tutto** - fonte,
frase, soggetto, grado di aderenza - e differiscono **per una parola**. ⇒ Che
`bloccato` prenda 99.6 e `interrotto` 1.4 sulla **stessa identica frase** non
dipende da come ho scritto il soggetto: **e' il giudice che cambia di 98 punti
per un sinonimo.**

📌 Rafforza @ws3 (`c466d298`, il giudice decide e non gradua): qui il salto e'
fra due parole che significano la stessa cosa, e cade **da una parte all'altra
della bimodalita'**, mai in mezzo.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: cinque fonti e quattro coppie **mie**; **tre fonti su cinque
hanno il soggetto disallineato** (sopra); «sinonimi» e' un giudizio mio;
guardo l'**esito**, non il punteggio.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-i-sinonimi-divergono-su-quante-fonti.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

# (nome, fonte, frase col %s, claim VERO di controllo)
FONTI = [
    ("collaudo",
     "Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo "
     "e la linea e' stata approvata dalla commissione.",
     "Il collaudo della linea 3 e' stato %s il 12 marzo.",
     "Il collaudo della linea 3 si e' concluso il 12 marzo."),
    ("consegna",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile e la bolla "
     "4471 e' stata registrata senza riserve.",
     "L'ordine di fornitura e' stato %s il 5 aprile.",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile."),
    ("riunione",
     "Il consiglio si e' riunito il 9 maggio e ha deliberato all'unanimita' "
     "sul punto tre dell'ordine del giorno.",
     "Il punto tre dell'ordine del giorno e' stato %s il 9 maggio.",
     "Il consiglio si e' riunito il 9 maggio."),
    ("pagamento",
     "Il pagamento della fattura 118 e' stato eseguito il 20 giugno con bonifico "
     "e l'importo risulta accreditato al fornitore.",
     "Il pagamento della fattura 118 e' stato %s il 20 giugno.",
     "Il pagamento della fattura 118 e' stato eseguito il 20 giugno."),
    ("pratica",
     "La pratica 88/2026 e' stata istruita e definita dall'ufficio il 14 luglio, "
     "con provvedimento favorevole.",
     "Il provvedimento sulla pratica 88/2026 e' stato %s il 14 luglio.",
     "La pratica 88/2026 e' stata definita dall'ufficio il 14 luglio."),
]

COPPIE = [("rinviato", "rimandato"), ("annullato", "revocato"),
          ("respinto", "rifiutato"), ("bloccato", "interrotto")]


def _cade(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    g = getattr(r, "grounding_score", None)
    return az != "persist", g


def main():
    print("  %-11s %-9s %-24s %-24s %s"
          % ("fonte", "controllo", "coppia", "esiti", "verdetto"))
    print("  " + "-" * 92)
    divergenti = {}
    fonti_valide = 0
    for nome, fonte, frase, vero in FONTI:
        cade_vero, gv = _cade(vero, fonte)
        ctrl = "🔴 cade" if cade_vero else "🟢 ok"
        if not cade_vero:
            fonti_valide += 1
        for i, (a, b) in enumerate(COPPIE):
            ca, ga = _cade(frase % a, fonte)
            cb, gb = _cade(frase % b, fonte)
            div = (ca != cb)
            if div:
                divergenti[(a, b)] = divergenti.get((a, b), 0) + 1
            print("  %-11s %-9s %-24s %-24s %s"
                  % (nome if i == 0 else "", ctrl if i == 0 else "",
                     "%s / %s" % (a, b),
                     "%s %.1f  |  %s %.1f" % ("ferm" if ca else "PASSA", ga or -1,
                                              "ferm" if cb else "PASSA", gb or -1),
                     "🔴 DIVERGONO" if div else "✔ concordi"))
        print("  " + "-" * 92)

    print("=== SINTESI ===")
    print("  fonti con il controllo valido   %d/%d" % (fonti_valide, len(FONTI)))
    print("  celle coppia x fonte            %d" % (len(COPPIE) * len(FONTI)))
    tot = sum(divergenti.values())
    print("  🔴 coppie che DIVERGONO         %d" % tot)
    for (a, b), n in sorted(divergenti.items(), key=lambda kv: -kv[1]):
        print("      %-24s su %d fonti su %d" % ("%s / %s" % (a, b), n, len(FONTI)))
    if not divergenti:
        print("      nessuna: il reperto era di QUELLA fonte")
    print("\n  ⚠️ Se il controllo cade su una fonte, quella riga non dice niente")
    print("     sui falsi: il gate stava rifiutando tutto.")


main()
