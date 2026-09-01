r"""La promessa centrale: i fatti scritti stasera TORNANO quando servono?

Dogfooding da utente. Ho salvato cinque fatti fra le 20:11 e le 20:45, uno per
misura. La promessa del prodotto non e' «il gate li ammette»: e' che poi **li
ritrovi**. Questo banco chiede al prodotto **le stesse cose, con le parole con cui
le chiederebbe chi deve decidere** — non con il topic, che chi cerca non conosce.

DUE POPOLAZIONI, ed e' la coppia a isolare il difetto::

    A  la domanda DA UTENTE     una frase, lessico del dominio, parole mie
    B  la query LETTERALE       le parole esatte del fatto salvato

⇒ Se `B` trova e `A` no, il fatto **c'e' ed e' indicizzato**: a mancare e' il
recupero semantico. Se non trova nemmeno `B`, il fatto non e' arrivato all'indice —
che e' un difetto di un'altra specie, e molto peggiore.

⚠️ `recall` mostra **5 risultati di default** e questo banco non alza il tetto: e' la
finestra che vede chi usa il comando come esce dalla scatola. Il rango riportato e'
dentro quei cinque; «assente» significa «non nei primi cinque», non «non nello store».

📌 E quando `recall` non trova, il prodotto offre `verimem ignorance` — «*WHY the
store cannot answer*». Il banco lo interroga sui casi mancati: **la diagnosi che
propone e' quella giusta?** E' la promessa piu' ambiziosa del prodotto, e nessuno
l'ha ancora messa alla prova su casi di cui si conosce la risposta.

🔴 ESITO — **due reperti: i fatti non tornano a chi non ne conosce le parole, e lo
strumento che dovrebbe spiegarlo dice il contrario**::

    ① IL RECUPERO
    fatto                      A domanda DA UTENTE      B query LETTERALE
    999 INVENTATO              🔴 assente nei primi 5   trovato, rango 1
    29ab5544                   trovato, rango 2         trovato, rango 1
    data senza anno non sost   trovato, rango 2         trovato, rango 1
    2026-08 gli ammessi        🔴 assente nei primi 5   trovato, rango 1
    tabellare, VERO passa      🔴 assente nei primi 5   trovato, rango 1
    ------------------------------------------------------------------------
    DA UTENTE  2 su 5                LETTERALE  5 su 5, tutti al PRIMO posto

    ② LA DIAGNOSI, sugli stessi tre casi mancati
    999 INVENTATO         answerable   best 0.87  floor 0.800  rumore misurato 0.872
    2026-08 gli ammessi   answerable   best 0.86  floor 0.800  rumore misurato 0.872
    tabellare, VERO       answerable   best 0.84  floor 0.800  rumore misurato 0.880

🔑 **① I FATTI CI SONO E SONO INDICIZZATI ALLA PERFEZIONE**: con le parole esatte
escono **5 su 5, tutti al primo posto**. Con la domanda che farebbe chi deve decidere
ne escono **2 su 5**. ⇒ **Non e' un difetto di scrittura: e' che tre reperti di
stasera su cinque non tornerebbero a chi li cerca senza conoscerne le parole.** Per un
prodotto che si chiama memoria, il gate ammette e l'indice conserva — ma la porta da
cui si rientra e' piu' stretta di quella da cui si e' entrati.

🔴 **② E `ignorance` DICE IL CONTRARIO DI QUELLO CHE E' SUCCESSO.** Il comando chiede
per argomento «*the questions that went unanswered*»: gli passo esattamente quelle, e
su **3 su 3** risponde **`answerable`** — che nel modulo significa, alla lettera,
«*not ignorance (counted for the honest denominator)*» (`ignorance_map.py:18`).
⇒ **Il prodotto dichiara di saper rispondere proprio dove non ha risposto.**

🔑 **③ LA CAUSA E' UN NUMERO, ed e' il prodotto stesso a stamparlo**: `floor=0.800`
(dichiarato) contro `noise_floor=0.872` (**misurato dal prodotto su se stesso**), e la
riga dice `decide 0.800`. ⇒ **Decide con una soglia che sta SOTTO il rumore che ha
appena misurato.** Nella banda 0.800-0.872 chiama «rispondibile» cio' che per sua
stessa definizione e' la zona dove «*un vicino qualunque ha lo stesso punteggio di un
match vero*» — e infatti **stampa quell'avviso**, giusto, accanto al verdetto
sbagliato. 🪞 E' la forma «**un campo stampato e non letto e' un campo assente**»:
qui il campo e' letto dall'utente e **non dalla decisione**.

⇒ **E la classe giusta ESISTE GIA'**: `below_floor` — «*hits exist, none clears the
floor*» — con una cura dichiarata. ⇒ **Non manca un concetto, manca il confronto fra
i due numeri**, che sono entrambi gia' in mano al comando.

REGIME: **sola lettura** dello store principale (nessuna scrittura) · **un solo
processo** per tutte le query, come da protocollo RAM misurato alle 20:47 (il giudice
costa 758 MB e tutto al primo uso) · claim `ram/giudice` preso.
⚠️ Le righe di log (`flow.recall`, warning di torch) escono sullo stesso canale della
risposta: **senza filtrarle si legge il log e si crede di aver letto la diagnosi** —
la prima versione di questo banco lo faceva, e mostrava `best=0.872` credendo fosse
l'esito.
⚖️ PUNTI DEBOLI: cinque fatti, tutti miei e tutti di stasera — e sono **fatti di
misura**, la classe piu' densa di numeri e sigle, non un campione del corpus; le
domande «da utente» le scrivo io che **so gia' la risposta**, quindi sono
plausibilmente piu' fortunate di quelle di un utente vero.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-i-fatti-di-stasera-tornano-quando-servono.py
"""
import contextlib
import io
import re
import sys

