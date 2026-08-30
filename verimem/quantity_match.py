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
# diagnosi gia' scritta quindici righe piu' sotto. Misurato (gradino 4):
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
# CJK. L'osservazione che lo rende curabile: `\w` comprende
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
# era l'avvertimento in sede di revisione, e questo e' il modo di rispettarlo.
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
# ⚠️ E ANCHE IL PUNTO DEL LOOKBEHIND VA QUALIFICATO, ed e' la
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
    # LA VIRGOLA DECIMALE ITALIANA, con lo STESSO criterio del punto ambiguo.
    # Il gate leggeva «176,6 MB» come DUE valori (176 e 6) e accusava la fonte di
    # non contenerli: misurato alla porta, `source «committed=176.6 MB»` +
    # `claim «176,6 MB»` -> downgrade con grounding 100.0 e
    # «...non contiene: 6 mb, 176». Firma sul corpus: 5 quarantinati su 71 con un
    # decimale a virgola contro 1 ammesso su 600 (35x).
    # ⚖️ SI ACCETTANO SOLO 1-2 CIFRE dopo la virgola, ed e' la riga che rende la
    # cura sicura in inglese: un separatore di MIGLIAIA ne ha sempre TRE
    # (`1,234`), quindi non entra qui e resta all'ambiguita' dichiarata —
    # esattamente come `_PUNTO_AMBIGUO` fa con `45.000`. Allargare a `[.,]\d+`
    # avrebbe letto «1,234 facts» come milleduecentotrentaquattro virgola.
    r"(?<![A-Za-z0-9_])(?<!\d\.)(?<!\d,)(\d+(?:\.\d+|,\d{1,2})?)(?:\s{0,3}-?\s{0,3}([^\W\d_]+))?"
    r"(?![A-Za-z0-9_])(?!\.\d)(?!,\d)",
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
# che non esistono (misurato: 28 conflitti su 30 fra topic diversi, unita' `verified`
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
    # store contiene di piu': misurato, «7453 verified contro 553».
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


#: La coda in HIRAGANA di un'unita' giapponese. Non e' una lista di verbi: e'
#: la struttura ortografica della lingua (okurigana), che scrive le desinenze
#: in hiragana e lascia sostantivi e unita' in katakana o kanji.
_CODA_HIRAGANA_RE = re.compile(r"[ぁ-ゟ]+$")


def _senza_coda_verbale_giapponese(w: str) -> str:
    """«480パレット**あります**» e «320パレット**です**» misurano la stessa cosa.

    ⚠️ IL DIFETTO CHE CURA, misurato prima di scriverla — due frasi giapponesi
    che si contraddicono, con verbi diversi::

        ヴェローナの倉庫には480パレットあります  ->  ('パレットあります', 480.0)
        ヴェローナの倉庫は320パレットです      ->  ('パレットです',   320.0)
        numeric_conflict                    ->  None      ⇐ falso negativo

    🔑 LA CAUSA NON È LA LINGUA, È LA POSIZIONE DEL VERBO, e si vede solo
    confrontando le due lingue senza spazi::

        ZH  有480个托盘 / 存放320个托盘  ->  ('个托盘', 480) e ('个托盘', 320)  ✅
        JA  480パレットあります / 320パレットです                              ❌

    In cinese il verbo precede il numero e resta fuori dall'unita'; in
    giapponese la segue e ci entra dentro. Stesso parser, stesso difetto
    potenziale, esito opposto per l'ordine delle parole.

    ⚖️ PERCHÉ UN CRITERIO E NON UNA LISTA DI VERBI: le desinenze giapponesi si
    scrivono in hiragana e le unita' in katakana o kanji — e' ortografia, non
    vocabolario, quindi copre anche i verbi che nessuno ha elencato. È la stessa
    scelta di `_DATA_CJK` (`8月10日` vale per due lingue senza dizionario) e di
    `norm_unit` sui diacritici, che questa casa ha gia' pagato tre volte per due
    elenchi divergenti.

    ⚠️⚠️ IL PRESIDIO NON È DECORAZIONE — la versione senza cade sulla
    popolazione opposta, e l'ho misurata prima di scegliere. Diversi contatori
    giapponesi **sono** hiragana::

        つ  こ  ひとつ  まい  ほん  ぴき      ->  tagliati a stringa VUOTA

    `つ` è il contatore generico, `まい` conta i fogli, `ぴき` gli animali
    piccoli: unita' legittime e frequenti. Se dopo il taglio non resta nulla,
    la parola ERA l'unita' e si tiene intera. Con il presidio: 11 casi su 11
    corretti, cinque code verbali tolte e sei unita' hiragana conservate.

    📌 RESTA SCOPERTO il verbo scritto in KANJI: «ミリグラム含まれています» ->
    «ミリグラム含», dove 含 è la radice di 含まれる. Il taglio migliora e non
    chiude, ed è dichiarato invece che taciuto.
    """
    tagliata = _CODA_HIRAGANA_RE.sub("", w)
    return tagliata if tagliata else w


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
    w = _senza_coda_verbale_giapponese((word or "").lower())
    if w in _UNIT_SYN:
        return _UNIT_SYN[w]
    piano = _senza_diacritici(w)   # `w` e' gia' .lower()
    if piano != w and piano in _UNIT_SYN:
        return _UNIT_SYN[piano]
    if piano != w:
        w = piano
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    # IL PLURALE NON E' SOLO INGLESE. Censito sul mandato lingue:
    #     EN  minute -> min      minutes -> min        ok
    #     FR  minute -> min      minutes -> min        ok  <- per caso, parola uguale
    #     ES  minuto -> minuto   minutos -> minuto     ok  <- per caso, plurale in -s
    #     IT  minuto -> minuto   minuti  -> minuti     DUE UNITA' DIVERSE
    #     DE  Minute -> min      Minuten -> minuten    idem
    # Le tre lingue che funzionavano funzionavano PER CASO, e non era una
    # scelta di nessuno: era il bordo di una regola scritta per una lingua sola.
    # Costo: due fatti sulla stessa grandezza non condividono l'unita', quindi
    # un conflitto vero puo' sfuggire, e `L4.2` (il vicinato) eredita il bordo
    # perche' sta a valle — «45 Minuten» contro «30 Minuten» e' il caso limite.
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
    Costo misurato: dei quarantinati di agosto con grounding **sopra 90**
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


#: «45.000» NON vale 45, e finché non sappiamo se vale 45000 non vale NIENTE.
#:
#: IL DIFETTO CHE LO MOTIVA e' il peggiore che questo prodotto abbia avuto, ed e'
#: stato trovato la notte del 09→10/08 in tre, nessuno leggendo il codice::
#:
#:     claim  «Lo stipendio annuo e' 45.000 euro»   (quarantacinquemila)
#:     fonte  «Contratto: lo stipendio e' 45 euro»  (quarantacinque)
#:     -> AMMESSO, nessuna obiezione
#:
#: perche' `float("45.000")` da' 45.0. Il gate non taceva e non accusava a torto:
#: **certificava come vero un fatto che la fonte contraddice di mille volte**.
#: La causa prima e' che il punto e' ANCHE il separatore decimale inglese, quindi
#: il pattern lo accetta volentieri e `float` restituisce un numero CREDIBILE e
#: falso. Delle quattro notazioni che rompono l'estrattore (virgola migliaia,
#: virgola decimale, spazio del SI, punto) questa e' l'unica che certifica: le
#: altre SPEZZANO il numero, un pezzo non sta nella fonte, e il layer protesta —
#: rumorose ma oneste. 🔑 **La classe piu' pericolosa e' quella che somiglia di
#: piu' a una notazione valida.**
#:
#: QUANTO E' GRANDE, misurato sul corpus reale (semantic.db in mode=ro,
#: 9365 proposizioni): la classe pericolosa e' **100 · 1,07%**, quella invisibile
#: (due o piu' gruppi, «1.500.000» -> `[]`) e' **2 · 0,02%** — CINQUANTA A UNO. E
#: le righe sono nostre: «102.913 LOC» letto 102.9, «16.300+ test pytest verdi»
#: letto 16.3 in tre fatti diversi. ⚠️ campione: 6 righe lette su 100, non tutte.
#:
#: IL CRITERIO, misurato 9/9 PRIMA di scrivere la cura. Ambiguo = tre cifre dopo
#: il punto, parte intera diversa da zero e non piu' lunga di tre cifre. Le due
#: osservazioni che lo rendono preciso, ed entrambe salvano dei veri decimali:
#:
#:   · `0.250` NON puo' essere migliaia: «zero mila duecentocinquanta» non esiste
#:     in nessuna convenzione ⇒ millesimi e tolleranze restano misurabili
#:   · un gruppo di migliaia ha ESATTAMENTE tre cifre ⇒ `3.1416` e' decimale
#:     certo, e la precisione scientifica non si perde
#:
#: ⚠️ E NON E' DISAMBIGUARE — quella strada e' stata scartata perche' «12,450»
#: vale 12450 in inglese e 12,45 in italiano, e sbagliare significherebbe
#: confrontare due valori diversi credendoli uguali: un difetto SILENZIOSO,
#: peggiore di quello che si cura. Qui si smette solo di AFFERMARE una
#: disambiguazione che non abbiamo.
#:
#: COSTO DICHIARATO: `3.141` (pi greco) diventa non misurabile, ed e' corretto —
#: in un testo italiano quel numero e' tremilacentoquarantuno. Sul corpus di casa
#: il costo e' zero: nelle righe del campione nessuna era un decimale legittimo.
_PUNTO_AMBIGUO = re.compile(r"(?!0\.)\d{1,3}\.\d{3}$")

