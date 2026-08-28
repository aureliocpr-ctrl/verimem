# -*- coding: utf-8 -*-
r"""REVIEW del design F1 (`L4.3`, doc `d809a433` di ws3) — ESEGUITA, non letta.

ws3 ha scritto: «le verifiche del meccanismo sono fatte A MANO SU CARTA, non
eseguite: possono essere sbagliate, ed e' il PRIMO posto dove guardare».
Questo banco esegue quelle verifiche, piu' la popolazione B che lui mi ha
chiesto di costruire senza mostrargliela.

RISULTATI

✅ **POPOLAZIONE B: 0 falsi positivi su 12**, in entrambi i regimi di ancore.
   Il criterio di ws3 («sopra 1 => DESIGN RESPINTO») **non scatta: il design
   passa la mia prova**. Lo 0/12 vale SOLO perche' il controllo positivo (blocco
   C) segnala 2 su 2: un meccanismo che non segnala mai non produce falsi
   positivi, e uno zero senza controllo sarebbe cieco.

🔴 **MA IL CASO CANONICO DELLO SCAMBIO NON VIENE SEGNALATO** — quello del design
   doc, in nessuno dei due regimi. Causa isolata per differenza: il **passo 3
   assolve** perche' la frase sbagliata **condivide il sostantivo di testa**
   («penale per il ritardo» / «penale per difformita'»). Cambiando i due
   soggetti in modo che NON condividano il sostantivo («mora» / «abbuono»), la
   stessa regola **SEGNALA**.
   ⇒ **Basta UNA parola condivisa perche' il passo 3 dica OK — e in uno scambio
   reale il termine di testa e' comune per costruzione.** Mette in dubbio la
   predizione «SCAMBIO 10/12 -> <=3/12».

🔴 **IL PREREQUISITO `ancore()` NON ESISTE**, e la lista che c'e' lo rompe.
   `query_intent._STOP` sono **76 parole dichiarate per un ALTRO scopo** (i
   termini di contenuto di una query di CONTEGGIO). Assenti in IT: `il lo la al
   alla per con su da e`; in EN: `and for`. Con la lista vera, il caso
   metformina passa a `ok` per colpa di un ARTICOLO (`A-tocca=['il']`); con una
   lista sana torna `astieniti` come ws3 aveva previsto. ⇒ **Una delle tre
   verifiche a mano cambia esito a seconda della stoplist.**

🟡 **LE PERCENTUALI ESCONO SENZA UNITA'**: `pari al 5%` -> `('', 5.0)`, come
   `5 per cento`. Il passo 4 richiede «la STESSA unita'»: con `''` una
   percentuale e un numero adimensionale sono indistinguibili. E `il 5 marzo`
   -> `[]`: **le date non sono valori per l'estrattore**, quindi `L4.3` non le
   vedra' mai.

✅ **`L4.2` ESISTE GIA'** (`vicinato_del_valore.valori_riusati_da_altro_contesto`)
   e copre lo STESSO perimetro dichiarato — «il valore c'e' ma parla d'altro» —
   con una finestra piu' stretta: UNA parola per lato. Misurato: **tace sul caso
   canonico**, perche' nel claim e nella fonte il vicinato del `5%` e' identico
   («al … del»), essendo identica la formula burocratica. ⇒ Non e' ridondanza,
   ma il doc dovrebbe dichiarare la disgiunzione anche verso `L4.2`, non solo
   verso `L4.1`, o si avranno due referti sulla stessa ricevuta.

⚖️ PUNTI DEBOLI, in ordine di quanto possono ribaltare il referto:
 1. **il prototipo e' MIO** — il codice di `L4.3` non esiste. Un difetto del
    prototipo si legge come difetto del design: **ne ho gia' trovato uno mio**
    (non toglievo i token dell'unita' dalle ancore, e `mg` faceva da ancora).
    Corretto prima di misurare; un secondo puo' essermi sfuggito.
 2. **la segmentazione in frasi e' mia** (`split` su `.!?`): nel gate non l'ho
    trovata. Su elenchi puntati e articoli di contratto NON segmenta, ed e'
    esattamente la domanda (2) che ws3 ha girato a @ws4.
 3. **12 casi costruiti da me**, IT+EN, prosa contrattuale e medica: non e' un
    corpus vero, e la popolazione B e' l'unica difesa contro un design cucito
    sul banco di chi lo propone.
 4. lo `0/12` **non dice «sicuro»**: dice «su queste 12 forme non ho trovato».

REGIME: build corrente · python 3.13.12 · NESSUN modello caricato (funzioni pure,
`extract_quantities` + `query_intent._STOP` + `valori_riusati_da_altro_contesto`)
· nessuna riga scritta nel prodotto · baseline design `d809a433`.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-review-F1-il-passo-3-assolve-lo-scambio.py
"""
import sys, re
sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.quantity_match import extract_quantities
from verimem.query_intent import _STOP

