# -*- coding: utf-8 -*-
"""M5 / T5.1 — decimale IT-EN, notazione scientifica, unità: le tre classi che
la baseline NON copre. Con la predizione scritta prima di eseguire.

    python docs/stato-reale/banchi/ws3-M5-T51-le-tre-classi-numeriche-non-misurate.py

CONTESTO. La baseline `ws3-M5-baseline-le-tre-forme-sugli-stessi-casi.py` misura
parola↔cifra, parafrasi e lingua. Il mandato T5.1 nomina **altre tre classi** —
separatore decimale IT/EN, notazione scientifica, unità di misura — e nessuna è
mai stata misurata. Sono la popolazione dove la canonicalizzazione **può**
funzionare, perché lì il numero **è nella fonte**: non va contato, va
riconosciuto sotto un'altra veste.

DISEGNO. Per ogni caso, due condizioni che differiscono per UNA cosa:
  · `identica`     fonte e claim scrivono il numero allo STESSO modo   <- riferimento
  · `trasformata`  stesso valore, notazione diversa                    (l'unica variabile)
e due popolazioni: il claim VERO (stesso valore) e il claim FALSO (valore
diverso). Senza i VERI si misura una colonna sola, che è il difetto di misura
che il paper di Zhang denuncia nei fact-checker pronti all'uso.

🔮 PREDIZIONE, depositata PRIMA dell'esecuzione (02/09 12:45):
  ① nella condizione `identica` il gate ammette i VERI (≤1/6 fermati) e ferma i
     FALSI (≥5/6): è il controllo, e se non si comporta così il banco non
     misura ciò che dico e i numeri sotto non vanno letti;
  ② nella condizione `trasformata` i **VERI FERMATI salgono ad almeno 4/6 su
     tutte e tre le classi** — perché lo strato a regola confronta il GLIFO, e
     `3.5` non è `3,5`;
  ③ i FALSI restano fermati in entrambe le condizioni (≤1/6 passati).
  ⇒ Se ①②③ reggono, **T5.1 è una cura per i FALSI ALLARMI, non per le falsità
     ammesse** — l'opposto di come il mandato la sta valutando, che chiede
     «≥95% fermati» guardando i soli falsi.

COME MUORE: se in `trasformata` i veri fermati restano ≤2/6, allora lo strato
riconosce già le notazioni equivalenti, T5.1 non ha nulla da curare qui, e la
mia lettura del confronto-per-glifo è sbagliata.

⚠️ LIMITI: n=6 per classe, UNA esecuzione, e le coppie di notazioni le ho
scritte io. La classe `unità` non è una riscrittura ma una CONVERSIONE (95 °C =
368,15 K): nessuna canonicalizzazione lessicale può risolverla, e la tengo
separata apposta — se cade come le altre due, non è la stessa causa.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws3_T51_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

# (classe, fonte, template del claim, valore VERO come in fonte,
#  valore VERO trasformato, valore FALSO)
CASI = [
    # ── separatore decimale: la fonte scrive all'italiana, il claim all'inglese
    ("decimale", "Il campione pesa 3,5 grammi secondo il verbale.",
     "Il peso del campione e' {n} grammi.", "3,5", "3.5", "8,5"),
    ("decimale", "La soglia di collaudo e' fissata a 0,75 millimetri.",
     "La soglia di collaudo e' {n} millimetri.", "0,75", "0.75", "0,95"),
    ("decimale", "Il lotto ha una tolleranza di 12,4 punti percentuali.",
     "La tolleranza del lotto e' {n} punti percentuali.", "12,4", "12.4", "19,4"),
    ("decimale", "Il serbatoio contiene 48,6 litri di reflui.",
     "I reflui nel serbatoio sono {n} litri.", "48,6", "48.6", "84,6"),
    ("decimale", "La misura di taratura riporta 1,05 volt.",
     "La taratura riporta {n} volt.", "1,05", "1.05", "1,50"),
    ("decimale", "Il consumo medio registrato e' 7,2 kilowattora.",
     "Il consumo medio e' {n} kilowattora.", "7,2", "7.2", "2,7"),
    # ── notazione scientifica: stesso valore, forma esponenziale
    ("scientifica", "Il contatore ha registrato 1500 impulsi nella prova.",
     "Gli impulsi registrati sono {n}.", "1500", "1,5 x 10^3", "2500"),
    ("scientifica", "Il campione contiene 250000 particelle per millilitro.",
     "Le particelle per millilitro sono {n}.", "250000", "2,5 x 10^5", "350000"),
    ("scientifica", "La resistenza misurata e' 4700 ohm.",
     "La resistenza misurata e' {n} ohm.", "4700", "4,7 x 10^3", "5700"),
    ("scientifica", "Il file di log pesa 32000 byte.",
     "Il peso del file di log e' {n} byte.", "32000", "3,2 x 10^4", "52000"),
    ("scientifica", "Il ciclo ha eseguito 60000 iterazioni.",
     "Le iterazioni del ciclo sono {n}.", "60000", "6 x 10^4", "90000"),
    ("scientifica", "La cella misura 0,0004 metri di spessore.",
     "Lo spessore della cella e' {n} metri.", "0,0004", "4 x 10^-4", "0,0009"),
    # ── unità: NON una riscrittura, una CONVERSIONE (tenuta separata apposta)
    ("unita", "La camera di prova ha raggiunto 95 gradi Celsius.",
     "La camera di prova ha raggiunto {n}.", "95 gradi Celsius", "368,15 kelvin",
     "120 gradi Celsius"),
    ("unita", "Il tratto misurato e' lungo 2 chilometri.",
     "Il tratto misurato e' lungo {n}.", "2 chilometri", "2000 metri",
     "5 chilometri"),
    ("unita", "Il carico dichiarato e' di 3 tonnellate.",
     "Il carico dichiarato e' di {n}.", "3 tonnellate", "3000 chilogrammi",
     "7 tonnellate"),
    ("unita", "La prova e' durata 2 ore.",
     "La prova e' durata {n}.", "2 ore", "120 minuti", "5 ore"),
    ("unita", "Il recipiente contiene 5 litri di soluzione.",
     "Il recipiente contiene {n} di soluzione.", "5 litri", "5000 millilitri",
     "9 litri"),
    ("unita", "La pressione rilevata e' 2 bar.",
     "La pressione rilevata e' {n}.", "2 bar", "200 kilopascal", "6 bar"),
]

CLASSI = ["decimale", "scientifica", "unita"]
CONDIZIONI = ["identica", "trasformata"]
veri_fermati, falsi_passati, chi = {}, {}, {}
for _c in CLASSI:
    for _k in CONDIZIONI:
        veri_fermati[(_c, _k)] = 0
        falsi_passati[(_c, _k)] = 0
        chi[(_c, _k)] = []

m = Memory()
print("T5.1 — LE TRE CLASSI NUMERICHE NON MISURATE (notazione = unica variabile)\n")
print("%-12s %-12s %-5s %-44s %-13s %s"
      % ("classe", "condizione", "verit", "claim", "esito", "chi ferma"))
print("-" * 110)

for i, (classe, fonte, tmpl, v_come_fonte, v_trasf, falso) in enumerate(CASI, 1):
    for cond in CONDIZIONI:
        vero_n = v_come_fonte if cond == "identica" else v_trasf
        for etichetta, valore in (("VERO", vero_n), ("falso", falso)):
            prop = tmpl.format(n=valore)
            r = m.add(prop, topic="ws3/T51-%s-%s-%d" % (classe, cond, i),
                      source=fonte)
            st = (r.get("status") or "?") if isinstance(r, dict) else "?"
            qb = ",".join(str(w.get("layer", "?"))
                          for w in (r.get("warnings") or [])) if isinstance(r, dict) else "-"
            fermato = (st == "quarantined")
            k = (classe, cond)
            if etichetta == "VERO" and fermato:
                veri_fermati[k] += 1
                chi[k].append(qb or "(nessuno)")
            if etichetta == "falso" and not fermato:
                falsi_passati[k] += 1
            print("%-12s %-12s %-5s %-44s %-13s %s"
                  % (classe, cond, etichetta, prop[:44], st, qb))

print("=" * 110)
print("T5.1 — sei casi per cella\n")
print("%-12s %-12s %-15s %-16s %s"
      % ("classe", "condizione", "VERI fermati", "FALSI passati", "chi ferma i VERI"))
for c in CLASSI:
    for k in CONDIZIONI:
        print("%-12s %-12s %-15s %-16s %s"
              % (c, k, "%d/6" % veri_fermati[(c, k)],
                 "%d/6" % falsi_passati[(c, k)],
                 ",".join(sorted(set(chi[(c, k)]))) or "-"))
    print()
print("  `identica` e' il CONTROLLO: se li' i veri sono gia' fermati, il banco")
print("  non misura la notazione e i numeri di `trasformata` non vanno letti.")
print("\nrifallo con:")
print("  python docs/stato-reale/banchi/"
      "ws3-M5-T51-le-tre-classi-numeriche-non-misurate.py")