#: Il gemello per la VIRGOLA. «1,234» e' milleduecentotrentaquattro in inglese e
#: uno-virgola-duecentotrentaquattro in italiano: le due letture differiscono di
#: mille volte, esattamente come per `_PUNTO_AMBIGUO`. Tre cifre esatte, perche'
#: con una o due (`176,6`) il separatore di migliaia e' escluso e il numero e' un
#: decimale che `_QUANT_RE` ora cattura e confronta.
_VIRGOLA_AMBIGUA = re.compile(r"(?!0,)\d{1,3},\d{3}$")


#: I gruppi di migliaia che `_QUANT_RE` NON VEDE AFFATTO, e che quindi non
#: potevano nemmeno essere dichiarati.
#:
#: `_QUANT_RE` porta un lookahead `(?!\.\d)` che vieta un punto seguito da cifra
#: DOPO il numero. Su «122.057.313» prova «122.057», vede «.313» che segue, e
#: RIFIUTA — senza riprovare piu' avanti. Risultato misurato::
#:
#:     «45.000 euro»        regex ['45.000']   -> ambiguo DICHIARATO
#:     «122.057.313 byte»   regex []           -> nessun valore E NESSUN AVVISO
#:     «1.250.000 euro»     regex []           -> nessun valore E NESSUN AVVISO
#:
#: ⚠️ Il secondo caso e' PEGGIORE del primo, non piu' raro e basta: sul primo il
#: prodotto dice «questo numero non l'ho verificato», sul secondo TACE — e il
#: fatto entra come se non ci fosse niente da verificare. Un numero grande scritto
#: all'europea (i byte, i fatturati, le popolazioni) e' esattamente il caso in cui
#: nessuno se ne accorge.
#:
#: Percio' questa regex e' INDIPENDENTE dall'estrattore: cerca nel testo cio' che
#: l'estrattore rifiuta. Uno o piu' gruppi di ESATTAMENTE tre cifre, parte intera
#: non «0» (perche' «zero mila duecentocinquanta» non esiste in nessuna
#: convenzione) e coda che ammette il punto di fine frase — senza quest'ultimo
#: dettaglio «contro 1.150.000.» in fondo a una frase restava invisibile.
#:
#: Misurata su entrambe le popolazioni prima di scriverla: prende 122.057.313,
#: 1.250.000, 45.000, 250.000, 1.500, 12.345.678; ignora 12.34, 3.1416, 99.9,
#: 0.250, 0.125, 2607.26760.
_MIGLIAIA_MULTIPLE = re.compile(r"(?<![\d.])(?!0\.)\d{1,3}(?:\.\d{3})+(?!\d)")

#: Il gemello con la VIRGOLA, per la convenzione inglese: «1,234 facts»,
#: «1,250,000». Stessa forma e stessa ragione di `_MIGLIAIA_MULTIPLE` — sono
#: numeri che `_QUANT_RE` non vede affatto, quindi senza questa riga non
#: ricevono nemmeno l'avviso e il fatto entra come se non ci fosse niente da
#: verificare. Misurato: `numeri_ambigui("The store holds 1,234 facts.")`
#: restituiva `[]`.
#: ⚠️ NON copre «176,6»: la parte decimale ha 1-2 cifre e `_QUANT_RE` la cattura
#: e la confronta (vedi la nota sul pattern). Qui entrano SOLO i gruppi da tre.
_MIGLIAIA_VIRGOLA = re.compile(r"(?<![\d,])(?!0,)\d{1,3}(?:,\d{3})+(?!\d)")


def numeri_ambigui(text: str) -> list[str]:
    """I numeri del claim che NON abbiamo potuto misurare, come sono scritti.

    ⚠️ ESISTE PERCHE' LA META' DELLA CURA NON BASTA, e la seconda meta' l'ha
    imposta da una verifica indipendente che ha smentito la prima proposta:
    *«togliere l'accusa non distingue
    le due popolazioni: i falsi negativi nascono convertendo i veri positivi in
    silenzio»*. Misurato subito dopo aver scritto `_PUNTO_AMBIGUO`::

        prima  «45.000 euro» contro «45 euro»  -> AMMESSO (confronto falso)
        dopo   «45.000 euro» contro «45 euro»  -> AMMESSO (nessun confronto)

    Per chi legge il fatto le due cose sono identiche: entra comunque. Smettere
    di affermare un valore falso e' necessario e NON e' sufficiente — senza
    questa funzione la cura sposta il difetto invece di chiuderlo.

    La regola, dal MEMORY.md di casa: *«un avviso non ha bisogno della
    popolazione opposta, un veto si»*. Quindi il fatto entra, ma **smette di
    mentire sul proprio stato**: chi lo legge sa che quel numero non e' stato
    verificato contro la fonte, e perche'.
    """
    span = claim_span(text)
    fuori: list[str] = []
    # ① quelli che l'estrattore VEDE e che il gate ha smesso di valutare.
    # ⚠️ `_VIRGOLA_AMBIGUA` qui dentro OGGI NON SCATTA MAI, e lo scrivo invece di
    # lasciarlo credere: i numeri che matcha (`1,234`) non sono catturati da
    # `_QUANT_RE`, quindi non arrivano a questo giro — ci arrivano dal ② qui
    # sotto. Misurato: `_QUANT_RE.search("1,234")` -> False,
    # `_VIRGOLA_AMBIGUA.match("1,234")` -> True. Resta come guardia simmetrica a
    # `_PUNTO_AMBIGUO` per il giorno in cui il pattern cambiasse; non e' una
    # copertura su cui contare oggi.
    for m in _QUANT_RE.finditer(span):
        num_s = m.group(1)
        if (_PUNTO_AMBIGUO.match(num_s) or _VIRGOLA_AMBIGUA.match(num_s))                 and num_s not in fuori:
            fuori.append(num_s)
    # ② quelli che l'estrattore NON VEDE AFFATTO — vedi `_MIGLIAIA_MULTIPLE`.
    # Senza questo giro «122.057.313 byte» non riceveva nemmeno l'avviso: il
    # fatto entrava come se non ci fosse niente da verificare.
    for rx in (_MIGLIAIA_MULTIPLE, _MIGLIAIA_VIRGOLA):
        for m in rx.finditer(span):
            if m.group(0) not in fuori:
                fuori.append(m.group(0))
    return fuori


# ---------------------------------------------------------------------------
# LE DATE NON SONO QUANTITA' — e la copertura c'era gia', a meta'.
#
# ⚠️ IL DIFETTO, su due fatti VERI del corpus (8728c271428f «10 agosto» e
# 45c3e17bd43f «31 luglio»): un claim che scrive la data ASSOLUTA contro una
# fonte che scrive «oggi» viene accusato di affermare un valore che la fonte
# non contiene. A/B nella stessa esecuzione, sul claim vero e sulla sua fonte::
#
#     claim «…dalle 16:00 del 10 agosto…»  ->  accusato ('10', 'agosto')
#     claim «…dalle 16:00 di oggi…»        ->  []
#
# 🔑 Il gate puniva ESATTAMENTE la pratica che una memoria persistente esige:
# risolvere le date relative in assolute. «Oggi», dentro un fatto che vivra'
# mesi, e' inutile o falso — e chi lo scriveva bene veniva accusato di inventare.
#
# COSA C'ERA GIA': `YEAR_RE` con `_introdotto_da_una_parola_temporale` scarta
# l'anno NUDO, e il docstring lo dichiarava — «le date hanno un percorso loro».
# Ma dentro una data l'anno non e' nudo, e infatti «10/08/2026» faceva accusare
# anche il 2026. Non mancava un criterio: mancava il RESTO di quello che c'era.
#
# ⚖️ LE FORME NUMERICHE SONO POSIZIONALI e valgono in ogni lingua; solo quelle
# estese hanno bisogno di un vocabolario — la classe che in questa casa cade
# sempre (liste monolingue in un prodotto mondiale), e per questo i mesi
# coprono cinque lingue invece del solo italiano.
_MESI = (
    "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre"
    "|january|february|march|april|june|july|august|september|october|november|december"
    "|janvier|fevrier|février|mars|avril|juin|juillet|aout|août|decembre|décembre"
    "|enero|febrero|abril|mayo|junio|julio|septiembre|octubre|noviembre|diciembre"
    "|januar|februar|marz|märz|juni|juli|oktober|dezember"
)
# ⛔ FUORI DELIBERATAMENTE, e il costo e' dichiarato invece che scoperto dopo:
#   * «may» (EN) e «mai» (FR/DE) sono anche un verbo modale e un avverbio —
#     «10 may be enough» perderebbe il 10. ⇒ «10 May» non e' riconosciuto.
#   * le ABBREVIAZIONI (jan, mar, dec…) sono parole di tre lettere che in altre
#     lingue significano altro. ⇒ «10 Aug» non e' riconosciuto.
# 🔑 Il criterio della scelta: qui un falso positivo CANCELLA un numero vero,
#   un falso negativo lascia le cose come stanno oggi. Fra i due si prende
#   quello che non toglie niente a nessuno — «precision over recall», che e' il
#   contratto dichiarato di questo modulo.
#: I mesi RUSSI, al GENITIVO perché è la forma che compare nelle date: «10
#: августа» si legge «10 di agosto». Il nominativo (август) non serve qui e
#: allargherebbe senza motivo.
_MESI_RU = ("января|февраля|марта|апреля|мая|июня|июля|августа|"
            "сентября|октября|ноября|декабря")

