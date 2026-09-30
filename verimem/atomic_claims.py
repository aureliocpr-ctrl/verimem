"""NON innestato nel gate: `decomponi()` da una scrittura ai suoi claim atomici.

E' il «tempo 1» del design «write = N claim atomici, ognuno giudicato»
(docs/ricerca/2026-09-05-design-write-n-claim-atomici.md, approvato dal lead
in 1b203709a2be2ed2). Pura, deterministica, nessuna dipendenza esterna, nessun
modello: prende un testo e restituisce una lista di frasi chiuse. NON e'
innestata nel gate: l'innesto in `run_validation_gate` e i campi di `GateResult`
sono un pezzo separato (capo programmatore). Questo modulo non cambia il
comportamento del prodotto da solo.

Ogni regola porta il numero che l'ha decisa (banchi in docs/stato-reale/banchi/):

  · SOGLIA 1 PAROLA. Lo splitter del 04/09 scartava i pezzi sotto le 3 parole,
    e «ed e' verificata» ne ha due: su 200 «<vero> ed e' verificata» l'intero
    fermava 115, l'atomico 1, con soglia 1 ne ferma 135
    (banco muro1-fase2-la-soglia-di-tre-parole-perde-la-coda). La coda — la
    self-claim in coda che e' il bersaglio del muro 1 — non si scarta mai.
  · « ed » DAVANTI A VOCALE. 301 fatti del corpus lo contengono, 153 restavano
    interi con la regex che spezzava solo « e » (banco muro1-le-due-regex-a-confronto).
  · APOSTROFO. Dopo `e'` un `\\b` non si accende mai (apostrofo e spazio sono
    entrambi non-word), e il corpus scrive `e'` 976 volte contro 357 `è`: la
    guardia del verbo iniziale usa `(?=\\s|$)`, non `\\b`
    (banco muro1-l-apostrofo-spegne-l-eredita-del-soggetto; il prodotto lo sapeva
    gia' in subject_extract.py:37).
  · EREDITA' DEL SOGGETTO. Un pezzo che comincia con un verbo finito riceve il
    soggetto del pezzo precedente (FActScore: i fatti atomici sono
    auto-contenuti). Il soggetto e' il testo del pezzo precedente fino al suo
    primo verbo finito, con un elenco di verbi APERTO — non `subject_of`, che
    riconosce il soggetto solo nel 15,7% dei primi pezzi (1.183/7.536), perche'
    `_VERB_MARK` e' una lista chiusa.
  · FUSIONE DEI NUDI. Un pezzo senza verbo finito non e' un claim: e' un pezzo
    di claim. Non si scarta e non si giudica da solo — si fonde col precedente
    (o col successivo, se e' il primo). E' la regola che protegge i veri di
    ieri: «Indietro 16 con tracciato 0.» usciva da solo e L1.17 lo fermava
    (banco muro1-il-falso-allarme-su-un-campione-non-scelto).
  · INGLESE, misurato il 2026-09-24 su 100 memorie estratte da conversazioni
    vere (LoCoMo, tre etichettatrici): 15 spezzature, 5 col senso SBAGLIATO, due
    su memorie VERE. Con un giudice per claim il pezzo sbagliato di una memoria
    vera diventa una quarantena falsa. Quattro cause, quattro regole:
      - la fusione ricuce il SEPARATORE ORIGINALE, non una «e» fissa («energy e
        support» in un testo inglese);
      - gli irregolari inglesi (felt, got, found, built...) sono verbi finiti:
        senza, «Andrew's dog got» diventava un soggetto;
      - un pezzo il cui UNICO verbo sta dopo una relativa o una subordinata
        («rest where she goes...», «a source when she started...») e' un pezzo
        del precedente, non un claim;
      - due verbi con lo STESSO complemento («inspired and motivated them») sono
        un claim solo: il pezzo di sinistra finisce sul suo verbo.
  · VIRGOLETTE. Mai spezzare dentro « », " " e '…': la citazione spezzata
    trasforma una MENZIONE in un'ASSERZIONE («Il fatto 'La migrazione e'
    completata' da' None.» cadeva su L1.13). Con gli apici singoli la scansione
    distingue l'apostrofo («e'», «l'impianto», «da'») dalla virgoletta.

Cio' che questo modulo NON fa, e dove lo dice il design: non tratta le
subordinate (1,9% del corpus, tempo 2); non produce triplette S-P-O (tempo 2:
parser o LLM); non decontestualizza oltre il soggetto.
  · LIMITE NOTO, misurato e non curato: la COPULA NUDA — «non e chiaro», la
    «è» scritta senza accento ne' apostrofo — viene letta come congiunzione e
    spezzata. Sul corpus vivo e' ~1% dei fatti (188 su 15.378 col righello
    stretto, 8 copule vere su 10 nel campione letto; banco
    quanto-corpus-e-scritto-in-ascii-e-quanta-copula-e-nuda, 06/09). La fusione
    dei nudi ne recupera una parte («chiaro se il modulo…» non ha verbo finito
    e si fonde). Una regex che distingua «e» copula da «e» congiunzione non
    esiste senza un parser: tempo 2, come le subordinate.
"""
from __future__ import annotations

