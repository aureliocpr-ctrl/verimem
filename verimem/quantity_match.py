"""Shared numeric-quantity contradiction primitives.

A *numeric conflict* between two statements = they describe the SAME
subject (share a distinctive, non-unit content word) and assert a
DIFFERENT value for the SAME normalised unit, with NO contrasting
qualifier ("read" vs "write"). Pure lexical, zero LLM, embedding-free.

Single source of truth used by BOTH:
  • the write-time gate (``validate_claim`` — sibling of its year-disjoint
    contradiction rule), and
  • the batch corpus scanner (``facts_conflict.find_numeric_conflicts`` —
    surfaces numeric inconsistencies already present in memory).

Keeping the two paths on identical semantics is the point: a confab that
the write gate would flag must also be findable retroactively in the
corpus, and vice-versa.
"""
from __future__ import annotations

import re
import unicodedata

# 4-digit years (1500–2099). Bare years are NOT quantities — they belong
# to the year-disjoint rule in validate_claim, so the two detectors never
# double-handle the same number.
YEAR_RE = re.compile(r"\b(?:1[5-9]\d{2}|20\d{2})\b")

# A STANDALONE number optionally followed by a unit word: "30 minutes",
# "200ms", "1024 entries", "7-snapshot". The leading ``(?<![\w.])`` and
# trailing ``(?![\w])`` anchors keep digits EMBEDDED in identifiers OUT —
# commit SHAs ("a64d252"), versions ("v38"), loop ids ("loop178") are NOT
# quantities. (Empirically critical: without the anchors a live-corpus scan
# produced ~700k false conflicts from SHA/id digits.)
# SECURITY (opus CodeQL triage 2026-07-18, alert [26]): the unit group had two
# adjacent unbounded ``\s*`` around an optional ``-?`` → quadratic backtracking
# on a number followed by a long run of spaces with no trailing letter. It runs
# on ``fact.proposition`` (documented up to 64KB, NOT capped by the L1 gate), so
# a tenant writing "5"+" "*60000 stalled the server ~30s per fact. Bounding the
# whitespace to 3 removes the ReDoS while still matching every real form
# ("5kg", "5 kg", "5-kg", "5 - kg") — real quantities never have >3 spaces.
# 2026-08-07 — L'UNITA' ERA IN ASCII, e il difetto e' la CLASSE ② con la sua
# diagnosi gia' scritta quindici righe piu' sotto. Misurato (ws4, gradino 4):
#     40 unità -> VUOTA     40 Stück -> VUOTA     40 años -> VUOTA
#     40 Stueck -> 'stueck'  40 minuti -> 'minuto'          (senza accento: ok)
# `([A-Za-z]+)` non contiene i diacritici, quindi ogni unita' scritta
# correttamente nella propria lingua spariva — e sono le PIU' COMUNI del
# dominio: `Stück` e' il tedesco per «pezzi», l'unita' di magazzino per
# eccellenza. ⇒ E spiega perche' il tedesco sembrava funzionare: nei banchi
# avevamo usato tutti «Minuten», «Paletten», «Stunden», il sottoinsieme che si
# scrive in ASCII.
# ⚠️ La stessa diagnosi era gia' in questo file dal 2026-08-04 per
# `content_tokens` («la parola TRONCATA sull'accento — città -> citt»), e non
# fu applicata qui. La domanda che mancava: *chi ALTRO fa la stessa cosa?*
# `[^\W\d_]` e' «una lettera di QUALUNQUE alfabeto» — chiude insieme il gradino
# 2 della mappa (cirillico, greco, arabo: hanno gli spazi come il latino e
# perdevano l'unita' per la stessa ragione).
# ⛔ NON tocca il gradino 3 (ZH/JA/TH): li' e' il NUMERO a non essere catturato,
# perche' i lookaround falliscono in assenza di spazi. Difetto diverso, cura
# diversa, e allargarlo cambierebbe la cattura in tutte le lingue insieme.
#
# 2026-08-07 (secondo giro) — I LOOKAROUND ERANO SU `\w`, E NON E' UN DIFETTO
# CJK. Isolato da ws1 con l'osservazione che lo rende curabile: `\w` comprende
# gli ideogrammi MA ANCHE le lettere latine, quindi il difetto e' lo stesso in
# ogni lingua — in cinese, giapponese e thai colpisce il 100% delle frasi
# perche' lo spazio non esiste e ogni numero e' preceduto da un ideogramma.
#     abc300 pallet     -> []          罗维戈仓库500个托盘 -> []
#     SKU300 pallet     -> []          คลัง500พาเลท        -> []
# La cura NON toglie il lookbehind, che serve: `SKU300` non contiene 300 pallet
# e `v1.2` non e' una quantita'. Restringe la classe da «qualunque carattere di
# parola» a «lettera LATINA, cifra, punto o underscore» — gli identificatori
# sono scritti in ASCII per costruzione e restano protetti, gli ideogrammi
# smettono di bloccare. E' mirata, non allarga la cattura in tutte le lingue:
# era l'avvertimento di ws4 e questo e' il modo di rispettarlo.
# 🔑 E RIPARA UN DIFETTO CHE NESSUNO CERCAVA, misurato scrivendo il test:
#     release 3.4.0   prima -> quantita' 3.4    dopo -> nessuna
#     il file 2.1.3   prima -> quantita' 2.1    dopo -> nessuna
#   Le versioni a tre componenti entravano nel confronto NUMERICO come decimali,
#   perche' il lookahead non vedeva il punto che seguiva.
#
# ⚠️ IL PUNTO NEL LOOKAHEAD VA QUALIFICATO, e la prima versione di questa cura
# non lo faceva: `(?![A-Za-z0-9._])` rifiuta il numero seguito da un punto, e
# quello e' il punto di FINE FRASE. «I fatti superseduti sono 1900.» smetteva di
# essere una quantita'. Preso da due presidi esistenti in meno di un minuto —
# il difetto che serve escludere e' `3.4` dentro `3.4.0`, cioe' un punto seguito
# da una CIFRA, non un punto qualsiasi.
#
# ⚠️ E ANCHE IL PUNTO DEL LOOKBEHIND VA QUALIFICATO — isolato da ws1, ed e' la
# classe di oggi vista DALL'ALTRO LATO: nel parser «attaccato» faceva catturare
# di troppo, nel gate fa NON riconoscere e boccia un fatto VERO.
#     fonte «Rilevazione: grad.3 su scala 5, temp.22 gradi» -> solo (5.0)
#     claim «…riporta grado 3 … e temperatura 22 gradi»     -> assenti [3, 22]
#     ⇒ L4.1 quarantina un fatto i cui numeri SONO nella fonte.
# In italiano il punto di abbreviazione davanti a un numero e' una forma
# corrente: grad.3 · temp.22 · art.15 · pag.7 · n.42 · fig.3 · tot.300 · Nr.5.
# LA DISTINZIONE E' STRUTTURALE e non chiede una lista di abbreviazioni:
#     1.2      punto fra due CIFRE         -> decimale/versione: NON catturare
#     grad.3   punto fra LETTERA e cifra   -> abbreviazione: catturare
# Il lookbehind diventa «non preceduto da CIFRA-punto» invece di «non preceduto
# da punto». Misurato: 7/7 recuperati, 7/7 protetti (v1.2, 3.4.0, 2.1.3,
# 65.61.137.117, 127.0.0.1, SKU300, abc300), 160 proposizioni su 8951 (1,79%).
_QUANT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?<!\d\.)(\d+(?:\.\d+)?)(?:\s{0,3}-?\s{0,3}([^\W\d_]+))?"
    r"(?![A-Za-z0-9_])(?!\.\d)",
    re.UNICODE,
)

# Function words that can FOLLOW a number but are never units ("30 and 45",
# "5 of 10"). Stripped to a bare (unitless) number, which the conflict check
# then ignores.
#
# 2026-07-25 — the Italian ARTICULATED prepositions were missing, and they are
# the commonest form in the language this store is actually used in. Cost of the
# gap, measured by dogfooding: "issue #42 nel tracker" yielded unit 'nel',
# "task 7 del piano" yielded 'del', so two DISTINCT facts read as same-unit
# different-value — a conflict — and the same-source supersede then retired the
# earlier one. Eight true facts out of nine dropped out of default recall.
# That breaks the contract this module states in numeric_conflict: "precision
# over recall — a false conflict downgrades a true fact, the opposite of the
# trust we sell".
#
# 2026-08-07 — PERCHE' QUESTA LISTA E' LEGITTIMA, e le liste che questa casa
# rifiuta no. Non enumera IL MONDO: le unita' di misura sono infinite e nuove
# ne nascono (pallet, bancali, container, valvole), e una lista che le insegue
# e' persa in partenza. Enumera le PAROLE FUNZIONALI di una lingua —
# preposizioni, articoli, congiunzioni — che sono una classe CHIUSA: l'italiano
# ha una ventina di preposizioni e non ne acquisisce di nuove. Il segnale che
# era incompleta e non sbagliata sono le sue ASIMMETRIE: `da` senza `a`, `an`
# senza `a`, `tra`/`fra` senza `contro`.
#
# ⛔ UN CRITERIO POSIZIONALE E' STATO PROVATO E RITIRATO, e vale la pena
# scriverlo perche' e' la strada che sembra piu' elegante — «la parola sta
# ESATTAMENTE fra due numeri ⇒ non e' un'unita'», zero liste, tutte le lingue.
# Misurato su entrambe le popolazioni: prende 3 bersagli su 5 («136 contro sub
# 10» e «7453 verified contro 553» hanno una parola in mezzo e gli sfuggono) e
# ne rompe DUE veri — «la stanza misura 3 metri 20» perde `metri`, che e' il
# modo normale di scrivere 3,20 m in italiano, e «300 pallet 45 corsie» perde
# `pallet`. Copertura minore della lista E un danno che la lista non ha.
#
# ⚠️ IL COSTO ACCETTATO, dichiarato: alcune di queste parole sono anche
# abbreviazioni di unita' — `in` (inches), `at` (atmosfere), `a` (ampere). La
# scelta era gia' stata fatta da chi ha scritto le prime due righe, e la
# confermo: l'asimmetria del danno la decide. Una falsa unita' CREA conflitti
# che non esistono (ws1: 28 conflitti su 30 fra topic diversi, unita' `verified`
# 38022 contro 9622); un'unita' persa fa MANCARE un conflitto. Il primo e' il
# danno che stiamo pagando, e il modulo dichiara "precision over recall".
_NON_UNIT_WORDS = frozenset({
    "and", "or", "to", "of", "in", "on", "at", "by", "for", "the", "an",
    "is", "are", "was", "were", "be", "per", "via", "with", "from", "but",
    "as", "that", "than", "then", "plus", "over", "into", "out", "more",
    "e", "o", "di", "da", "su", "con", "tra", "fra", "ed", "il", "la", "un",
    # preposizioni articolate + articoli/pronomi che seguono un numero
    "del", "dello", "della", "dei", "degli", "delle",
    "nel", "nello", "nella", "nei", "negli", "nelle",
    "al", "allo", "alla", "ai", "agli", "alle",
    "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "col", "coi", "lo", "le", "gli", "uno", "una", "che", "non", "come",
    "sono", "era", "erano", "ha", "hanno", "piu", "meno",
    # ── LE DUE ASIMMETRIE (2026-08-07) ────────────────────────────────────
    # `da` c'era e `a` no; `an` c'era e `a` no. «passa da 33 a 45» dava unita'
    # `a` al 33 — la preposizione che APRE l'intervallo era coperta, quella
    # che lo CHIUDE no. Un buco per omissione, non per scelta.
    "a",
    # ── LE CONGIUNZIONI DI CONFRONTO, EN·IT·DE·FR·ES ──────────────────────
    # `tra`/`fra`/`and`/`e` c'erano gia': accostano due numeri e non sono
    # unita'. Le congiunzioni di CONFRONTO fanno esattamente la stessa cosa
    # («30 and 45» e «30 vs 45» hanno la stessa struttura) e non c'erano —
    # ed e' la forma in cui si scrive una MISURA, cioe' il testo che questo
    # store contiene di piu': misurato da ws1, «7453 verified contro 553».
    "vs", "versus", "contro", "against", "gegen", "contre", "frente",
    # ── LE PARTICELLE ITALIANE (2026-08-07, secondo giro) ─────────────────
    # Misurate sul corpus vivo DOPO l'allargamento della cattura a Unicode:
    # `ma` 43 occorrenze · `ne` 14 · `si` 10 · `se` 7 su 45381 unita' estratte.
    # Non ci sono mai state e prima non servivano — con `[A-Za-z]` la cattura
    # le prendeva gia', ma il difetto restava sotto la soglia di attenzione.
    # ⚠️ Sono OMOGRAFI accettati consapevolmente, come `in` (inches) e `at`
    # (atmosfere) che sono in lista dal principio: `si` e' anche il silicio,
    # `mi` una nota. La scelta e' la stessa e la ragione pure — una falsa unita'
    # CREA conflitti che non esistono, un'unita' persa ne fa mancare uno.
    "ma", "ne", "se", "si", "ci", "vi", "mi", "ti", "pero", "quindi",
    "anche", "solo", "gia", "ancora", "poi", "cioe", "ossia", "ovvero",
    "puo", "perche", "poiche", "mentre", "dopo", "prima", "quando",
    # ⚠️ `i` MANCAVA, ed e' la terza asimmetria della stessa lista trovata
    # oggi: c'erano `il` `lo` `la` `le` `gli` `un` `uno` `una` e non `i`, come
    # c'erano `da` e non `a`, `an` e non `a`. «sono gia' 200 i fatti» dava
    # unita' `i`. Le liste non si sbagliano in blocco: perdono UNA voce.
    "i",
})