#: 🔑 CINESE E GIAPPONESE NON HANNO BISOGNO DI UNA LISTA. La data si scrive
#: «8月10日» in entrambe, e 月 (mese) e 日 (giorno) sono gli stessi caratteri:
#: il criterio è POSIZIONALE, non lessicale, quindi copre le due lingue con un
#: pattern solo e non invecchia con il vocabolario.
#: ⚠️ Il danno che ripara è il PEGGIORE dei tre misurati: «8月10日» produceva
#: DUE numeri spuri — ('', 8.0) e ('日运行失败', 10.0) — contro l'uno solo delle
#: forme latine, perché senza spazi il secondo si porta dietro il resto della
#: frase come falsa unità.
_DATA_CJK = r"\d{1,2}\s*月\s*\d{1,2}\s*日|\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"

_DATA_RE = re.compile(
    r"\b\d{4}-\d{1,2}-\d{1,2}\b"                       # ISO   2026-08-10
    r"|" + _DATA_CJK +                                  # 8月10日 · 2026年8月10日
    r"|\d{1,2}\s+(?:" + _MESI_RU + r")\b"              # 10 августа
    r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"              # 10/08/2026 · 10-08-26
    # ⚠️ `\s*(?:[°º]\s*)?` E NON `\s*(?:°|º)?\s*`: due `\s*` ADIACENTI separati da
    # un gruppo opzionale fanno backtracking QUADRATICO su una lunga corsa di
    # spazi che poi fallisce, ed e' esattamente il difetto che questa casa aveva
    # gia' curato il 2026-07-18 su `_QUANT_RE` dopo un alert CodeQL (27,9s su 40k
    # spazi). L'ho reintrodotto qui in una regex NUOVA e il presidio che esisteva
    # gia' — `tests/test_redos_uncapped_proposition.py`, che gira su una
    # `proposition` non limitata in lunghezza — l'ha preso. Misurato, vecchia
    # contro nuova nella stessa esecuzione::
    #
    #     spazi     vecchia        nuova
    #      1000       0,331 s     0,0013 s
    #      4000       5,192 s     0,0036 s
    #     16000      87,131 s     0,0102 s      <- quadratica contro lineare
    #
    # 🔑 Mettendo lo spazio DENTRO il gruppo opzionale, quel gruppo non puo' piu'
    # entrare senza consumare `°`: le due ripetizioni non si contendono piu' gli
    # stessi caratteri e il costo torna lineare. Le forme riconosciute non
    # cambiano — verificato su «10 agosto», «1° marzo», «31 luglio», «10 August»,
    # «3 settembre», con esito identico prima e dopo.
    # ⚠️ L'ANNO FA PARTE DELLA DATA, e ometterlo lo lasciava una QUANTITA'.
    # Misurato il 28/08 alla porta, A/B a variabile singola su fonte inglese:
    # «The contract covers 2027 units of product» — claim INVENTATO, la fonte
    # non parla di unita' — entrava AMMESSO a 99.9 con L4.1 muto, mentre lo
    # stesso claim con 2044 era quarantinato e L4.1 parlava. Separazione 2 su 2
    # contro 0 su 3. Causa: questo pattern catturava «March 12» ma NON l'anno,
    # quindi 2027 usciva dalla soppressione e finiva fra i numeri NUDI — lo
    # stesso meccanismo di «Art. 4» -> ('', 4.0), curato poco sopra.
    # 🔑 IN ITALIANO IL DIFETTO NON SI VEDEVA: in «al 12 marzo 2027» l'anno segue
    # il MESE e `_introdotto_da_una_parola_temporale` lo escludeva gia'; in
    # inglese segue «12,» — un numero — e passava. Il difetto era invisibile
    # nella lingua in cui misuriamo di piu'.
    # ⚠️ `\s{1,3}` LIMITATO e non `\s*`: due quantificatori illimitati adiacenti
    # separati da un gruppo opzionale sono esattamente il backtracking quadratico
    # che questo file ha gia' curato qui sopra (87 s su 16k spazi). Una
    # ripetizione limitata non puo' averlo, e tre spazi coprono il testo vero.
    r"|\b\d{1,2}\s*(?:[°º]\s*)?(?:" + _MESI + r")\b(?:,?\s{1,3}\d{4})?"
    r"|\b(?:" + _MESI + r")\s+\d{1,2}\b(?:,?\s{1,3}\d{4})?",
    re.IGNORECASE)


#: Un IDENTIFICATORE: lettere attaccate a un trattino e a delle cifre.
#:
#: IL DIFETTO (misurato il 2026-08-04, referto sulla scala — «duecento record
#: scritti, uno vivo: il corpus ha capienza UNO»). Il codice di un record veniva
#: letto come una QUANTITA' e la parola dopo come la sua unita'::
#:
#:     «Il campione S-001 contiene piombo a 11 mg/l»  ->  ('contiene', 1.0) …
#:     «Il campione S-002 contiene cadmio a 12 mg/l»  ->  ('contiene', 2.0) …
#:     numeric_conflict                              ->  ('contiene', 1.0, 2.0)
#:
#: ⇒ **L'identificatore che DISTINGUE due record diventava la prova che si
#: contraddicono.** Moltiplicato per un registro, lascia un fatto vivo su
#: venticinque.
#:
#: Sul corpus vivo sono 908 fatti su 6109 (15%), e i piu' frequenti non sono
#: codici di laboratorio ma i nomi che usiamo ogni giorno: `glm-5`, `GPT-5`,
#: `gemini-2`, `opus-4`, `round-2`, `top-10`.
#:
#: 📌 PERCHE' ARRIVA OGGI E NON IL 04/08, quando fu scritta e ritirata: quella
#: cura faceva DUE cose insieme — toglieva il codice dall'estrazione **e**
#: aggiungeva un discriminante di soggetto dentro `numeric_conflict`. Cadde
#: intera. Qui entra solo la prima meta', che non tocca la supersessione; il
#: discriminante resta fuori, e con lui resta armato l'xfail
#: `test_due_schede_con_codici_diversi_non_sono_in_conflitto`, che senza di
#: quello non puo' passare. E' la stessa separazione che il 10/08 ha fatto
#: passare le date dove la cura indivisa era caduta: **una cura che cade per
#: essere troppo larga non e' sbagliata, e' indivisa.**
_IDENTIFICATORE_RE = re.compile(r"\b[A-Za-z]{1,6}-\d{1,6}\b")

#: Lo stesso codice, ma con la lettera presa in QUALUNQUE alfabeto: `[^\W\d_]`
#: è «un carattere di parola che non sia cifra né underscore», cioè una lettera
#: Unicode. Vede `С-001` in cirillico, `样品-001`, `試料-001`.
#:
#: ⚠️ LA `С` CIRILLICA È VISIVAMENTE IDENTICA ALLA `C` LATINA. Un umano che
#: rilegge il codice non vede nessuna differenza, la regex sì: è un difetto
#: internazionale che non si trova guardando, solo misurando.
#:
#: 🔑 PERCHÉ QUESTA VERSIONE VIVE SOLO NELL'ESTRAZIONE E NON NEL CONFRONTO.
#: In cinese e giapponese non ci sono spazi, quindi `{1,6}` si porta dentro
#: anche le parole prima del codice — misurato::
#:
#:     «这个样品-001含有11毫克»  ->  这个样品-001    (voluto: 样品-001)
#:     «この試料-001には11ミリグラム» ->  この試料-001   (voluto: 試料-001)
#:
#: Per TOGLIERE il codice dal testo questo è innocuo: si cancella qualche
#: carattere in più, e quei caratteri non erano una quantità. Ma per DECIDERE
#: se due record sono diversi sarebbe un difetto nuovo: «这个样品-001» e
#: «那个样品-001» — *questo* e *quel* campione, **lo stesso record** —
#: risulterebbero codici diversi, quindi disgiunti, quindi il conflitto vero
#: verrebbe perso. Oggi quel caso funziona proprio perché i codici CJK non
#: vengono visti affatto: allargare la vista lì **peggiorerebbe**.
#: ⇒ `_identificatori_disgiunti` resta sul pattern latino, e il limite è
#:   dichiarato nel banco `test_un_codice_non_e_una_quantita_in_nessuna_lingua`.
_IDENTIFICATORE_UNICODE_RE = re.compile(r"(?<![\w-])[^\W\d_]{1,6}-\d{1,6}(?!\d)")


