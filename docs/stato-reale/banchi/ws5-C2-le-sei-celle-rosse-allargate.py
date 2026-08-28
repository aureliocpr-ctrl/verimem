r"""C2 - le SEI celle rosse allargate a quattro casi, piu' l'end-to-end di «Article N».

Nel primo referto C2 (`ws5-C2-le-classi-core-in-italiano-e-inglese.py`) avevo
dichiarato il limite: **due casi per classe e lingua**, e che una cella rossa su
due casi non e' una classe bucata, sono due casi bucati. Questo banco paga quel
debito **sulle sole celle rosse** - le difese restano un limite dichiarato,
perche' aggiungere casi a una cella verde non la rende piu' verde.

LE SEI ROSSE, quattro casi FALSI ciascuna (devono essere fermati) e due VERI
(devono passare, altrimenti la classe non e' bucata: e' spenta):
    cifra-riusata IT · omissione IT · omissione EN
    numerale-a-parole IT · numerale-a-parole EN · unita-cambiata IT

PIU' UN BLOCCO A PARTE - l'END-TO-END del rilievo che ho dato a @ws3 sulla sua
cura «Art. 3» (`29ab5544`) e che ho misurato solo sull'ESTRATTORE:

    'art. 3 del contratto'       valori []            potato ['3']   <- cura attiva
    'Article 3 of the contract'  valori [('', 3.0)]   potato []      <- non riconosciuta

Che il numero entri come quantita' non prova ancora che un claim inventato
venga AMMESSO: **il livello a cui misuri decide il verdetto**, e li' era il
livello della funzione. Qui e' la porta.

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`) rimosso da un
`trap`, non in coda al comando - e' cosi' che se ne sono accumulati 232 stasera:
quando un comando va in timeout prima della `rm`, lo store resta ·
`ground_write=True`.

ESITO A - allargando, **UNA CELLA ROSSA SU SEI NON ERA BUCATA**.

    cifra-riusata       IT   falsi passati 1/4  ·  veri salvi 2/2  -> i due casi NON generalizzano
    omissione           IT   falsi passati 3/4  ·  veri salvi 1/2
    omissione           EN   falsi passati 3/4  ·  veri salvi 1/2
    numerale-a-parole   IT   falsi passati 3/4  ·  veri salvi 1/2
    numerale-a-parole   EN   falsi passati 4/4  ·  veri salvi 2/2  -> BUCATA su tutti
    unita-cambiata      IT   falsi passati 3/4  ·  veri salvi 2/2

⇒ **`cifra-riusata IT` va tolta dalle rosse**: su quattro casi ne passa **uno**,
ed e' proprio quello del primo referto. Il limite che avevo dichiarato («due
casi non chiudono una classe») valeva **in entrambe le direzioni**, e qui ha
morso me: **una cella dichiarata rossa su n=2 e' largamente difesa a n=4.**
⇒ Le altre cinque reggono, e **`numerale-a-parole EN` peggiora**: 4 su 4.
🔴 E il danno doppio resta su **tre celle**: `omissione IT`, `omissione EN`,
`numerale IT` perdono anche **un claim VERO su due**.

ESITO B - 🪞 **IL MIO RILIEVO SU «Article» CADE ALLA PORTA.**

    IT  art. abbreviato    downgrade  99.0   L4.1,L4.2
    IT  articolo esteso    downgrade  98.9   L4.1,L4.2
    EN  art. abbreviato    downgrade  99.3   L4.1,L4.2
    EN  Article esteso     downgrade  62.1   L4.2,L4-review     <- fermato lo stesso
    EN  Section esteso     downgrade  85.5   L4.1,L4.2
    controllo (91 mai nella fonte)  downgrade  0.3  L4.1,L4-grounding

Sull'ESTRATTORE il rilievo regge: «Article 3» non e' riconosciuto come
riferimento e il 3 entra come quantita' a unita' vuota. **Ma alla PORTA il claim
viene fermato lo stesso**, da `L4.2` invece che da `L4.1`.
⇒ **Formulazione corretta**: la cura dedicata **non copre «Article»** - si vede
dal layer che manca - ma in questo caso **un altro strato para il colpo**. Non
e' vero, come avevo scritto a @ws3, che «su un contratto inglese il difetto
resta INTERO»: quella frase valeva sul livello che avevo misurato, non su questo.
🔑 E' la mia stessa regola applicata a me: **il livello a cui misuri decide il
verdetto** - regex interna < funzione pubblica < porta che il prodotto usa.
Avevo dichiarato che dovevo salire di livello, sono salita, e il verdetto si e'
ribaltato.
⚖️ Resta vero, e vale la riga: **`Article` esce a 62.1 mentre le altre tre forme
stanno a 98.9-99.3**. Il margine e' molto piu' sottile, e sotto la soglia
sbagliata quel caso passerebbe. La copertura lessicale asimmetrica IT/EN e' un
debito reale; non e' un buco aperto.

REGIME: build corrente · store TEMPORANEO rimosso da un `trap` · `ground_write=True`.
⚠️ **Limite**: quattro casi per cella restano quattro casi, e le fonti sono
costruite da me. Il blocco B e' **un solo claim** ripetuto su cinque forme di
riferimento: dice cosa succede a quel claim, non a tutti.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-C2-le-sei-celle-rosse-allargate.py <dir-temp>
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

# ---- A: le sei celle rosse, quattro falsi e due veri ciascuna ---------------
ROSSE = {
 ("cifra-riusata", "IT"): {
   "falsi": [
     ("La penale per il ritardo e' di 500 euro.",
      "La penale per il ritardo e' di 200 euro. La penale per difformita' e' di 500 euro."),
     ("Lo sconto sul primo ordine e' del 12 per cento.",
      "Lo sconto sul primo ordine e' del 4 per cento. Lo sconto sul rinnovo e' del 12 per cento."),
     ("Il compenso del revisore e' di 9000 euro.",
      "Il compenso del revisore e' di 3000 euro. Il compenso del consulente e' di 9000 euro."),
     ("La quota di ammortamento del capannone e' 40000 euro.",
      "La quota di ammortamento del capannone e' 15000 euro. "
      "La quota di ammortamento dei macchinari e' 40000 euro."),
   ],
   "veri": [
     ("La penale per il ritardo e' di 200 euro.",
      "La penale per il ritardo e' di 200 euro. La penale per difformita' e' di 500 euro."),
     ("Il compenso del consulente e' di 9000 euro.",
      "Il compenso del revisore e' di 3000 euro. Il compenso del consulente e' di 9000 euro."),
   ]},
 ("omissione", "IT"): {
   "falsi": [
     ("La merce e' stata spedita con corriere espresso.",
      "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
     ("Il consiglio ha deliberato all'unanimita'.",
      "Il consiglio ha deliberato l'aumento di capitale nella seduta di ieri."),
     ("La riunione si e' tenuta in videoconferenza.",
      "La riunione si e' tenuta ieri e ha approvato il bilancio."),
     ("Il pagamento e' avvenuto tramite bonifico.",
      "Il pagamento e' stato registrato in data odierna."),
   ],
   "veri": [
     ("La merce e' arrivata integra.",
      "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
     ("Il consiglio ha deliberato l'aumento di capitale.",
      "Il consiglio ha deliberato l'aumento di capitale nella seduta di ieri."),
   ]},
 ("omissione", "EN"): {
   "falsi": [
     ("The goods were shipped by express courier.",
      "The goods were shipped on April 12th and arrived undamaged."),
     ("The board decided unanimously.",
      "The board approved the capital increase at yesterday's meeting."),
     ("The meeting was held by video conference.",
      "The meeting was held yesterday and approved the budget."),
     ("The payment was made by bank transfer.",
      "The payment was recorded today."),
   ],
   "veri": [
     ("The goods arrived undamaged.",
      "The goods were shipped on April 12th and arrived undamaged."),
     ("The board approved the capital increase.",
      "The board approved the capital increase at yesterday's meeting."),
   ]},
 ("numerale-a-parole", "IT"): {
   "falsi": [
     ("Il fatturato annuo e' di settantamila euro.",
      "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
     ("I dipendenti assunti sono dodici.",
      "L'azienda ha completato le assunzioni previste dal piano."),
     ("La garanzia dura ventiquattro mesi.",
      "La garanzia decorre dalla data di acquisto."),
     ("Il ritardo e' stato di tre giorni.",
      "La consegna e' avvenuta in ritardo rispetto al termine pattuito."),
   ],
   "veri": [
     ("Il bilancio si e' chiuso in pareggio.",
      "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
     ("La garanzia decorre dalla data di acquisto.",
      "La garanzia decorre dalla data di acquisto."),
   ]},
 ("numerale-a-parole", "EN"): {
   "falsi": [
     ("The annual revenue is seventy thousand euro.",
      "The financial year closed at break-even after a difficult period."),
     ("Twelve employees were hired.",
      "The company completed the hiring planned in the budget."),
     ("The warranty lasts twenty-four months.",
      "The warranty starts from the purchase date."),
     ("The delay was three days.",
      "Delivery occurred later than the agreed term."),
   ],
   "veri": [
     ("The financial year closed at break-even.",
      "The financial year closed at break-even after a difficult period."),
     ("The warranty starts from the purchase date.",
      "The warranty starts from the purchase date."),
   ]},
 ("unita-cambiata", "IT"): {
   "falsi": [
     ("Il termine di consegna e' di 30 mesi.",
      "Il termine di consegna e' di 30 giorni dalla firma."),
     ("Il canone e' di 1200 euro al giorno.",
      "Il canone e' di 1200 euro al mese."),
     ("La distanza e' di 15 chilometri.",
      "La distanza dal deposito e' di 15 metri."),
     ("La dose e' di 500 grammi.",
      "La dose prescritta e' di 500 milligrammi al giorno."),
   ],
   "veri": [
     ("Il termine di consegna e' di 30 giorni.",
      "Il termine di consegna e' di 30 giorni dalla firma."),
     ("Il canone e' di 1200 euro al mese.",
      "Il canone e' di 1200 euro al mese."),
   ]},
}

# ---- B: end-to-end del riferimento di sezione, IT contro EN ------------------
SEZIONI = [
 ("IT  art. abbreviato   (cura ATTIVA)", "Il contratto prevede 3 rate.",
  "art. 3 del contratto - Oggetto. Il fornitore consegna la merce entro il termine."),
 ("IT  articolo esteso   (cura ATTIVA)", "Il contratto prevede 3 rate.",
  "articolo 3 del contratto - Oggetto. Il fornitore consegna la merce entro il termine."),
 ("EN  art. abbreviato   (cura ATTIVA)", "The contract provides for 3 instalments.",
  "art. 3 of the contract - Subject. The supplier delivers the goods within the term."),
 ("EN  Article esteso    (LA MIA IPOTESI)", "The contract provides for 3 instalments.",
  "Article 3 of the contract - Subject. The supplier delivers the goods within the term."),
 ("EN  Section esteso    (in lista)", "The contract provides for 3 instalments.",
  "Section 3 of the contract - Subject. The supplier delivers the goods within the term."),
 ("controllo: numero MAI nella fonte", "The contract provides for 91 instalments.",
  "Article 3 of the contract - Subject. The supplier delivers the goods within the term."),
]


def esegui(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    az = str(getattr(r, "action", None) or getattr(r, "decision", None) or "?")
    return az, g, ws


def main():
    print("=== A: le SEI celle rosse, 4 falsi + 2 veri ciascuna ===")
    print("  %-19s %-3s %-7s %-10s %8s  %s"
          % ("classe", "lg", "verita", "azione", "ground", "layer"))
    sintesi = []
    for (classe, lg), gruppi in ROSSE.items():
        fermati = passati = 0
        for claim, fonte in gruppi["falsi"]:
            az, g, ws = esegui(claim, fonte)
            if az == "persist":
                passati += 1
            else:
                fermati += 1
            print("  %-19s %-3s %-7s %-10s %8s  %-24s%s"
                  % (classe, lg, "falso", az,
                     ("%.1f" % g) if g is not None else "None",
                     ",".join(ws)[:24] or "-",
                     "  <== il falso PASSA" if az == "persist" else ""))
        veri_ok = 0
        for claim, fonte in gruppi["veri"]:
            az, g, ws = esegui(claim, fonte)
            if az == "persist":
                veri_ok += 1
            print("  %-19s %-3s %-7s %-10s %8s  %-24s%s"
                  % (classe, lg, "VERO", az,
                     ("%.1f" % g) if g is not None else "None",
                     ",".join(ws)[:24] or "-",
                     "" if az == "persist" else "  <== il VERO cade"))
        sintesi.append((classe, lg, passati, len(gruppi["falsi"]),
                        veri_ok, len(gruppi["veri"])))

    print("\n=== SINTESI: la cella e' bucata o erano due casi? ===")
    for classe, lg, passati, tot, veri_ok, tot_v in sintesi:
        if passati == tot:
            verdetto = "BUCATA su tutti"
        elif passati == 0:
            verdetto = "i due casi del primo referto NON generalizzano"
        else:
            verdetto = "PARZIALE"
        print("  %-19s %-3s  falsi passati %d/%d  ·  veri salvi %d/%d   -> %s"
              % (classe, lg, passati, tot, veri_ok, tot_v, verdetto))

    print("\n=== B: end-to-end del riferimento di sezione (IT vs EN) ===")
    print("  %-38s %-10s %8s  %s" % ("caso", "azione", "ground", "layer"))
    for nome, claim, fonte in SEZIONI:
        az, g, ws = esegui(claim, fonte)
        print("  %-38s %-10s %8s  %-24s%s"
              % (nome, az, ("%.1f" % g) if g is not None else "None",
                 ",".join(ws)[:24] or "-",
                 "  <== il falso PASSA" if az == "persist" else ""))
    print("  ^ il claim inventa 'rate' che la fonte non nomina MAI: se passa, e'")
    print("    perche' il numero della sezione ha immunizzato il 3.")


if __name__ == "__main__":
    main()