import re

__all__ = ["decomponi", "ha_verbo_finito", "soggetto_di"]

# ── verbi finiti: ausiliari, copule, modali e i verbi piu' frequenti nel corpus.
# APERTO nel senso che si estende qui, dichiarato, con il numero che lo motiva —
# non e' una regex sulle desinenze (troppo larga: «mano», «piano») ne' la lista
# chiusa di _VERB_MARK (troppo stretta: 15,7% di richiamo sui primi pezzi).
_VERBI_FINITI = (
    # italiano — ausiliari e copule (con la grafia ASCII dell'accento)
    "è|e'|sono|ha|hanno|era|erano|fu|furono|sara'|sarà|saranno|viene|vengono|"
    "sta|stanno|stava|stavano|va|vanno|"
    # italiano — verbi frequenti nel corpus (misure, stati, esiti)
    "resta|restano|risulta|risultano|costa|costano|contiene|contengono|dice|dicono|"
    "fa|fanno|da'|dà|danno|passa|passano|torna|tornano|funziona|funzionano|"
    "entra|entrano|esce|escono|legge|leggono|scrive|scrivono|conta|contano|"
    "misura|misurano|ferma|fermano|ammette|ammettono|chiama|chiamano|produce|"
    "producono|usa|usano|serve|servono|manca|mancano|cade|cadono|regge|reggono|"
    "gira|girano|parte|partono|finisce|finiscono|comincia|cominciano|inizia|"
    "iniziano|apre|aprono|chiude|chiudono|tiene|tengono|porta|portano|prende|"
    "prendono|mette|mettono|trova|trovano|vede|vedono|sa|sanno|puo'|può|possono|"
    "deve|devono|vuole|vogliono|stampa|stampano|emette|emettono|riceve|ricevono|"
    "pesa|pesano|ospita|ospitano|copre|coprono|perde|perdono|vale|valgono|"
    "spezza|spezzano|scatta|scattano|"
    # inglese
    "is|are|was|were|has|have|had|does|do|did|can|could|will|would|should|may|"
    "might|must|runs|ran|fails|failed|passes|passed|returns|returned|shows|showed|"
    "works|worked|holds|held|remains|remained|contains|contained|takes|took|"
    "gives|gave|reports|reported|reads|read|writes|wrote|says|said|goes|went|"
    "becomes|became|means|meant|costs|cost|weighs|weighed|"
    # inglese — passati irregolari (non finiscono in -ed) e presenti frequenti nelle
    # memorie estratte da conversazioni. Solo forme che raramente sono un nome:
    # «plans», «values», «needs» restano fuori, perche' un pezzo che comincia con un
    # nome letto come verbo erediterebbe un soggetto che non ha.
    "felt|got|found|made|built|met|kept|told|bought|brought|began|came|knew|won|"
    "ate|drove|flew|sat|stood|taught|chose|heard|sold|caught|fought|spoke|wore|"
    "woke|hid|thought|saw|feels|loves|enjoys|likes|wants|thinks|believes|seems|"
    "knows|tries|helps|prefers|admires|appreciates|considers|expresses|mentions|"
    "finds|keeps|makes|gets|"
    # francese e spagnolo — forme finite che NON sono anche parole inglesi o italiane: il francese «a»
    # (ha) e' l'articolo inglese, lo spagnolo «son» ed «es» sono nomi inglesi, e la lista vale per
    # tutte le lingue. Senza «a», il passato prossimo francese («et a acheté») non si spezza: resta intero.
    "est|sont|ont|était|étaient|fut|furent|sera|seront|vont|fait|font|peut|peuvent|doit|doivent|"
    "veut|veulent|avait|avaient|está|están|eran|fue|fueron|será|serán|tiene|tienen|tenía|tenían|"
    "hace|hacen|hizo|hicieron|van|puede|pueden|debe|deben|quiere|quieren"
)
# in inglese passato semplice e participio coincidono («tested», «signed») e fanno
# entrambi da predicato: le forme in -ed contano come verbo finito. In italiano no.
# lo spagnolo marca il passato remoto con -ó, -aron, -ieron («compró», «visitaron»): nessuna parola
# inglese o italiana finisce con la «ó» acuta, e le tre lettere davanti tengono fuori «Aaron».
_PASSATO_SPAGNOLO = r"[a-záéíóúñ]{3,}(?:ó|aron|ieron)"
_RE_VERBO = re.compile(
    rf"(?<![\w'])(?:{_VERBI_FINITI}|[a-z]{{3,}}ed|{_PASSATO_SPAGNOLO})(?=\s|$|[.,;:!?])", re.IGNORECASE)
