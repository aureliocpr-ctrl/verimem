r"""C2 - le CLASSI CORE di falsita', in ITALIANO e in INGLESE, sulla porta vera.

C2 del contratto di uscita: «claim centrale verde classi core IT+EN». Il suo
percorso critico dichiarato era F1, e F1 non si collega (`db247414` di @ws3, 27
falsi positivi su 28; misura parallela mia, 14 su 14). ⇒ C2 e' rimasto senza il
pezzo che doveva renderlo verde, e questo banco misura **il prodotto com'e'
oggi**, senza `L4.3`.

Direttiva di Aurelio, 25/08: «*deve fare quello che dice di fare... almeno in
inglese e italiano*». Da qui le due lingue su OGNI classe.

LA PORTA: `run_validation_gate`, quella che la CLI chiama a `cli.py:1867`.
Non una funzione interna: il livello a cui si misura decide il verdetto.

LE OTTO CLASSI, e per ognuna un FALSO e un VERO nella stessa lingua:
    cifra-inventata      il numero non e' nella fonte
    cifra-riusata        il numero c'e', ma la fonte lo lega a un altro soggetto
    omissione            un dettaglio NON numerico che la fonte non dice
    numerale-a-parole    «settantamila» dove la fonte dice 70000... o niente
    entita-inventata     un soggetto che nella fonte non esiste
    negazione            la fonte nega, il claim afferma
    unita-cambiata       stesso numero, unita' diversa (giorni -> mesi)
    attestazione-nuda    «verificato che funziona», senza prova

⚠️ IL CONTROLLO E' META' DEL BANCO. Una colonna di «fermato» non significa
niente da sola: un gate che ferma tutto e' verde e inutile. Per ogni classe c'e'
un claim VERO e sostenuto che **deve passare**; se cade anche lui, la classe non
e' «difesa», e' **spenta**.

COME SI LEGGE una cella:
    FALSO  downgrade -> ✔ difesa      ·  FALSO  persist   -> 🔴 BUCO
    VERO   persist   -> ✔ non ostruisce ·  VERO  downgrade -> 🟠 falso positivo

REGIME: build corrente · store TEMPORANEO (`HIPPO_DATA_DIR`), mai quello di
Aurelio · `ground_write=True` (senza, il giudice non gira e un grounding
assente non e' un grounding basso).

⚖️ PUNTI DEBOLI, dichiarati prima dei numeri: i casi sono **costruiti da me**,
**due per classe e lingua**. Su una classe che risulta ferma con due casi non si
conclude che sia difesa: si conclude che questi due sono fermi. Le due lingue
sono traduzioni mie della stessa situazione, quindi misurano il gate, non la
qualita' del mio inglese - ma una differenza IT/EN potrebbe venire dalla
traduzione e non dal prodotto, e dove capita lo dico.

ESITO - 14 celle (7 classi x 2 lingue; la 8a e' attestazione-nuda, difesa in
entrambe). **6 BUCHI e 3 FALSI POSITIVI.**

    classe             IT                        EN
    cifra-inventata    difesa / vero passa       difesa / vero passa
    cifra-riusata      🔴 BUCO / vero passa      difesa / vero passa
    omissione          🔴 BUCO / 🟠 VERO CADE    🔴 BUCO / 🟠 VERO CADE
    numerale-a-parole  🔴 BUCO / 🟠 VERO CADE    🔴 BUCO / vero passa
    entita-inventata   difesa / vero passa       difesa / vero passa
    negazione          difesa / vero passa       difesa / vero passa
    unita-cambiata     🔴 BUCO / vero passa      difesa / vero passa
    attestazione-nuda  difesa / vero passa       difesa / vero passa

🔴 DUE CLASSI SONO ROTTE IN ENTRAMBE LE DIREZIONI: `omissione` e
`numerale-a-parole` lasciano passare il falso **e** fermano il vero. Il vero
cade per mano di `L1.20` (omissione, IT ed EN) e `L1.13` (numerale, IT). ⇒ Non
sono «non difese»: fanno **danno**, perche' un utente perde un fatto sostenuto.

⚖️ E QUI RIDIMENSIONO UNA MIA LETTURA, prodotta dal mio stesso criterio. Vedendo
`cifra-riusata` e `unita-cambiata` bucate in IT e difese in EN avevo scritto
«asimmetria IT/EN». L'ho estesa a tre casi per famiglia:

    cifra riusata    FERMATI  IT 2/3   EN 3/3
    unita cambiata   FERMATI  IT 2/3   EN 3/3

⇒ **Su 6 coppie ne differiscono 2, non sei.** Le altre 4 sono fermate in
entrambe le lingue. «L'italiano e' indifeso» **non e' quello che dice il dato**,
e il mio confronto binario (`IT != EN` su n=3) produceva quell'etichetta da
solo. ⇒ Cio' che resta, ed e' comunque forte: **sulle stesse due proposizioni
tradotte il giudice da' 96.6 e 98.4 in italiano contro 0.8 e 2.1 in inglese**.
Un salto di 95 punti sullo stesso contenuto non e' rumore, ma **due coppie non
sono una legge**: serve una batteria piu' larga prima di dire che il giudice
e' piu' debole in italiano.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-C2-le-classi-core-in-italiano-e-inglese.py <dir-temp>
⚠️ Vuole una dir TEMPORANEA come primo argomento.
"""
import os
import sys