#: No real unit of measure ends in ``-ly`` (EN) or ``-mente`` (IT): ms, kg, min,
#: h, entries, requests, tests… all fail this test. Two morphological rules
#: replace an open-ended list of adverbs ("8080 locally", "1024 entries only",
#: "porta 8080 localmente", "3 volte esattamente").
#:
#: ``-mente`` was MISSING in the first version of this fix and an adversarial
#: review (glm-5.2, 2026-07-25) caught it: the rule covered English and left
#: Italian — the language this store is actually written in — exactly as broken
#: as before. Confirmed by running it: "porta 8080 localmente" yielded unit
#: 'localmente', and two different ports still produced a conflict.
#:
#: Known cost, accepted: two words added above are ALSO unit symbols.
#:   * ``dal`` — articulated preposition, and the symbol for decalitre (raised by
#:     glm-5.2);
#:   * ``ha`` — third person of "avere" ("il fatto 3 ha 500 righe"), and the
#:     symbol for hectare (raised by the critic's counterexample worker).
#: Both now yield a bare number, so no conflict is detected on decalitres or
#: hectares. Deliberate: in the prose this store holds, the preposition and the
#: verb are overwhelmingly the commoner reading, and leaving them out would
#: FABRICATE conflicts ("il fatto 3 ha 500 righe" vs "il fatto 5 ha 200 righe").
#: A missed conflict is the cheaper error here than an invented one — the same
#: "precision over recall" trade-off this module states below.
_ADVERB_SUFFIXES = ("ly", "mente")

#: …except the FREQUENCY words, which really are units in the domains this store
#: serves: "10 daily reports", "5000 yearly", "3 weekly backups". Raised by a
#: second adversary (deepseek-v4-pro, 2026-07-25) and confirmed by running it —
#: my ``-ly`` rule had turned a fabricated conflict into a systematically MISSED
#: one: "10 daily reports" vs "50 daily reports" stopped conflicting at all.
#: A blunt morphological rule needs this exception list; without it the fix for
#: one error class quietly created another.
_FREQUENCY_UNITS = frozenset({
    "hourly", "daily", "nightly", "weekly", "biweekly", "fortnightly",
    "monthly", "quarterly", "yearly", "annually",
    "orario", "giornaliero", "settimanale", "mensile", "trimestrale", "annuale",
})

# Unit synonyms → canonical form so "200ms" and "500 milliseconds" compare
# and "30 minutes"/"45 minutes" share unit "min". Plural/`-ies` handled
# generically in :func:`norm_unit`.
_UNIT_SYN = {
    "ms": "ms", "msec": "ms", "msecs": "ms",
    "millisecond": "ms", "milliseconds": "ms",
    "s": "s", "sec": "s", "secs": "s", "second": "s", "seconds": "s",
    "m": "min", "min": "min", "mins": "min", "minute": "min", "minutes": "min",
    "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "d": "day", "day": "day", "days": "day",
}

# ≥4-char filler words excluded from the distinctive-overlap check.
_CONTENT_STOP = frozenset({
    "with", "from", "into", "over", "each", "after", "before", "than",
    "that", "this", "these", "those", "their", "your", "default", "about",
    "while", "when", "then", "also", "only", "most", "more", "less",
    "such", "some", "any", "via", "per", "upto", "starting", "uses",
    "used", "using", "have", "has", "was", "were", "are", "the",
})

# Contrasting qualifiers: if two statements each hold a DIFFERENT member of
# one group they describe DIFFERENT attributes ("read timeout" vs "write
# timeout") — a same-unit/different-value pair is then NOT a contradiction.
# Conservative and not exhaustive, but kills the common false-positive
# class. Tokens are singularised upstream by :func:`content_tokens`.
CONTRAST_QUALIFIERS: tuple[frozenset[str], ...] = (
    frozenset({"read", "write"}),
    frozenset({"request", "response"}),
    frozenset({"upload", "download"}),
    frozenset({"input", "output"}),
    frozenset({"send", "receive"}),
    frozenset({"inbound", "outbound"}),
    frozenset({"ingress", "egress"}),
    frozenset({"source", "destination"}),
    frozenset({"encode", "decode"}),
    frozenset({"encrypt", "decrypt"}),
    frozenset({"push", "pull"}),
    frozenset({"client", "server"}),
    frozenset({"minimum", "maximum"}),
    frozenset({"primary", "backup", "secondary", "replica", "standby"}),
    frozenset({"staging", "production"}),
    # 2026-07-25 — coppie ITALIANE. La batteria di ampiezza ha trovato
    # "il gate legge in 45 ms" che ritirava "il gate scrive in 300 ms": la lista
    # copriva {read, write} in inglese e questo store e' scritto in italiano.
    # Un criterio strutturale ("ciascun lato ha una parola esclusiva") e' stato
    # provato e FALSIFICATO da due test: non distingue un attributo opposto
    # ("legge"/"scrive") da un sinonimo ("holds"/"bounded") ne' da un valore che
    # cambia ("Rome"/"Paris"). Qui la lista e' il design giusto, perche' le coppie
    # contrapposte sono un insieme piccolo e conosciuto.
    frozenset({"legge", "scrive"}),
    frozenset({"lettura", "scrittura"}),
    frozenset({"richiesta", "risposta"}),
    frozenset({"ingresso", "uscita"}),
    frozenset({"entrata", "uscita"}),
    frozenset({"invio", "ricezione"}),
    frozenset({"caricamento", "scaricamento"}),
    frozenset({"origine", "destinazione"}),
    frozenset({"client", "server"}),
    # flessioni: content_tokens non lemmatizza l'italiano, quindi la coppia
    # va data in entrambi i generi ("latenza minima" / "latenza massima")
    frozenset({"minimo", "massimo"}),
    frozenset({"minima", "massima"}),
    frozenset({"minime", "massime"}),
    frozenset({"primario", "secondario", "replica"}),
    frozenset({"collaudo", "produzione"}),
    frozenset({"caldo", "freddo"}),
    # PERIODICITA'. I trenta gruppi qui sopra coprono il dominio
    # INFRASTRUTTURALE — letture, repliche, ambienti — e non quello
    # commerciale e temporale, che e' il primo che incontra chi prova il
    # prodotto con il proprio listino. Costo misurato il 2026-08-04:
    #   «Il piano annuale costa 100 euro» + «Il piano mensile costa 20 euro»
    #       -> VIVI=1, l'annuale RITIRATO. Anche in inglese.
    #   «La latenza di lettura e' 5 ms»   + «... di scrittura e' 9 ms»
    #       -> VIVI=2, perche' lettura/scrittura e' un gruppo che c'e'.
    # Il meccanismo funzionava: gli mancava il mondo. Era l'aperto «il mensile
    # cancella l'annuale», cercato per giorni nella soglia di overlap — dove
    # non poteva stare, perche' su frasi corte la quota e' 0.75.
    #
    # Due fatti sullo STESSO periodo con numeri diversi restano una
    # contraddizione: `ca == cb` non e' un contrasto, e la supersessione
    # continua a scattare (presidiato).
    # UN GRUPPO NON PUO' CONTENERE DUE NOMI DELLA STESSA PERIODICITA': il
    # contrasto si decide su `ca != cb`, quindi «annual» accanto a «yearly»
    # farebbe leggere come attributi diversi due frasi che dicono lo stesso.
    # Per questo mancano «yearly» e «biannual» (che vale sia semestrale sia
    # biennale, a seconda di chi scrive).
    frozenset({"annual", "monthly", "weekly", "daily", "quarterly", "hourly"}),
    frozenset({"annuale", "mensile", "settimanale", "giornaliero",
               "trimestrale", "semestrale", "orario"}),
    # `content_tokens` singolarizza l'inglese ma NON l'italiano (misurato: «i
    # canoni annuali» -> `annuali`), quindi il plurale va dato a mano — in un
    # gruppo SEPARATO, se no «annuale» contro «annuali» diventerebbe un
    # contrasto fra la stessa cosa scritta due volte.
    frozenset({"annuali", "mensili", "settimanali", "giornalieri",
               "trimestrali", "semestrali", "orari"}),
    # GLI ALTRI DOMINI DELLO STESSO SCHEMA, misurati end-to-end dall'altra
    # istanza subito dopo la periodicita': `base`/`premium` e `netto`/`lordo`
    # davano ancora VIVI=1 su 2 sulle STESSE frasi. Un listino a due livelli e
    # un prezzo con e senza imposta sono forme dei dati comuni quanto
    # annuale/mensile, e sullo stesso schema stanno taglia, canale, tipo di
    # cliente e verso del viaggio.
    #
    # ⛔ QUESTO NON CHIUDE LA CLASSE, e va detto: la lista e' il SURROGATO di un
    # terzo esito che il giudice non ha. Misurato su coppie fatto->fatto, il CE
    # binario da contraddice 0.77/0.92 e indipendente 1.25/0.28/0.30 — uno degli
    # indipendenti sta SOPRA entrambi i contraddice, mentre il controllo
    # «supporta» sta a 99.19. I due gruppi da separare collassano, perche' la
    # distinzione vive dentro il «non-supporta», che e' un esito unico. Finche'
    # il giudice ha due esiti, ogni dominio nuovo va aggiunto a mano.
    frozenset({"base", "premium", "enterprise", "pro"}),
    frozenset({"netto", "lordo"}),
    frozenset({"net", "gross"}),
    frozenset({"piccola", "media", "grande"}),
    frozenset({"piccolo", "medio", "grande"}),
    frozenset({"small", "medium", "large"}),
    frozenset({"online", "negozio"}),
    frozenset({"privati", "aziende"}),
    frozenset({"andata", "ritorno"}),
    frozenset({"acquisto", "noleggio"}),
    frozenset({"nuovo", "usato"}),
)


