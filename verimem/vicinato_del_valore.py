"""Il numero c'è nella fonte, ma parla d'altro.

IL BUCO DI L4.1, emerso verificando la cura in indipendenza::

    «Il fornitore Gatti ha consegnato 14 valvole.»  ->  100.0  AMMESSO
     la fonte dice «14 operai»

    cifra RIUSATA: fermati 0/3   ·   cifra NUOVA: fermati 3/3

``valori_non_nella_fonte`` confronta i VALORI e non le coppie (unità, valore),
e il suo docstring lo dichiarava — *«l'unità in un testo libero è la parola che
segue, troppo fragile per farci poggiare un veto»*. La giustificazione regge
ancora; **quello che era sbagliato è la stima del costo**: in un documento
aziendale le cifre da 1 a 20 sono ovunque (date, numeri di linea, percentuali),
e un'allucinazione con un numero piccolo trova quasi sempre una cifra gemella.
Un limite dichiarato ma sottostimato resta un difetto, non una scelta.

LA DOMANDA CHE HA DECISO LA CURA, misurata prima di scrivere una riga: **nei
VERI RIFORMULATI il sostantivo che segue il numero cambia o resta?**::

                            vicinato UGUALE   DIVERSO
    inventati, cifra riusata        0            7      <- 7 casi, due autori
    veri riformulati              10            1      <- 11 casi, due autori

Resta, e per una ragione strutturale: **riformulare cambia il VERBO e la
struttura, non l'UNITÀ DI MISURA**. «prodotti 850 telai» → «realizzato 850
telai»; euro resta euro, giorni resta giorni. È questo che rende il vicinato un
segnale più stretto della copertura lessicale, caduta con 6 falsi
positivi su 8 proprio perché guardava TUTTE le parole — che invece cambiano.

⚠️ IL FALSO POSITIVO, e il perché della seconda metà del criterio. L'unico caso
mancato è «La linea 3 **è rimasta** operativa» contro una fonte che dice «La
linea 3 **ha lavorato**»: lì il 3 non è una quantità, è un IDENTIFICATIVO, e
quello che lo segue è un verbo — che la riformulazione cambia.

🔑 La distinzione è posizionale, non lessicale: **un identificativo SEGUE il suo
sostantivo** («linea 3», «ordine 77»), **una quantità lo PRECEDE** («3 anni»).
Quindi il criterio guarda entrambi i lati e tace quando il lato *precedente*
coincide — nessuna lista di parole, e la posizione regge in IT/EN/DE/FR/ES.

⚠️ E PER QUESTO DICHIARA INVECE DI QUARANTINARE — la scelta è misurata, non
prudenziale. La prima stesura faceva fallire il write, e ha rotto un presidio
verde scritto in indipendenza: «A Prato ci sono **300 pallet** stoccati» contro una fonte
che dice «il deposito di Prato **ospita 300 bancali**». Lì cambiano *entrambi*
i lati — verbo e sostantivo — e il criterio scatta::

    banco lingue, riformulati VERI   falsi positivi  1/5  (20%)
    inventati con cifra riusata      colpiti         7/7

80 punti di separazione, sopra la soglia dei 40 — eppure il caso che sbaglia è
il sinonimo puro, che in un prodotto internazionale è ovunque, e **una cura che
rompe il presidio verde di un altro non si consegna come veto.** Resta come
avviso: dice che il numero è riusato da un altro contesto e lascia decidere.

📌 La misura che me l'ha nascosto per un'ora vale più del criterio: i sinonimi
li avevo provati tenendo lo STESSO verbo («ospita 300 pallet» contro «ospita 300
bancali»), cambiando una cosa sola — e il criterio vinceva perché l'altro lato
coincideva. Chi ha scritto il banco, non sapendo di questo criterio, aveva prodotto la
riformulazione vera, che cambia tutto. **Un banco scritto da chi propone il
criterio lo misura contro sé stesso**, ed è la trappola già registrata in casa.

⚠️ LIMITI DICHIARATI:
  * non copre l'INVERSIONE: «sono state respinte 60 casse» contro una fonte che
    dice «spedite 60 casse» ha lo stesso vicinato e passa. Quella è la classe
    delle negazioni/inversioni, che è un altro buco noto e non si cura
    con un confronto di token.
  * lingue senza spaziatura fra le parole restano scoperte: il vicinato è
    definito sui token alfabetici.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .quantity_match import extract_quantities

__all__ = ["ValoreRiusato", "valori_riusati_da_altro_contesto"]

_PAROLA = re.compile(r"[^\W\d_]+", re.UNICODE)


@dataclass(frozen=True)
class ValoreRiusato:
    """Un valore che la fonte contiene, ma riferito a un'altra grandezza."""
    valore: float
    nel_claim: str
    nella_fonte: str