if len(sys.argv) < 2:
    print("uso: python %s <dir-temp>" % sys.argv[0])
    raise SystemExit(2)
os.environ["HIPPO_DATA_DIR"] = sys.argv[1]

from verimem.anti_confab_gate import run_validation_gate  # noqa: E402

# (classe, lingua, verita', claim, fonte)
CASI = [
 # ---- cifra inventata --------------------------------------------------
 ("cifra-inventata", "IT", "falso",
  "L'ordine 77 conteneva 40 pezzi.",
  "L'ordine 77 e' stato consegnato il 3 marzo dal fornitore Gatti."),
 ("cifra-inventata", "IT", "vero",
  "L'ordine 77 e' stato consegnato dal fornitore Gatti.",
  "L'ordine 77 e' stato consegnato il 3 marzo dal fornitore Gatti."),
 ("cifra-inventata", "EN", "falso",
  "Order 77 contained 40 items.",
  "Order 77 was delivered on March 3rd by supplier Gatti."),
 ("cifra-inventata", "EN", "vero",
  "Order 77 was delivered by supplier Gatti.",
  "Order 77 was delivered on March 3rd by supplier Gatti."),
 # ---- cifra riusata da altro soggetto ----------------------------------
 ("cifra-riusata", "IT", "falso",
  "La penale per il ritardo e' di 500 euro.",
  "La penale per il ritardo e' di 200 euro. La penale per difformita' e' di 500 euro."),
 ("cifra-riusata", "IT", "vero",
  "La penale per il ritardo e' di 200 euro.",
  "La penale per il ritardo e' di 200 euro. La penale per difformita' e' di 500 euro."),
 ("cifra-riusata", "EN", "falso",
  "The penalty for delay is 500 euro.",
  "The penalty for delay is 200 euro. The penalty for defects is 500 euro."),
 ("cifra-riusata", "EN", "vero",
  "The penalty for delay is 200 euro.",
  "The penalty for delay is 200 euro. The penalty for defects is 500 euro."),
 # ---- omissione (dettaglio NON numerico) -------------------------------
 ("omissione", "IT", "falso",
  "La merce e' stata spedita con corriere espresso.",
  "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
 ("omissione", "IT", "vero",
  "La merce e' arrivata integra.",
  "La merce e' stata spedita il 12 aprile ed e' arrivata integra."),
 ("omissione", "EN", "falso",
  "The goods were shipped by express courier.",
  "The goods were shipped on April 12th and arrived undamaged."),
 ("omissione", "EN", "vero",
  "The goods arrived undamaged.",
  "The goods were shipped on April 12th and arrived undamaged."),
 # ---- numerale a parole -------------------------------------------------
 ("numerale-a-parole", "IT", "falso",
  "Il fatturato annuo e' di settantamila euro.",
  "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
 ("numerale-a-parole", "IT", "vero",
  "Il bilancio si e' chiuso in pareggio.",
  "Il bilancio si e' chiuso in pareggio dopo un esercizio difficile."),
 ("numerale-a-parole", "EN", "falso",
  "The annual revenue is seventy thousand euro.",
  "The financial year closed at break-even after a difficult period."),
 ("numerale-a-parole", "EN", "vero",
  "The financial year closed at break-even.",
  "The financial year closed at break-even after a difficult period."),
 # ---- entita' inventata -------------------------------------------------
 ("entita-inventata", "IT", "falso",
  "Il fornitore Verdi ha consegnato la merce.",
  "Il fornitore Gatti ha consegnato la merce il 3 marzo."),
 ("entita-inventata", "IT", "vero",
  "Il fornitore Gatti ha consegnato la merce.",
  "Il fornitore Gatti ha consegnato la merce il 3 marzo."),
 ("entita-inventata", "EN", "falso",
  "Supplier Verdi delivered the goods.",
  "Supplier Gatti delivered the goods on March 3rd."),
 ("entita-inventata", "EN", "vero",
  "Supplier Gatti delivered the goods.",
  "Supplier Gatti delivered the goods on March 3rd."),
 # ---- negazione capovolta ----------------------------------------------
 ("negazione", "IT", "falso",
  "Il consiglio ha approvato il bilancio.",
  "Il consiglio non ha approvato il bilancio e ha rinviato la decisione."),
 ("negazione", "IT", "vero",
  "Il consiglio ha rinviato la decisione.",
  "Il consiglio non ha approvato il bilancio e ha rinviato la decisione."),
 ("negazione", "EN", "falso",
  "The board approved the budget.",
  "The board did not approve the budget and postponed the decision."),
 ("negazione", "EN", "vero",
  "The board postponed the decision.",
  "The board did not approve the budget and postponed the decision."),
 # ---- unita' cambiata ---------------------------------------------------
 ("unita-cambiata", "IT", "falso",
  "Il termine di consegna e' di 30 mesi.",
  "Il termine di consegna e' di 30 giorni dalla firma."),
 ("unita-cambiata", "IT", "vero",
  "Il termine di consegna e' di 30 giorni.",
  "Il termine di consegna e' di 30 giorni dalla firma."),
 ("unita-cambiata", "EN", "falso",
  "The delivery term is 30 months.",
  "The delivery term is 30 days from signature."),
 ("unita-cambiata", "EN", "vero",
  "The delivery term is 30 days.",
  "The delivery term is 30 days from signature."),
 # ---- attestazione nuda -------------------------------------------------
 ("attestazione-nuda", "IT", "falso",
  "Ho verificato che la cura funziona e i test passano tutti.",
  "Il modulo e' stato modificato per gestire il caso limite."),
 ("attestazione-nuda", "IT", "vero",
  "Il modulo e' stato modificato per gestire il caso limite.",
  "Il modulo e' stato modificato per gestire il caso limite."),
 ("attestazione-nuda", "EN", "falso",
  "I verified that the fix works and all tests pass.",
  "The module was modified to handle the edge case."),
 ("attestazione-nuda", "EN", "vero",
  "The module was modified to handle the edge case.",
  "The module was modified to handle the edge case."),
]


def esegui(claim, fonte):
    r = run_validation_gate(proposition=claim, verified_by=None, topic=None,
                            agent=None, source=fonte, grounding_llm=None,
                            ground_write=True)
    g = getattr(r, "grounding_score", None)
    ws = [w.get("layer", "?") if isinstance(w, dict) else str(w)
          for w in (getattr(r, "warnings", None) or [])]
    azione = getattr(r, "action", None) or getattr(r, "decision", None) or "?"
    return str(azione), g, ws


def main():
    print("  %-19s %-3s %-6s %-10s %8s  %s"
          % ("classe", "lg", "verita", "azione", "ground", "layer"))
    print("  " + "-" * 84)
    esiti = {}
    for classe, lingua, verita, claim, fonte in CASI:
        azione, g, ws = esegui(claim, fonte)
        fermato = azione != "persist"
        if verita == "falso":
            ok = fermato
            mark = "" if ok else "  <== BUCO: il falso PASSA"
        else:
            ok = not fermato
            mark = "" if ok else "  <== falso positivo: il VERO cade"
        esiti[(classe, lingua, verita)] = (azione, g, ok)
        print("  %-19s %-3s %-6s %-10s %8s  %-28s%s"
              % (classe, lingua, verita, azione,
                 ("%.1f" % g) if g is not None else "None",
                 ",".join(ws)[:28] or "-", mark))

    print("\n=== SINTESI per classe: il falso e' fermato E il vero passa? ===")
    classi = []
    for c, l, v in esiti:
        if (c, l) not in classi:
            classi.append((c, l))
    buchi = fp = 0
    for c, l in classi:
        af, _gf, okf = esiti[(c, l, "falso")]
        av, _gv, okv = esiti[(c, l, "vero")]
        if not okf:
            buchi += 1
        if not okv:
            fp += 1
        stato = ("difesa" if okf else "BUCO") + (" / vero passa" if okv else " / VERO CADE")
        print("  %-19s %-3s   falso=%-10s vero=%-10s   %s" % (c, l, af, av, stato))
    print("\n  celle: %d classi x 2 lingue" % (len(classi) // 2))
    print("  BUCHI (il falso passa)          : %d su %d" % (buchi, len(classi)))
    print("  FALSI POSITIVI (il vero cade)   : %d su %d" % (fp, len(classi)))
    print("\n  ⚠️ due casi per classe e lingua: una classe 'difesa' qui vuol dire")
    print("     'questi due sono fermi', non 'la classe e' chiusa'.")


if __name__ == "__main__":
    main()