def _identificatori_disgiunti(text_a: str, text_b: str) -> bool:
    """Entrambi i testi portano un codice di record, e non ne condividono nemmeno uno?

    E' IL DISCRIMINANTE DI SOGGETTO CHE MANCAVA, ed e' la seconda meta' della cura
    degli identificatori: la prima (``_senza_identificatori``, commit 232c3486)
    ha tolto il falso segnale — il codice letto come quantita' — ma sotto restava
    quello vero. Misurato dopo la prima meta'::

        numeric_conflict("Il campione S-001 contiene piombo a 11 mg/l",
                         "Il campione S-002 contiene cadmio a 12 mg/l")
            ->  ('milligrammo', 11.0, 12.0)

    ⇒ Due schede distinte continuavano a risultare «stessa unita', valori
    diversi», cioe' una contraddizione. Sono due campioni, e **il codice lo dice**.

    ⚠️ SERVONO SU ENTRAMBI I LATI. Se uno solo dei due testi porta un codice non
    si sa nulla: «il campione S-001 contiene 11» e «il campione contiene 25»
    possono benissimo parlare della stessa cosa, e li' il conflitto va visto.

    ⚠️ E DEVONO ESSERE DISGIUNTI. Stesso codice con due valori e' esattamente la
    contraddizione che questo modulo esiste per trovare: «S-001 contiene 11» e
    «S-001 contiene 25» restano in conflitto.

    📌 PERCHE' NON E' IL «VETO ENTITA'» GIA' CADUTO: quello leggeva le entita'
    estratte — solo il 43,5% dei fatti ne ha, e le piu' condivise erano una
    negazione, una sigla tecnica e un nome proprio ricorrente, cioe' rumore.
    Qui il segnale e' un pattern sintattico
    stretto (lettere-trattino-cifre), presente nel 15% del corpus, con una
    semantica sola: e' un codice di record.
    """
    ia = {m.group(0).lower() for m in _IDENTIFICATORE_RE.finditer(text_a or "")}
    if not ia:
        return False
    ib = {m.group(0).lower() for m in _IDENTIFICATORE_RE.finditer(text_b or "")}
    if not ib:
        return False
    return not (ia & ib)


def _senza_identificatori(testo: str) -> str:
    """Il testo con i codici di record sostituiti da SPAZI.

    Spazi e non stringa vuota: le posizioni restano quelle originali, cosi' chi
    ragiona per offset non si sposta — e qui sotto ci ragiona
    `_spans_delle_date`, che senza questa accortezza salterebbe di qualche
    carattere per ogni codice incontrato.
    """
    return _IDENTIFICATORE_UNICODE_RE.sub(
        lambda m: " " * (m.end() - m.start()), testo or "")


#: Un numero che **nomina** una parte del documento non è una grandezza
#: misurata: «Art. 3», «comma 2», «Section 5». È la stessa famiglia degli anni
#: nudi (``YEAR_RE`` qui sopra), e non è teorica — misurato il 28/08 sulla porta
#: SDK, A/B a variabile singola su un contratto con Art. 3..8::
#:
#:     claim «Il numero di rate previste dal contratto e' N»
#:           (la fonte NON parla di rate: e' inventato in tutti i casi)
#:     N = 3, 6, 8    -> AMMESSO 100.0 / 100.0 / 96.2   L4.1 muto  0 su 3
#:     N = 91, 97, 43 -> quarantinato 0.2 ovunque       L4.1 parla 3 su 3
#:
#: ⇒ la numerazione **inocula sé stessa** come valore valido della fonte, e
#: ogni documento a sezioni numerate — contratti, leggi, regolamenti, protocolli
#: — immunizza i propri numeri. L'intervallo coperto (2..8) è per giunta quello
#: più usato nei claim ordinari: «3 rate», «6 mesi», «5 giorni».
#: ⚠️ La potatura vale **solo sul numero nudo**: «comma 2 prevede 5 giorni»
#: perde il 2 e tiene i 5 giorni. Un riferimento non porta mai un'unità, e
#: sopprimere una quantità misurata sarebbe un buco più grande di quello curato.
_RIFERIMENTO_RE = re.compile(
    r"(?:\b(?:art|artt|articolo|articoli|comma|commi|sez|sezione|sezioni|capo|"
    r"titolo|punto|lettera|allegato|allegati|all|tab|tabella|fig|figura|"
    r"pag|pagina|riga|righe|nota|"
    r"section|sec|clause|paragraph|para|annex|exhibit|schedule|item|chapter|"
    r"chap|appendix|table|figure|page|line|note|no|nr)\b\.?|§)"
    r"\s*(\d+)\b",
    re.IGNORECASE,
)


def _spans_dei_riferimenti(testo: str) -> list[tuple[int, int]]:
    """Gli intervalli occupati dal NUMERO di un riferimento a una sezione.

    Gemella di `_spans_delle_date`, e per la stessa ragione: si ragiona sugli
    span invece che sul singolo numero, così «art. 3, comma 2» perde entrambi e
    non uno solo. Si restituisce lo span del **numero** (gruppo 1), non della
    parola chiave, perché è il numero che va saltato.
    """
    return [(m.start(1), m.end(1)) for m in _RIFERIMENTO_RE.finditer(testo)]


def _spans_delle_date(testo: str) -> list[tuple[int, int]]:
    """Gli intervalli occupati da una data, per saltarli IN BLOCCO.

    Si ragiona sugli SPAN e non sul singolo numero perche' una data ne contiene
    piu' d'uno: «2026-08-10» produce 08 e 10, «10/08/2026» anche il 2026. Un
    controllo per-numero ne prenderebbe uno e lascerebbe gli altri — che e'
    esattamente il modo in cui la copertura degli anni era rimasta a meta', e
    ripeterlo qui sarebbe rifare lo stesso errore con la sua diagnosi in mano.
    """
    return [(m.start(), m.end()) for m in _DATA_RE.finditer(testo)]


def extract_quantities(text: str, *,
                       come_fonte: bool = False) -> set[tuple[str, float]]:
    """Extract ``(unit_norm, value)`` pairs from the CLAIM part of *text*
    (provenance after an evidence marker is not measured); bare YEARS excluded.

    ``come_fonte=True`` legge il testo INTERO, saltando le TRE potature. Sono
    giuste su un claim e sbagliate su una fonte, e il difetto misurato il 16/08
    e' esattamente questo — un numero PRESENTE nella fonte non veniva visto, il
    claim che lo citava sembrava inventarselo e L4.1 quarantinava un fatto vero
    contro un giudice a 99,98::

        claim_span             la fonte finisce con «… Source: `file.json`» e
                               tutto cio' che segue non veniva letto: nella
                               fonte quello non e' una citazione, e' contenuto
        _senza_identificatori  `cli.py-354-` e' il formato di `git grep -C`,
                               non un codice prodotto: `cli.py:100:` dava 100,
                               `cli.py-354-` dava nulla
        _spans_dei_riferimenti «art. 15» in un CLAIM e' un puntatore a una
                               norma, non un valore da confrontare (28/08,
                               `29ab5544`). In una FONTE quel 15 e' contenuto:
                               nata SOTTO il bivio, acciecava 3 casi su 8 anche
                               qui — misurato e curato il 30/08

    ⚠️ CHI AGGIUNGE LA QUARTA LA METTA SOPRA QUESTA RIGA, o la scriva qui: il
    numero in questa frase e' l'unica cosa che dice al prossimo quante sono, e
    una potatura dimenticata non rende rossa nessuna riga.

    ⚠️ Il default NON cambia: le sei superfici che leggono questa funzione
    continuano a vedere la parte-claim, ed e' cio' che vogliono. Solo chi SA di
    avere una fonte fra le mani chiede l'altra lettura.
    """
    out: set[tuple[str, float]] = set()
    # I codici di record spariscono PRIMA di cercare i numeri, e spariscono
    # sostituiti da spazi: gli offset restano validi per `_spans_delle_date`.
    claim = text if come_fonte else _senza_identificatori(claim_span(text))
    # Gli span UNA VOLTA per testo e non per numero: il costo e' lineare sul
    # testo invece che sul prodotto testo x numeri.
    _date = _spans_delle_date(claim)
    _riferimenti = _spans_dei_riferimenti(claim)
    for m in _QUANT_RE.finditer(claim):
        num_s, unit_s = m.group(1), (m.group(2) or "")
        if any(a <= m.start(1) < b for a, b in _date):
            continue  # il numero fa parte di una DATA — vedi `_DATA_RE`
        if unit_s and _e_una_forma_elisa(claim, m.end(2)):
            unit_s = ""   # «120 l'anno» non contiene litri
        # ⚠️ SI CONFRONTA LA FORMA NORMALIZZATA, NON QUELLA SCRITTA — la cura e'
        # una riga, e nasce da una misura del difetto sul corpus reale
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
        _u = _senza_diacritici(unit_s.lower())
        if _u in _NON_UNIT_WORDS or (len(_u) > 3
                                     and _u not in _FREQUENCY_UNITS
                                     and _u.endswith(_ADVERB_SUFFIXES)):
            unit_s = ""  # a following function word / adverb is not a unit
        if (not unit_s and YEAR_RE.fullmatch(num_s)
                and _introdotto_da_una_parola_temporale(claim, m.start(1))):
            continue  # bare year → year path, not a quantity
        if not unit_s and any(a <= m.start(1) < b for a, b in _riferimenti):
            continue  # «Art. 3» NOMINA una parte del documento, non misura
        if _PUNTO_AMBIGUO.match(num_s) or _VIRGOLA_AMBIGUA.match(num_s):
            continue  # vedi _PUNTO_AMBIGUO: meglio nessun valore che quello falso
        try:
            # LA VIRGOLA DECIMALE DIVENTA UN VALORE, NON NESSUN VALORE. Senza
            # questa riga il pattern nuovo cattura «176,6» ma `float` solleva
            # ValueError e il numero finisce nel `continue` qui sotto: il claim
            # smetterebbe di essere accusato, e passerebbe per NON ESSERE STATO
            # CONFRONTATO. E' il difetto che il docstring di `numeri_ambigui`
            # denuncia con parole sue — «i falsi negativi nascono convertendo i
            # veri positivi in silenzio» — e sarebbe stato spostare il difetto,
            # non chiuderlo.
            # ⚖️ Qui arrivano solo le forme con 1-2 cifre: quelle con TRE sono
            # gia' uscite come ambigue alla riga sopra, quindi questo `replace`
            # non puo' leggere un separatore di MIGLIAIA inglese come decimale.
            val = float(num_s.replace(",", "."))
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
def _classe_dei_segni() -> str:
    """I combining mark, CHIESTI A UNICODE invece che elencati a mano.

    Serve perche' `\\w` — e quindi `[^\\W\\d_]` — comprende lettere e cifre ma
    **non i mark**, e nelle scritture abugida i mark SONO le vocali. Elencarli
    a mano sarebbe la classe di errore piu' ricorrente di questa casa (liste
    monolingue in un prodotto mondiale) e invecchierebbe a ogni versione di
    Unicode; derivarli da `unicodedata` costa **30 ms una volta sola** all'import
    e si aggiorna da solo con Python.

    Il limite superiore e' il blocco oltre il quale non esistono mark (U+1E94A
    e' l'ultimo in Unicode 15): scandire l'intero spazio dei codepoint costerebbe
    dieci volte tanto senza trovare nulla di piu'.
    """
    trovati = [c for c in range(0x0300, 0x1E950)
               if unicodedata.category(chr(c))[0] == "M"]
    gruppi: list[tuple[int, int]] = []
    inizio = prec = None
    for c in trovati:
        if inizio is None:
            inizio = prec = c
        elif c == prec + 1:
            prec = c
        else:
            gruppi.append((inizio, prec))
            inizio = prec = c
    if inizio is not None:
        gruppi.append((inizio, prec))
    return "".join(chr(a) if a == b else f"{chr(a)}-{chr(b)}" for a, b in gruppi)