def _senza_diacritici(parola: str) -> str:
    """`unità` → `unita`, `Stück` → `stuck`, `años` → `anos`, `unités` → `unites`.

    Si normalizza invece di elencare le varianti accentate — la stessa scelta,
    con la stessa motivazione, di `temporal_context._senza_accenti`: una lista
    di varianti e' una lista in piu' da tenere allineata.

    ⚠️ LIMITE DICHIARATO — LE TRASLITTERAZIONI NON SONO ACCENTI CADUTI. Chi non
    ha l'umlaut sulla tastiera scrive «Stueck», non «Stuck», e nei gestionali
    tedeschi quella e' la forma corrente. Qui `Stück` e `Stuck` si uniscono (una
    e' l'altra senza il segno) mentre `Stueck` resta a parte, perche' unirla
    richiederebbe la regola inversa `ue -> u`, che romperebbe ogni parola in cui
    `ue` e' scritto per se stesso. Ho provato la traslitterazione `ü -> ue` come
    forma canonica e sposta solo il problema: allora e' `Stuck` a restare fuori.
    Serve un dizionario per-lingua, che e' un'altra cura — e la scelta di quale
    delle due grafie unire va fatta con un dato sul corpus, non a intuito.
    """
    import unicodedata
    p = (parola or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", p)
                   if not unicodedata.combining(c))


def norm_unit(word: str) -> str:
    """Canonicalise a unit word (synonyms + plural/`-ies` singularisation).

    ⚠️ I DIACRITICI SI NORMALIZZANO, non si elencano (2026-08-07): chi scrive
    «unità» e chi scrive «unita» misura la stessa grandezza, e se restano due
    unita' diverse due fatti sullo stesso magazzino non si confrontano mai.
    Stessa scelta — e stessa motivazione scritta — di `temporal_context`, che
    normalizza invece di tenere una lista di varianti accentate: «questa casa ha
    gia' pagato tre volte per due elenchi che divergono».
    ⚠️ Il tedesco fa eccezione e non e' un dettaglio: `ü` si traslittera in `ue`,
    non in `u` — «Stück» e «Stueck» sono la STESSA parola scritta da due
    tastiere diverse, ed e' la forma che si trova nei sistemi gestionali.
    """
    w = (word or "").lower()
    if w in _UNIT_SYN:
        return _UNIT_SYN[w]
    piano = _senza_diacritici(w)
    if piano != w and piano in _UNIT_SYN:
        return _UNIT_SYN[piano]
    if piano != w:
        w = piano
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    # IL PLURALE NON E' SOLO INGLESE. Censito da ws4 sul mandato lingue:
    #     EN  minute -> min      minutes -> min        ok
    #     FR  minute -> min      minutes -> min        ok  <- per caso, parola uguale
    #     ES  minuto -> minuto   minutos -> minuto     ok  <- per caso, plurale in -s
    #     IT  minuto -> minuto   minuti  -> minuti     DUE UNITA' DIVERSE
    #     DE  Minute -> min      Minuten -> minuten    idem
    # Le tre lingue che funzionavano funzionavano PER CASO, e non era una
    # scelta di nessuno: era il bordo di una regola scritta per una lingua sola.
    # Costo: due fatti sulla stessa grandezza non condividono l'unita', quindi
    # un conflitto vero puo' sfuggire, e `L4.2` (il vicinato) eredita il bordo
    # perche' sta a valle — «45 Minuten» contro «30 Minuten» e' il caso di ws4.
    #
    # NON UNA LISTA DI PAROLE, che crescerebbe con le lingue del mondo: i
    # plurali si formano con SUFFISSI, e sono una manciata. E' morfologia.
    #
    # ⛔ IL PLURALE ITALIANO IN «-e» E' STATO PROVATO E TOLTO, ed e' il limite
    # che questa cura DICHIARA invece di nascondere: «-e» segna il plurale di un
    # femminile italiano («cassa»->«casse») ma anche il SINGOLARE di quasi ogni
    # unita' di tempo tedesca («Stunde», «Minute», «Woche»). Applicandolo,
    # «Stunde» diventava «stunda» — cioe' per curare un plurale italiano
    # rompevo il singolare tedesco. Senza sapere in che lingua e' scritto il
    # testo le due regole si contraddicono, e non si sceglie a caso quale
    # lingua servire. Restano coperti «-i» (IT) e «-en» (DE), che non
    # collidono con niente; «cassa/casse» e «ora/ore» restano scoperti, ed e'
    # il prezzo dichiarato.
    # ⚠️ Si MAPPA al singolare invece di TRONCARE: troncare accorcia anche
    # parole che plurali non sono e fa collassare unita' distinte («ora»/«oro»
    # su «or»), che sarebbe peggio del difetto curato. La lunghezza minima
    # protegge le parole corte, dove un suffisso e' quasi tutta la parola.
    if len(w) > 3:
        # ⚠️ Si RIPASSA dal dizionario dopo aver tolto il suffisso: senza,
        # «Minuten» diventava «minute» e si fermava li', mentre «Minute» era
        # gia' nel dizionario e usciva «min» — due forme della stessa unita'
        # separate dall'ultimo passo, che e' il difetto che si sta curando.
        radice = None
        if w.endswith("en"):       # DE: Minuten->minute, Stunden->stunde
            radice = w[:-1]
        elif w.endswith("i"):      # IT: minuti->minuto, giorni->giorno
            radice = w[:-1] + "o"
        if radice:
            return _UNIT_SYN.get(radice, radice)
    return w


#: Markers after which the text stops asserting and starts citing PROVENANCE:
#: how many samples, which run, which commit. Numbers there describe the check,
#: not the claim.
#:
#: 2026-07-25, root cause of a real loss: the OEIS organism wrote each relation
#: with its evidence inline —
#:   "… = 0 | evidence: holds exactly at 199 common points (window n<=200)"
#:   "… = 0 | evidence: holds exactly at 200 common points (window n<=200)"
#: — so two DIFFERENT relations, checked over a different number of points, read
#: as "same unit 'common', 199 vs 200" and the supersede retired the first. Of 9
#: verified relations, 2 survived. Measured: dropping the text after 'evidence:'
#: made the conflict disappear. Anyone writing "verified on 200 samples" into a
#: fact was manufacturing conflicts with themselves.
_EVIDENCE_MARKER_RE = re.compile(
    r"\b(?:evidence|verified_by|verified|source|sources|ref|refs|citation|"
    r"prova|prove|fonte|fonti|riferimento)\s*:",
    re.IGNORECASE)


#: A provenance marker only ends the claim if what follows is a TAIL. Measured on
#: the live corpus the moment this was written: the first version cut 140 facts of
#: 6293, discarding a median 67% of their text, because it fired on markers used
#: INLINE inside a metadata block —
#:   "RESEARCH FINDING [provisional, source: arxiv.org/… ] ProvSEEK (Aug 2025) …"
#: where the real claim comes AFTER the bracket. That version kept the heading and
#: threw the content away, hiding 97% of those facts from every detector. So the
#: cut must leave a substantial claim standing; if it leaves crumbs, the marker
#: was part of the sentence, not the start of its footnote.
#: A claim shorter than this is not a claim — the marker opened the sentence
#: ("fonte: il documento dichiara 45 ms"), so there is nothing to keep.
_MIN_CLAIM_CHARS = 12
_OPENERS, _CLOSERS = "([{", ")]}"

#: A marker ends the claim only when it OPENS A SECTION: preceded by a delimiter
#: (bar, newline, full stop, semicolon, dash) or by the start of the text —
#: optionally with an upper-case label in between ("EMPIRICAL EVIDENCE:",
#: "STEP-BY-STEP EVIDENCE:"). Counting characters was not enough, and an
#: adversarial review found why (glm-5.2, 2026-07-25, confirmed by running it):
#:   "Riferendosi alla fonte: il record 42 ha valore 100"
#: left "Riferendosi alla " — 17 chars, above the threshold — and threw away the
#: claim, identifier and value included. "fonte" and "prova" are ordinary Italian
#: words and "ref:" shows up in technical notes; only the position tells a
#: footnote from a phrase.
_SECTION_DELIMS = "|\n\r.;—-•"
#: An upper-case label may sit between the delimiter and the marker.
_LABEL_RE = re.compile(r"[A-Z][A-Z0-9_-]*\s*$")


def _inside_brackets(text: str, pos: int) -> bool:
    """True when *pos* sits inside a bracket opened earlier and not yet closed.

    This is the test that separates a footnote from an aside. A first version
    asked instead whether ANY closer appeared after the marker, and that was
    wrong twice over: it rejected "evidence: holds at 199 points (window n<=200)"
    — where the parentheses open and close inside the tail — while the case it
    meant to catch is the marker sitting INSIDE an open bracket.
    """
    depth = 0
    for ch in text[:pos]:
        if ch in _OPENERS:
            depth += 1
        elif ch in _CLOSERS:
            depth = max(0, depth - 1)
    return depth > 0