#: Quante parole di contenuto si guardano per lato del numero (T17, 06/09).
_PAROLE_PER_LATO = 3
#: Raggio in caratteri entro cui si cercano; un fine riga o una cella di
#: tabella («|») chiudono il vicinato prima.
_RAGGIO = 60


def _vicinato_grezzo(testo: str, inizio: int, fine: int) -> list[str]:
    return [t.casefold() for t in _PAROLA.findall(testo[inizio:fine])]


def _intorno(testo: str, valore: float) -> tuple[set[str], set[str]]:
    """Le parole DI CONTENUTO vicine a ogni occorrenza del numero.

    Ritorna ``(seguenti, precedenti)``. Un numero può comparire più volte: si
    raccolgono tutte le occorrenze, perché al criterio basta che UNA regga lo
    stesso significato per non pronunciarsi.

    T17 (06/09, misurato su 7.974 fatti con span: l'avviso toccava il 50,8% e
    quasi sempre a torto, banco T17-quanti-avvisi-L42-toglie-ciascuna-regola):
    · il numero dentro un COMPOSTO — «03:27», «2026-09-06», «3/40» — non e' un
      numero a se': «27» non si cerca. Prima il lookbehind escludeva cifre,
      punto e virgola ma non i due punti, il trattino e la barra;
    · il numero seguito dal PUNTO FINALE («esce 2.») si trova: prima il
      lookahead lo escludeva e il claim risultava senza parole accanto;
    · si guardano fino a ``_PAROLE_PER_LATO`` parole di contenuto per lato,
      SALTANDO la grammatica: in prosa il numero e' preceduto da «sono /
      risulta / a» e seguito dal punto, e la grandezza sta due-tre parole
      prima («i gruppi con lo stesso testo sono 40»). Il vicinato si ferma al
      fine riga e alla cella di tabella;
    · una parola adiacente a un ALTRO numero e' l'etichetta di quello («Line
      3 … 22 days»: «line» e' del 3) e non entra nel vicinato di questo;
    · la forma ETICHETTA: valore dell'output di programma («STRUMENTI ESPOSTI A
      RUNTIME: 249», «EXIT=2») da' come lato precedente l'etichetta intera.
    """
    intero = int(valore) if float(valore).is_integer() else valore
    seguenti: set[str] = set()
    precedenti: set[str] = set()
    # «9» si scrive anche «9.0» / «9,0»: un intero con la coda decimale nulla e'
    # lo stesso numero, e si trova.
    forma = re.escape(str(intero)) + (r"(?:[.,]0+)?" if isinstance(intero, int) else "")
    # Il trattino esclude solo se PRECEDUTO DA UNA CIFRA («2026-09-06», «166-237»):
    # un numero NEGATIVO («-3 °C», «−12 dB») resta un numero (domanda del lead,
    # b10984ebf24c24c6; il meno tipografico U+2212 non e' nella classe).
    for m in re.finditer(rf"(?<![\d.,:/])(?<!\d-){forma}(?![\d,]|\.(?=\d))", testo):
        inizio = max(0, m.start() - _RAGGIO)
        fine = min(len(testo), m.end() + _RAGGIO)
        for sep in ("\n", "|"):
            j = testo.rfind(sep, inizio, m.start())
            if j >= 0:
                inizio = j + 1
            j = testo.find(sep, m.end(), fine)
            if j >= 0:
                fine = j
        prima_grezze = _vicinato_grezzo(testo, inizio, m.start())
        dopo_grezze = _vicinato_grezzo(testo, m.end(), fine)
        # Le parole IMMEDIATAMENTE accanto al nostro numero sono sue, anche se
        # altrove nel testo stanno accanto a un altro numero («6 casi … 96
        # casi», «verimem EXIT=0 ⏎ hippoagent EXIT=0»); e la parte decimale
        # del nostro numero non e' un altro numero.
        immediate = set(prima_grezze[-1:]) | set(dopo_grezze[:1])
        etichette_altrui = {
            t for n in re.finditer(r"\d+(?:[.,]\d+)?", testo)
            if n.end() <= m.start() or n.start() >= m.end()
            for t in (_vicinato_grezzo(testo, max(0, n.start() - 12), n.start())[-1:]
                      + _vicinato_grezzo(testo, n.end(), n.end() + 12)[:1])} - immediate
        prima = [t for t in prima_grezze
                 if t not in _GRAMMATICA and t not in etichette_altrui]
        dopo = [t for t in dopo_grezze
                if t not in _GRAMMATICA and t not in etichette_altrui]
        if re.search(r"[:=]\s*$", testo[max(0, m.start() - 3):m.start()]):
            precedenti |= set(prima)          # l'etichetta intera della riga
            seguenti |= set(dopo[:1])
            continue
        precedenti |= set(prima[-_PAROLE_PER_LATO:])
        seguenti |= set(dopo[:_PAROLE_PER_LATO])
    return seguenti, precedenti