#: ⚠️ LA SOGLIA RESTA QUATTRO CARATTERI — non e' stata toccata, ed e' il vincolo
#: scritto qui sopra. Cambia solo CHE COSA CONTA come carattere di una parola:
#: prima solo le lettere, ora anche i segni che le accompagnano.
#:
#: 🔑 IL DIFETTO CHE CURA, misurato: in devanagari le vocali sono **mark**, non
#: lettere, e `[^\W\d_]{4,}` si spezzava su ognuna::
#:
#:     वेरोना (Verona)  ->  pezzi ['व', 'र', 'न'], lunghezze [1, 1, 1]
#:     व  Lo  \w=True    े  Mn  \w=False   (DEVANAGARI VOWEL SIGN E)
#:     र  Lo  \w=True    ो  Mc  \w=False   (DEVANAGARI VOWEL SIGN O)
#:
#: Nessun pezzo raggiungeva quattro ⇒ `content_tokens` restituiva **zero token**
#: su ogni frase hindi, bengali o tamil, e con zero token ogni guardia di
#: stesso-soggetto e' cieca. Riguarda oltre un miliardo di parlanti.
#:
#: ⚖️ E LA SOGLIA NON E' NEUTRA FRA LE SCRITTURE, che e' la ragione per cui il
#: primo tentativo di cura non bastava: raggruppando `(?:lettera segni*){4,}` si
#: contano le SILLABE, e «वेरोना» ne ha tre. Quattro sillabe in devanagari sono
#: una parola lunghissima. Contando i caratteri — il primo obbligatoriamente una
#: lettera — la soglia torna a significare la stessa cosa ovunque.
_PAROLA_RE = re.compile(
    r"[^\W\d_](?:[^\W\d_]|[" + _classe_dei_segni() + r"]){3,}", re.UNICODE)


def _senza_diacritici(text: str) -> str:
    """«città» -> «citta»: la stessa parola, una grafia sola.

    ⚠️ NON ABBASSA — il chiamante passa il testo gia' in minuscolo. Sembra un
    dettaglio e il 2026-08-07 e' costato una regressione: avevo scritto una
    SECONDA `_senza_diacritici` in cima al modulo, che abbassava, e Python
    tiene l'ULTIMA definizione. Le mie due chiamate ne usavano una che non
    conoscevo: «0.709 e alto» era filtrato e «0.709 E alto» no. Isolata in revisione
    a una riga. ⇒ La cura non e' stata scegliere quale tenere: e' stato
    CANCELLARE il duplicato. Due funzioni con lo stesso nome sono la classe ①
    di questa casa — una copia invece della superficie unica — e la domanda che
    mi mancava e' la piu' semplice: *esiste gia'?* Un `grep` prima di scrivere.

    ⚠️ E IL LIMITE, che vale per entrambe le chiamate: le TRASLITTERAZIONI non
    sono accenti caduti. Chi non ha l'umlaut scrive «Stueck», non «Stuck», e
    nei gestionali tedeschi quella e' la forma corrente. Qui «Stück» e «Stuck»
    si uniscono, «Stueck» resta a parte: unirla richiederebbe la regola inversa
    `ue -> u`, che romperebbe ogni parola in cui `ue` sta per se stesso. Provata
    la traslitterazione inversa come forma canonica: sposta solo il problema.

    ⚠️⚠️ E SI RICOMPONE IN NFC, che non e' cosmesi: senza, questa funzione
    RESTITUIVA UNA PAROLA CHE NON ESISTE PIU' NEL TESTO da cui viene. Le
    scritture che si decompongono in segni NON combinanti — l'hangul coreano su
    tutte — uscivano in jamo separati e non tornavano mai insieme::

        _senza_diacritici("베로나")  ->  "베로나"      identico a vedersi
        len(originale) = 3            len(risultato) = 6
        0xbca0 0xb85c 0xb098    ->    0x1107 0x1166 0x1105 0x1169 0x1102 0x1161
        "베로나" in testo_originale   ->   False

    🔑 È LA TRAPPOLA PERFETTA: le due stringhe si STAMPANO uguali. Nessuna
    rilettura del codice e nessuna ispezione a occhio dell'output puo' trovarla
    — servono `len()` o i codepoint. Misurato alla porta: `_content_overlap` di
    una frase coreana con SE STESSA valeva **0.00**, quindi in coreano ogni
    guardia di stesso-soggetto era cieca e il gate non poteva confermare nulla.

    📌 NFC dopo NFKD non annulla la parte di COMPATIBILITA' (① resta 1, ４８０
    resta 480): ricompone solo cio' che era stato spezzato senza motivo.
    """
    return unicodedata.normalize(
        "NFC",
        "".join(c for c in unicodedata.normalize("NFKD", text)
                if not unicodedata.combining(c)))


#: Han (cinese e kanji giapponesi), hiragana, katakana ed estensioni.
#: ⚠️ NON ESTENDERE QUESTA: la usa anche ``_e_prevalentemente_cjk``, che decide
#: una cosa DIVERSA — se il testo sia privo di spazi fra le parole. Il coreano
#: gli spazi ce li ha, quindi allargarla cambierebbe quel verdetto senza che
#: nessuno l'abbia chiesto. Per i bigrammi c'è ``_SENZA_PAROLE_RE`` sotto.
_CJK_RE = re.compile(r"[぀-ヿㇰ-ㇿ㐀-䶿一-鿿豈-﫿]{2,}")


#: Le scritture in cui la PAROLA non è l'unità utile del confronto — 15/08.
#: Ai CJK si aggiungono **hangul** e **thai**, per due ragioni diverse:
#:   · il thai non separa le parole con spazi, esattamente come il cinese;
#:   · il coreano gli spazi ce li ha, ma le sue parole sono agglutinate e una
#:     negazione ne cambia una INTERA («있습니다» → «없습니다»), quindi due frasi
#:     sullo stesso soggetto condividevano UN solo token e la guardia dello
#:     stesso-soggetto non poteva scattare.
#: Misurato PRIMA di scrivere, token condivisi fra una frase e la sua negata::
#:     KO  1 → 8        TH  0 → 14        KO (magazzino)  2 → 13
#: e sulla popolazione opposta, frasi di soggetto DIVERSO, 0 → 1 e 0 → 0: il
#: criterio non diventa generoso, che è il rischio vero di un n-gramma.
#: ⚠️ Controprova: italiano, inglese, russo, cinese e giapponese danno token
#: IDENTICI a prima — la riga sotto non tocca chi già funzionava.
_SENZA_PAROLE_RE = re.compile(
    r"[぀-ヿㇰ-ㇿ㐀-䶿一-鿿豈-﫿"
    r"가-힯ᄀ-ᇿ"       # hangul: sillabe precomposte e jamo
    r"฀-๿]{2,}")       # thai


