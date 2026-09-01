r"""Lo stesso avviso, parola per parola, per il claim VERO e per quello FALSO — e il
falso passa a 99.9.

Non l'ho cercato: e' emerso salvando i fatti di stasera. **Quattro salvataggi su
quattro** con source = output di banco hanno prodotto un `L4.2` la cui spiegazione cita
come «parola accanto» un frammento della colonna precedente o la lettera di riga::

    58   qui «(nessuna parola accanto)», nella fonte «(solo parole grammaticali accanto)»
    0.3  qui «prima del numero: ground», nella fonte «b»
    99.5 qui «(solo parole grammaticali accanto)», nella fonte «f»
    8.6  qui «delta», nella fonte «pt»

⚠️ Quattro aneddoti non sono una misura: manca una popolazione in **prosa** e manca un
caso in cui `L4.2` **deve** scattare — senza, «scatta troppo» non e' distinguibile da
«scatta».

L'INCROCIO, stessa informazione, stesso numero — **tre forme x {vero, falso}**::

                        claim CORRETTO              claim SCAMBIATO
    fonte TABELLARE     A  L4.2 non dovrebbe        C  L4.2 DEVE scattare
    fonte PROSA         B  L4.2 non dovrebbe        D  L4.2 DEVE scattare
    soggetto ADIACENTE  E  L4.2 non dovrebbe        F  L4.2 DEVE scattare

⇒ `E` ed `F` pagano il limite che questo stesso banco aveva dichiarato: li' il soggetto
e' **attaccato al numero** («*Ammessi 14304.*»), senza verbo in mezzo.

🔴🔴 ESITO — **tre coppie su tre identiche, e DUE mie letture falsificate**::

    caso                     esito    ground   layer
    A tabellare, VERO        passa      99.9   L4.2
    B prosa, VERO            passa     100.0   L4.2
    C tabellare, FALSO       passa      99.9   L4.2
    D prosa, FALSO           passa     100.0   L4.2
    E adiacente, VERO        passa      99.7   L4.2
    F adiacente, FALSO       passa      99.9   L4.2

    A: «... 14304 qui e' «(nessuna parola accanto)», nella fonte «quarantinati»»
    C: identica ad A          E: identica ad A          F: identica ad A
    B: «... 14304 qui e' «(nessuna parola accanto)», nella fonte «(solo parole
        grammaticali accanto)»»
    D: identica a B

🔴 **① L'AVVISO NON DISTINGUE IL VERO DAL FALSO.** `A` dice il vero («gli ammessi sono
14304») e `C` dice il falso (i quarantinati sono **2679**, non 14304): **ricevono la
stessa identica stringa, parola per parola**. ⇒ Un avviso che dice la stessa cosa
quando hai ragione e quando hai torto **non porta informazione**: leggerlo non aiuta a
decidere, e chi lo legge sul caso vero impara a ignorarlo — proprio prima di incontrare
quello falso.

🔴 **② E IL CLAIM FALSO PASSA**: `C` a **99.9**, `D` a **100.0**, `F` a **99.9**. E' lo
scambio di grandezza classico — prendere il numero giusto e attaccarlo all'oggetto
sbagliato — e **ne' il giudice ne' i layer lo fermano**, in **nessuna** delle tre forme.

⚠️ **MA NON E' UNA SVISTA, e lo preciso avendo letto il modulo DOPO aver consegnato
questa riga** (`vicinato_del_valore.py`): `L4.2` **avvisa invece di vetare per scelta
misurata** — «*la prima stesura faceva fallire il write, e **ha rotto un presidio verde
scritto in indipendenza** […] una cura che rompe il presidio verde di un altro non si
consegna come veto. Resta come avviso: dice che il numero e' riusato da un altro
contesto e **lascia decidere***». Come veto dava **1 falso positivo su 5** riformulati
veri, contro 7 inventati colpiti su 7. ⇒ **Che il falso entri e' un limite DICHIARATO,
non un difetto** — e per il rilascio e' **una riga di documentazione**, non una patch.

🔑 **⇒ CIRCOSCRITTO alle 21:36 da `7de4f365`**: l'avviso e' identico sul vero e sul
falso **nella forma in cui il numero SEGUE il sostantivo**, che e' quella provata qui.
Quando il numero lo **PRECEDE** («*1167 job conclusi*») `L4.2` **distingue e lo dice
bene**: «*1167 qui e' «job», nella fonte «run»*». ⇒ La cecita' e' **posizionale**, ed e'
lo stesso criterio che `vicinato_del_valore.py` dichiara. Il reperto non si annulla:
si circoscrive, e diventa azionabile (basta invertire l'ordine).

🔑 **⇒ E IL REPERTO DI QUESTO BANCO DIVENTA PIU' STRETTO E PIU' SOLIDO**: il modulo
dichiara che l'avviso serve a «**lasciar decidere**». **Un avviso identico parola per
parola sul vero e sul falso non da' l'informazione per decidere.** Il progetto e'
coerente; **e' l'attuazione del messaggio che non lo e'**, e questo in nessun commento
sta scritto.

🪞 **③ LA MIA PRIMA IPOTESI CADE: non e' la forma tabellare.** Ero partita da «*l'avviso
legge la colonna sbagliata*». `B` e `D` sono **in prosa** e si comportano uguale.

🪞 **③-bis E CADE ANCHE LA SPIEGAZIONE CHE AVEVO DATO AL POSTO SUO.** Avevo scritto: «*in
«Gli ammessi sono 14304» il soggetto non e' adiacente al numero — c'e' il verbo in mezzo
— quindi il layer non trova il contesto*». **Falsificata da `E` ed `F`**: li' il soggetto
e' **attaccato al numero** («*Ammessi 14304.*») e il layer dice **lo stesso**
«*(nessuna parola accanto)*», con la stessa identica stringa sul vero e sul falso.
⇒ **Non e' una lacuna sintattica su una costruzione particolare: il lato claim non
estrae il contesto nemmeno quando la parola e' letteralmente accanto al numero.**
🔑 E la lezione e' che la mia spiegazione l'avevo consegnata **prima di questo
controllo**, quando pagarlo e' costato tre minuti.

⚠️ **④ E sulla tabella il contesto estratto e' l'OPPOSTO del significato**: la riga e'
`ammessi (status != quarantined)  14304`, e il layer riporta «*nella fonte
«quarantinati»*» — ha preso la parola piu' vicina **dentro una parentesi di negazione**,
ignorando il `!=`. La forma tabellare non e' la causa, ma **aggiunge un errore**: da' un
contesto sbagliato invece di nessuno.

📌 **SI LEGA AL CONTROLLO POSITIVO DI @ws4** (canale, 20:00): «*il claim prende il numero
giusto e lo attacca alla grandezza sbagliata. E' esattamente W7-98, e qui il moat lo
ferma: g=2.12. E' IL CONTROLLO POSITIVO CHE MI MANCAVA: su questa popolazione il moat
NON e' cieco*». ⇒ **Qui c'e' il controesempio**: stesso tipo di scambio, `g=99.9` e
`g=100.0`, passa. **Il moat becca quello scambio su quella popolazione e non su questa**
— e chi decide sul cut deve avere tutti e due i casi, non uno solo.

⇒ **PER LA DECISIONE**: in **sei casi su sei** `L4.2` non ha distinto il vero dal falso,
e in **tre su tre** il falso e' passato. ⚠️ **Le mie prime due ipotesi sulla causa sono
cadute** («e' la tabella», «e' la distanza soggetto-numero»); la terza **non l'ho
indovinata, l'ho letta**: e' **la POSIZIONE del numero rispetto al sostantivo**, e sta
scritta in `vicinato_del_valore.py` — «*un identificativo SEGUE il suo sostantivo, una
quantita' lo PRECEDE*». In tutti e sei i casi qui sopra il numero **segue**, e il
criterio tace; invertendo l'ordine **parla, e ha ragione** (`7de4f365`).

⇒ **Quindi la domanda per il rilascio non e' piu' «dichiarare la classe non coperta»**:
la classe **e' coperta**, ma **solo in una delle due forme in cui si scrive la stessa
frase**. ⇒ Cio' che va scritto e' **quella condizione**, non un limite generale — e nel
frattempo **la riformulazione la aggira senza costo** (`4fe3e4e5`, quattro controlli).

🪞 **E la lezione di processo, la piu' cara di stasera**: ho fatto **tre giri di banco**
per cercare una causa che stava **in un commento del modulo**. Il rapporto misurato su
di me: **quattro volte su quattro**, cio' che stavo per proporre era gia' scritto li'
dentro (censimento in `8c2604f5`: 34 righe in 17 moduli).

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) · `ground_write=True` ·
porta `run_validation_gate` · daemon attivo, nessun `None` nel grounding.
⚖️ PUNTI DEBOLI: un claim per cella; la fonte tabellare e' **la mia** (l'output di un
banco), non una tabella qualunque; misuro la **stringa** dell'avviso, che puo' cambiare
senza che cambi il verdetto; e le tre forme provate non esauriscono l'italiano —
**resta non provato** un claim in cui il contesto sia una parola PIENA subito prima del
numero in una frase ordinaria (qui «Ammessi 14304.» e' un frammento, non una frase).

RIPRODUCI:  python docs/stato-reale/banchi/ws5-lo-stesso-avviso-per-il-vero-e-per-il-falso.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

#: l'output di un banco, come lo passiamo tutti i giorni con --source
TABELLARE = (
    "  popolazione                          totale marca breve    quota\n"
    "  ---------------------------------------------------------------\n"
    "  ammessi (status != quarantined)       14304       2328    16.3%\n"
    "  quarantinati, qualunque causa          2679       1468    54.8%\n")

#: le stesse identiche informazioni, in prosa
PROSA = (
    "Gli ammessi, cioe' i fatti il cui status non e' quarantined, sono 14304 e di questi "
    "2328 portano la marca breve, pari al 16.3 per cento. I quarantinati di qualunque "
    "causa sono 2679 e di questi 1468 portano la marca breve, pari al 54.8 per cento.")

VERO = "Gli ammessi sono 14304."
#: 14304 e' il numero degli AMMESSI: attribuirlo ai quarantinati (che sono 2679) e' falso
FALSO = "I quarantinati sono 14304."

CASI = [
    ("A tabellare, VERO", VERO, TABELLARE, "non dovrebbe"),
    ("B prosa, VERO", VERO, PROSA, "non dovrebbe"),
    ("C tabellare, FALSO", FALSO, TABELLARE, "DEVE"),
    ("D prosa, FALSO", FALSO, PROSA, "DEVE"),
    # E ed F pagano il limite dichiarato: qui il soggetto E' ADIACENTE al numero,
    # senza verbo in mezzo. Se il layer distingue E da F, il difetto e' circoscritto
    # («non copre la frase con il verbo interposto»); se non distingue nemmeno qui,
    # non e' una lacuna sintattica: il confronto non funziona.
    ("E adiacente, VERO", "Ammessi 14304.", TABELLARE, "non dovrebbe"),
    ("F adiacente, FALSO", "Quarantinati 14304.", TABELLARE, "DEVE"),
]


def main():
    print("  %-24s %-8s %8s  %-22s %s"
          % ("caso", "esito", "ground", "layer", "atteso su L4.2"))
    print("  " + "-" * 92)
    spieg = {}
    scatta = {}
    passa = {}
    for nome, claim, fonte, atteso in CASI:
        r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                                agent=None, source=fonte, grounding_llm=None,
                                ground_write=True)
        g = getattr(r, "grounding_score", None)
        warn = [w for w in (getattr(r, "warnings", None) or []) if isinstance(w, dict)]
        layers = [str(w.get("layer", "?")) for w in warn]
        l42 = [w for w in warn if str(w.get("layer", "")).startswith("L4.2")]
        k = nome[0]
        scatta[k] = bool(l42)
        if l42:
            spieg[k] = " ".join(str(l42[0].get("reason") or l42[0]).split())
        az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
        passa[k] = az == "persist"
        det = [x for x in layers if x not in {"L4-grounding", "L4-review", "moat", "gate"}]
        print("  %-24s %-8s %8s  %-22s %s"
              % (nome, "passa" if passa[k] else "CADE",
                 ("%.1f" % g) if g is not None else "None",
                 ", ".join(det) or "-", atteso))

    print("\n  --- IL TESTO DELL'AVVISO ---")
    for k in sorted(spieg):
        print("  %s: %s" % (k, spieg[k][:230]))

    print("\n=== SINTESI ===")
    if not (scatta.get("C") or scatta.get("D")):
        print("  ⚠️ L4.2 non scatta nemmeno sui claim SCAMBIATI: layer spento, nulla da dire.")
        return
    # ⚠️ Il confronto che conta non e' «scatta o no»: e' se il messaggio DIFFERISCE
    # fra il claim vero e quello falso. Se e' identico, l'avviso non porta informazione.
    for forma, vero, falso in (("tabellare", "A", "C"), ("prosa", "B", "D"),
                               ("adiacente", "E", "F")):
        if vero in spieg and falso in spieg:
            uguale = spieg[vero] == spieg[falso]
            print("  %s %-10s: avviso sul VERO e sul FALSO %s"
                  % ("🔴" if uguale else "🟢", forma,
                     "IDENTICO parola per parola" if uguale else "DIVERSO"))
    if any(passa.get(k) for k in ("C", "D", "F")):
        quali = [k for k in ("C", "D", "F") if passa.get(k)]
        print("  🔴🔴 E IL CLAIM FALSO PASSA (%s): lo scambio di grandezza non e' fermato"
              % ", ".join(quali))
        print("       ne' dal giudice ne' dai layer.")
    if scatta.get("A") and scatta.get("B"):
        print("  🪞 La forma tabellare NON e' la causa: succede anche in prosa.")
    if spieg.get("E") == spieg.get("F") and "E" in spieg:
        print("  🪞 E nemmeno la distanza soggetto-numero: con il soggetto ATTACCATO al")
        print("     numero l'avviso e' ancora identico ⇒ il lato claim non estrae il")
        print("     contesto in nessuna delle tre forme.")


main()