_RE_VERBO_INIZIALE = re.compile(
    rf"^(?:{_VERBI_FINITI}|[a-z]{{3,}}ed|{_PASSATO_SPAGNOLO})(?=\s|$)", re.IGNORECASE)

# ── parole che aprono una relativa o una subordinata, nelle due lingue: il verbo
# che viene dopo non fa del pezzo un claim («rest where she goes to relax»).
_RE_SUBORDINANTE = re.compile(
    r"(?<![\w'])(?:where|who|whom|whose|which|that|when|while|because|since|"
    r"although|though|if|unless|until|after|before|che|cui|dove|quando|mentre|"
    r"perché|perche'|poiché|poiche'|se|benché|benche'|sebbene|finché|finche')(?=\s|$|[.,;:!?])",
    re.IGNORECASE)

# ── «to» come ultima PAROLA prima del verbo: l'infinito inglese («to read»).
# Parola intera: «photo», «Toronto», «onto» non contano.
_RE_TO_FINALE = re.compile(r"(?:^|\s)to\s*$", re.IGNORECASE)

# ── davanti a un -ed inglese queste parole ne fanno un PREDICATO, non un verbo
# finito: «got excited», «felt inspired», «was tested», «staying motivated».
_COPULE_AUSILIARI = frozenset((
    "is", "are", "was", "were", "be", "been", "being", "am", "get", "gets", "got",
    "getting", "feel", "feels", "felt", "stay", "stays", "stayed", "become",
    "becomes", "became", "seem", "seems", "seemed", "look", "looks", "looked",
    "remain", "remains", "remained", "keep", "keeps", "kept"))

# ── davanti a un -ed queste parole ne fanno un MODIFICATORE: «for underserved
# communities», «a finished product», «the pickled onions».
_MODIFICATORI = frozenset((
    "for", "of", "in", "on", "at", "with", "by", "from", "into", "onto", "about", "the",
    "a", "an", "his", "her", "their", "its", "our", "my", "your", "this", "these",
    "those", "some", "many", "more", "most", "very", "well", "newly"))

# ── la copula subito dopo un -ed: «focused is key» e' un pezzo di «resilient and
# focused», non un claim che comincia col verbo «focused».
_COPULE = frozenset(("is", "are", "was", "were", "è", "e'", "sono", "era", "erano"))

# ── pronomi oggetto: «reassured HIM» dice che il verbo di destra prende lo stesso
# complemento di quello di sinistra («encouraged and reassured him»).
_RE_PRONOME_OGGETTO = re.compile(
    r"^(?:him|her|them|it|me|us|you|lo|la|li|le|gli|ci|vi)(?=\s|$|[.,;:!?])", re.IGNORECASE)

# ── participio con l'AUSILIARE SOTTINTESO: «L'implementazione e' finita e collaudata»
# -> «collaudata» non ha un verbo finito, ma non e' un frammento: e' «[e'] collaudata».
# Eredita soggetto E ausiliare dal pezzo precedente. Desinenze regolari + irregolari
# frequenti; in inglese il caso non si pone (-ed e' gia' finito).
_RE_PARTICIPIO_INIZIALE = re.compile(
    r"^(?:\w+(?:at[oaie]|ut[oaie]|it[oaie])|conclus[oaie]|chius[oaie]|apert[oaie]|"
    r"scritt[oaie]|fatt[oaie]|mess[oaie]|pres[oaie]|vist[oaie]|risolt[oaie]|"
    r"decis[oaie]|rimoss[oaie]|corrett[oaie]|rott[oaie]|spent[oaie]|access[oaie])"
    r"(?=\s|$|[.,;:!?])", re.IGNORECASE)