def _bigrammi_cjk(text: str) -> set[str]:
    """I bigrammi di caratteri delle scritture senza parole separate.

    🔑 LA DOMANDA CHE HA PORTATO QUI non era «come tokenizziamo il cinese», ma
    **«esiste un criterio di stesso-soggetto che non passi dalle parole?»** — e
    la risposta è sì: in cinese e giapponese la coppia di caratteri adiacenti è
    l'unità di significato più piccola stabile, ed è la base standard del
    retrieval per queste lingue proprio perché **non richiede un dizionario**.
    Un segmentatore sarebbe stato un componente in più da mantenere, e in questa
    casa i vocabolari sono la classe di difetti che torna sempre.

    IL DIFETTO CHE CHIUDE, misurato il 12/08 prima della cura::

        content_tokens("样品-001含有11毫克。")   ->  set()      (zero token)
        content_tokens("维罗纳仓库有480个托盘。")  ->  {'维罗纳仓库有'}  (mezza frase)

    ⇒ La guardia dello stesso-soggetto chiede almeno una parola distintiva in
    comune. Con zero token non è mai soddisfatta: **due schede cinesi diverse
    davano ``None``, e quel ``None`` significava «non ho potuto guardare»
    travestito da «non c'è contraddizione»**. Le frasi lunghe funzionavano per
    coincidenza — mezza frase incollata che capitava identica nelle due — e
    bastava cambiare una parola all'inizio per perdere il conflitto.

    Con i bigrammi::

        「样品-001含有11毫克」 -> {样品, 含有, 毫克}
        「样品-002含有12毫克」 -> {样品, 含有, 毫克}     ⇒ 3 condivisi, guardia superata

    ⚠️ LA POPOLAZIONE OPPOSTA, verificata PRIMA di scrivere la cura: tre coppie
    di frasi che parlano di cose diverse (magazzino/servizio, pallet/minuti,
    magazzino/cache in giapponese) condividono **zero** bigrammi. Il criterio
    separa, non incolla — che è il rischio vero di un n-gramma: essere così
    generoso da rendere tutto simile a tutto.

    📌 Le altre lingue non sono toccate: senza caratteri CJK questa funzione
    restituisce l'insieme vuoto e ``content_tokens`` resta identica a prima.
    """
    out: set[str] = set()
    for run in _SENZA_PAROLE_RE.findall(text or ""):
        for i in range(len(run) - 1):
            out.add(run[i:i + 2])
    return out


def content_tokens(text: str) -> set[str]:
    """Lower-cased alpha tokens ≥4 chars minus fillers, lightly singularised.

    Used as the topical-overlap precision guard: two statements must share
    a *distinctive* (non-unit) content word before a same-unit/different-
    value pair counts as a contradiction.

    Gli accenti sono normalizzati e gli alfabeti non latini contano come
    lettere — vedi il blocco su ``_PAROLA_RE`` per la misura che lo giustifica.

    ⚠️ E IN CINESE E GIAPPONESE NON CI SONO PAROLE — vedi ``_bigrammi_cjk``.
    Fino al 12/08 questa funzione restituiva **zero token** su una frase cinese
    breve e **mezza frase come token unico** su una lunga, quindi la guardia non
    poteva mai essere soddisfatta e ogni conflitto usciva ``None``: non
    «nessuna contraddizione», ma «non ho potuto guardare», scritto nello stesso
    modo.
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
    out |= _bigrammi_cjk(text)
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
      • no DIFFERENT record identifiers (``S-001`` vs ``S-002``);
      • same normalised unit, different value.
    """
    if _identificatori_disgiunti(text_a, text_b):
        return None
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
#   e il portoghese va elencato a parte. E' la lezione appresa su «ora».
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
    sulla punteggiatura. Misurato in indipendenza (5120 conflitti su
    21151, 24,2%) e su un secondo campione (147 coppie vere, 26,5%) — due stime che convergono.

    IL CRITERIO e' raro perche' migliora ENTRAMBE le popolazioni
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
        farebbe entrare versioni e date come soggetti (controipotesi sollevata in revisione).
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
    r"|(?:\bلا\b|\bلم\b|\bلن\b|\bليس\b)"
    # RUSSO — mancava, ed è nel perimetro delle sette lingue chiesto il 12/08.
    # «не» è la negazione ordinaria, «нет» quella esistenziale, «ни» quella
    # coordinata: tutte parole intere, delimitate da spazi come in inglese.
    r"|\b(?:не|нет|ни)\b"
    # COREANO · TURCO · HINDI · THAI — 15/08. Senza questi il gate rispondeva
    # `supported` a una frase NEGATA: un fatto e la sua smentita ricevevano lo
    # stesso verdetto positivo, che è peggio del restare muto.
    #
    # ⚠️⚠️ QUI SI ENTRA SOLO PASSANDO DALLA POPOLAZIONE OPPOSTA, e la lista è
    # più corta di quella «ovvia» perché CINQUE CANDIDATI SU DIECI sono stati
    # scartati misurandoli su frasi affermative::
    #
    #     안  →  scatta su 안녕하세요 «ciao», 안전 «sicuro», 안내 «guida»   3/3
    #     못  →  scatta su 못 «chiodo»                                    1
    #     ना  →  scatta dentro नाव «barca»                                2
    #     मत  →  scatta dentro मतदान «voto»                               1
    #     -me →  scatta dentro değiştirmek «cambiare»                     1
    #
    # Sono negatori VERI — «안 하다» nega, «मत» è un imperativo negativo — ma
    # lessicalmente indistinguibili da parole comuni: coprirli farebbe
    # RESPINGERE FATTI VERI, e un rifiuto somiglia sempre alla prudenza, quindi
    # nessuno se ne accorgerebbe. ⇒ Restano fuori, e questa nota è il debito.
    #
    # Ciò che entra è misurato pulito (zero falsi positivi sul banco):
    #   coreano  «없» esistenziale (없다/없습니다/없어요) — morfema, niente spazi
    #   turco    parole intere, il turco ha gli spazi
    #   hindi    «नहीं» parola intera; il devanagari usa gli spazi
    #   thai     «ไม่» — il thai non separa le parole, come il cinese; il tono
    #            lo distingue da «ไม้» (legno), che è un codepoint diverso
    r"|(?:없)"
    r"|\b(?:yok|değil|değildir)\b"
    r"|(?:नहीं)"
    r"|(?:ไม่)",
    re.IGNORECASE,
)


def _has_negator(text: str) -> bool:
    return bool(_NEGATOR_RE.search(text or ""))


def _negated_tokens(text: str) -> set[str]:
    """Content words in the negator's SCOPE: the first 1-2 alpha tokens right
    after each negator, singularised like :func:`content_tokens`.

    ⚠️ IL NEGATORE ERA MULTILINGUE E IL SUO OGGETTO NO — misurato il 12/08.
    `_NEGATOR_RE` copriva già giapponese, cinese e arabo dal 04/08, ma qui la
    coda si cercava con ``[a-zA-Z]{4,}``: **la negazione veniva riconosciuta e
    ciò che negava no**, quindi nessun token entrava nello scope e il polarity
    flip non scattava mai::

        RU «Сервис не доступен.»  negatore visto (dopo la cura) · coda [] → nessun conflitto

    ⇒ Un difetto in **due pezzi**: metà curata da un'altra istanza il 04/08 (i
    negatori giapponesi, cinesi e arabi), metà rimasta qui. **Riconoscere una
    negazione non serve a niente se poi non si guarda che cosa nega.**

    📌 LIMITE DICHIARATO, E MISURATO DOPO LA CURA — **cinese e giapponese
    restano scoperti**, e non per dimenticanza. Lo scope adesso li estrae
    («不可用» → «可用»), ma il polarity flip confronta quel token con quelli
    della frase affermativa, e lì non c'è nessun «可用»: c'è il blocco
    «服务可用», perché senza spazi `content_tokens` non ritaglia parole.
    In giapponese si aggiunge che la negazione è un **suffisso**
    («利用できます» → «利用できません»), quindi l'oggetto sta pure dalla parte
    sbagliata.
    ⇒ Non è una regex che manca: **è la segmentazione**, la stessa che rende
      `content_tokens` cieco in quelle due lingue. Curare qui senza risolvere
      là sposterebbe il difetto invece di chiuderlo.
    """
    t = text or ""
    out: set[str] = set()
    for m in _NEGATOR_RE.finditer(t):
        # `[^\W\d_]{4,}` = una parola in QUALUNQUE alfabeto (cirillico compreso);
        # `[一-鿿]{2,4}` = i caratteri cinesi subito dopo il negatore, che non
        # hanno spazi e sono corti — «不可用» nega «可用», due caratteri.
        following = re.findall(r"[^\W\d_]{4,}|[一-鿿]{2,4}", t[m.end():])[:2]
        for w in following:
            # ⚠️ I DIACRITICI SI TOLGONO QUI PERCHE' `content_tokens` LI TOGLIE.
            # Questo insieme viene confrontato con i token dell'altra frase, e
            # se i due lati normalizzano in modo diverso il confronto fallisce
            # su una lettera. Misurato — «Der Dienst ist NICHT verfügbar»
            # contro «Der Dienst ist verfügbar»::
            #
            #     content_tokens(A)  ->  {'dienst', 'verfugbar'}
            #     scope di «nicht»   ->  {'verfügbar'}      ⇐ con la ü
            #     'verfügbar' in token(A)  ->  False
            #     Jaccard 2/2 = 1.00       ⇐ la guardia passava!
            #
            # Tutto il resto funzionava: negatore riconosciuto, scope giusto,
            # stesso soggetto. Mancava una sola normalizzazione su un lato, e
            # il gate rispondeva `supported` — «claim coerente con la memoria»
            # su una frase che dice l'esatto contrario.
            #
            # 📌 PERCHE' NON ERA STATO VISTO: italiano, spagnolo e polacco
            # cadono nello stesso buco ma ne escono per caso — lo scope prende
            # DUE parole e ne basta una senza diacritici («activo», «riuscita»,
            # «jest») perche' il conflitto si produca lo stesso. Il difetto si
            # vede solo quando e' la parola NEGATA a portare il segno.
            w = _senza_diacritici(w.lower())
            if w.endswith("ies"):
                w = w[:-3] + "y"
            elif w.endswith("s") and len(w) > 3:
                w = w[:-1]
            out.add(w)
    return out or _scope_a_ritroso(t)


