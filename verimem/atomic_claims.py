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
    "becomes|became|means|meant|costs|cost|weighs|weighed"
)
# in inglese passato semplice e participio coincidono («tested», «signed») e fanno
# entrambi da predicato: le forme in -ed contano come verbo finito. In italiano no.
_RE_VERBO = re.compile(
    rf"(?<![\w'])(?:{_VERBI_FINITI}|[a-z]{{3,}}ed)(?=\s|$|[.,;:!?])", re.IGNORECASE)
_RE_VERBO_INIZIALE = re.compile(rf"^(?:{_VERBI_FINITI}|[a-z]{{3,}}ed)(?=\s|$)", re.IGNORECASE)

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
_RE_COORD = re.compile(r"\s*(?:,\s*ed?\s+|\s+ed?\s+|,\s*and\s+|\s+and\s+|;\s+)", re.IGNORECASE)

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


def ha_verbo_finito(pezzo: str) -> bool:
    """Un pezzo e' un claim solo se ha un verbo finito (lista aperta sopra)."""
    return _RE_VERBO.search(pezzo) is not None


def soggetto_di(pezzo: str) -> str:
    """Il testo del pezzo fino al suo primo verbo finito; '' se non c'e' un verbo
    o se il pezzo COMINCIA col verbo (nessun soggetto davanti)."""
    m = _RE_VERBO.search(pezzo)
    if not m or m.start() == 0:
        return ""
    return pezzo[:m.start()].strip().rstrip(",;:")


def _spezza(testo: str) -> list[str]:
    """Split sulle coordinate, saltando i punti che cadono dentro le virgolette.
    Soglia: 1 parola (nessun pezzo viene scartato per lunghezza)."""
    zone = _zone_protette(testo)
    pezzi: list[str] = []
    ultimo = 0
    for m in _RE_COORD.finditer(testo):
        if _dentro(m.start(), zone) or _dentro(max(m.start(), m.end() - 1), zone):
            continue
        pezzo = testo[ultimo:m.start()].strip(" .")
        if pezzo:
            pezzi.append(pezzo)
        ultimo = m.end()
    coda = testo[ultimo:].strip(" .")
    if coda:
        pezzi.append(coda)
    return pezzi or [testo.strip(" .")]


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
    for p in pezzi:
        if ha_verbo_finito(p) or not out:
            out.append(p)
        elif _RE_PARTICIPIO_INIZIALE.match(p) and _ausiliare_di(out[-1]):
            out.append(f"{_ausiliare_di(out[-1])} {p}")
        else:
            out[-1] = f"{out[-1]} e {p}"
    if len(out) >= 2 and not ha_verbo_finito(out[0]):
        out[1] = f"{out[0]} e {out[1]}"
        out = out[1:]
    return out


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