_RE_AUSILIARE = re.compile(
    r"(?<![\w'])(è|e'|sono|ha|hanno|era|erano|viene|vengono|fu|furono)(?=\s|$)",
    re.IGNORECASE)

# ── coordinate su cui si spezza (italiano e inglese); « ed » davanti a vocale
_RE_COORD = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|,\s*et\s+|\s+et\s+|"
                       r",\s*y\s+|\s+y\s+|;\s+)", re.IGNORECASE)

# ── espressioni fisse che contengono la coordinata e non sono coordinate: il francese «il y a»
# («c'e'»), e «et al.» in fondo a un elenco di autori.
_RE_IL_Y_A = re.compile(r"(?:^|\s)il\s+y\s+(?:a|avait|aura|aurait|eut)\b", re.IGNORECASE)
_RE_ET_AL = re.compile(r"\bet\s+al\.", re.IGNORECASE)

# ── parole che davanti a un apostrofo sono elisioni/accenti, non virgolette
_ELISIONI = {"e", "l", "d", "s", "c", "n", "un", "un'", "dall", "dell", "nell", "sull",
             "all", "quell", "coll", "da", "po", "gl", "quest", "sant", "com", "dov",
             "perch", "anch", "senz", "tutt", "mezz", "cinquant", "trent", "vent"}


def _zone_protette(testo: str) -> list[tuple[int, int]]:
    """Gli intervalli [inizio, fine) che stanno dentro virgolette.

    Scansione carattere per carattere, non regex: con gli apici singoli bisogna
    distinguere «l'impianto», «e'», «da'» (apostrofi) da «'La migrazione e'
    completata'» (citazione). La regola: un `'` e' apostrofo se la parola che lo
    precede e' un'elisione nota; altrimenti apre una citazione se e' preceduto da
    spazio/inizio, e la chiude se e' seguito da spazio/punteggiatura/fine.
    """
    zone: list[tuple[int, int]] = []
    i, n = 0, len(testo)
    aperta: tuple[str, int] | None = None  # (carattere di chiusura atteso, inizio)
    while i < n:
        c = testo[i]
        if aperta:
            chiusura, inizio = aperta
            if c == chiusura and (c != "'" or _e_chiusura_di_citazione(testo, i)):
                zone.append((inizio, i + 1))
                aperta = None
        elif c == "«":
            aperta = ("»", i)
        elif c == '"':
            aperta = ('"', i)
        elif c == "'" and _e_apertura_di_citazione(testo, i):
            aperta = ("'", i)
        i += 1
    return zone


def _parola_prima(testo: str, i: int) -> str:
    j = i
    while j > 0 and (testo[j - 1].isalpha() or testo[j - 1] == "'"):
        j -= 1
    return testo[j:i].lower().rstrip("'")


def _e_apertura_di_citazione(testo: str, i: int) -> bool:
    prima = testo[i - 1] if i > 0 else " "
    dopo = testo[i + 1] if i + 1 < len(testo) else " "
    if prima.isalpha() and _parola_prima(testo, i) in _ELISIONI:
        return False  # «l'impianto», «e'», «un'ora»
    return (prima.isspace() or prima in "([«\"") and (dopo.isalnum() or dopo in "«\"")


def _e_chiusura_di_citazione(testo: str, i: int) -> bool:
    prima = testo[i - 1] if i > 0 else " "
    dopo = testo[i + 1] if i + 1 < len(testo) else " "
    if prima.isalpha() and _parola_prima(testo, i) in _ELISIONI:
        return False  # «e' completata» dentro la citazione: e' un accento
    return (prima.isalnum() or prima in ".!?»\")") and (dopo.isspace() or dopo in ".,;:!?)»" or i + 1 == len(testo))


def _dentro(pos: int, zone: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in zone)


def _verbi_finiti(pezzo: str) -> list[re.Match[str]]:
    """I verbi finiti del pezzo, nell'ordine. Non contano: il verbo dopo «to» (un
    infinito, «to read»), e il -ed inglese dopo una copula, un ausiliare o un
    gerundio (un predicato: «got excited», «staying motivated»)."""
    out = []
    for m in _RE_VERBO.finditer(pezzo):
        prima = pezzo[:m.start()]
        if _RE_TO_FINALE.search(prima):
            continue
        if m.group(0).lower().endswith("ed"):
            precedenti = prima.rstrip().split()
            if precedenti:
                p = precedenti[-1].lower().strip(",;:")
                if p in _COPULE_AUSILIARI or p in _MODIFICATORI or p.endswith("ing"):
                    continue
        out.append(m)
    return out


