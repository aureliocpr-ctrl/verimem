# -*- coding: utf-8 -*-
r"""F1 - VALIDAZIONE CIECA della regola FINALE di @ws3 (passo 2-bis + passo 3 curato).

@ws3 ha scritto nel suo doc: «ho corretto la regola DOPO aver visto quali casi
fallivano => il 12/12 e' sul set di taratura e NON conta come validazione. La
validazione richiede la popolazione B di @ws5 e casi che non ho visto. Il banco
lo scriva chi non ha in mente la cura, e quel banco non e' mio.»

Questo e' quel banco. **Nessun caso qui e' stato visto da chi ha scritto la
regola**, ed e' l'unica proprieta' che lo rende una validazione.

DUE POPOLAZIONI, consegnate insieme - perche' uno 0 falsi positivi ottenuto da
una regola che si astiene sempre non vale niente:
  A'  16 SCAMBI miei, 8 domini, IT+EN   -> deve SEGNALARE
  B'  16 claim VERI e sostenuti          -> non deve segnalare

DUE REGIMI di ancore, perche' il prerequisito `ancore()` non esiste:
  P = query_intent._STOP (la lista VERA del prodotto, 76 parole, altro scopo)
  S = P + articoli e preposizioni IT/EN (la lista di cui il design avrebbe bisogno)

REGIME: build corrente - nessun modello caricato - `extract_quantities` vero -
regola trascritta dal doc `F1-DESIGN-DOC-strato-soggetto-valore.md` sezione 7.
PUNTO DEBOLE: la regola e' TRASCRITTA da me, il codice non esiste. Un mio errore
di trascrizione si legge come un difetto del design - e me n'e' gia' sfuggito uno
(non toglievo le unita' dalle ancore). La segmentazione in frasi e' la mia
(`split` su `.!?`): sugli elenchi puntati non segmenta.

ESITO - il design NON passa: 3 falsi positivi contro un criterio che ne ammette 1.

    A' SCAMBI  15 su 16 segnalati      <- l'intuizione GENERALIZZA su casi mai visti
    B' VERI     3 FALSI POSITIVI su 16 <- il criterio di @ws3 era «sopra 1 => RESPINTO»
    separazione: 15/16 contro 3/16

I TRE FALSI POSITIVI, in ordine di gravita':

(1) LA CURA DEL PASSO 3 LI PRODUCE. Fonte «Il canone e' di 1200 euro e il
    deposito e' di 2400 euro.», claim VERO «Il deposito e' di 2400 euro.»
    -> SEGNALA «1200 invece di 2400».
    CONTROFATTUALE nel blocco C, che isola la causa: la STESSA informazione
    spezzata in DUE frasi da' `ok`; nella stessa frase da' `SEGNALA`. Cambia
    solo il punto fermo.
    MECCANISMO: la cura dice che una frase con >=2 valori della stessa unita'
    non e' una finestra utilizzabile e si cade ai passi 4/5. Ma su un claim
    VERO il passo 4 trova SEMPRE l'altro valore di quella frase. «Fallire in
    sicurezza verso astensione-o-segnalazione» diventa, sul vero, «fallire
    verso il falso positivo».
    NON E' UN CASO RARO: @ws3 ha introdotto quella cura proprio perche' aveva
    misurato che il 28,7% delle frasi con un valore ne portano due.

(2) IDENTIFICATIVI. «L'ordine 77 e' stato evaso», fonte «L'ordine 77 risulta
    evaso. L'ordine 88 e' in attesa.» -> SEGNALA «88 invece di 77».
    Un identificativo non e' una quantita'. `L4.2` questa distinzione CE
    L'HA GIA', posizionale e senza liste di parole: «un identificativo SEGUE
    il suo sostantivo, una quantita' lo PRECEDE» (docstring di
    `vicinato_del_valore`). `L4.3` non ce l'ha. E' il difetto piu' facile da
    curare dei tre, e la cura esiste gia' in casa.

(3) ELENCO PUNTATO. «Oneri accessori: canone mensile 1200 euro; spese
    condominiali 150 euro.» -> SEGNALA su un claim vero.
    ATTENZIONE: qui la causa puo' essere MIA. La mia segmentazione spezza su
    `.!?` e non sul `;`, quindi l'elenco resta una frase sola e ricade nel
    caso (1). E' la domanda (2) che @ws3 ha girato a @ws4 e resta aperta: se
    la segmentazione vera spezza gli elenchi, questo FP sparisce e restano due.

CIO' CHE IL BANCO CONFERMA, ed e' la parte buona: **15 scambi su 16** colti su
casi mai visti da chi ha scritto la regola, in 8 domini e due lingue, tutti col
termine di testa CONDIVISO (il caso difficile). L'intuizione delle ancore
discriminanti non e' cucita sul banco di taratura: generalizza.
L'unico scambio mancato e' quello a **unita' diverse** (`12 mesi` contro `30
giorni`), dove il passo 2-bis si astiene - ed e' coerente col design, che sulle
unita' diverse dichiara di non avere una regola.

RIPRODUCI:  python docs/stato-reale/banchi/ws5-F1-validazione-cieca-regola-finale.py
"""
import sys
import re