_PAROLA = re.compile(r"[^\W\d_]+", re.UNICODE)
_UNITA = {"mg","kg","euro","eur","giorni","giorno","mesi","mese","anni","anno",
          "ore","ora","minuti","pezzi","metri","mm","cm","usd","dollari","km","ml"}
_SANE = {"il","lo","la","i","gli","le","un","uno","una","del","dello","della","dei",
         "degli","delle","al","allo","alla","ai","agli","alle","dal","dalla","nel",
         "nella","nei","sul","sulla","per","con","su","da","e","ed","o","od","se",
         "ma","come","piu","meno","essere","stato","viene","pari","ammonta","era",
         "and","for","or","but","its","it","this","that","be","been","at","by","from"}

def frasi(t): return [f.strip() for f in re.split(r"(?<=[.!?])\s+", t) if f.strip()]

def ancore(t, regime):
    stop = _STOP if regime == "P" else (_STOP | _SANE)
    return {w.casefold() for w in _PAROLA.findall(t)
            if w.casefold() not in stop and w.casefold() not in _UNITA and len(w) > 1}

def L43(claim, fonte, regime):
    q_claim, q_fonte = extract_quantities(claim), extract_quantities(fonte, come_fonte=True)
    vals_fonte = {vv for _, vv in q_fonte}
    A = ancore(claim, regime)
    for (unita, v) in sorted(q_claim):
        if v not in vals_fonte: continue                       # passo 1
        if not (A & ancore(fonte, regime)): return "astieniti", "passo 2"
        fcv = [f for f in frasi(fonte)
               if v in {vv for _, vv in extract_quantities(f, come_fonte=True)}]
        if any(A & ancore(f, regime) for f in fcv):
            continue                                           # passo 3 OK
        for f in frasi(fonte):
            if not (A & ancore(f, regime)): continue
            for (u2, v2) in extract_quantities(f, come_fonte=True):
                if v2 != v and u2 == unita:
                    return "SEGNALA", "passo 4: %s %s invece di %s" % (v2, u2 or "-", v)
        return "astieniti", "passo 5"
    return "ok", "passo 1/3"

FP = ("Il contratto prevede una penale per il ritardo nella consegna pari al 2% "
      "del valore dell'ordine. E' inoltre prevista una penale per difformita' "
      "qualitativa pari al 5% del corrispettivo.")
FM = "Il paziente assume metformina. Il dosaggio e' 850 mg."
A_MANO = [("scambio penale 5%", "La penale per il ritardo e' pari al 5%", FP, "SEGNALA"),
          ("vero    penale 2%", "La penale per il ritardo e' pari al 2%", FP, "ok"),
          ("vero    metformina", "Il paziente assume metformina 850 mg",  FM, "astieniti")]

print("=== A: le tre verifiche di ws3, nei DUE regimi ===")
print("  %-20s %-24s %-24s" % ("caso", "regime P (lista vera)", "regime S (lista sana)"))
for nome, c, f, atteso in A_MANO:
    eP, _ = L43(c, f, "P"); eS, dS = L43(c, f, "S")
    mk = lambda e: e + (" ✔" if e == atteso else " ✘")
    print("  %-20s %-24s %-24s  atteso=%s" % (nome, mk(eP), mk(eS), atteso))