#: Un numero dentro un composto — «03:27», «2026-09-06», «3/40», «2.14.0» — non
#: e' un numero a se'. Non i decimali semplici («97.05»), che restano numeri.
_COMPOSTO = re.compile(r"\d+(?:[:/-]\d+)+|\d+(?:\.\d+){2,}")


def _prefissi(parole: set[str]) -> set[str]:
    """Le flessioni non cambiano la grandezza: «exits»/«exit», «strumenti»/«strumento»."""
    return {p[:4] for p in parole}


#: Parole che NON nominano una grandezza: articoli, preposizioni, congiunzioni,
#: ausiliari, IT ed EN. Fino al 06/09 serviva solo al TESTO della ricevuta —
#: il criterio non la vedeva, «e questo e' voluto: filtrare il criterio
#: cambierebbe quali fatti vengono segnalati». Era vero, ed era il difetto:
#: misurato su 7.974 fatti, il criterio prendeva come grandezza il token
#: adiacente ANCHE quando era grammatica («sono 40», «risulta 3939») e
#: avvisava sul 50,8% dei fatti (T17). Ora la salta anche nel criterio, con i
#: numeri nel banco T17-quanti-avvisi-L42-toglie-ciascuna-regola.
#: ⚠️ La lista e' una scelta dichiarata: una voce in piu' o in meno sposta il
#: testo mostrato, mai il verdetto.
#:
#: 🪞 **CORRETTA IL 30/08, POCHE ORE DOPO ESSERE STATA SCRITTA.** La prima
#: stesura aveva sei ausiliari INGLESI (`is are was were be been`) e **zero
#: italiani** — in un prodotto usato in italiano. Il caso che l'ha mostrata e'
#: una ricevuta vera del prodotto, 19:02:36::
#:
#:     146 qui e' «hanno», nella fonte «prima del numero: quarantined»
#:
#: cioe' **la cura mancava il caso che l'aveva motivata**. Misurato sulla
#: popolazione intera (6261 fatti vivi con fonte, 5222 riusi) prima di toccare
#: una riga: lato `nel_claim` **221 occorrenze su 3323 (6.7%)**, lato
#: `nella_fonte` **14 su 6004 (0.2%)**. 🔑 L'asimmetria E' il reperto — il claim
#: e' prosa italiana, la fonte e' quasi sempre output di macchina.
#:
#: 🔴 **AMBIGUI TENUTI FUORI DI PROPOSITO**: «danno», «conta», «stato», «era»
#: in italiano sono ANCHE sostantivi, quindi possono essere una grandezza vera.
#: Una parola che puo' nominare una grandezza non entra in una lista di
#: non-grandezze, per quanto frequente sia come verbo.
_GRAMMATICA = frozenset({
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "l", "d",
    "del", "dello", "della", "dei", "degli", "delle", "dell", "di", "da",
    "dal", "dalla", "dai", "dagli", "dalle", "in", "nel", "nella", "nei",
    "negli", "nelle", "nell", "con", "col", "su", "sul", "sulla", "sui",
    "sugli", "sulle", "sull", "per", "tra", "fra", "a", "al", "allo",
    "alla", "ai", "agli", "alle", "all", "e", "ed", "o", "od", "ma",
    "che", "chi", "cui", "non", "come", "se", "si", "ne", "ci", "vi",
    "gia", "ancora", "solo", "anche", "poi", "piu", "meno", "ogni",
    "the", "an", "of", "on", "at", "to", "for", "and", "or", "is", "are",
    "was", "were", "be", "been", "with", "by", "from", "as", "it", "its",
    "this", "that", "these", "those", "not", "only", "also", "each",
    # ── ausiliari e copule IT, dal corpus e non dall'intuito (30/08): sono i
    #    token che il banco ha trovato ADIACENTI a un numero. «sono» era il 3°
    #    piu' frequente del lato claim (92) e «hanno» il 12° (61).
    "ha", "hanno", "sono", "sia", "siano", "sta", "stanno",
    "viene", "vengono", "risulta", "risultano", "resta", "restano",
    "diventa", "diventano", "vale", "valgono",
    # ── e le forme di `have`, che mancavano anche all'inglese gia' coperto
    "has", "have", "had",
})