def _opens_a_section(head: str) -> bool:
    """True when what precedes a marker ends a SECTION rather than a phrase.

    Walks back over an optional upper-case label ("EMPIRICAL EVIDENCE:") and then
    asks for a delimiter or the start of the text. "Riferendosi alla fonte:" fails
    on both counts — "alla" is neither.
    """
    stripped = head.rstrip(" \t")
    if not stripped:
        return True                       # marker at the very beginning
    label = _LABEL_RE.search(stripped)
    if label is not None:
        # NB: strip spaces and tabs only. A newline IS the delimiter we are
        # looking for, and rstripping it here made "…tests)\nEMPIRICAL EVIDENCE:"
        # look mid-phrase — the label swallowed the very evidence of a break.
        stripped = stripped[:label.start()].rstrip(" \t")
        if not stripped:
            return True
    return stripped[-1] in _SECTION_DELIMS


def claim_span(text: str) -> str:
    """The asserting part of *text*: everything before a provenance marker that
    introduces a trailing citation. Whole text when there is no such marker, when
    the marker sits inside brackets (an aside, not a footnote), or when cutting
    would leave less than :data:`_MIN_CLAIM_CHARS` of claim."""
    if not text:
        return ""
    for m in _EVIDENCE_MARKER_RE.finditer(text):
        if _inside_brackets(text, m.start()):
            continue                      # parenthetical citation, not a tail
        head = text[:m.start()]
        if len(head.strip()) < _MIN_CLAIM_CHARS:
            continue                      # the marker opened the sentence
        if not _opens_a_section(head):
            continue                      # mid-phrase use, not a footnote
        return head
    return text


#: Gli apostrofi che la gente scrive davvero: l'ASCII e il TIPOGRAFICO U+2019,
#: che e' quello che producono Word, iOS e i modelli di linguaggio. Guardare
#: solo il primo coprirebbe il testo battuto a mano e non quello che questo
#: store riceve.
_APOSTROFI = "'’ʼ"

#: Le vocali che possono seguire un'elisione. `y` non c'e': in italiano non e'
#: una vocale, e in inglese non segue mai un apostrofo di elisione.
_VOCALI_DOPO_ELISIONE = frozenset("aeiouAEIOUàèéìòùÀÈÉÌÒÙáéíóúÁÉÍÓÚäöüÄÖÜâêîôûëï")


def _e_una_forma_elisa(testo: str, fine_unita: int) -> bool:
    """La presunta unita' che finisce a *fine_unita* e' il moncone di una parola
    ELISA («120 **l'**anno», «40 **all'**ora»)?

    🔑 LA REGOLA E' GRAMMATICALE, e per questo non ha bisogno di liste::

        apostrofo + VOCALE      -> elisione (IT/FR)   l'anno · all'ora · d'entre
        apostrofo + «s»/spazio  -> genitivo (EN)      days' notice · day's work

    L'elisione italiana **esiste solo davanti a vocale** — e' la sua
    definizione — mentre il genitivo sassone non e' mai seguito da una vocale.
    Le due popolazioni non si toccano, e la regola vale per ogni parola elisa
    senza enumerarne nessuna: le elisioni sono una classe aperta (all', dell',
    nell', dall', sull', coll', l', un', quest', d', qu'…) e in francese lo sono
    ancora di piu'.

    ⚠️ E' LA META' CHE MANCAVA A `_NON_UNIT_WORDS`: quella lista copre le
    preposizioni PIENE («nel tracker», «del piano») e nessuna elisa. La cura del
    2026-07-25 aveva chiuso meta' della stessa classe.

    ⛔ PERCHE' NON UNA LISTA. Il moncone piu' dannoso e' ``l``, che **e'
    un'unita' vera**: il litro. Mettendolo fra le non-unita' «la tanica contiene
    120 l» perderebbe la sua unita'. La popolazione opposta esclude la lista e
    lascia solo il criterio posizionale.
    """
    if fine_unita <= 0 or fine_unita >= len(testo):
        return False
    if testo[fine_unita] not in _APOSTROFI:
        return False
    dopo = fine_unita + 1
    # apostrofo a fine testo, o seguito da spazio -> genitivo sassone plurale
    # («a 3 days' notice»), non un'elisione: l'unita' e' vera e resta.
    return dopo < len(testo) and testo[dopo] in _VOCALI_DOPO_ELISIONE


#: Le parole che INTRODUCONO una data. Preposizioni e articoli — classe chiusa,
#: come `_NON_UNIT_WORDS`: nessuna lingua ne acquisisce di nuove. EN·IT·DE·FR·ES.
_INTRODUCE_UN_ANNO = frozenset({
    "nel", "nell", "del", "dell", "dal", "dall", "al", "all", "il", "l",
    "entro", "da", "a", "di", "fino", "verso", "circa", "anno", "anni",
    "in", "on", "by", "since", "until", "till", "from", "the", "of", "for",
    "year", "fy", "ab", "seit", "bis", "im", "jahr", "vom", "zum",
    "en", "depuis", "jusqu", "an", "annee", "année", "desde", "hasta", "ano",
})


def _nomi_di_mese() -> frozenset[str]:
    """I nomi di mese, PRESI DA `temporal_context` invece che ricopiati qui.

    ⚠️ E' la classe ① — «una copia invece della superficie unica» — e questa
    casa la paga a ogni giro: due liste di mesi divergono al primo che ne
    estende una sola. `temporal_context._MONTHS` e' gia' EN·IT·DE·FR·ES ed e'
    la lista che il percorso delle date usa davvero; se domani qualcuno la
    estende, questo criterio si estende con lei.

    L'import e' pigro e non crea ciclo: `temporal_context` importa solo la
    libreria standard. Il costo e' un dizionario letto una volta.
    """
    global _MESI_CACHE
    if _MESI_CACHE is None:
        try:
            from .temporal_context import _MONTHS
            _MESI_CACHE = frozenset(str(k).lower() for k in _MONTHS)
        except Exception:      # pragma: no cover — il criterio degrada, non rompe
            _MESI_CACHE = frozenset()
    return _MESI_CACHE


_MESI_CACHE: frozenset[str] | None = None


def _introdotto_da_una_parola_temporale(testo: str, inizio_numero: int) -> bool:
    """Il numero a quattro cifre che comincia a *inizio_numero* e' una DATA
    («scade **nel** 2027») o un CONTEGGIO («i superseduti **sono** 1900»)?

    🔑 LA DISTINZIONE E' NEL VICINATO, ed e' la stessa forma di criterio che ha
    retto su L4.2: guardare la parola ATTACCATA al numero invece del numero.
    Misurata sulle due popolazioni, 9/9 e 7/7::

        ANNI      nel · il · dal · al · in · ab · en · since   preposizioni/articoli
        CONTEGGI  sono · totali · contiene · restano · are     verbi/sostantivi

    ⚠️ PERCHE' SERVE, e non e' un dettaglio di forma. `YEAR_RE` scarta ogni
    numero fra 1000 e 2100 che non abbia un'unita' accanto, e nei referti di
    misura quei numeri sono la norma: le fonti sono output di script — tabelle,
    colonne, `chiave=valore` — dove il numero sta a fine riga senza unita'.
    Costo misurato da ws4: dei quarantinati di agosto con grounding **sopra 90**
    (cioe' che il moat APPROVA), 20 su 21 portano L4.1/L4.2, e fra loro c'e' il
    referto che misurava il gate, quarantinato dal gate.

    E il danno era su DUE lati, non uno: oltre ai falsi positivi, «i superseduti
    sono 1900» con una fonte che dice 1805 **non veniva fermato** — il numero
    inventato spariva prima di essere confrontato. Stessa causa, esiti opposti.

    📌 L'esclusione degli anni resta dove serve: «il contratto scade nel 2027»
    non e' un dettaglio numerico inventato, e le date hanno un percorso loro.
    """
    testa = testo[:inizio_numero].rstrip(" \t-–—")
    if not testa:
        return False              # numero a inizio testo: nessun introduttore
    if testa[-1] in ".;:!?\n":
        return False              # inizio di frase o cella di tabella
    m = re.search(r"([^\W\d_]+)$", testa, re.UNICODE)
    if m is None:
        return False
    parola = m.group(1).lower()
    return parola in _INTRODUCE_UN_ANNO or parola in _nomi_di_mese()


def extract_quantities(text: str) -> set[tuple[str, float]]:
    """Extract ``(unit_norm, value)`` pairs from the CLAIM part of *text*
    (provenance after an evidence marker is not measured); bare YEARS excluded."""
    out: set[tuple[str, float]] = set()
    claim = claim_span(text)
    for m in _QUANT_RE.finditer(claim):
        num_s, unit_s = m.group(1), (m.group(2) or "")
        if unit_s and _e_una_forma_elisa(claim, m.end(2)):
            unit_s = ""   # «120 l'anno» non contiene litri
        # ⚠️ SI CONFRONTA LA FORMA NORMALIZZATA, NON QUELLA SCRITTA — la cura e'
        # una riga ed e' di ws4, che ha misurato il difetto sul corpus reale
        # (66 fatti su 5874 guadagnavano un'unita' che non lo era):
        #     'e' in _NON_UNIT_WORDS -> True    norm_unit('e') -> 'e'
        #     'è' in _NON_UNIT_WORDS -> False   norm_unit('è') -> 'e'
        # Il filtro vedeva la forma ACCENTATA e la normalizzazione arrivava
        # dopo, quindi «è», «già», «perché», «può» diventavano unita' di misura.
        # 🔑 E LA CAUSA PRIMA E' MIA: `_NON_UNIT_WORDS` era completa PER
        # COSTRUZIONE finche' il regex catturava solo `[A-Za-z]` — le parole
        # accentate non ci arrivavano nemmeno. Allargando la cattura a «una
        # lettera di qualunque alfabeto» (5e78549a) ho reso incompleta una lista
        # che nessuno aveva sbagliato. ⇒ Una cura che allarga un input rende
        # incomplete tutte le liste A VALLE, e quelle liste non sembrano
        # difettose perche' per anni non lo erano: e' la classe ② vista dal lato
        # opposto — non «chi altro fa la stessa cosa?» ma «chi RICEVE cio' che
        # ho appena allargato?».
        _u = _senza_diacritici(unit_s)
        if _u in _NON_UNIT_WORDS or (len(_u) > 3
                                     and _u not in _FREQUENCY_UNITS
                                     and _u.endswith(_ADVERB_SUFFIXES)):
            unit_s = ""  # a following function word / adverb is not a unit
        if (not unit_s and YEAR_RE.fullmatch(num_s)
                and _introdotto_da_una_parola_temporale(claim, m.start(1))):
            continue  # bare year → year path, not a quantity
        try:
            val = float(num_s)
        except ValueError:  # pragma: no cover — regex guarantees numeric
            continue
        out.add((norm_unit(unit_s), val))
    return out