# ---- POPOLAZIONE B: claim VERI, sostenuti dalla fonte, prosa realistica ------
B = [
 ("parafrasi fedele", "Il canone mensile ammonta a 1.200 euro.",
  "Il conduttore corrisponde un canone mensile di 1.200 euro."),
 ("sinonimo del soggetto", "La sanzione per il ritardo e' del 2%.", FP),
 ("valore preso da frase con ANAFORA", "Il canone dell'appartamento e' di 1.200 euro.",
  "Il canone del box e' di 100 euro. Quello dell'appartamento ammonta a 1.200 euro."),
 ("due valori stessa unita', stessa frase", "Il deposito e' di 2.400 euro.",
  "Il canone e' di 1.200 euro e il deposito e' di 2.400 euro."),
 ("serie storica dello stesso soggetto", "Il canone e' di 1.200 euro.",
  "Il canone iniziale era di 1.000 euro. Dal 2025 il canone e' di 1.200 euro."),
 ("elenco puntato", "Le spese condominiali sono 150 euro.",
  "Oneri accessori: canone mensile 1.200 euro; spese condominiali 150 euro."),
 ("EN parafrasi", "The monthly rent is 1200 euro.",
  "The tenant pays a monthly rent of 1200 euro."),
 ("EN due soggetti", "The penalty for delay is 2%.",
  "A penalty for delay of 2% applies. A penalty for defects of 5% applies."),
 ("unita' assente nel claim", "Il preavviso e' di 6.",
  "Il preavviso di disdetta e' di 6 mesi. La durata e' di 4 anni."),
 ("soggetto solo nel titolo", "La franchigia e' di 500 euro.",
  "Polizza incendio. Massimale 100.000 euro. Franchigia 500 euro."),
 ("numero come identificativo", "L'ordine 77 e' stato evaso.",
  "L'ordine 77 risulta evaso il 3 marzo. L'ordine 88 e' in attesa."),
 ("valore ripetuto in due ruoli", "Lo sconto applicato e' del 5%.",
  "Lo sconto applicato e' del 5%. La penale per difformita' e' del 5%."),
]
print("\n=== B: POPOLAZIONE B - claim VERI e sostenuti (un SEGNALA = falso positivo) ===")
fpP = fpS = 0
for nome, c, f in B:
    eP, dP = L43(c, f, "P"); eS, dS = L43(c, f, "S")
    if eP == "SEGNALA": fpP += 1
    if eS == "SEGNALA": fpS += 1
    flag = "  <== FALSO POSITIVO" if eS == "SEGNALA" else ""
    print("  %-40s P=%-10s S=%-10s %s%s" % (nome[:40], eP, eS, dS if eS=="SEGNALA" else "", flag))
print("\n  FALSI POSITIVI  regime P (lista vera del prodotto): %d su %d" % (fpP, len(B)))
print("  FALSI POSITIVI  regime S (lista sana):              %d su %d" % (fpS, len(B)))
print("  CRITERIO ws3: >1 => DESIGN RESPINTO  ->  P: %s   S: %s"
      % ("RESPINTO" if fpP > 1 else "passa", "RESPINTO" if fpS > 1 else "passa"))

# ---- CONTROLLO POSITIVO: senza questo, lo 0/12 non significa nulla ----------
CTRL = [
 ("scambio COSTRUITO (il passo 4 DEVE scattare)",
  "Il canone del box e' di 1200 euro.",
  "Il canone del box e' di 100 euro. Quello dell'appartamento ammonta a 1200 euro.",
  "SEGNALA"),
 ("scambio penale, MA con soggetti che NON condividono il sostantivo",
  "La mora per il ritardo e' pari al 5%.",
  "La mora per il ritardo e' pari al 2%. L'abbuono per difformita' e' pari al 5%.",
  "SEGNALA"),
]
print("\n=== C: CONTROLLO POSITIVO - il prototipo sa segnalare? ===")
n_seg = 0
for nome, c, f, atteso in CTRL:
    eS, dS = L43(c, f, "S")
    if eS == "SEGNALA": n_seg += 1
    print("  %-52s S=%-10s %s  (atteso %s)" % (nome[:52], eS, dS, atteso))
print("  segnalazioni: %d su %d" % (n_seg, len(CTRL)))
if n_seg == 0:
    print("  !! IL BANCO E' CIECO: lo 0/12 della popolazione B non significa nulla.")
else:
    print("  ✔ il banco separa: lo 0/12 e' informativo.")

print("\n=== D: le UNITA' che l'estrattore vero attribuisce ===")
for t in ["pari al 5%", "5 giorni", "1200 euro", "850 mg", "il 5 marzo", "5 per cento"]:
    print("  %-16s -> %s" % ("'"+t+"'", sorted(extract_quantities(t, come_fonte=True))))