def ha_verbo_finito(pezzo: str) -> bool:
    """Un pezzo e' un claim solo se ha un verbo finito (lista aperta sopra)."""
    return bool(_verbi_finiti(pezzo))


def soggetto_di(pezzo: str) -> str:
    """Il testo del pezzo fino al suo primo verbo finito; '' se non c'e' un verbo
    o se il pezzo COMINCIA col verbo (nessun soggetto davanti)."""
    verbi = _verbi_finiti(pezzo)
    if not verbi or verbi[0].start() == 0:
        return ""
    return pezzo[:verbi[0].start()].strip().rstrip(",;:")


def _spezza(testo: str) -> list[tuple[str, str]]:
    """Split sulle coordinate, saltando i punti che cadono dentro le virgolette.
    Soglia: 1 parola (nessun pezzo viene scartato per lunghezza).

    Ogni pezzo porta il SEPARATORE che lo precedeva nel testo (« and », «, e »,
    «; »...): chi fonde due pezzi li ricuce con quello, cosi' la fusione restituisce
    il testo com'era scritto e non inventa una «e» italiana in una frase inglese."""
    zone = _zone_protette(testo)
    pezzi: list[tuple[str, str]] = []
    ultimo = 0
    separatore = ""
    fisse = [(x.start(), x.end()) for x in _RE_IL_Y_A.finditer(testo)] + \
            [(x.start(), x.end()) for x in _RE_ET_AL.finditer(testo)]
    for m in _RE_COORD.finditer(testo):
        if _dentro(m.start(), zone) or _dentro(max(m.start(), m.end() - 1), zone):
            continue
        if any(a <= m.start() + 1 < b or a < m.end() - 1 <= b for a, b in fisse):
            continue   # «il y a», «et al.»: la coordinata sta dentro un'espressione fissa
        pezzo = testo[ultimo:m.start()].strip(" .")
        if pezzo:
            pezzi.append((separatore, pezzo))
        separatore = m.group(0)
        ultimo = m.end()
    coda = testo[ultimo:].strip(" .")
    if coda:
        pezzi.append((separatore, coda))
    return pezzi or [("", testo.strip(" ."))]


def _ausiliare_di(pezzo: str) -> str:
    """L'ultimo ausiliare del pezzo ('' se non c'e'): e' quello che il participio
    successivo sottintende («e' finita e [e'] collaudata»)."""
    trovati = _RE_AUSILIARE.findall(pezzo)
    return trovati[-1] if trovati else ""


def _fondi_i_nudi(pezzi: list[str]) -> list[str]:
    """Un pezzo senza verbo finito si fonde col precedente (o col successivo se
    e' il primo): non diventa mai un frammento giudicato da solo.
    ECCEZIONE, con la sua ragione: un pezzo che COMINCIA con un participio dopo
    un pezzo che ha un ausiliare non e' nudo, e' ellittico — riceve l'ausiliare
    (il soggetto lo ricevera' dopo, come ogni pezzo che comincia col verbo).
    E' la coda «e collaudata» / «ed e' verificata»: 1 pezzo su 200 con la soglia
    di tre parole, 135 con la soglia a una."""
    out: list[str] = []
    separatori: list[str] = []   # separatori[i] precedeva out[i] nel testo
    for separatore, p in pezzi:
        if not out:
            out.append(p)
            separatori.append("")
        elif (ha_verbo_finito(p) and not _solo_verbo_subordinato(p)
              and not _stesso_complemento(out[-1], p)
              and not _frammento_aggettivale(p)
              and not _subordinata_aperta(out[-1])):
            out.append(p)
            separatori.append(separatore)
        elif _RE_PARTICIPIO_INIZIALE.match(p) and _ausiliare_di(out[-1]):
            out.append(f"{_ausiliare_di(out[-1])} {p}")
            separatori.append(separatore)
        else:
            out[-1] = f"{out[-1]}{separatore}{p}"
    if len(out) >= 2 and not ha_verbo_finito(out[0]):
        out[1] = f"{out[0]}{separatori[1]}{out[1]}"
        out = out[1:]
    return out


def _solo_verbo_subordinato(pezzo: str) -> bool:
    """Il pezzo ha UN solo verbo finito e davanti a lui c'e' una parola che apre una
    relativa o una subordinata: «rest where she goes to relax», «a steady presence
    when he started running». Non e' un claim, e' un pezzo del precedente.
    Con due verbi («il test che gira passa») il secondo e' il verbo principale e il
    pezzo resta un claim."""
    verbi = _verbi_finiti(pezzo)
    if len(verbi) != 1:
        return False
    sub = _RE_SUBORDINANTE.search(pezzo)
    return sub is not None and sub.start() < verbi[0].start()