#: Le lettere di QUALUNQUE alfabeto, non solo ASCII.
#:
#: PERCHE' (2026-08-04). `[a-zA-Z]{4,}` e' la classe ASCII, e questa funzione e'
#: la guardia di sovrapposizione lessicale su cui poggiano supersessione e
#: rilevamento di contraddizioni. Fuori da ASCII restavano:
#:
#:   cirillico · greco · arabo   ZERO token — e sono alfabeti ORDINARI, con gli
#:                               spazi fra le parole: nulla li distingue dal
#:                               latino se non il blocco Unicode.
#:   accenti italiani            la parola TRONCATA sull'accento —
#:                               «citta'» -> citta ma «città» -> citt,
#:                               «pero'» -> pero ma «però» -> per (3 char, via).
#:
#: Il caso non e' ipotetico: sul corpus vivo (6068 fatti) ci sono 100 parole
#: scritte in ENTRAMBE le grafie — `perche` 322 contro `perché` 88, `entita`
#: 118 contro `entità` 32, `singolarita` 66 contro `singolarità` 131. Chi scrive
#: da tastiera italiana e chi scrive da una shell che mangia gli accenti parlano
#: della stessa cosa, e la funzione che misura la sovrapposizione non lo sapeva.
#:
#: MISURATO SULLE DUE POPOLAZIONI — obbligatorio qui, perche' la cura gemella
#: («conservare token corti e cifre») fu falsificata proprio cosi', portando le
#: coppie sopra soglia da 848 a 2293 su 3000, cioe' PIU' ritiri:
#:   BENEFICIO  coppie «stessa frase, due grafie»: 215 su 400 non risultavano
#:              identiche; dopo, 0. Jaccard mediano 0.984 -> 1.000.
#:   COSTO      coppie casuali sopra soglia, su 3000: +0.
#:
#: ⚠️ IL PREZZO, dichiarato: in italiano l'accento distingue parole — `metà` e
#: `meta`, `completò` e `completo` diventano lo stesso token. Si paga perche' sul
#: corpus non produce un solo ritiro in piu' e perche' la coppia che unisce e'
#: molto piu' frequente di quella che confonde. Se un giorno costera' qualcosa
#: di misurabile, la strada e' l'analisi morfologica, non il ritorno ad ASCII.
#:
#: ⚠️ NON si toccano la soglia dei 4 caratteri ne' le cifre: quella strada e'
#: gia' falsificata sul corpus (`7aa678f57c73`). Qui cambia solo l'ALFABETO.
_PAROLA_RE = re.compile(r"[^\W\d_]{4,}", re.UNICODE)


def _senza_diacritici(text: str) -> str:
    """«città» -> «citta»: la stessa parola, una grafia sola."""
    return "".join(c for c in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(c))


def content_tokens(text: str) -> set[str]:
    """Lower-cased alpha tokens ≥4 chars minus fillers, lightly singularised.

    Used as the topical-overlap precision guard: two statements must share
    a *distinctive* (non-unit) content word before a same-unit/different-
    value pair counts as a contradiction.

    Gli accenti sono normalizzati e gli alfabeti non latini contano come
    lettere — vedi il blocco su ``_PAROLA_RE`` per la misura che lo giustifica.
    """
    toks = _PAROLA_RE.findall(_senza_diacritici((text or "").lower()))
    out: set[str] = set()
    for t in toks:
        if t in _CONTENT_STOP:
            continue
        if t.endswith("ies"):
            t = t[:-3] + "y"
        elif t.endswith("s") and len(t) > 3:
            t = t[:-1]
        out.add(t)
    return out


def _min_shared_ratio() -> float:
    """Quanta parte della frase PIU' POVERA deve essere condivisa perche' due
    proposizioni parlino dello stesso soggetto. 0 = guardia spenta.

    Perche' un RAPPORTO e non un conteggio: il conteggio e' gia' stato
    falsificato il 2026-07-25 — «ciascun lato ha una parola distintiva che
    l'altro non ha, quindi sono soggetti diversi» cadde su due test che
    esistevano gia', perche' un attributo opposto, un sinonimo e un valore
    cambiato hanno la STESSA forma lessicale (vedi
    tests/test_exclusive_words_mean_other_subject.py). Un rapporto invece
    misura una cosa diversa: due frasi corte che condividono meta' dei loro
    termini sono lo stesso soggetto, due prose che ne condividono un
    ventottesimo no.

    LA SOGLIA STA IN MEZZO A DUE POPOLAZIONI SEPARATE, misurate il 2026-08-03
    PRIMA di scrivere la guardia:

        conflitti che il codice dichiara sulle frasi dei TEST (118 coppie)
            quota minima   0.3333
        falsi dal corpus vero, tenuti in piedi da UN token (84 coppie)
            quota massima  0.0714

    Un fattore 4.7 fra le due, e 0.15 non tocca nessuno dei casi presidiati.

    E LA CURA ESISTEVA GIA', SUI DUE MODULI FRATELLI. `facts_conflict.
    find_conflicting_pairs` (polarita') e `corroboration.find_corroborations`
    hanno entrambi `min_overlap=0.30` — lo stesso overlap coefficient — piu' un
    `min_shared_tokens=2`, e il commento del primo descrive letteralmente
    questo difetto: «AVOIDS the failure mode where a single common token like
    "main" between unrelated facts gives high overlap coefficient». Il percorso
    NUMERICO, l'unico dei tre che fa RITIRARE un fatto, non aveva ne' l'una ne'
    l'altro.

    PERCHE' QUI SERVE IL RAPPORTO E NON IL CONTEGGIO — misurato, cosi' nessuno
    «allinea per coerenza» e rompe tre conflitti veri. Su quattro coppie che i
    test pretendono siano conflitti, TRE hanno UN SOLO token condiviso:

        Marco ha 30 anni. / Marco ha 40 anni.            1 token, quota 1.000
        Cache is bounded at 1024 / Cache holds 4096       1 token, quota 0.500
        Sessions ... TTL of 30 min / ... 45 minutes       1 token, quota 0.500

    `min_shared_tokens=2` le farebbe cadere tutte e tre. I fratelli lavorano su
    prosa e possono permetterselo; questo percorso deve reggere anche «Marco ha
    30 anni», dove un token condiviso e' il CENTO PER CENTO della frase. E'
    esattamente la differenza che il rapporto vede e il conteggio no: «marco»
    e' 1 su 1, «loop» e' 1 su 28.

    Cosa toglie: sul campione (220 fatti con quantita', 24090 coppie) i
    conflitti erano 321, di cui 84 (26%) retti da un solo token condiviso —
    «json» con unita' `tool` 5 contro 4, «chain» con `loc` 1700 contro 1414,
    «loop» con `skill` 8 contro 324. Fatti che non parlano della stessa cosa.
    E il costo non e' cosmetico: `anti_confab_gate.py` legge
    `verdict=contradicted` e manda il fatto vecchio a `_route_evolutions`,
    cioe' lo RITIRA — il meccanismo gia' quantificato il 01/08 come «la
    supersessione mangia i fatti veri».

    ENGRAM_CONFLICT_MIN_SHARED_RATIO=0 riporta al comportamento precedente."""
    from .env_num import env_float
    return max(0.0, env_float("ENGRAM_CONFLICT_MIN_SHARED_RATIO", 0.15))


def _shared_enough(da: set[str], db: set[str]) -> bool:
    """I token condivisi sono una frazione sufficiente della frase piu' povera?

    Sul lato PIU' POVERO e non sull'unione: se una frase corta e specifica
    incontra una prosa lunga, e' la corta a dire se il soggetto e' lo stesso.
    """
    soglia = _min_shared_ratio()
    if soglia <= 0.0:
        return True
    piccola = min(len(da), len(db))
    if piccola <= 0:
        return True
    return len(da & db) / piccola >= soglia


def contrasting_attrs(a_tokens: set[str], b_tokens: set[str]) -> bool:
    """True if the two token sets describe DIFFERENT attributes — each holds
    a different member of a contrasting-qualifier group (read vs write)."""
    for grp in CONTRAST_QUALIFIERS:
        ca, cb = a_tokens & grp, b_tokens & grp
        if ca and cb and ca != cb:
            return True
    return False


def distinctive_tokens(text: str) -> set[str]:
    """Content tokens minus the statement's own unit words (the 'subject')."""
    units = {u for (u, _v) in extract_quantities(text) if u}
    return {t for t in content_tokens(text) if norm_unit(t) not in units}


def conflict_from_parts(
    qa: set[tuple[str, float]], ca: set[str],
    qb: set[tuple[str, float]], cb: set[str],
    *, ia: set[tuple[str, int]] | None = None,
    ib: set[tuple[str, int]] | None = None,
) -> tuple[str, float, float] | None:
    """Core numeric-conflict check on PRE-COMPUTED quantities/content tokens.

    Lets a batch scan precompute ``(quantities, content_tokens)`` once per
    fact and reuse them across the O(n²) pair loop without re-parsing.
    Guards identical to :func:`numeric_conflict`.

    ``ia``/``ib`` are the pre-computed :func:`event_indices`. When both sides
    index the same KIND with different numbers they are different subjects, and
    no shared unit makes them comparable — pass them and the pair is refused
    before any value is compared. Optional so existing batch callers keep
    working; :func:`numeric_conflict` always supplies them.
    """
    if ia and ib and _indices_disjoint(ia, ib):
        return None  # different subject: "fatto 3" vs "fatto 5"
    if not qa or not qb:
        return None
    units_a = {u for (u, _v) in qa if u}
    units_b = {u for (u, _v) in qb if u}
    da = {t for t in ca if norm_unit(t) not in units_a}
    db = {t for t in cb if norm_unit(t) not in units_b}
    if not (da & db):
        return None  # unrelated subject
    if not _shared_enough(da, db):
        return None  # una parola su decine: prose diverse, non stesso soggetto
    if contrasting_attrs(ca, cb):
        return None  # different attribute (kept: catches pairs that share words)
    for (ua, va) in qa:
        if not ua:
            continue  # bare unitless number → too ambiguous
        for (ub, vb) in qb:
            if ua == ub and va != vb:
                return (ua, va, vb)
    return None