#: L'ultimo blocco di kanji prima della coda verbale in kana: in «暗号化されて
#: いません» il contenuto è `暗号化`, non `されてい`.
_KANJI_PRIMA_DELLA_CODA = re.compile(r"([一-鿿㐀-䶿]{2,4})[ぁ-ゟー]*$")


def _scope_a_ritroso(t: str) -> set[str]:
    """Ciò che il negatore nega quando sta **in coda alla frase**.

    ⚠️⚠️ QUESTA È LA META' DEL MONDO CHE `_negated_tokens` NON GUARDAVA, e la
    sua assenza non faceva perdere un rilevamento: ne faceva **inventare** uno.

    La ricerca in avanti (`t[m.end():]`) descrive le lingue in cui il negatore
    PRECEDE ciò che nega — «not *encrypted*». Nelle lingue SOV il negatore
    CHIUDE: `暗号化されて**いません**`, `sifreli **degil**`, `एन्क्रिप्टेड **नहीं** है`.
    Lì lo scope usciva vuoto, e con lo scope vuoto la guardia di precisione di
    :func:`negation_conflict` **non scatta affatto** — la condizione è
    ``if scoped and not scoped_shared``. Il caso scivolava al fallback e veniva
    dichiarato conflitto. Misurato, con il gemello inglese che rende la cosa
    conclusiva::

        giapponese  「署名されました」 / 「署名されましたが暗号化されていません」
              scope []            → 'され'      ⇐ due frasi COMPATIBILI in conflitto
        inglese     «signed» / «signed but not encrypted»
              scope ['encrypted'] → None        ⇐ corretto

    🔑 Una regola posizionale non è neutra fra tipologie linguistiche, ed è la
    gemella cattiva di «una soglia non è neutra»: un rilevamento inventato
    ritira un fatto vero, mentre uno mancato lascia le cose come stanno.

    ⚠️ IL RIPIEGO SI ATTIVA **SOLO** SE IN AVANTI NON C'È NULLA, e l'asimmetria
    è voluta: cercare all'indietro anche in inglese prenderebbe «is» da «is not
    blocked», cioè uno scope falso in una lingua che oggi funziona.

    ⚠️ E prende POCO. La prima versione riusava `[^\\W\\d_]{4,}`, che in
    giapponese cattura **l'intera frase** — kana e kanji sono tutti `\\w` — e
    con il confronto per caratteri quello scope copriva ogni token condiviso:
    il falso positivo restava, per una ragione nuova. Serve l'ultimo blocco di
    kanji prima della coda verbale.

    Misurato su quattro coppie compatibili e cinque contraddittorie:
    falsi positivi **da 1 a 0**, rilevamenti veri invariati a 5 su 5.
    """
    out: set[str] = set()
    for m in _NEGATOR_RE.finditer(t or ""):
        blocco = _KANJI_PRIMA_DELLA_CODA.search((t or "")[:m.start()])
        if blocco:
            out.add(blocco.group(1))
    return out


def _senza_negatori(text: str) -> str:
    """Il testo senza i negatori, per confrontare le due frasi «a parità di
    resto».

    ⚠️ E IL NEGATORE SI TOGLIE IN DUE MODI DIVERSI, misurato il 12/08. La
    guardia di `negation_conflict` chiede Jaccard ≥ 0.6 fra i token dei due
    lati, ed è tarata su lingue dove il negatore è **una parola fra le altre**:
    togliere «non» da «il servizio non è disponibile» non tocca nessun'altra
    parola. In cinese il negatore sta **dentro** la parola, e cambiarlo riscrive
    il vicinato::

        服务可用     bigrammi  {服务, 务可, 可用}
        服务不可用   bigrammi  {服务, 务不, 不可, 可用}   ⇒ Jaccard 0.29, guardia BLOCCA

    Sostituirlo con uno spazio non basta: spezza `服务不可用` in due sequenze e
    **si perde il bigramma di giunzione** (0.29 → 0.50, ancora sotto soglia).
    Togliendolo senza lasciare spazio la frase torna quella affermativa e i due
    insiemi coincidono — Jaccard 1.00 su tutte e sette le lingue del perimetro,
    con la popolazione opposta (frasi che parlano di cose diverse) ferma a 0.00.

    🔑 La regola generale: **un negatore che sta fra le parole si sostituisce
    con uno spazio, uno che sta dentro la parola si toglie e basta.** Sono due
    lingue diverse dentro la stessa funzione.
    """
    def _via(m: re.Match) -> str:
        s = m.group(0)
        dentro_la_parola = bool(s) and "぀" <= s[0] <= "鿿"
        return "" if dentro_la_parola else " "
    return _NEGATOR_RE.sub(_via, text or "")


def _e_prevalentemente_cjk(text: str) -> bool:
    """Vero se il testo è per lo più han/kana, cioè privo di spazi fra le parole."""
    pieni = [c for c in (text or "") if not c.isspace()]
    if len(pieni) < 4:
        return False
    cjk = sum(1 for c in pieni if _CJK_RE.match(c * 2) or "一" <= c <= "鿿"
              or "぀" <= c <= "ヿ" or "㐀" <= c <= "䶿")
    return cjk >= len(pieni) * 0.5


#: Punteggiatura a piena larghezza: separa, non è contenuto.
_PUNTEGGIATURA_CJK = "，。、；：！？「」『』（）"


def _token_di_confronto(text: str) -> set[str]:
    """I token con cui :func:`negation_conflict` confronta DUE frasi.

    ⚠️ NON è `content_tokens` per le scritture senza spazi, e la differenza è
    tutta nel confronto: `content_tokens` segmenta il CJK in **bigrammi**, e un
    negatore cinese sta DENTRO la frase — toglierlo riscrive i bigrammi che lo
    attraversavano. Due muoiono, uno nasce, e il denominatore del Jaccard cresce
    mentre il numeratore resta fermo::

        系统已签名 / 系统未签名   con i bigrammi   Jaccard 0.286   → nessun flip
                                  coi caratteri    Jaccard 0.800   → flip visto

    Misurato su cinque coppie affermazione/negazione: **1 flip visto su 5** coi
    bigrammi, **5 su 5** coi caratteri, e **zero** falsi positivi su cinque casi
    costruiti apposta perché il negatore scopi una parola che l'altra frase non
    contiene (il caso «complete, not blocked» del contratto qui sotto).

    🔑 PERCHÉ UN AIUTANTE E NON UNA MODIFICA A `content_tokens`: quella funzione
    non appartiene a questo confronto. La usano `corroboration` e
    `facts_conflict` — più una ventina di punti in questo modulo — dove i
    caratteri singoli non sono stati misurati e sarebbero un'altra decisione.
    La misura fatta qui autorizza questo confronto, non tutti.
    """
    if _e_prevalentemente_cjk(text):
        return {c for c in text
                if not c.isspace() and c not in _PUNTEGGIATURA_CJK}
    return content_tokens(text)