def _da_mostrare(dopo: set[str], prima: set[str]) -> str:
    """Il contesto da mostrare nella ricevuta, col lato DICHIARATO.

    La decisione qui sopra guarda entrambi i lati del numero; il messaggio ne
    mostrava uno solo — quello che SEGUE. In italiano quel token e' spessissimo
    una congiunzione o una preposizione («0.3732 ed esito», «99.9588 su due»),
    e quando manca del tutto la ricevuta stampava «?» su entrambi i lati, cioe'
    niente su cui agire. Chi legge vedeva meta' dell'informazione con cui il
    layer aveva deciso (diagnosi del 18/08, letta al sorgente).

    Il lato precedente non sostituisce quello seguente: lo integra quando
    l'altro non c'e', e si annuncia, perche' «linea» detto senza dire da che
    parte sta rispetto al numero e' ambiguo quanto «?».

    ⚠️ ESTESO IL 30/08 — «quando l'altro non c'e'» diventa «quando l'altro NON
    DICE NIENTE». La riga sopra restava vera e insufficiente: il token adiacente
    puo' esserci ed essere **solo grammatica**, e allora la ricevuta stampa una
    grandezza che grandezza non e'. Il caso che l'ha aperto::

        26 qui e' «fatti», nella fonte «di fonti il la non su»

    MISURATO PRIMA DI CURARE (`W7-80`, popolazione INTERA, 6176 fatti con
    fonte): il lato `nella_fonte` e' **solo grammatica nel 15,5%** dei casi, il
    lato `nel_claim` nel **34,6%** — e l'avviso tocca **3077 fatti (49,8%)**.
    ⇒ Il commento qui sopra diceva «spessissimo», che e' un avverbio: ora c'e'
    il numero, ed e' **piu' basso di quanto l'avverbio lasciasse credere sul
    lato che nomina, e piu' alto sull'altro**.

    ⚖️ La regola originale NON e' rovesciata: quando il lato che segue e'
    PIENO resta quello (il presidio che lo fissa continua a passare). Cambia
    solo il caso in cui «c'e'» e «serve» non coincidono.
    """
    dopo_utili = {t for t in dopo if t not in _GRAMMATICA}
    prima_utili = {t for t in prima if t not in _GRAMMATICA}
    if dopo_utili:
        return " ".join(sorted(dopo_utili))
    if prima_utili:
        return "prima del numero: " + " ".join(sorted(prima_utili))
    if dopo or prima:
        # C'erano parole, ma nessuna nomina una grandezza. Dirlo e' meglio che
        # stamparle: chi legge crederebbe che QUELLA sia la grandezza.
        return "(solo parole grammaticali accanto)"
    return "(nessuna parola accanto)"


def valori_riusati_da_altro_contesto(
    proposition: str, source: str,
) -> list[ValoreRiusato]:
    """I valori del claim che la fonte contiene, ma riferiti ad altro.

    Vuoto quando manca uno dei due testi, quando il claim non porta numeri, e
    — per costruzione — per i valori ASSENTI dalla fonte: quelli sono già il
    perimetro di ``valori_non_nella_fonte`` e ripeterli qui darebbe due
    avvisi per lo stesso difetto.
    """
    if not proposition or not source:
        return []
    fuori: list[ValoreRiusato] = []
    composti_in_fonte = {c for c in _COMPOSTO.findall(proposition) if c in source}
    for _unita, valore in sorted(extract_quantities(proposition),
                                 key=lambda q: q[1]):
        intero = str(int(valore)) if float(valore).is_integer() else str(valore)
        if any(re.search(rf"(?<!\d){re.escape(intero)}(?!\d)", c) for c in composti_in_fonte):
            # T17: il numero sta in un COMPOSTO — orario, data, rapporto,
            # versione — che la fonte porta tale e quale: e' la stessa
            # grandezza. NON i decimali («97.05»): un decimale identico puo'
            # essere riusato da un altro soggetto, misurato (867621d4c810).
            continue
        claim_dopo, claim_prima = _intorno(proposition, valore)
        fonte_dopo, fonte_prima = _intorno(source, valore)
        if not fonte_dopo and not fonte_prima:
            continue  # valore assente: non è questo il criterio che lo copre
        if _prefissi(claim_dopo) & _prefissi(fonte_dopo):
            continue  # stessa grandezza: è una riformulazione, il caso normale
        if _prefissi(claim_prima) & _prefissi(fonte_prima):
            # Il lato che PRECEDE coincide: è lo stesso identificativo
            # («linea 3» in entrambi) e ciò che segue è un verbo, che la
            # riformulazione cambia legittimamente.
            continue
        if _prefissi(claim_dopo | claim_prima) & _prefissi(fonte_dopo | fonte_prima):
            # T17: la grandezza sta a DESTRA nel claim («249 strumenti») e a
            # SINISTRA nella fonte («STRUMENTI ESPOSTI A RUNTIME: 249»), che e'
            # la forma di ogni output di programma. I due lati si incrociano.
            continue
        fuori.append(ValoreRiusato(
            valore=valore,
            nel_claim=_da_mostrare(claim_dopo, claim_prima),
            nella_fonte=_da_mostrare(fonte_dopo, fonte_prima),
        ))
    return fuori