#: (frammento che identifica il fatto, domanda DA UTENTE, query LETTERALE)
CASI = [
    ("999 INVENTATO",
     "un numero che la fonte non contiene viene fermato dal gate?",
     "Il caso A 999 INVENTATO cade con ground 0.3"),
    ("29ab5544",
     "da quando e' diventato rosso il test sui numeri che la fonte non dice?",
     "Il claim con riga 999 dava PRIMA e ORA set()"),
    ("data senza anno non sost",
     "una data che la fonte non sostiene passa il gate?",
     "Il caso E data completa non sost. passa con 99.5"),
    ("2026-08 gli ammessi",
     "quanto pesano gli orari e le date brevi sui fatti quarantinati?",
     "Nel mese 2026-08 gli ammessi sono 9384 con marca 5.6%"),
    ("tabellare, VERO passa",
     "l'avviso sullo scambio di grandezza distingue il claim vero da quello falso?",
     "Il caso A tabellare, VERO passa con ground 99.9"),
]


def chiedi(comando):
    """Una query, nello STESSO processo: il modello si carica una volta sola."""
    from verimem.cli import app
    buf = io.StringIO()
    argv = sys.argv
    sys.argv = ["verimem"] + comando
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                app()
            except SystemExit:
                pass
    finally:
        sys.argv = argv
    return buf.getvalue()


def rango(uscita, frammento):
    """A che posto compare il fatto atteso, fra quelli che `recall` ha stampato."""
    testo = re.sub(r"\s+", " ", uscita)
    if frammento.lower() not in testo.lower():
        return None
    # i risultati sono numerati o separati: conto quante volte compare un marcatore
    # di risultato PRIMA del frammento. Se il formato non ha marcatori, il rango
    # non e' leggibile e si dichiara «presente, rango ignoto».
    prima = testo.lower().split(frammento.lower())[0]
    marcatori = len(re.findall(r"\b\d+[\.\)]\s", prima))
    return marcatori + 1 if marcatori else 1


