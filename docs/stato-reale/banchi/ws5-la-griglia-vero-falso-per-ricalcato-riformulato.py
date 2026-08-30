r"""LA GRIGLIA: decide il RICALCO della fonte o decide la VERITA' del claim?

Completa la griglia che @ws2 ha lasciato aperta alle 21:00 di ieri (W2-74):
«*vero x falso  per  ricalcato x riformulato = quattro celle. Chi la completa ha
il quadro intero, e sarebbe il dato piu' forte del report su C2*».

DUE MISURE ESISTENTI, ognuna con META' della griglia:
    W2-64 (@ws2)   claim VERO: ricalcando **100.0**, riformulando **3.5**
                   ⇒ ha la colonna «vero», e nessun falso
    cella 13 (mia) claim FALSO e ricalcato: entra a **99.1 senza alcun layer**
                   ⇒ ha meta' della colonna «falso», e nessun vero

⚠️⚠️ **CONFLITTO DI INTERESSE, DICHIARATO**: @ws2 ha scritto che preferiva la
facesse **chi non ha gia' una delle due meta'**, perche' «*io ho un'ipotesi e
questo mi rende il misuratore peggiore*». **Io ho l'altra meta', quindi ho lo
stesso difetto.** La prendo lo stesso (quindici ore, nessuna l'ha presa) con
questa mitigazione: **la predizione e' stata pubblicata sul canale PRIMA di
eseguire il banco** (messaggio delle 12:33), ed e' questa:

    vero  + ricalcato    → PASSA        vero  + riformulato  → CADE
    falso + ricalcato    → PASSA        falso + riformulato  → CADE
    ⇒ tesi predetta: DECIDE IL RICALCO, NON LA VERITA'

🎯 **La cella che decide e' `falso+ricalcato`**: se passa su una popolazione
vera, il claim centrale di C2 - «*un fatto che la fonte non sostiene viene
quarantinato*» - cede **per costruzione**, non come caso limite.
⚠️ **E l'esito che mi smentirebbe**: se `vero+ricalcato` e `falso+ricalcato` si
comportassero **diversamente**, allora il gate **sta guardando la verita'** e la
tesi mia e di @ws2 e' sbagliata. E' l'esito che rende il banco utile.

IL DISEGNO - due assi ortogonali, cinque fonti::

    ricalcato    riusa le PAROLE della fonte
    riformulato  stesse informazioni, parole diverse
    vero         quello che la fonte dice
    falso        **un dato cambiato** (un numero), il resto identico

⚠️ La cifra falsa e' scritta **in cifre** in tutte le celle: scriverla a parole
introdurrebbe il buco `numerale-a-parole` che ho gia' misurato (l'estrattore non
li vede) e confonderebbe due difetti.
⚠️ **POPOLAZIONE DI CONTROLLO**: le stesse cinque fonti su cui ho gia' verificato
che il claim vero passa **5 volte su 5** - se una fonte rifiutasse tutto, le sue
quattro celle non direbbero niente.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) da `trap` ·
`ground_write=True` · porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: fonti e riformulazioni **mie** - «riformulato» e' un giudizio
mio, e una riformulazione piu' aggressiva darebbe numeri diversi; il falso e'
sempre **una cifra cambiata**, quindi la griglia parla di quella classe di
falsita' e non di tutte.

🔴🔴 ESITO - **LA MIA PREDIZIONE E' FALSIFICATA. Decide la VERITA', non il
ricalco - e la cella che doveva far cedere C2 e' la meglio difesa di tutte.**::

                        ricalcato    riformulato
          vero          5/5          4/5
          falso         0/5          2/5

    passati per FORMA:    ricalcato 5   riformulato 6   differenza 1
    passati per VERITA':  vero      9   falso       2   differenza 7

    collaudo   falso+ricalc  CADE  0.4  L4.1     fornitura falso+ricalc CADE 0.7 L4.1
    delibera   falso+ricalc  CADE  0.6  -        pagamento falso+ricalc CADE 0.8 L4.1
    pratica    falso+ricalc  CADE  0.5  L4.1

**Avevo predetto `falso+ricalcato → PASSA` e ho scritto che se fosse passato
«*il claim centrale di C2 cederebbe per costruzione*». CADE 5 volte su 5**, con
punteggi fra 0.4 e 0.8 e `L4.1` che parla in 4 casi su 5. ⇒ **E' la cella meglio
difesa dell'intera griglia**, ed e' l'opposto di cio' che io e @ws2 ci
aspettavamo.
⇒ L'asse che il gate guarda e' **la verita'** (differenza 7), non la forma
(differenza 1). **Su questa popolazione il prodotto fa quello che promette.**

🪞 **E LA PREDIZIONE ERA PUBBLICA PRIMA DEL BANCO** (canale, messaggio
`2878f7c9` delle 12:33), scritta cosi': «*tesi predetta: DECIDE IL RICALCO, NON
LA VERITA'*». La dichiaro falsificata senza attenuanti. ⚠️ Ed e' esattamente il
motivo per cui @ws2 aveva scritto che, avendo un'ipotesi, era «*il misuratore
peggiore*»: **avevo la stessa ipotesi e lo stesso difetto, e il banco mi ha
smentita.**

🔑 **MA LE DUE MISURE NON SI CONTRADDICONO: DELIMITANO IL DOMINIO.** La mia
cella 13 (falso ricalcato, **entrato a 99.1 senza layer**) era su una **licenza
reale** - fonte lunga. Qui le fonti sono **corte e costruite da me**, e lo
stesso tipo di falso cade sempre. ⇒ **La variabile non e' il ricalco: e' la
FONTE.**
⇒ Si salda con due misure di altre: **W2-70** (@ws2: oltre ~900 caratteri il
gate non separa le popolazioni) e **W7-11** (@ws4: 160 caratteri di
pseudo-parole aprono la porta). **Tre vie diverse indicano la stessa
variabile**, e non e' quella che io e @ws2 avevamo scritto.
📌 **La griglia che chiude davvero la questione e' questa stessa, su fonti
LUNGHE E REALI.** Questo banco dice dove il prodotto tiene; quello direbbe dove
cede.

📐 **Il dato secondario, che regge e vale**: `pratica vero+riform` **CADE a
96.7** con `L1.13, L4.2, L4-relazione`, e `pagamento vero+riform` passa ma con
`L4.2` che parla. ⇒ **Un vero su cinque cade se riformulato, e cade per i
LAYER, non per il giudice** (96.7 vuol dire che il giudice lo sostiene). E'
la direzione di @ws2 (riformulare costa) **ma molto piu' debole del suo 3.5**:
1 su 5, non il crollo.

REGIME: build corrente · store TEMPORANEO da `trap` · `ground_write=True` ·
porta `run_validation_gate`.
⚖️ PUNTI DEBOLI: **fonti corte e mie** - ed e' il limite che il risultato stesso
indica come decisivo; «riformulato» e' un giudizio mio; il falso e' sempre **una
cifra cambiata**, quindi la griglia parla di quella classe di falsita' e non di
tutte - e proprio `L4.1` (che confronta i valori) e' il layer che la prende.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-la-griglia-vero-falso-per-ricalcato-riformulato.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

NON_DETERMINISTICI = {"L4-grounding", "L4-review", "moat", "gate"}

# (nome, fonte, vero-ricalcato, vero-riformulato, falso-ricalcato, falso-riformulato)
CASI = [
    ("collaudo",
     "Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo "
     "e la linea e' stata approvata dalla commissione.",
     "Il collaudo della linea 3 si e' concluso il 12 marzo con esito positivo.",
     "La verifica tecnica della terza linea e' terminata bene il 12 marzo.",
     "Il collaudo della linea 7 si e' concluso il 12 marzo con esito positivo.",
     "La verifica tecnica della settima linea e' terminata bene il 12 marzo."),
    ("fornitura",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile e la bolla "
     "4471 e' stata registrata senza riserve.",
     "La fornitura di 200 unita' e' entrata in magazzino il 5 aprile.",
     "Duecento pezzi sono arrivati al deposito il 5 aprile.",
     "La fornitura di 500 unita' e' entrata in magazzino il 5 aprile.",
     "Cinquecento pezzi sono arrivati al deposito il 5 aprile."),
    ("delibera",
     "Il consiglio si e' riunito il 9 maggio e ha deliberato all'unanimita' "
     "sul punto tre dell'ordine del giorno.",
     "Il consiglio ha deliberato all'unanimita' sul punto tre il 9 maggio.",
     "L'organo collegiale ha votato compatto il terzo argomento il 9 maggio.",
     "Il consiglio ha deliberato all'unanimita' sul punto otto il 9 maggio.",
     "L'organo collegiale ha votato compatto l'ottavo argomento il 9 maggio."),
    ("pagamento",
     "Il pagamento della fattura 118 e' stato eseguito il 20 giugno con bonifico "
     "e l'importo di 4300 euro risulta accreditato al fornitore.",
     "Il pagamento della fattura 118 di 4300 euro e' stato eseguito il 20 giugno.",
     "Al fornitore sono arrivati 4300 euro il 20 giugno per la fattura 118.",
     "Il pagamento della fattura 118 di 9700 euro e' stato eseguito il 20 giugno.",
     "Al fornitore sono arrivati 9700 euro il 20 giugno per la fattura 118."),
    ("pratica",
     "La pratica 88/2026 e' stata istruita e definita dall'ufficio il 14 luglio, "
     "con provvedimento favorevole.",
     "La pratica 88/2026 e' stata definita dall'ufficio il 14 luglio.",
     "Il fascicolo numero 88 del 2026 e' stato chiuso dagli uffici il 14 luglio.",
     "La pratica 44/2026 e' stata definita dall'ufficio il 14 luglio.",
     "Il fascicolo numero 44 del 2026 e' stato chiuso dagli uffici il 14 luglio."),
]


def _gate(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") for w in (getattr(r, "warnings", None) or [])
          if isinstance(w, dict)]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az == "persist", g, [x for x in ws if x not in NON_DETERMINISTICI]


def main():
    print("  %-11s %-22s %-8s %8s  %s"
          % ("fonte", "cella", "esito", "ground", "layer"))
    print("  " + "-" * 76)
    # conta [passati, totale] per cella della griglia
    g = {k: [0, 0] for k in ("vero+ricalc", "vero+riform", "falso+ricalc", "falso+riform")}
    for nome, fonte, vr, vf, fr, ff in CASI:
        for etichetta, claim in (("vero+ricalc", vr), ("vero+riform", vf),
                                 ("falso+ricalc", fr), ("falso+riform", ff)):
            passa, sc, det = _gate(claim, fonte)
            g[etichetta][1] += 1
            if passa:
                g[etichetta][0] += 1
            print("  %-11s %-22s %-8s %8s  %s"
                  % (nome, etichetta, "passa" if passa else "CADE",
                     ("%.1f" % sc) if sc is not None else "None",
                     ", ".join(det) or "-"))
        print("  " + "-" * 76)

    print("=== LA GRIGLIA (quanti PASSANO su quante celle) ===\n")
    print("                    ricalcato        riformulato")
    print("      vero          %-16s %s"
          % ("%d/%d" % tuple(g["vero+ricalc"]), "%d/%d" % tuple(g["vero+riform"])))
    print("      falso         %-16s %s"
          % ("%d/%d" % tuple(g["falso+ricalc"]), "%d/%d" % tuple(g["falso+riform"])))

    ric = g["vero+ricalc"][0] + g["falso+ricalc"][0]
    rif = g["vero+riform"][0] + g["falso+riform"][0]
    ver = g["vero+ricalc"][0] + g["vero+riform"][0]
    fal = g["falso+ricalc"][0] + g["falso+riform"][0]
    print("\n  passati per FORMA:    ricalcato %d   riformulato %d   (differenza %d)"
          % (ric, rif, abs(ric - rif)))
    print("  passati per VERITA':  vero      %d   falso       %d   (differenza %d)"
          % (ver, fal, abs(ver - fal)))
    print("\n  ⚠️ L'asse con la differenza PIU' GRANDE e' quello che il gate")
    print("     sta davvero guardando. La predizione pubblicata prima del banco")
    print("     era: decide il RICALCO, non la VERITA'.")
    print("  🎯 E la cella che decide e' falso+ricalcato: se passa, il claim")
    print("     centrale di C2 cede per costruzione.")


main()