def negation_conflict(text_a: str, text_b: str) -> str | None:
    """The shared predicate token when *text_a*/*text_b* state the SAME thing
    with OPPOSITE polarity ("is signed" vs "is not signed"); else ``None``.

    Precision guards: the polarity must differ, the content-token sets must
    be near-identical (Jaccard ≥ 0.6 with ≥2 shared tokens), AND the word in
    the negator's scope must itself be SHARED — "complete, not blocked" does
    not flip "complete" (the negator scopes "blocked", absent from the other
    statement).

    Space-less scripts are compared CHARACTER-wise (:func:`_token_di_confronto`)
    on BOTH sides — the content tokens and the negator's scope. Normalising one
    side only silently disables the third guard: the Jaccard reaches 1.000 while
    ``scope ∩ shared`` is empty, so the flip is dropped and the change looks
    like a regression instead of a half-applied fix."""
    na, nb = _has_negator(text_a), _has_negator(text_b)
    if na == nb:
        return None  # same polarity → no flip
    ca = _token_di_confronto(_senza_negatori(text_a))
    cb = _token_di_confronto(_senza_negatori(text_b))
    shared = ca & cb
    union = ca | cb
    if len(shared) < 2 or not union or (len(shared) / len(union)) < 0.6:
        return None  # different statement, not a flip of this one
    if contrasting_attrs(ca, cb):
        return None
    #: Lo scope si tiene in DUE forme: quella normalizzata decide, quella
    #: originale è ciò che si restituisce — il chiamante mostra questo token a
    #: chi legge, e «成» al posto di «成功» sarebbe una diagnosi illeggibile.
    #: ⚠️ LO SCOPE VA MISURATO NELLE STESSE UNITA' DI ``ca``/``cb``, e il modo
    #: sicuro di ottenerlo è **richiamare la funzione che quelle unità le ha
    #: prodotte**. La versione precedente ne ripeteva la logica a mano — i
    #: caratteri singoli, giusti per cinese e giapponese — e condizionava la
    #: cosa a ``_e_prevalentemente_cjk``. Su una scrittura senza spazi che
    #: quella funzione NON riconosce, il thai, restavano disallineate::
    #:
    #:     scoped   {'ดพลาด'}         una parola intera
    #:     shared   {'ดพ', 'พล', …}   bigrammi
    #:     ⇒ scoped_shared vuoto, e la guardia sotto rispondeva None
    #:
    #: cioè «la negazione colpisce una parola che l'altro lato non dice»
    #: mentre l'altro lato la diceva eccome: la frase e la sua negata avevano
    #: 14 token in comune su 18.
    #: 🔑 Una copia della logica invece della superficie unica: appena le due
    #: si separano, il difetto compare **solo** dove la copia non arriva.
    #: Misurato prima della cura, lo scope ri-tokenizzato è IDENTICO su
    #: inglese, italiano, coreano, giapponese, cinese e sul caso-trappola
    #: «complete, not blocked» — cambia solo dove serviva.
    #: ⚠️⚠️ IL THAI RESTA SCOPERTO QUI, E LA CURA OVVIA È STATA PROVATA E
    #: RITIRATA il 15/08. La diagnosi è certa: su una scrittura senza spazi che
    #: ``_e_prevalentemente_cjk`` non riconosce, ``scoped`` resta una parola
    #: intera mentre ``shared`` contiene bigrammi, e la guardia sotto risponde
    #: «la negazione colpisce una parola che l'altro lato non dice» su due
    #: frasi che condividono 14 token su 18::
    #:
    #:     scoped   {'ดพลาด'}          shared   {'ดพ', 'พล', …}
    #:
    #: Ma **allineare le unità qui rompe tre casi veri**, misurati:
    #:   · ``_token_di_confronto`` sullo scope → il cinese perde il flip, perché
    #:     quella funzione taglia in base alla LUNGHEZZA del testo che riceve e
    #:     uno scope di due caratteri non è «prevalentemente cjk» mentre la
    #:     frase da cui viene lo è;
    #:   · condizionandolo alla frase → cadono «il farmaco riduce la mortalità»
    #:     contro «non riduce» (il caso fondativo di questa superficie),
    #:     e inglese e arabo tornano a rispondere `supported` a una negazione.
    #:
    #: 🔑 La diagnosi era giusta e la cura sbagliata, e la cura sbagliata
    #: sembrava la più pulita delle due: «riusa la superficie unica invece di
    #: ripeterne la logica». Qui la logica ripetuta a mano è corretta proprio
    #: perché il criterio dipende dal testo INTERO, non dal frammento.
    #: ⇒ Il thai chiede una via che non passa da questa riga.
    scoped_orig = _negated_tokens(text_a if na else text_b)
    scoped = ({c for tok in scoped_orig for c in tok}
              if _e_prevalentemente_cjk(text_a if na else text_b) else scoped_orig)
    scoped_shared = scoped & shared
    if scoped and not scoped_shared:
        return None  # the negation targets a word the other side never states
    if not scoped and (cb - ca if nb else ca - cb):
        # ⚠️⚠️ LO SCOPE VUOTO NON E' UN VIA LIBERA — era il buco della guardia.
        # La ricerca dello scope fallisce quando il negatore chiude la frase
        # (lingue SOV) o quando la sua coda non è una parola riconoscibile: in
        # quei casi `scoped` esce vuoto, la riga sopra non entra, e il confronto
        # scivolava al fallback DICHIARANDO UN CONFLITTO. Misurato: «il sistema
        # è firmato» contro «il sistema è firmato, NON cifrato» risultava una
        # contraddizione in turco e in hindi.
        #
        # 🔑 Qui non si cerca più DOVE sta l'oggetto della negazione — quella
        # domanda dipende dalla scrittura, e curarla per il giapponese l'aveva
        # lasciata aperta per le altre tre lingue della stessa classe. Si guarda
        # invece una proprietà che nessun alfabeto cambia: **il lato negato
        # porta contenuto che l'altro non enuncia**. Se c'è, il negatore parla
        # (anche) di quello, e due frasi che non dicono la stessa cosa non
        # possono esserne l'una la smentita.
        #
        # Misurato su sette coppie contraddittorie e sei compatibili, sette
        # lingue: i rilevamenti veri restano **7 su 7** — comprese le due che
        # senza i negatori nuovi non uscivano — e i conflitti inventati passano
        # da **2 a 0**.
        return None
    if scoped_shared:
        #: Basta che il token originale TOCCHI i caratteri condivisi. Pretendere
        #: che ne sia interamente composto degradava il giapponese da «され» a
        #: «さ»: il flip restava visto, ma la diagnosi mostrata diventava una
        #: sillaba — una cura che peggiora ciò che il prodotto DICE.
        leggibili = {t for t in scoped_orig if set(t) & scoped_shared} or scoped_shared
        return sorted(leggibili)[0]
    return _piu_leggibile(shared, text_a, text_b)


def _piu_leggibile(shared: set[str], text_a: str, text_b: str) -> str:
    """Il token da MOSTRARE quando il negatore non ha uno scope proprio.

    ⚠️ Serve perché il confronto a caratteri cambia anche cosa si restituisce.
    Un negatore giapponese come ``ません`` chiude la frase e non lascia una coda,
    quindi `_negated_tokens` torna vuoto e si finisce qui: prima della cura
    ``sorted(shared)[0]`` sceglieva fra bigrammi e dava ``され``, dopo sceglie
    fra caratteri e darebbe ``さ``. Il flip resta visto in entrambi i casi — ma
    la diagnosi che il chiamante mostra a chi legge diventa una sillaba.

    🔑 È lo stesso difetto che questo modulo esiste per prevenire, applicato a
    sé: un cambiamento misurato sul VERDETTO che peggiora ciò che il prodotto
    DICE, e che nessuna delle due popolazioni avrebbe segnalato.
    """
    if _e_prevalentemente_cjk(text_a):
        originali = (content_tokens(_senza_negatori(text_a))
                     & content_tokens(_senza_negatori(text_b)))
        utili = {t for t in originali if len(t) > 1 and set(t) <= shared}
        if utili:
            return sorted(utili)[0]
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


#: Numerali scritti a parole, EN·IT. La partizione NON e' «quali parole sono
#: ambigue» ma «quali costano poco», ed e' una misura sul corpus reale (11.262
#: proposizioni, 16/08): `un` 1481 (13,2%) · `una` 772 (6,9%) · `uno` 193
#: (1,7%) valgono da soli 21,8 punti su 26,5 — oltre l'80% degli scatti — e
#: sono FUORI perche' in italiano sono gli ARTICOLI INDETERMINATIVI, cioe' fra
#: le parole piu' frequenti della lingua. Con dentro anche loro un avviso
#: comparirebbe su 2484 fatti su 11262 (22,1%): un avviso che compare sempre
#: equivale a nessun avviso.
#: ⚠️ Restano DENTRO parole con omonimi veri — `sei` e' anche il verbo essere,
#: `venti` il plurale di vento — e questo e' un LIMITE NOTO, non una svista:
#: costano 1,4 e 0,3 punti, e senza `sei` la cura non curerebbe il caso da cui
#: e' nata. Regge perche' chi la usa lo fa per DECLASSARE un veto ad avviso,
#: mai per ammettere: un omonimo produce un avviso in piu', non un numero.
_NUMERALI_A_PAROLE: dict[str, float] = {
    # -- inglese
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000,
    # -- italiano
    "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6, "sette": 7,
    "otto": 8, "nove": 9, "dieci": 10, "undici": 11, "dodici": 12,
    "tredici": 13, "quattordici": 14, "quindici": 15, "sedici": 16,
    "diciassette": 17, "diciotto": 18, "diciannove": 19, "venti": 20,
    "trenta": 30, "quaranta": 40, "cinquanta": 50, "sessanta": 60,
    "settanta": 70, "ottanta": 80, "novanta": 90, "cento": 100,
    "mille": 1000,
}
#: ⛔ `one` e `a`/`an` in inglese, `un`/`uno`/`una` in italiano: mai qui.

_NUMERALE_RE = re.compile(
    r"\b(" + "|".join(sorted(_NUMERALI_A_PAROLE, key=len, reverse=True)) +
    r")\b", re.IGNORECASE)


def valori_scritti_a_parole(text: str) -> set[float]:
    """I numeri che il testo scrive a PAROLE, non in cifra.

    ⚠️ Volutamente NON usata da `extract_quantities`, e la ragione sta scritta
    in `valore_non_nella_fonte.py:228` per il caso gemello («nessun X» vale
    zero): insegnare al parser a vedere numeri dove il testo non ne misura
    creerebbe quantita' fantasma nei sei moduli del gate che lo leggono. Qui
    l'equivalenza vive solo in un confronto fra due testi: non entra nel corpus
    e non crea nulla.
    """
    if not text:
        return set()
    return {float(_NUMERALI_A_PAROLE[m.group(1).lower()])
            for m in _NUMERALE_RE.finditer(text)}


__all__ = [
    "YEAR_RE",
    "CONTRAST_QUALIFIERS",
    "norm_unit",
    "extract_quantities",
    "valori_scritti_a_parole",
    "numeri_ambigui",
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