def agreement_from_parts(
    qa: set[tuple[str, float]], ca: set[str],
    qb: set[tuple[str, float]], cb: set[str],
) -> tuple[str, float] | None:
    """Twin of :func:`conflict_from_parts` — returns ``(unit, value)`` when a
    and b assert the SAME value for the same unit about the same subject
    (no contrasting qualifier); else ``None``. The positive signal behind
    corroboration: two statements that AGREE on a specific quantity.
    """
    if not qa or not qb:
        return None
    units_a = {u for (u, _v) in qa if u}
    units_b = {u for (u, _v) in qb if u}
    da = {t for t in ca if norm_unit(t) not in units_a}
    db = {t for t in cb if norm_unit(t) not in units_b}
    if not (da & db):
        return None
    if contrasting_attrs(ca, cb):
        return None
    for (ua, va) in qa:
        if not ua:
            continue
        for (ub, vb) in qb:
            if ua == ub and va == vb:
                return (ua, va)
    return None


def numeric_conflict(
    text_a: str, text_b: str,
) -> tuple[str, float, float] | None:
    """Return ``(unit, value_a, value_b)`` if *text_a* and *text_b* state a
    DIFFERENT value for the same unit about the same subject; else ``None``.

    Guards (precision over recall — a false conflict downgrades a true
    fact, the opposite of the trust we sell):
      • both must carry a quantity;
      • they must share ≥1 distinctive (non-unit) content word (same
        subject) — stops coincidental same-unit matches across topics;
      • no contrasting qualifier (read/write, client/server, …);
      • same normalised unit, different value.
    """
    return conflict_from_parts(
        extract_quantities(text_a), content_tokens(text_a),
        extract_quantities(text_b), content_tokens(text_b),
        ia=event_indices(text_a), ib=event_indices(text_b),
    )


# ---------------------------------------------------------------------------
# Lexical expansion (0.7.0): version / sub-year date / negation conflicts.
#
# Same design contract as the numeric detector — deterministic, zero-LLM,
# PRECISION over recall (a false conflict downgrades a true fact, the opposite
# of the trust we sell). Every detector requires the same-subject guard
# (shared distinctive content word) before a difference counts as a conflict.
# Single source of truth for write-time (validate_claim) and batch scanning.
# ---------------------------------------------------------------------------

# Dotted version strings. ≥3 numeric components ("2.3.1") are unambiguous
# anywhere; 2-component ("2.3") only counts near a version keyword, else it
# is a decimal quantity ("2.3 degrees") and belongs to the numeric path.
_VERSION3_RE = re.compile(r"(?<![\w.])v?(\d+(?:\.\d+){2,})(?!\w)(?!\.\d)")
# 2026-08-07 — LA PAROLA CHIAVE ERA IN INGLESE, e le altre lingue maggiori si
# salvavano PER SOMIGLIANZA invece che per copertura. Misurato:
#     EN runs version 2.1      -> {'2.1'}   DE laeuft Version 2.1     -> {'2.1'}
#     FR la version 2.1        -> {'2.1'}   ES la version 2.1         -> {'2.1'}
#     IT monta la versione 2.1 -> set()   🔴  DE Versionen / ES versiones 🔴
# ⇒ non cadeva «una lingua»: cadeva ogni forma DECLINATA. L'italiano declina
#   sempre («versione»), le altre solo al plurale — e l'unica lingua che non
#   funzionava mai e' quella in cui questo store e' scritto.
# COSTO, e il livello a cui e' misurato e' dichiarato perche' la mia prima
# versione di questa riga era piu' ambiziosa del dato:
#     version_conflict IT   riga vecchia: None   con la cura: ('2.1','3.4')
#     lexical_conflict IT   riga vecchia: None   con la cura: ('version','2.1 vs 3.4')
# ⇒ IL BENEFICIO DIMOSTRATO E' IL RILEVAMENTO. Due fatti italiani sulla stessa
#   cosa a due versioni diverse non producevano NESSUN conflitto, ne' dal
#   detector ne' dal composto che sta a valle.
# ⚠️ NON e' dimostrata la supersessione: sul banco end-to-end (Client.add, store
#   isolato, stesso topic e topic diversi) il numero di fatti vivi e' IDENTICO
#   con e senza la cura — 1 e 1, poi 2 e 2. A stesso topic il vecchio veniva
#   gia' ritirato da un'altra via; a topic diversi non lo ritira nessuna delle
#   due. Che il conflitto sia RILEVATO e non produca supersessione in `add()` e'
#   una domanda aperta, non un difetto dimostrato: non l'ho inseguita qui.
# 📌 E' la regola di casa applicata a me stesso: regex interna < funzione
#   pubblica < porta che il prodotto usa, e ogni salto puo' ribaltare. Il primo
#   commit di questa cura dichiarava «il vecchio resta vivo accanto al nuovo»
#   misurandolo al secondo livello e scrivendolo come se fosse il terzo.
# LA CURA E' LA RADICE, non l'elenco delle lingue: tutte le romanze e le
# germaniche prendono la parola dal latino *versio*, e un suffisso libero copre
# version(s) · versione · versioni · versionen · versión · versiones ·
# versioning, comprese le lingue che nessuno di noi parla.
# ⚠️ PERCHE' `version` E NON `versi`, che sarebbe piu' corta e coprirebbe anche
#   il portoghese in un colpo: in italiano «versi» sono le righe di una poesia
#   («i versi 2.3 sono i piu' belli»). L'omografo decide la forma della radice,
#   e il portoghese va elencato a parte. E' la lezione di ws4 su «ora».
# ⛔ `release` e `build` NON sono stati estesi: sono prestiti che ogni lingua
#   tecnica usa in inglese. La parola che le lingue traducono davvero e' *version*.
_VERSION2_KW_RE = re.compile(
    r"\b(?:vers(?:ion\w*|ión\w*|ão|ões|ao|oes)|release|releases|build|builds|v)"
    r"[\s:]{0,3}"
    r"(\d+\.\d+(?:\.\d+)*)(?!\w)(?!\.\d)",
    re.IGNORECASE,
)


def extract_versions(text: str) -> set[str]:
    """Version strings in *text*, normalised without the ``v`` prefix."""
    t = text or ""
    out = {m.group(1) for m in _VERSION3_RE.finditer(t)}
    out.update(m.group(1) for m in _VERSION2_KW_RE.finditer(t))
    return out


# The version/date carrier words are not the SUBJECT (like units for the
# numeric path): "version"/"release" shared between two statements says
# nothing about them describing the same thing.
_VERSION_CARRIER_TOKENS = frozenset({"version", "release", "build"})

_CAPS_NAME_RE = re.compile(r"\b[A-Z][a-zA-Z]{2,}\b")

#: L'inizio di una frase, dove la maiuscola e' punteggiatura e non un nome.
_APRE_LA_FRASE_RE = re.compile(r"(?:^|[.;:!?\n]\s*|^\s*[-•*]\s*)([A-Z][a-zA-Z]{2,})")

def _nomi_propri(testo: str) -> set[str]:
    """Le parole maiuscole di *testo* che sono davvero NOMI PROPRI.

    ⛔ IL DIFETTO CURATO (2026-08-07). La firma era `[A-Z][a-zA-Z]{2,}` — una
    maiuscola e due lettere — e in italiano la soddisfano tutte le parole che
    APRONO una frase::

        «Sul corpus reale…» vs «Dopo la cura…»   -> soggetti «Sul» e «Dopo»
        «ASSUNTO che…»      vs «CONFERMATA la…»  -> soggetti urlati

    Due frasi che cominciano con parole diverse avevano «nomi propri disgiunti»
    e la guardia concludeva che parlassero di cose diverse: un veto che scatta
    sulla punteggiatura. Misurato in indipendenza da ws1 (5120 conflitti su
    21151, 24,2%) e da ws4 (147 coppie vere, 26,5%) — due stime che convergono.

    IL CRITERIO E' DI ws4, ed e' raro perche' migliora ENTRAMBE le popolazioni
    insieme: sulle 147 coppie vere toglie 22 falsi soggetti E AGGIUNGE 5
    protezioni su coppie con sovrapposizione mediana 3,9% — ritiri quasi
    certamente sbagliati che oggi passano. I casi protetti scendono da 39 a 22.

    ⚠️ NON E' POSIZIONALE PURO, ED E' IL CORPUS REALE A ESIGERLO. La lettura
    ovvia del criterio — «scarta la parola che apre la frase» — l'ho misurata
    sugli 8865 fatti dello store: **il 72% delle proposizioni apre con una
    maiuscola**, e le piu' frequenti sono `PYTEST` 268, `Orin` 149, `OMNEX` 119,
    `VERIMEM` 103, `Lab`, `MASTER`, `User`, `Pattern` — nomi propri veri.
    Scartare per posizione spegnerebbe la guardia proprio sui soggetti piu'
    ricorrenti del corpus. La parola cade solo se apre la frase **ed e' anche
    una parola funzionale**, cioe' se non puo' essere un nome in nessuna lettura.

    MISURATO sul corpus, entrambe le popolazioni::
        aperture maiuscole            6420
          scartate (funzionali)        794  12,4%   Per Non DEI GLI UNA COME Nel
          tenute   (candidati nome)   5626  87,6%   OMNEX HippoAgent Episodes

    ⚠️ La lista NON e' `composer._ARTICOLI_TUTTI`, che era la strada proposta e
    l'ho verificata prima di prenderla: ha 20 voci — il, la, the, el… — e non
    contiene NESSUNA delle parole del referto (`sul`, `dopo`, `assunto`,
    `questo`: tutte assenti). Gli articoli non aprono le frasi di questo store:
    le aprono le PREPOSIZIONI, che stanno in `_NON_UNIT_WORDS`.

    ⚠️ DUE LIMITI APERTI E DICHIARATI, che sono la stessa firma troppo larga:
      · NON VEDE `S-007`, `SRV-12`, `L-45` — cifra e trattino, e nei domini veri
        (macchine, lotti, ticket, server) sono LA norma. Allargare alle cifre
        farebbe entrare versioni e date come soggetti (controipotesi di ws4).
      · CONTA GLI ACRONIMI — `RAM`, `CPU`, `API`. Effetto oggi benigno (uniscono
        due frasi che parlano della stessa cosa) ma la firma e' la stessa.
      · `_NON_UNIT_WORDS` e' piu' ricca in italiano che in inglese, quindi
        `This`, `All`, `Across`, `Multiple` in apertura restano contati come
        nomi. Si vede nel campione delle 5626 tenute: la cura toglie i falsi
        soggetti italiani e lascia quelli inglesi.
    """
    testo = testo or ""
    apre = {m.group(1) for m in _APRE_LA_FRASE_RE.finditer(testo)}
    return {w for w in _CAPS_NAME_RE.findall(testo)
            if not (w in apre and w.lower() in _NON_UNIT_WORDS)}