def _frammento_aggettivale(pezzo: str) -> bool:
    """«focused is key for entrepreneurs»: un -ed minuscolo seguito subito da una
    copula non e' un verbo (un verbo non regge una copula), e' un aggettivo
    coordinato con l'ultima parola del pezzo precedente («resilient and focused»)."""
    parole = pezzo.split()
    return (len(parole) >= 2 and re.fullmatch(r"[a-z]{3,}ed", parole[0]) is not None
            and parole[1].lower() in _COPULE)


def _subordinata_aperta(sinistra: str) -> bool:
    """Il pezzo di sinistra apre una subordinata e non le ha ancora dato un verbo:
    «believes that regular grooming, daily brushing, baths, nail trims | and lots of
    love are essential». La coordinata sta DENTRO il soggetto della subordinata, e il
    verbo che la chiude e' nel pezzo di destra: si ricuce."""
    ultima = None
    for m in _RE_SUBORDINANTE.finditer(sinistra):
        ultima = m
    if ultima is None:
        return False
    return not _verbi_finiti(sinistra[ultima.end():])


def _stesso_complemento(sinistra: str, destra: str) -> bool:
    """«encouraged | reassured him»: il pezzo di sinistra FINISCE sul suo verbo (che
    non e' preceduto da un altro verbo: «got scared» e' un predicato, non un verbo
    rimasto senza complemento) e quello di destra comincia con un verbo seguito da un
    pronome oggetto. I due verbi reggono lo stesso complemento: un claim solo."""
    parole = sinistra.rstrip(" .,;").split()
    if not parole or not _RE_VERBO_INIZIALE.match(parole[-1]):
        return False
    if len(parole) >= 2 and _RE_VERBO_INIZIALE.match(parole[-2]):
        return False
    m = _RE_VERBO_INIZIALE.match(destra)
    return m is not None and bool(_RE_PRONOME_OGGETTO.match(destra[m.end():].lstrip()))


def _eredita_il_soggetto(pezzi: list[str]) -> list[str]:
    """Un pezzo che comincia con un verbo finito riceve il soggetto del pezzo
    precedente — quello immediatamente precedente, non il primo."""
    out: list[str] = []
    soggetto = ""
    for p in pezzi:
        if _RE_VERBO_INIZIALE.match(p) and soggetto:
            p = f"{soggetto} {p[0].lower() + p[1:]}"
        else:
            s = soggetto_di(p)
            if s:
                soggetto = s
        out.append(p)
    return out


def _chiudi(pezzo: str) -> str:
    p = pezzo.strip()
    if not p:
        return p
    p = p[0].upper() + p[1:]
    return p if p.endswith((".", "!", "?")) else p + "."


def decomponi(testo: str, *, eredita_soggetto: bool = True) -> list[str]:
    """La scrittura -> i suoi claim atomici, ognuno una frase chiusa.

    Un testo vuoto o di una sola proposizione torna com'e', in una lista di un
    elemento (identita': N=1). Deterministica; non muta l'ingresso.

    DUE FORME, per due layer — misurato il 05/09 sui 200 «<vero> + coda»:
      · `eredita_soggetto=True` (default): claim AUTO-CONTENUTI, «Il comando
        warmup e' finito alle 14:53». E' la forma per il moat (un giudice NLI
        vuole il soggetto) e per la ricevuta che l'utente legge.
      · `eredita_soggetto=False`: i pezzi NUDI, «E' finito alle 14:53». E' la
        forma per L1: il rilevatore semantico di self-claim (L1.20) riconosce la
        forma impersonale, e con un soggetto davanti la carve-out di terzi la
        ESENTA. Con soggetto L1 ferma 101/200 code, senza 145/200; l'intero 114.
    Chi innesta nel gate manda la forma nuda a L1 e quella auto-contenuta a L4:
    lo stesso claim, due grafie, due giudici.
    """
    if not testo or not testo.strip():
        return [testo]
    pezzi = _spezza(testo)
    if len(pezzi) == 1:
        return [testo.strip()]
    pezzi = _fondi_i_nudi(pezzi)
    if len(pezzi) == 1:
        return [testo.strip()]
    if eredita_soggetto:
        pezzi = _eredita_il_soggetto(pezzi)
    return [_chiudi(p) for p in pezzi]