sys.path.insert(0, r"C:\Users\aurel\Code\HippoAgent")
from verimem.quantity_match import extract_quantities
from verimem.query_intent import _STOP

_PAROLA = re.compile(r"[^\W\d_]+", re.UNICODE)
_UNITA = {"mg", "kg", "euro", "eur", "giorni", "giorno", "mesi", "mese", "anni",
          "anno", "ore", "ora", "minuti", "pezzi", "metri", "mm", "cm", "usd",
          "dollari", "km", "ml", "punti"}
_SANE = {"il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "del", "dello",
         "della", "dei", "degli", "delle", "al", "allo", "alla", "ai", "agli",
         "alle", "dal", "dalla", "nel", "nella", "nei", "sul", "sulla", "per",
         "con", "su", "da", "e", "ed", "o", "od", "se", "ma", "come", "piu",
         "meno", "essere", "stato", "viene", "pari", "ammonta", "era", "and",
         "for", "or", "but", "its", "it", "this", "that", "be", "been", "at",
         "by", "from", "the", "of", "is", "to", "a", "an", "in", "on", "with"}


def frasi(t):
    return [f.strip() for f in re.split(r"(?<=[.!?])\s+", t) if f.strip()]


def ancore(t, regime):
    stop = _STOP if regime == "P" else (_STOP | _SANE)
    return {w.casefold() for w in _PAROLA.findall(t)
            if w.casefold() not in stop and w.casefold() not in _UNITA
            and len(w) > 1}


def qty(t):
    return extract_quantities(t, come_fonte=True)


def L43_finale(claim, fonte, regime):
    """La regola della sezione 7: passo 2-bis (ancore DISCRIMINANTI) + passo 3 curato."""
    A = ancore(claim, regime)
    for (unita, v) in sorted(extract_quantities(claim)):
        if v not in {vv for _, vv in qty(fonte)}:
            continue                                    # passo 1: e' L4.1
        if not (A & ancore(fonte, regime)):
            return "astieniti", "passo 2"
        cand = [f for f in frasi(fonte) if any(u == unita for u, _ in qty(f))]
        A_disc = {a for a in A
                  if sum(1 for f in cand if a in ancore(f, regime)) == 1}
        if not A_disc:
            return "astieniti", "passo 2-bis: nessuna ancora discriminante"
        for f in cand:
            if v not in {vv for _, vv in qty(f)}:
                continue
            if not (A_disc & ancore(f, regime)):
                continue
            if sum(1 for u, _ in qty(f) if u == unita) >= 2:
                continue                                # finestra inutilizzabile
            return "ok", "passo 3"
        for f in cand:
            if not (A_disc & ancore(f, regime)):
                continue
            for (u2, v2) in qty(f):
                if v2 != v and u2 == unita:
                    return "SEGNALA", "passo 4: %s invece di %s" % (v2, v)
        return "astieniti", "passo 5"
    return "ok", "passo 1/nessun valore"