def _named_subjects_disjoint(text_a: str, text_b: str) -> bool:
    """True when BOTH statements name capitalized subjects and the two sets
    are fully disjoint ("Orion ..." vs "Zephyr ...") — different named
    things, so a differing version/date between them is NOT a conflict."""
    ca = _nomi_propri(text_a)
    cb = _nomi_propri(text_b)
    return bool(ca) and bool(cb) and not (ca & cb)


def version_conflict(text_a: str, text_b: str) -> tuple[str, str] | None:
    """``(version_a, version_b)`` if the two statements pin DIFFERENT versions
    for the same subject; ``None`` otherwise. Disjoint version sets on a
    shared subject = the value moved (2.3.1 → 4.0.0)."""
    va, vb = extract_versions(text_a), extract_versions(text_b)
    if not va or not vb or (va & vb):
        return None
    shared = (distinctive_tokens(text_a) & distinctive_tokens(text_b))
    if not (shared - _VERSION_CARRIER_TOKENS):
        return None  # unrelated subject (carrier words don't count)
    if _named_subjects_disjoint(text_a, text_b):
        return None  # different named things (Orion vs Zephyr)
    if contrasting_attrs(content_tokens(text_a), content_tokens(text_b)):
        return None
    return (sorted(va)[0], sorted(vb)[0])


# Sub-year dates: ISO ``YYYY-MM-DD`` plus month names (EN). Different YEARS
# are deliberately left to validate_claim's year-disjoint rule — these
# detectors only handle the finer granularity the year rule cannot see.
_ISO_DATE_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})-(\d{2})-(\d{2})\b")
_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}
_MONTH_RE = re.compile(
    r"\b(january|february|march|april|may|june|july|august|september|"
    r"october|november|december)\b(?:\s+(\d{1,2})(?:st|nd|rd|th)?(?!\d))?"
    r"(?:,?\s+(1[5-9]\d{2}|20\d{2}))?",
    re.IGNORECASE,
)


# A BARE month word (no day, no year) is only a date when anchored: the word
# is Capitalized AND preceded by a temporal preposition. Kills the classic
# false positives — "the audit may slip" (modal), "they march to the office"
# (verb) — while keeping "moved to September" / "launches in May".
_TEMPORAL_PREPS = frozenset({
    "in", "on", "by", "until", "till", "before", "after", "since", "during",
    "to", "from", "for", "late", "early", "mid", "next", "last", "this",
    "around", "circa",
})


def extract_dates(text: str) -> set[tuple[int | None, int, int | None]]:
    """``(year, month, day)`` tuples from ISO dates and month names.

    Year/day are ``None`` when the text does not state them ("moved to
    September"). Bare years carry no month → they stay with the year rule.
    A bare month word needs a Capitalized form + temporal preposition (see
    ``_TEMPORAL_PREPS``) — "may"/"march" as modal/verb are not dates.
    """
    t = text or ""
    out: set[tuple[int | None, int, int | None]] = set()
    for m in _ISO_DATE_RE.finditer(t):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            out.add((y, mo, d))
    for m in _MONTH_RE.finditer(t):
        mo = _MONTHS[m.group(1).lower()]
        day = int(m.group(2)) if m.group(2) else None
        year = int(m.group(3)) if m.group(3) else None
        if day is None and year is None:
            if not m.group(1)[0].isupper():
                continue  # "may slip", "march to the office"
            # Bounded look-behind: only the word IMMEDIATELY before the match
            # decides the anchor, so re-scanning the whole prefix for every
            # match was O(n*m). Measured on 'May ' repeated (audit F8):
            # 20k chars 1.35s, 40k 5.80s, 80k 23.38s — textbook quadratic, and
            # this path runs on every write under validate="full", so one
            # oversized proposition could pin a shared gateway for everyone.
            _win = t[max(0, m.start() - 64):m.start()]
            prev = re.findall(r"[A-Za-z]+", _win)
            if not prev or prev[-1].lower() not in _TEMPORAL_PREPS:
                continue  # Capitalized but unanchored ("May I help")
        out.add((year, mo, day))
    return out


def date_conflict(
    text_a: str, text_b: str,
) -> tuple[tuple[int | None, int, int | None],
           tuple[int | None, int, int | None]] | None:
    """A sub-year date move about the same subject: same (or unstated) year
    but a DIFFERENT month, or same year+month but a different day. Pairs
    with different years return ``None`` (the year-disjoint rule owns them)."""
    da, db = extract_dates(text_a), extract_dates(text_b)
    if not da or not db or (da & db):
        return None
    if not (distinctive_tokens(text_a) & distinctive_tokens(text_b)):
        return None  # unrelated subject
    if _named_subjects_disjoint(text_a, text_b):
        return None  # different named things
    if contrasting_attrs(content_tokens(text_a), content_tokens(text_b)):
        return None
    for (ya, ma, dda) in da:
        for (yb, mb, ddb) in db:
            same_year = ya is None or yb is None or ya == yb
            if not same_year:
                continue  # year rule's jurisdiction
            if ma != mb:
                return ((ya, ma, dda), (yb, mb, ddb))
            if dda is not None and ddb is not None and dda != ddb:
                return ((ya, ma, dda), (yb, mb, ddb))
    return None


# Polarity flip: the same statement with a negator on exactly one side.
#
# ⚠️ QUESTA E' LA SUPERFICIE UNICA DEI NEGATORI, dal 2026-08-04.
# `contradiction._has_negation` la importa invece di tenere la propria lista:
# ne esistevano DUE, con difetti complementari, ed e' il motivo per cui il
# difetto e' sopravvissuto a lungo.
#
#   contradiction._has_negation        aveva gia' l'italiano  MA girava solo
#                                      dentro scan_corpus, mai in scrittura
#   quantity_match._NEGATOR_RE (qui)   gira in scrittura      MA era solo
#                                      inglese
#
# Il prodotto sapeva riconoscere una negazione italiana e sapeva usarla, in due
# posti diversi e mai insieme. Effetto misurato: «Il farmaco riduce la
# mortalita» e «Il farmaco NON riduce la mortalita» restavano VIVI ENTRAMBI,
# mentre le stesse due in inglese no. Per una memoria verificata e' il guasto
# peggiore: la smentita convive col fatto e la domanda dopo ne pesca uno a caso.
#
# Isolato passo per passo, tutto il resto del percorso funzionava gia':
# content_tokens identici, jaccard 4/4 = 1.00, contrasting_attrs False. Cadeva
# solo `_has_negator`, alla prima riga.
_NEGATOR_RE = re.compile(
    # inglese (l'insieme originale)
    r"\b(?:not|never|no longer|cannot|can't|won't|isn't|aren't|wasn't|"
    r"weren't|doesn't|don't|didn't|nor|no)\b"
    # italiano: «non» e' una PAROLA qui e un PREFISSO in inglese
    # (non-blocking, non-deterministic), quindi si esclude il trattino —
    # senza questa guardia un corpus tecnico inglese darebbe falsi positivi
    # a raffica.
    r"|(?<![\w-])non(?![-\w])"
    # tedesco · olandese · polacco · scandinavi
    r"|\b(?:nicht|kein(?:e|en|em|er|es)?|niet|geen|nie|ikke|inte|ei)\b"
    # spagnolo · portoghese (il «no» spagnolo e' gia' coperto dall'inglese)
    r"|\b(?:n[aã]o|nunca|jam[aá]s|tampoco)\b"
    # francese: «ne … pas» e' discontinuo, quindi si aggancia il «ne» solo se
    # il «pas» arriva poco dopo — «ne» da solo e' troppo corto e frequente
    # per essere un negatore affidabile.
    r"|\bne\b(?=.{0,40}\bpas\b)|\bn'(?=.{0,40}\bpas\b)"
    # LINGUE A NEGAZIONE MORFOLOGICA. Il giapponese nega col suffisso verbale,
    # il cinese con una particella attaccata, l'arabo con una particella
    # separata: nessuno di questi e' una «parola» delimitata da spazi, ma sono
    # tutti riconoscibili lessicalmente — e lasciarli fuori sarebbe coprire
    # «le lingue con gli spazi» invece che «le lingue».
    r"|(?:ません|ないです|なかった|ない|ぬ)"
    r"|(?:没有|不是|不会|不能|不|未|非)"
    r"|(?:\bلا\b|\bلم\b|\bلن\b|\bليس\b)",
    re.IGNORECASE,
)


def _has_negator(text: str) -> bool:
    return bool(_NEGATOR_RE.search(text or ""))


def _negated_tokens(text: str) -> set[str]:
    """Content words in the negator's SCOPE: the first 1-2 alpha tokens right
    after each negator, singularised like :func:`content_tokens`."""
    t = text or ""
    out: set[str] = set()
    for m in _NEGATOR_RE.finditer(t):
        following = re.findall(r"[a-zA-Z]{4,}", t[m.end():])[:2]
        for w in following:
            w = w.lower()
            if w.endswith("ies"):
                w = w[:-3] + "y"
            elif w.endswith("s") and len(w) > 3:
                w = w[:-1]
            out.add(w)
    return out


def negation_conflict(text_a: str, text_b: str) -> str | None:
    """The shared predicate token when *text_a*/*text_b* state the SAME thing
    with OPPOSITE polarity ("is signed" vs "is not signed"); else ``None``.

    Precision guards: the polarity must differ, the content-token sets must
    be near-identical (Jaccard ≥ 0.6 with ≥2 shared tokens), AND the word in
    the negator's scope must itself be SHARED — "complete, not blocked" does
    not flip "complete" (the negator scopes "blocked", absent from the other
    statement)."""
    na, nb = _has_negator(text_a), _has_negator(text_b)
    if na == nb:
        return None  # same polarity → no flip
    ca, cb = content_tokens(text_a), content_tokens(text_b)
    shared = ca & cb
    union = ca | cb
    if len(shared) < 2 or not union or (len(shared) / len(union)) < 0.6:
        return None  # different statement, not a flip of this one
    if contrasting_attrs(ca, cb):
        return None
    scoped = _negated_tokens(text_a if na else text_b)
    scoped_shared = scoped & shared
    if scoped and not scoped_shared:
        return None  # the negation targets a word the other side never states
    if scoped_shared:
        return sorted(scoped_shared)[0]
    return sorted(shared)[0]


def lexical_conflict(text_a: str, text_b: str) -> tuple[str, str] | None:
    """First lexical conflict between two statements as ``(kind, detail)`` —
    kind ∈ {"numeric", "version", "date", "negation"} — or ``None``.

    The one-call façade over the four deterministic detectors, so callers
    (gate, scanners, benches) share identical semantics."""
    q = numeric_conflict(text_a, text_b)
    if q is not None:
        u, va, vb = q
        return ("numeric", f"{va:g} {u} vs {vb:g} {u}")
    v = version_conflict(text_a, text_b)
    if v is not None:
        return ("version", f"{v[0]} vs {v[1]}")
    d = date_conflict(text_a, text_b)
    if d is not None:
        return ("date", f"{d[0]} vs {d[1]}")
    n = negation_conflict(text_a, text_b)
    if n is not None:
        return ("negation", f"polarity flip on '{n}'")
    return None


