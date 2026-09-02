# -*- coding: utf-8 -*-
"""M5 anello ① — BASELINE UNIFICATA: le tre forme sugli STESSI casi.

    python docs/stato-reale/banchi/ws3-M5-baseline-le-tre-forme-sugli-stessi-casi.py

PERCHE' ESISTE, dato che le tre forme sono gia' misurate.
Ognuna ha il suo banco, e ognuno ha CASI DIVERSI:
  · numero in parola   `ws6-la-cifra-e-la-parola.py`
  · parafrasi          `ws3-la-parafrasi-fedele-e-un-caso-o-una-classe.py`
  · lingua             `ws3-l-asimmetria-di-lingua-su-cinque-coppie-piu-una-terza-lingua.py`
                       + la porta inglese di un'altra istanza (5/10 scambiate, 10/10 vere)
⇒ I tre numeri **non sono confrontabili**: differiscono per la forma E per i casi.
Qui la forma e' l'UNICA variabile — sei casi soli, quattro condizioni, e ogni
condizione si scosta dalla CANONICA per **una cosa sola**:
    canonica   fonte IT, numero in CIFRA, claim letterale        <- il riferimento
    parola     identica, ma il numero e' in LETTERE               (cambia: la forma del numero)
    parafrasi  fonte IDENTICA alla canonica, claim RIFORMULATO    (cambia: le parole del claim)
    inglese    fonte e claim tradotti, numero in cifra            (cambia: la lingua)

⚠️ SENZA RIFERIMENTO UN BANCO NON DICE NIENTE: la riga `canonica` non e' un
riempitivo, e' la sola contro cui le altre tre significano qualcosa.

⚠️ SI MISURANO ENTRAMBE LE POPOLAZIONI, e per la ragione che le separa:
  · FALSI PASSATI  -> quanto il gate lascia entrare  (piu' basso e' meglio)
  · VERI FERMATI   -> i falsi allarmi                (piu' basso e' meglio)
Un criterio giudicato sui soli falsi sembra sempre ottimo: basta fermare tutto.

📌 I sei casi base sono quelli di `ws6-la-cifra-e-la-parola.py` (gruppo COPIA:
la fonte PORTA il numero, non lo si deve contare) — riusati apposta, cosi' la
colonna `parola` di questo banco e' confrontabile con la sua misura.

⚠️ LIMITI, prima dei numeri: n=6 per cella, UNA esecuzione, e le parafrasi e le
traduzioni le ho scritte io — sono materiale del banco, non un campione.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ws3_M5_baseline_")
os.environ["HIPPO_DATA_DIR"] = _tmp
os.environ["ENGRAM_DATA_DIR"] = _tmp
os.environ.pop("VERIMEM_DATA_DIR", None)

from verimem import Memory  # noqa: E402

PAROLA = {"2": "due", "3": "tre", "4": "quattro", "5": "cinque",
          "7": "sette", "8": "otto", "9": "nove", "10": "dieci"}

# (fonte_it, claim_it, claim_parafrasi_it, fonte_en, claim_en, vero, falso)
CASI = [
    ("Il magazzino ha ricevuto 3 bancali il 9 giugno.",
     "I bancali ricevuti dal magazzino sono {n}.",
     "Al magazzino sono arrivati {n} bancali.",
     "The warehouse received 3 pallets on 9 June.",
     "The pallets received by the warehouse are {n}.",
     "3", "8"),
    ("Il verbale registra 5 presenti alla riunione.",
     "I presenti registrati nel verbale sono {n}.",
     "Il verbale conta {n} partecipanti alla riunione.",
     "The minutes record 5 attendees at the meeting.",
     "The attendees recorded in the minutes are {n}.",
     "5", "9"),
    ("La squadra e' composta da 4 operai.",
     "Gli operai della squadra sono {n}.",
     "La squadra comprende {n} addetti.",
     "The crew is made up of 4 workers.",
     "The workers in the crew are {n}.",
     "4", "10"),
    ("Il modulo e' importato da 3 file del pacchetto.",
     "I file che importano il modulo sono {n}.",
     "A richiamare il modulo sono {n} file.",
     "The module is imported by 3 files of the package.",
     "The files importing the module are {n}.",
     "3", "7"),
    ("Il verbale cita 2 sedi dell'azienda.",
     "Le sedi citate nel verbale sono {n}.",
     "Il verbale menziona {n} sedi aziendali.",
     "The minutes cite 2 offices of the company.",
     "The offices cited in the minutes are {n}.",
     "2", "7"),
    ("Nel magazzino restano 2 pallet.",
     "I pallet rimasti in magazzino sono {n}.",
     "Restano {n} pallet nel deposito.",
     "2 pallets remain in the warehouse.",
     "The pallets remaining in the warehouse are {n}.",
     "2", "8"),
]


# ── SECONDA POPOLAZIONE, aggiunta alle 12:36 perche' la prima NON MOSTRAVA IL
# MURO: sui casi qui sopra (la fonte PORTA il numero) tutte e quattro le forme
# danno 0 falsi passati e 0 veri fermati — un gate perfetto, e quindi una
# baseline che non misura niente. Il motivo si legge nella colonna «chi ferma»:
# in `parola` il falso e' fermato da `L4-grounding`, cioe' dal GIUDICE, non da
# `L4.1` — che il numero in lettere non lo vede affatto. Lo strato lessicale e'
# cieco e il moat copre.
# ⇒ Qui il numero NON e' nella fonte: va CONTATO. E' la classe su cui un'altra
# istanza misura «in parola 4 falsita' su 6 passano». Se il muro esiste, e' qui
# che deve comparire — e allora la variabile non e' solo la FORMA, e' la forma
# INSIEME alla classe del caso.
CASI_CONTEGGIO = [
    ("Il registro elenca i lotti A1, A2 e A3 usciti dal deposito il 9 giugno.",
     "I lotti usciti dal deposito sono {n}.",
     "Dal deposito ne sono usciti {n} di lotti.",
     "The register lists lots A1, A2 and A3 that left the depot on 9 June.",
     "The lots that left the depot are {n}.",
     "3", "8"),
    ("Il collaudo ha verificato le affermazioni 1, 2, 3, 4 e 5 del manuale.",
     "Le affermazioni verificate nel collaudo sono {n}.",
     "Il collaudo ne ha controllate {n} di affermazioni.",
     "The test verified statements 1, 2, 3, 4 and 5 of the manual.",
     "The statements verified by the test are {n}.",
     "5", "9"),
    ("La squadra di turno era composta da Rossi, Bianchi, Verdi e Neri.",
     "Gli operai della squadra di turno sono {n}.",
     "Nella squadra di turno c'erano {n} addetti.",
     "The shift crew was made up of Rossi, Bianchi, Verdi and Neri.",
     "The workers in the shift crew are {n}.",
     "4", "10"),
    ("Il modulo e' importato da parser.py, engine.py e report.py.",
     "I file che importano il modulo sono {n}.",
     "A richiamare il modulo sono {n} file.",
     "The module is imported by parser.py, engine.py and report.py.",
     "The files importing the module are {n}.",
     "3", "7"),
    ("Il verbale cita le sedi di Torino e di Genova.",
     "Le sedi citate nel verbale sono {n}.",
     "Il verbale menziona {n} sedi aziendali.",
     "The minutes cite the offices of Turin and Genoa.",
     "The offices cited in the minutes are {n}.",
     "2", "7"),
    ("Nel magazzino restano i pallet numero 4 e numero 7.",
     "I pallet rimasti in magazzino sono {n}.",
     "Restano {n} pallet nel deposito.",
     "The pallets numbered 4 and 7 remain in the warehouse.",
     "The pallets remaining in the warehouse are {n}.",
     "2", "8"),
]


def in_lettere(testo, cifra):
    """La fonte con il numero scritto in lettere invece che in cifra.

    Sui casi di CONTEGGIO la cifra nella fonte non c'e' (o e' un'etichetta, non
    una quantita'): il replace non trova nulla e la fonte resta identica — ed e'
    giusto cosi', perche' li' l'unico posto dove il numero compare e' il claim.
    """
    return testo.replace(cifra, PAROLA[cifra], 1)


def condizioni(caso, gruppo):
    """Le quattro forme dello STESSO caso: (nome, fonte, template).

    ⚠️ La fonte va convertita in lettere SOLO nel gruppo «copia», dove la cifra
    e' una quantita'. Nel «conteggio» le cifre della fonte sono ETICHETTE (`A3`,
    `pallet numero 4`) e un replace cieco scriverebbe «A1, A2 e Atre»: avrei
    cambiato la fonte invece della forma del numero, e il confronto direbbe
    un'altra cosa. Trovato prima di eseguire, guardando il caso 1.
    """
    f_it, c_it, c_par, f_en, c_en, vero, _falso = caso
    f_parola = in_lettere(f_it, vero) if gruppo == "copia" else f_it
    return [
        ("canonica",  f_it,       c_it),
        ("parola",    f_parola,   c_it),
        ("parafrasi", f_it,       c_par),
        ("inglese",   f_en,       c_en),
    ]


FORME = ["canonica", "parola", "parafrasi", "inglese"]
GRUPPI = (("copia", CASI), ("conteggio", CASI_CONTEGGIO))
falsi_passati, veri_fermati, chi_ferma_falsi, chi_ferma_veri = {}, {}, {}, {}
for _g, _ in GRUPPI:
    for _f in FORME:
        falsi_passati[(_g, _f)] = 0
        veri_fermati[(_g, _f)] = 0
        chi_ferma_falsi[(_g, _f)] = []
        chi_ferma_veri[(_g, _f)] = []

m = Memory()
print("M5 — LE TRE FORME SUGLI STESSI CASI, su DUE popolazioni\n")

for gruppo, casi in GRUPPI:
    print("\n=== il numero e' %s ===" %
          ("COPIATO dalla fonte" if gruppo == "copia" else "da CONTARE nella fonte"))
    print("%-11s %-5s %-46s %-13s %s" % ("forma", "verit", "claim", "esito", "chi ferma"))
    print("-" * 104)
    for i, caso in enumerate(casi, 1):
        vero, falso = caso[5], caso[6]
        for nome, fonte, tmpl in condizioni(caso, gruppo):
            for etichetta, valore in (("VERO", vero), ("falso", falso)):
                # nella forma «parola» anche il numero del claim va in lettere,
                # o cambierebbero DUE cose e il confronto direbbe un'altra cosa
                n = PAROLA[valore] if nome == "parola" else valore
                prop = tmpl.format(n=n)
                r = m.add(prop, topic="ws3/M5-%s-%s-%d" % (gruppo, nome, i),
                          source=fonte)
                st = (r.get("status") or "?") if isinstance(r, dict) else "?"
                qb = ",".join(str(w.get("layer", "?"))
                              for w in (r.get("warnings") or [])) if isinstance(r, dict) else "-"
                fermato = (st == "quarantined")
                k = (gruppo, nome)
                if etichetta == "falso":
                    if fermato:
                        chi_ferma_falsi[k].append(qb or "(nessuno)")
                    else:
                        falsi_passati[k] += 1
                elif fermato:
                    veri_fermati[k] += 1
                    chi_ferma_veri[k].append(qb or "(nessuno)")
                print("%-11s %-5s %-46s %-13s %s"
                      % (nome, etichetta, prop[:46], st, qb))
        print()

print("=" * 104)
print("BASELINE M5 — sei casi per cella, prodotto di oggi\n")
print("%-11s %-11s %-15s %-14s %s"
      % ("popolaz.", "forma", "FALSI passati", "VERI fermati", "chi ferma i FALSI"))
for gruppo, _ in GRUPPI:
    for f in FORME:
        k = (gruppo, f)
        print("%-11s %-11s %-15s %-14s %s"
              % (gruppo, f, "%d/6" % falsi_passati[k], "%d/6" % veri_fermati[k],
                 ",".join(sorted(set(chi_ferma_falsi[k]))) or "-"))
    print()
print("  FALSI passati: piu' basso e' meglio (il gate deve fermarli)")
print("  VERI fermati : piu' basso e' meglio (sono i falsi allarmi)")
print("  `canonica` e' il RIFERIMENTO: le altre tre righe si leggono contro quella.")
print("  La colonna «chi ferma i FALSI» dice se a reggere e' lo strato LESSICALE")
print("  (`L4.1`) o il GIUDICE (`L4-grounding`): stesso esito, copertura diversa.")
print("\nrifallo con:")
print("  python docs/stato-reale/banchi/"
      "ws3-M5-baseline-le-tre-forme-sugli-stessi-casi.py")