# ---------- A' : 16 SCAMBI (il claim e' FALSO, deve SEGNALARE) ----------------
A1 = [
 ("commerciale, testa condivisa 'penale'", "La penale per il ritardo e' di 500 euro.",
  "La penale per il ritardo e' di 200 euro. La penale per difformita' e' di 500 euro."),
 ("locazione, testa condivisa 'canone'", "Il canone del box e' di 1200 euro.",
  "Il canone del box e' di 100 euro. Il canone dell'appartamento e' di 1200 euro."),
 ("lavoro, testa condivisa 'indennita'", "L'indennita' di trasferta e' di 80 euro.",
  "L'indennita' di trasferta e' di 50 euro. L'indennita' di rischio e' di 80 euro."),
 ("medico, testa condivisa 'dosaggio'", "Il dosaggio del ramipril e' 10 mg.",
  "Il dosaggio del ramipril e' 5 mg. Il dosaggio della metformina e' 10 mg."),
 ("tecnico, testa condivisa 'tolleranza'", "La tolleranza dell'albero e' 30 mm.",
  "La tolleranza dell'albero e' 12 mm. La tolleranza del foro e' 30 mm."),
 ("logistica, testa condivisa 'scorta'", "La scorta minima e' di 400 pezzi.",
  "La scorta minima e' di 120 pezzi. La scorta di sicurezza e' di 400 pezzi."),
 ("assicurativo, testa condivisa 'massimale'", "Il massimale incendio e' 300 euro.",
  "Il massimale incendio e' 100000 euro. Il massimale furto e' 300 euro."),
 ("bancario, testa condivisa 'tasso'", "Il tasso del mutuo e' 9 punti.",
  "Il tasso del mutuo e' 3 punti. Il tasso dello scoperto e' 9 punti."),
 ("scadenze, testa condivisa 'termine'", "Il termine di consegna e' 60 giorni.",
  "Il termine di consegna e' 30 giorni. Il termine di collaudo e' 60 giorni."),
 ("energia, testa condivisa 'consumo'", "Il consumo in stand-by e' 900 ore.",
  "Il consumo in stand-by e' 12 ore. Il consumo a pieno carico e' 900 ore."),
 ("EN, head shared 'fee'", "The shipping fee is 45 euro.",
  "The shipping fee is 12 euro. The handling fee is 45 euro."),
 ("EN, head shared 'salary'", "The base salary is 4000 euro.",
  "The base salary is 2500 euro. The bonus salary is 4000 euro."),
 ("testa DIVERSA (controllo: caso piu' facile)", "La mora per il ritardo e' 500 euro.",
  "La mora per il ritardo e' 200 euro. L'abbuono per difformita' e' 500 euro."),
 ("tre frasi, il distrattore in mezzo", "Il canone e' di 900 euro.",
  "Il canone e' di 400 euro. Le spese sono di 150 euro. Il deposito e' di 900 euro."),
 ("scambio con unita' DIVERSE", "La durata e' di 30 giorni.",
  "La durata e' di 12 mesi. Il preavviso e' di 30 giorni."),
 ("scambio su decimali", "Lo sconto e' di 5.5 euro.",
  "Lo sconto e' di 2.5 euro. La commissione e' di 5.5 euro."),
]