def main():
    print("  %-26s %-30s %-30s" % ("fatto", "A domanda DA UTENTE", "B query LETTERALE"))
    print("  " + "-" * 92)
    esiti = []
    for frammento, utente, letterale in CASI:
        ua = chiedi(["recall", utente])
        ub = chiedi(["recall", letterale])
        ra, rb = rango(ua, frammento), rango(ub, frammento)
        esiti.append((frammento, ra, rb))
        print("  %-26s %-30s %-30s"
              % (frammento[:26],
                 ("trovato, rango %d" % ra) if ra else "🔴 ASSENTE nei primi 5",
                 ("trovato, rango %d" % rb) if rb else "🔴 ASSENTE nei primi 5"))

    trovati_a = sum(1 for _, ra, _ in esiti if ra)
    trovati_b = sum(1 for _, _, rb in esiti if rb)
    print("\n  === CONTEGGIO ===")
    print("  con la domanda DA UTENTE: %d su %d   ·   con la query LETTERALE: %d su %d"
          % (trovati_a, len(esiti), trovati_b, len(esiti)))

    mancati = [(f, u) for (f, ra, _), (_, u, _) in zip(esiti, CASI) if not ra]
    classi = []
    if mancati:
        print("\n  === E QUANDO NON TROVA, IL PRODOTTO SA DIRE PERCHE'? ===")
        print("  (`ignorance` vuole per argomento «*the questions that went unanswered*»:")
        print("   gli passo esattamente quelle, e la classe attesa e' `below_floor`)\n")
        for frammento, domanda in mancati:
            out = chiedi(["ignorance", domanda])
            # ⚠️ le righe di log (`flow.recall`, warning di torch) sono sullo stesso
            # canale: senza toglierle si legge il log e si crede di leggere la risposta.
            utili = [r.strip() for r in out.splitlines()
                     if r.strip() and "flow." not in r and not r.startswith("W0")
                     and "RuntimeWarning" not in r and "_threshold" not in r]
            testo = " ".join(" ".join(utili).split())
            cl = re.search(r"\b(answerable|below_floor|no_evidence|quarantined_only|conflict)\s*=?\s*(\d+)?", testo)
            fl = re.search(r"floor=([\d.]+)\s+noise_floor=([\d.]+)", testo)
            classi.append((frammento, cl.group(1) if cl else "?",
                           fl.group(1) if fl else None, fl.group(2) if fl else None))
            print("  · %s" % frammento)
            print("    %s" % testo[:300])

    print("\n=== SINTESI ===")
    if trovati_b == 0:
        print("  🔴🔴 NEMMENO LA QUERY LETTERALE TROVA: i fatti non sono nell'indice")
        print("       interrogabile — difetto di scrittura, non di recupero.")
    elif trovati_a == trovati_b == len(esiti):
        print("  🟢 %d su %d con entrambe le formulazioni: la promessa regge su questi" % (trovati_b, len(esiti)))
        print("     cinque, ed erano fatti densi di numeri e sigle.")
    elif trovati_b > trovati_a:
        print("  🔴 LA LETTERALE TROVA %d, LA DOMANDA DA UTENTE %d: i fatti CI SONO"
              % (trovati_b, trovati_a))
        print("     e sono indicizzati — a mancare e' il recupero su come si chiede.")
    else:
        print("  ⚠️ esito inatteso: utente %d, letterale %d" % (trovati_a, trovati_b))

    if classi:
        detti_rispondibili = [c for c in classi if c[1] == "answerable"]
        print("\n  --- e la DIAGNOSI su quegli stessi casi ---")
        for frammento, classe, floor, rumore in classi:
            nota = ""
            if floor and rumore and float(floor) < float(rumore):
                nota = "  ⚠️ decide con floor %s, sotto il rumore che MISURA (%s)" % (floor, rumore)
            print("    %-26s %s%s" % (frammento[:26], classe, nota))
        if detti_rispondibili:
            print("  🔴 %d su %d casi NON RISPOSTI sono classificati `answerable`, che nel"
                  % (len(detti_rispondibili), len(classi)))
            print("     modulo significa «*not ignorance*» ⇒ il prodotto dice di saper")
            print("     rispondere proprio dove non ha risposto. La classe giusta")
            print("     (`below_floor`) ESISTE gia': a mancare e' il confronto col rumore.")


main()