# Ordinal EVENT indices ("day 4", "sprint 3", "week 12"): a cardinal counter of
# repeated events, NOT a calendar value. Two statements carrying DIFFERENT
# indices of the same kind narrate two distinct events (a diary), so neither
# supersedes nor contradicts the other. Calendar dates (March, 2025-03-06) are
# deliberately excluded — "launches in March" -> "launches in September" is one
# VALUE moving, which the evolution path must keep superseding.
#: Words whose following number IDENTIFIES rather than MEASURES. "45 ms" is a
#: measure — a different value is the same thing having changed. "issue 42" is an
#: identifier — a different value is a DIFFERENT thing, and no other quantity in
#: the sentence can make the two statements comparable.
#:
#: 2026-07-25 — extended from diary kinds (day/week/cycle…) to entity names, in
#: both languages, and to the ``#42`` spelling. Before this, "il fatto 3 ha 500
#: righe" and "il fatto 5 ha 200 righe" were declared a conflict: the shared unit
#: was 'righe' and the distinctive words matched, so the judge read one subject
#: with a changed value, while the indices 3 and 5 say they are two subjects.
#: Masking the offending function words (the earlier cure) treated the symptom;
#: this is the distinction the detector was missing.
_EVENT_INDEX_RE = re.compile(
    r"\b(day|night|week|month|quarter|sprint|round|session|meeting|"
    r"iteration|cycle|episode|phase|step|attempt|run|note|entry|item|log|"
    r"chapter|part|lesson|task|"
    # entity identifiers — EN
    r"issue|ticket|bug|pr|line|port|record|fact|project|commit|batch|slot|"
    r"row|column|page|version|build|job|worker|shard|partition|"
    # entity identifiers — IT
    r"fatto|riga|colonna|porta|progetto|punto|nota|capitolo|paragrafo|"
    r"pagina|ciclo|fase|passo|tentativo|elemento|scheda|turno|lotto"
    # `\s*(?:#\s*)?` e NON `\s*#?\s*`: la seconda forma ha due quantificatori di
    # spazio separati da un opzionale, quindi su una corsa di spazi il motore
    # prova ogni divisione fra i due e degrada col QUADRATO dell'input —
    # misurato 4031 ms su 16000 spazi, e questo modulo legge il testo dei fatti
    # scritti dall'utente. Qui gli spazi dopo il cancelletto esistono solo se il
    # cancelletto c'e': nessuna ambiguita', crescita lineare, stesse forme
    # riconosciute. Segnalato da CodeQL (py/polynomial-redos) su una PR.
    r")\s*(?:#\s*)?(\d{1,6})\b",
    re.IGNORECASE,
)


#: Alphanumeric CODES: an alphabetic prefix glued to digits — A000030 (OEIS),
#: CVE2024, ABC123. The prefix is the kind, the digits the index, so two codes
#: with the same prefix and different numbers are different things.
#:
#: A commit SHA must NOT match (every fact citing one would become its own
#: subject): the trailing ``\b`` after the digits rejects "a64d252", because the
#: letters resume. Same for versions like "v1" — at least two digits are needed.
_ALNUM_CODE_RE = re.compile(r"\b([A-Za-z]{1,6})(\d{2,})\b")


#: The POSITIONAL rule, which no list of kinds can replace: a word followed by a
#: BARE number indexes something ("message 0", "issue 42", "porta 8080"), while a
#: number followed by a unit measures it ("7883 test", "45 ms"). The named lists
#: above stay for the kinds worth treating specially (progression), but this is
#: what covers the open vocabulary.
#:
#: Why it exists: a suite test proved the closed list could not hold. Of 9
#: distinct facts — "sends message 0/1/2", "stores profile 0/1/2", "computes rate
#: 0/1/2" — SEVEN were retired, because message/profile/rate were not listed.
#: A vocabulary cannot be enumerated; a position can be read.
#: Stessa cura anti-ReDoS di _EVENT_INDEX_RE, e per lo stesso motivo misurato.
_GENERIC_INDEX_RE = re.compile(
    r"\b([A-Za-z][A-Za-z_-]{2,})\s*(?:#\s*)?(\d{1,6})\b")


def _bare_numbers(text: str) -> set[str]:
    """Numbers in *text* that carry NO unit — the ones eligible to be indices.
    Reads the same extractor the measure path uses, so the two can never disagree
    about which numbers are measures."""
    return {f"{v:g}" for (u, v) in extract_quantities(text) if not u}


def event_indices(text: str) -> set[tuple[str, int]]:
    """``(kind, n)`` indices in the CLAIM part of *text*: ordinals ("day 4" ->
    ("day", 4)), entity identifiers ("issue #42" -> ("issue", 42)), alphanumeric
    codes ("A000030" -> ("a", 30)) and the positional rule — any word followed by
    a bare number ("message 0" -> ("message", 0)).

    Reads :func:`claim_span`, not the whole text, for the same reason quantities
    do: an identifier in the PROVENANCE names the check, not the subject. Caught
    by a null-control test — "la suite conta 7883 test | evidence: pytest run
    12345" against the same claim proved by "run 99999" was read as two different
    subjects, so a real conflict on the claim went undetected.
    """
    span = claim_span(text)
    out = {(m.group(1).lower(), int(m.group(2)))
           for m in _EVENT_INDEX_RE.finditer(span)}
    out |= {(m.group(1).lower(), int(m.group(2)))
            for m in _ALNUM_CODE_RE.finditer(span)}
    # positional rule, gated on the number being BARE: "message 0" indexes,
    # "conta 7883 test" measures and must stay a measure
    bare = _bare_numbers(text)
    out |= {(m.group(1).lower(), int(m.group(2)))
            for m in _GENERIC_INDEX_RE.finditer(span)
            if f"{float(m.group(2)):g}" in bare}
    return out


#: Kinds whose number marks a STAGE of one thing, not one thing among many.
#: "version 2" is the same module later; "issue 43" is another issue. Treating the
#: first group as identifiers lost legitimate retirements — counterexample from an
#: adversarial review (glm-5.2, 2026-07-25), confirmed by running it:
#:   "issue 42, fase 1: bug aperto"  vs  "issue 42, fase 2: bug chiuso"
#:   "version 1: latenza 45 ms"      vs  "version 2: latenza 200 ms"
#: read as different subjects, so the stale value stayed. These kinds are still
#: EXTRACTED (a caller may want them) but they never make two subjects.
_PROGRESSION_KINDS = frozenset({
    "version", "build", "phase", "fase", "step", "passo", "cycle", "ciclo",
    "iteration", "attempt", "tentativo", "round", "turno", "part", "parte",
})


def _indices_disjoint(ea: set[tuple[str, int]],
                      eb: set[tuple[str, int]]) -> bool:
    """Core of :func:`distinct_event_indices` on PRE-COMPUTED index sets, so the
    numeric path can reuse it without re-parsing the text.

    Progression kinds are skipped: a different stage number is the same subject
    moving on, and letting it claim "different subjects" hid real evolutions.
    """
    if not ea or not eb:
        return False
    # Compare the index SETS, do not hunt for a shared kind. Hunting was the
    # bigger hole and only strumenting the write path found it: with different
    # kinds the loop never ran, so the guard answered "not different subjects" —
    # the opposite of the truth. Measured: one fact about "email/message 0"
    # retired THREE about "tax/rate 0/1/2".
    ia = {(k, n) for (k, n) in ea if k not in _PROGRESSION_KINDS}
    ib = {(k, n) for (k, n) in eb if k not in _PROGRESSION_KINDS}
    if ia and ib and ia != ib:
        return True
    shared = ({k for (k, _n) in ea} & {k for (k, _n) in eb}) - _PROGRESSION_KINDS
    for k in shared:
        na = {n for (kk, n) in ea if kk == k}
        nb = {n for (kk, n) in eb if kk == k}
        # DIFFERENT index sets = different subjects. Two earlier criteria were
        # both too strict, each failing on a real case from the corpus:
        #   * "disjoint intersection" missed statements sharing a common term —
        #     the OEIS relations "A000030 - A000045" and "A000032 - A000045" both
        #     cite A000045, so the sets intersect while 30 and 32 say plainly
        #     that the subjects differ;
        #   * "each side has an exclusive index" then missed the SUBSET case —
        #     a relation over {A000032, A000045} against one over {A000045}.
        # Equality is the honest test: same indices = same subject (so "fatto 3
        # ha 500 righe" vs "fatto 3 ha 200 righe" stays a real conflict), any
        # difference = another thing being talked about.
        if na != nb:
            return True  # same kind, different indices -> different things
    return False


def indexed_vs_unindexed(text_a: str, text_b: str) -> bool:
    """True when ONE statement names indexed subjects and the other names none.

    A specific statement and a generic one have no subject in common to
    contradict. Found by dogfooding 2026-07-25: the service note "a stray note
    that is not a relation" SUPERSEDED a verified relation
    "OEIS verified relation: +2*A000217(n) -A002378(n) = 0" — the NLI judge read
    the negation ("is NOT a relation" vs "verified relation") as a contradiction,
    and same-source + later time turned it into a retirement.

    Scope note for whoever wires this: it is a PRECISION guard on a model's
    verdict, not on the deterministic detectors — same call as the reference
    guard after the adversarial review. On the deterministic path a concrete
    clash (same unit, different value) stands on its own evidence.
    """
    ia, ib = event_indices(text_a), event_indices(text_b)
    return bool(ia) != bool(ib)


def distinct_event_indices(text_a: str, text_b: str) -> bool:
    """True when the two statements index DIFFERENT things of the same kind
    ("On day 4 ..." vs "On day 5 ...", "issue 42" vs "issue 43"): distinct
    subjects, not an evolution and not a contradiction. False when either
    carries no index, or the shared kind has the same index."""
    return _indices_disjoint(event_indices(text_a), event_indices(text_b))


__all__ = [
    "YEAR_RE",
    "CONTRAST_QUALIFIERS",
    "norm_unit",
    "extract_quantities",
    "content_tokens",
    "contrasting_attrs",
    "distinctive_tokens",
    "conflict_from_parts",
    "numeric_conflict",
    "extract_versions",
    "version_conflict",
    "extract_dates",
    "date_conflict",
    "negation_conflict",
    "lexical_conflict",
    "event_indices",
    "distinct_event_indices",
    "indexed_vs_unindexed",
]