# ---------- B' : 16 claim VERI e sostenuti (NON deve segnalare) ---------------
B1 = [
 ("parafrasi fedele", "Il canone mensile ammonta a 1200 euro.",
  "Il conduttore corrisponde un canone mensile di 1200 euro."),
 ("sinonimo del soggetto", "La sanzione per il ritardo e' di 200 euro.",
  "La penale per il ritardo e' di 200 euro. La penale per difformita' e' di 500 euro."),
 ("anafora 'quello'", "Il canone dell'appartamento e' di 1200 euro.",
  "Il canone del box e' di 100 euro. Quello dell'appartamento ammonta a 1200 euro."),
 ("anafora 'essa'", "L'indennita' di trasferta e' di 50 euro.",
  "L'indennita' di trasferta e' disciplinata dall'accordo. Essa ammonta a 50 euro."),
 ("due valori stessa unita' nella stessa frase", "Il deposito e' di 2400 euro.",
  "Il canone e' di 1200 euro e il deposito e' di 2400 euro."),
 ("serie storica dello stesso soggetto", "Il canone e' di 1200 euro.",
  "Il canone iniziale era di 1000 euro. Dal 2025 il canone e' di 1200 euro."),
 ("elenco puntato", "Le spese condominiali sono 150 euro.",
  "Oneri accessori: canone mensile 1200 euro; spese condominiali 150 euro."),
 ("soggetto solo nel titolo", "La franchigia e' di 500 euro.",
  "Polizza incendio. Massimale 100000 euro. Franchigia 500 euro."),
 ("EN parafrasi", "The monthly rent is 1200 euro.",
  "The tenant pays a monthly rent of 1200 euro."),
 ("EN due soggetti, claim vero", "The shipping fee is 12 euro.",
  "The shipping fee is 12 euro. The handling fee is 45 euro."),
 ("numero come identificativo", "L'ordine 77 e' stato evaso.",
  "L'ordine 77 risulta evaso. L'ordine 88 e' in attesa."),
 ("valore ripetuto in due ruoli", "Lo sconto applicato e' di 5 euro.",
  "Lo sconto applicato e' di 5 euro. La penale per difformita' e' di 5 euro."),
 ("vero con due unita' nel claim", "Il preavviso e' di 6 mesi su una durata di 4 anni.",
  "Il preavviso di disdetta e' di 6 mesi. La durata del contratto e' di 4 anni."),
 ("vero, soggetto ripetuto in tutte le frasi", "Il canone e' di 1200 euro.",
  "Il canone e' dovuto mensilmente. Il canone e' di 1200 euro. Il canone e' rivalutato."),
 ("vero con apposizione", "La tolleranza del foro e' 30 mm.",
  "La tolleranza dell'albero, misurata a freddo, e' 12 mm. La tolleranza del foro e' 30 mm."),
 ("vero, riformulazione con verbo diverso", "Il fornitore ha spedito 850 telai.",
  "Il fornitore ha realizzato 850 telai nel primo trimestre."),
]


def esegui(pop, atteso, regime):
    giusti = 0
    righe = []
    for nome, c, f in pop:
        e, d = L43_finale(c, f, regime)
        ok = (e == "SEGNALA") if atteso == "SEGNALA" else (e != "SEGNALA")
        giusti += ok
        righe.append((nome, e, d, ok))
    return giusti, righe


for regime in ("P", "S"):
    et = "lista VERA del prodotto" if regime == "P" else "lista sana"
    print("\n" + "=" * 74)
    print("REGIME %s (%s)" % (regime, et))
    gA, rA = esegui(A1, "SEGNALA", regime)
    gB, rB = esegui(B1, "tace", regime)
    print("  A' SCAMBI (deve segnalare): %2d su %d segnalati" % (gA, len(A1)))
    for nome, e, d, ok in rA:
        if not ok:
            print("      MANCATO  %-42s %-10s [%s]" % (nome[:42], e, d))
    print("  B' VERI (non deve segnalare): %2d su %d salvi -> %d FALSI POSITIVI"
          % (gB, len(B1), len(B1) - gB))
    for nome, e, d, ok in rB:
        if not ok:
            print("      FALSO POSITIVO  %-36s %-10s [%s]" % (nome[:36], e, d))
    print("  ---- separazione: scambi colti %d/%d  contro  falsi positivi %d/%d"
          % (gA, len(A1), len(B1) - gB, len(B1)))

# ---- C: CONTROFATTUALE che isola la causa del primo falso positivo ----------
print("\n" + "=" * 74)
print("C: CONTROFATTUALE - la stessa informazione, una frase contro due")
_c = "Il deposito e' di 2400 euro."
for _et, _f in [("una frase (2 valori euro)",
                 "Il canone e' di 1200 euro e il deposito e' di 2400 euro."),
                ("due frasi (1 valore ciascuna)",
                 "Il canone e' di 1200 euro. Il deposito e' di 2400 euro.")]:
    print("  %-30s -> %s" % (_et, L43_finale(_c, _f, "S")))
print("  ^ il claim e' VERO in entrambi i casi. Cambia solo il punto fermo.")
