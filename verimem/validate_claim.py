"""P1 — `validate_claim`: anti-confabulazione deterministica.

Spec: docs/specs/p1-hippo-validate-claim.md (commit ce67839).

Tool chiamato PRIMA che Claude affermi un fatto verificabile (es. "X
è nato nel Y", "Z ha detto W"). Cerca evidenza in memoria semantica e
restituisce verdict + advice. Zero LLM call: NER super-light
(Capitalized + anni) + token overlap + contradiction-by-different-year.

Origine: pattern di confabulazione pescati live (sessione 2026-05-14):
Tonegawa Nobel 1987→2014, Anthropic Skills 2025→2026, LightRAG
HKUDS→HKUST. La meccanica è puramente lessicale — non sostituisce
ragionamento, ma intercetta i casi più frequenti di "ho cambiato un
numero/data/attribuzione".
"""
from __future__ import annotations

import re
from typing import Any, Protocol

# Numeric-quantity contradiction primitives — shared with the batch corpus
# scanner (facts_conflict) so write-time and retroactive detection use
# IDENTICAL semantics. Aliased to the historical private names below.
from .quantity_match import (
    YEAR_RE as _YEAR_RE,
)
from .quantity_match import (
    agreement_from_parts as _agreement_from_parts,
)
from .quantity_match import (
    conflict_from_parts as _conflict_from_parts,
)
from .quantity_match import (
    content_tokens as _content_tokens,
)
from .quantity_match import (
    date_conflict as _date_conflict,
)
from .quantity_match import (
    event_indices as _event_indices,
)
from .quantity_match import (
    extract_dates as _extract_dates,
)
from .quantity_match import (
    extract_quantities as _extract_quantities,
)
from .quantity_match import (
    extract_versions as _extract_versions,
)
from .quantity_match import (
    negation_conflict as _negation_conflict,
)
from .quantity_match import (
    norm_unit as _norm_unit,
)
from .quantity_match import (
    version_conflict as _version_conflict,
)

_CAPS_RE = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b")

# Parole capitalized che non sono nomi propri — sono inizio frase /
# pronomi / determiners / verbi modali / congiunzioni / preposizioni.
# Lista corta volutamente: si può espandere se emergono falsi positivi.
_CAPS_STOPWORDS = {
    "The", "And", "But", "Or", "If", "When", "While", "Although",
    "From", "With", "Was", "Were", "Are", "Has", "Have", "Had",
    "This", "That", "These", "Those", "Such", "Some", "Any",
    "Will", "Would", "Could", "Should", "May", "Might", "Must",
    "His", "Her", "Their", "Its", "Our", "Your", "Whose",
    "Who", "What", "Where", "Why", "How",
    "Not", "Yes", "Maybe",
}


class _FactLike(Protocol):
    id: str
    proposition: str
    topic: str
    confidence: float
    source_episodes: list[str]


class _SemanticLike(Protocol):
    def search_facts(
        self, query: str, *, limit: int = 20, topic: str | None = None,
    ) -> list[_FactLike]: ...


class _AgentLike(Protocol):
    semantic: _SemanticLike


def _extract_salients(text: str) -> tuple[set[str], set[str]]:
    """Estrae (capitalized_names, years) dalla stringa.

    NER super-light: nessuna libreria, nessun modello. Filtra
    capitalized stopwords (inizi frase, pronomi). Anni 1500-2099.
    """
    caps_raw = _CAPS_RE.findall(text or "")
    caps = {w for w in caps_raw if w not in _CAPS_STOPWORDS}
    years = set(_YEAR_RE.findall(text or ""))
    return caps, years


def _termine_presente(termine: str, testo_lower: str) -> bool:
    """Il termine come PAROLA INTERA, non come sottostringa.

    Estratta da `_subj_overlap` perche' ora ha due chiamanti e la domanda e'
    la stessa: «Rust» non sta dentro «t·rust·-check». Il confine `\\b` da solo
    non basta sui nomi con punteggiatura (`PROC-1037`, `scikit-learn`), quindi
    si scappa il termine e si ancora ai bordi non-alfanumerici.
    """
    return bool(re.search(
        rf"(?<![0-9a-z]){re.escape(termine)}(?![0-9a-z])", testo_lower))


#: Un dominio e' un NOME, non un predicato. Senza questa riga «verimem.com»
#: entra fra le parole che portano l'asserzione con i suoi due pezzi — e
#: «verimem» e «com» si trovano in mezzo corpus, per cui qualunque cosa si
#: affermi su un sito risulterebbe asserita da qualcuno. Misurato: e' l'unico
#: motivo per cui una claim del banco sopravviveva al controllo qui sotto.
#: Le parole che RIBALTANO una frase, e che percio' non possono essere tolte
#: dal contenuto insieme alle vuote. Elenco CHIUSO — non e' una lista di
#: «parole importanti» che cresce a piacere: sono le negazioni, e la loro
#: proprieta' e' che togliendole la frase dice il CONTRARIO.
#: Oggi solo `non` e' anche in `_PAROLE_VUOTE`; le altre ci sono perche' quella
#: lista e' una fonte esterna che puo' cambiare, e allora il difetto tornerebbe
#: in silenzio su un'altra lingua.
_NEGAZIONI = frozenset({
    "non", "no", "not", "mai", "never", "nessun", "nessuna", "nessuno",
    "niente", "nulla", "senza", "without", "neither", "nor", "ni",
    "pas", "sans", "jamais", "aucun", "sin", "nunca", "ninguno",
})

#: Sopra questa frazione di parole capitalizzate (escluse le iniziali di
#: frase), il riconoscimento dei nomi propri PER MAIUSCOLA non sta piu'
#: leggendo dei nomi. Misurato:
#:     Der Server ist ein Produktionsknoten.        2 su 4 = 0.50
#:     Der Graph hat 8625 Knoten.                   2 su 4 = 0.50
#:     The Database Is A Postgres Cluster.          5 su 5 = 1.00
#:     Il server di Roma ospita il cluster Postgres da marzo.   2 su 9 = 0.22
#:     The annual plan costs 200 euros.             0 su 5 = 0.00
#: Fra 0.22 e 0.50 c'e' spazio per una soglia che non e' un valore scelto a
#: occhio: e' «piu' di un terzo», cioe' piu' di quanti nomi propri veri sta in
#: una frase che ne ha diversi.
_SOGLIA_CAPITALIZZATE = 0.4

#: Sotto questo numero di parole non iniziali una densita' non significa
#: niente: una frase di tre parole con un nome proprio darebbe 0.5.
_MIN_PAROLE_PER_DENSITA = 4


def leggibile_a_maiuscole(text: str) -> bool:
    """Il riconoscimento dei nomi propri per MAIUSCOLA funziona su questa frase?

    Serve perche' quel riconoscimento e' una convenzione TIPOGRAFICA, e non e'
    universale: in tedesco ogni sostantivo e' maiuscolo, quindi finiscono tutti
    fra i «nomi propri» e `_parole_di_contenuto` li toglie. Cio' che resta non
    e' contenuto, e' scarto grammaticale::

        Der Server ist ein Produktionsknoten.    -> ['ein', 'ist']  testa 'ist'
        Die Datenbank ist ein Postgres Cluster.  -> ['ein', 'ist']  testa 'ist'

    e due fatti scorrelati diventano l'uno l'aggiornamento dell'altro, per due
    vie insieme: stessa testa nominale e due parole condivise. Chi scrive dieci
    misure in tedesco ne ritrova una.

    NON SI CURA CON UNA LISTA. Aggiungere `der`/`die`/`das`/`ist` alle parole
    vuote sistemerebbe il tedesco e lascerebbe identici polacco, turco, russo,
    indonesiano e le altre settemila lingue: il prodotto ha liste per quattro
    lingue e utenti in tutto il mondo, e quella strada non arriva in fondo per
    costruzione.

    Quindi il segnale e' STRUTTURALE e non nomina nessuna lingua: la densita'
    di parole capitalizzate. Alta densita' = la maiuscola qui non distingue i
    nomi, e chi legge deve saperlo invece di ricevere una risposta a caso. Vale
    identico sul Title Case inglese, che non e' una lingua ma ha lo stesso
    effetto.

    Le frasi troppo corte per una densita' sono dichiarate leggibili: meglio il
    comportamento di prima che una soglia calcolata su tre parole.
    """
    parole = _PAROLA_RE.findall(text or "")
    if len(parole) - 1 < _MIN_PAROLE_PER_DENSITA:
        return True
    resto = parole[1:]                       # la prima e' maiuscola per regola
    su = sum(1 for p in resto if p[:1].isupper())
    return (su / len(resto)) < _SOGLIA_CAPITALIZZATE


#: Sopra questa similarita' due frasi parlano dello STESSO soggetto con un
#: valore aggiornato. Misurata, non scelta: banco di dodici coppie scritte a
#: mano in lingue NON coperte dalle liste (de, pt, pl, tr), meta' evoluzioni
#: vere e meta' osservazioni scorrelate.
#:     vere   0.9349 .. 0.9682
#:     false  0.8121 .. 0.8674
#: piu' tre casi duri (stesso soggetto, grandezza DIVERSA — non evoluzioni):
#:     0.8581  Korpus 6682 Fakten     | mediane Laenge 795 Zeichen
#:     0.9117  Graph 8625 Knoten      | Dichte 0.42
#:     0.9082  corpus 6682 fatti      | mediana 795 caratteri
#: A 0.93 il banco si separa tutto. IL MARGINE E' STRETTO — 0.9349 la vera piu'
#: bassa contro 0.9117 il duro piu' alto, 0.023 — e non e' una separazione
#: comoda: e' quel tanto che basta sul banco disponibile. Se una coppia vera
#: scende sotto, si rimisura su un banco piu' grande, non si abbassa la soglia.
_SOGLIA_SIMILARITA = 0.93


def similarita_semantica(a: str, b: str) -> float:
    """Quanto due frasi parlano della stessa cosa, in QUALUNQUE lingua.

    Usa l'embedder che il prodotto ha gia' installato e gia' in uso —
    `intfloat/multilingual-e5-base`, cento lingue, 768 dimensioni — invece di
    una lista di parole scritta a mano per quattro. Sul corpus di Aurelio tutti
    i 6972 fatti hanno gia' il loro vettore persistito in tabella: qui si
    ricalcola perche' la funzione riceve due stringhe e non due fatti, ed e'
    il prezzo del fallback, pagato solo dove le liste non arrivano.

    Restituisce 0.0 se l'encode non e' disponibile: un motore assente non deve
    far cadere una scrittura, e zero significa «non ho potuto misurare», che
    porta alla decisione conservativa (nessuna evoluzione).
    """
    try:
        import numpy as np

        from . import embedding
        va = np.asarray(embedding.encode(a or ""), dtype=float)
        vb = np.asarray(embedding.encode(b or ""), dtype=float)
        na, nb = float(np.linalg.norm(va)), float(np.linalg.norm(vb))
        if na == 0.0 or nb == 0.0:
            return 0.0
        return float(va @ vb / (na * nb))
    except Exception:  # noqa: BLE001 — un motore assente non rompe una scrittura
        return 0.0


def _polarita(text: str) -> bool:
    """La frase e' NEGATA? — il segnale che distingue una frase dal suo
    contrario, e che nessun conteggio di parole condivise puo' portare.

    Serve perche' «Il gate NON gira sul canale MCP» e «Il gate gira sul canale
    MCP» hanno le STESSE parole di contenuto e la stessa testa nominale: per il
    criterio dell'evoluzione sono lo stesso fatto aggiornato, e il secondo
    ritira il primo mentre dice il contrario.

    Sta qui e non dentro `_parole_di_contenuto` perche' quella strada e' stata
    provata e MISURATA come peggiore: rimettere le negazioni fra le parole
    contate porta le riconosciute-evoluzione da 228 a 229 sulle 260 coppie
    corte del corpus, e la coppia in piu' e' un falso positivo — due
    osservazioni diverse unite dal solo fatto di nominare entrambe «non».
    Come polarita' quel caso non si muove: hanno la stessa, e a decidere resta
    il criterio di prima.

    Deliberatamente GREZZA — presenza di una negazione, non la sua portata
    sintattica. Non risolve la doppia negazione ne' capisce su quale sintagma
    cade: dice solo che due frasi hanno polarita' diverse, che e' abbastanza
    per NON dichiararle un aggiornamento l'una dell'altra. Nel dubbio non
    evolve, che e' il verso di errore che questo prodotto preferisce.
    """
    parole = {t.lower() for t in _PAROLA_RE.findall(text or "")}
    return bool(parole & _NEGAZIONI)


_DOMINIO_RE = re.compile(r"\b[\w-]+(?:\.[\w-]+)+\b")

#: Le parole, per il controllo di asserzione. Tre lettere minime: sotto ci
#: sono sigle e desinenze, non predicati.
_PAROLA_RE = re.compile(r"\w+", re.UNICODE)


def _parole_di_contenuto(text: str) -> set[str]:
    """Le parole che portano l'ASSERZIONE: né nomi, né parole vuote.

    I nomi dicono DI COSA si parla, queste dicono COSA se ne dice. La
    distinzione e' tutto il punto del controllo qui sotto: due testi che
    condividono solo i nomi parlano dello stesso soggetto, non della stessa
    cosa.
    """
    from .document_index import _PAROLE_VUOTE  # una fonte, non una copia

    # I NOMI SONO IN TITLE CASE. Una parola TUTTA MAIUSCOLA e' enfasi o sigla,
    # mai un nome proprio, e toglierla dal contenuto le faceva perdere il peso
    # che ha. Misurato sui 5151 fatti vivi del corpus il 2026-08-02: dei 14102
    # nomi distinti estratti (86977 occorrenze) ne sono TUTTE MAIUSCOLE 7833
    # (54717 occorrenze) — il 63% — e la piu' frequente e' «NON», 1461 volte.
    # Una negazione contata come nome proprio, e quindi tolta dal contenuto:
    #     Il gate NON gira sul canale MCP. -> ['canale','gate','gira','sul']
    #     Il gate gira sul canale MCP.     -> ['canale','gate','gira','sul']
    # cioe' una frase e la sua negazione indistinguibili per il criterio che
    # decide se un fatto e' l'EVOLUZIONE di un altro: la seconda ritira la
    # prima come aggiornamento, mentre dice il contrario.
    #
    # Le sigle (MCP, TDD, API) tornano fra le parole di contenuto, ed e'
    # giusto: portano contenuto, e chiamarle nomi propri serviva solo a
    # toglierle.
    #
    # PORTATA SUL PREGRESSO: ZERO. Sulle 260 coppie corte gia' superseduta del
    # corpus vivo, riconosciute evoluzione 228 prima e 228 dopo — il corpus e'
    # prosa di sviluppo e non contiene negazioni urlate contrapposte. Vale per
    # cio' che un utente scrive («il deploy NON e' andato»), non per cio' che
    # c'e' gia'.
    #
    # `_extract_salients` NON e' toccata: i suoi altri due consumatori
    # (`salient_count`, `_subj_overlap`) alimentano il gate misurato sul banco
    # delle 20 claim, e questo giro non ha misurato quello.
    caps, _ = _extract_salients(text)
    nomi = {c.lower() for c in caps if not c.isupper()}
    # LA NEGAZIONE RESTA FUORI DAL CONTENUTO, ed e' una correzione a me stesso.
    # Il primo tentativo la rimetteva dentro — «non» e' nelle parole vuote per
    # l'italiano e non per `not`/`no`/`mai`/`senza`/`never`/`without`, il che e'
    # gia' un'incoerenza — ma MISURATO sul corpus quel rimedio PEGGIORA: sulle
    # 260 coppie corte gia' superseduta le riconosciute-evoluzione passano da
    # 228 a 229, e la coppia in piu' e' un falso positivo (due osservazioni
    # diverse, una sul grafo entity_kg e una sulle frequenze, unite dal solo
    # fatto di contenere entrambe «non»).
    # La negazione non e' una parola in piu' da contare: e' la POLARITA' della
    # frase, e va confrontata come tale. Lo fa `_polarita`, usata dalla guardia
    # dell'evoluzione, che distingue «Il gate NON gira» da «Il gate gira»
    # SENZA gonfiare l'intersezione di chi la nomina per caso.
    vuote = _PAROLE_VUOTE
    for dominio in _DOMINIO_RE.findall(text or ""):
        nomi.update(p.lower() for p in _PAROLA_RE.findall(dominio))
    return {t.lower() for t in _PAROLA_RE.findall(text or "")
            if len(t) > 2 and not t.isdigit()
            and t.lower() not in vuote and t.lower() not in nomi}


def _testa_nominale(text: str) -> str:
    """La prima parola di contenuto: in una frase SVO e' la testa del soggetto.

    «Il corpus contiene 6682 fatti» -> «corpus». Non e' un parser: e' la
    domanda «di che cosa parla questa frase» risolta con la sola cosa che
    l'italiano scritto garantisce quasi sempre, l'ordine. Sbaglia sulle frasi
    che aprono con un complemento («Nel piano annuale il prezzo e' 100 euro»
    -> «piano»), ed e' per questo che chi la usa non ci si affida da sola —
    vedi `_puo_essere_una_evoluzione`, dove e' UNA delle due condizioni.
    """
    contenuto = _parole_di_contenuto(text)
    if not contenuto:
        return ""
    for tok in _PAROLA_RE.findall(text or ""):
        if tok.lower() in contenuto:
            return tok.lower()
    return ""


def _qualcuno_asserisce(claim: str, facts: list[_FactLike]) -> bool:
    """Almeno un fatto dice qualcosa DELLA claim, non solo dei suoi soggetti.

    IL CASO REALE che ha portato qui, misurato sul corpus vivo il 2026-08-01::

        "Il moat di Verimem è stato progettato da Google."
            -> supported, confidence 0.95, «Claim coerente con la memoria.»
               7 fatti citati come evidenza

    I sette parlano di Google Ads, Google Analytics e Search Console per
    verimem.com. L'overlap dei nomi e' LEGITTIMO — «Verimem» e «Google» ci sono
    per davvero, non per sottostringa — e nessuno contraddice, perche' sono
    d'argomento tutt'altro. Su venti claim: otto confabulazioni su dieci
    ricevevano `supported`, contro due verita' su dieci. Il verdetto correlava
    col numero di nomi propri, non col contenuto.

    Non e' semantica nuova: questo modulo la applica GIA' in due casi su tre —
    la claim con quantita' non confermate e la `lexical_only` restano `unknown`
    proprio per non dare «false reassurance» sul solo overlap dei nomi. Questo
    e' il terzo caso, quello che mancava: la claim che asserisce una RELAZIONE
    che nessun fatto enuncia.

    IL PERIMETRO, dichiarato perche' e' un costo vero e non un dettaglio: il
    controllo e' lessicale, quindi una claim vera scritta con parole diverse da
    quelle del fatto («il monitoraggio e' attivo» contro «Analytics LIVE»)
    scende a `unknown`. E' la direzione giusta per un prodotto che promette
    l'astensione invece dell'invenzione — dire «non lo so» di una cosa vera
    costa all'utente un controllo, dire «coerente con la memoria» di una falsa
    gli costa la fiducia in tutto il resto. Il giorno in cui serve piu' finezza,
    la si aggiunge qui: il CE locale NON serve allo scopo, misurato lo stesso
    giorno — dava 99.09 alla relazione mai enunciata, perche' e' tarato sul
    write path, dove la source e' l'evidenza scelta per QUEL fatto.
    """
    volute = _parole_di_contenuto(claim)
    if not volute:
        return True  # nessun predicato da cercare: non c'e' niente da negare
    for f in facts:
        testo = (f.proposition or "").lower()
        if any(_termine_presente(p, testo) for p in volute):
            return True
    return False


def _subj_overlap(claim_caps: set[str], fact_text: str) -> float:
    """Frazione di nomi-claim presenti nel testo del fact (case-insensitive).

    Riproduce il match "i nomi della claim appaiono nel fact". Lavora
    su stringa-lower per gestire eventuali normalizzazioni (es. "Tonegawa"
    in claim, "tonegawa" in proposition).

    PAROLA INTERA, non sottostringa (2026-08-01). Con `t.lower() in fact_lower`
    il nome «Rust» risultava presente dentro «adhoc/t·rust·-check», e con
    «database» che compariva davvero l'overlap saliva a 0.667 — sopra la soglia
    0.6. Il fatto entrava fra i candidati, non aveva conflitti di anni o
    quantita', e finiva fra i `supporting`: cosi' la claim «verimem e' scritto
    in Rust e usa Oracle Database» riceveva verdetto **supported**, con
    «Claim coerente con la memoria», mentre la sola «verimem e' scritto in
    Rust» dava onestamente `unknown`. Allungare una falsita' la faceva passare.

    E' la classe gia' in memoria come feedback dopo sei falsi allarmi in una
    sessione — «interroga la struttura, non il testo» — il cui caso peggiore era
    un `"91"` trovato dentro un id casuale. Qui decideva se una claim risulta
    verificata dal gate anti-confabulazione.

    Il confine `\\b` non basta da solo per i nomi che contengono punteggiatura
    (`PROC-1037`, `scikit-learn`): si scappa il termine e si ancora ai bordi
    non-alfanumerici, cosi' «Rust» non entra in «trust» ma «PROC-1037» si trova
    ancora dentro «il codice PROC-1037 identifica».
    """
    if not claim_caps:
        return 0.0
    fact_lower = (fact_text or "").lower()
    hits = 0
    for t in claim_caps:
        tl = t.lower().strip()
        if not tl:
            continue
        if _termine_presente(tl, fact_lower):
            hits += 1
    return hits / len(claim_caps)


def validate_claim(
    agent: _AgentLike,
    claim: str,
    topic_hint: str | None = None,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """Valida una claim factual contro la memoria semantica dell'agente.

    Args:
        agent: oggetto con `.semantic.search_facts(query, *, limit, topic)`.
        claim: stringa con asserzione verificabile (es. "X è nato nel Y").
        topic_hint: filtra i fact a un topic specifico (es.
            "science/biology/nobel").
        threshold: soglia minima di subject-overlap per considerare un
            fact "soggettivamente rilevante" per la claim. Default 0.6.

    Returns:
        dict con chiavi:
          - verdict ∈ {"supported", "contradicted", "unknown"}
          - confidence: float in [0, 1]
          - evidence_facts: list[str] di fact_id
          - evidence_episodes: list[str] di episode_id
          - advice: stringa breve in italiano per Claude

    Verdict logic:
      1. Estrai (caps, years) dalla claim. Se totale < 2 ⇒ "unknown"
         (claim troppo generica per validazione lessicale).
      2. Cerca fact correlati via `semantic.search_facts`. Se vuoto
         ⇒ "unknown".
      3. Per ogni fact con subj_overlap ≥ threshold:
         - se claim_years ∧ fact_years sono disgiunti ⇒ contradicting
         - altrimenti ⇒ supporting
      4. Se contradicting ⇒ "contradicted". Altrimenti se supporting
         ⇒ "supported". Altrimenti ⇒ "unknown".
    """
    claim_caps, claim_years = _extract_salients(claim)
    salient_count = len(claim_caps) + len(claim_years)

    # Numeric-quantity path (sibling of the year-disjoint rule). A claim
    # that states a measurable quantity ("45 minutes", "1024 entries") can
    # contradict a stored fact even with ZERO capitalized names — exactly
    # the subtle confab the keyword L1 detectors miss. Years are excluded
    # from quantities (handled by the year path) so the two never collide.
    claim_quants = _extract_quantities(claim)
    claim_units = {u for (u, _v) in claim_quants if u}
    claim_content = _content_tokens(claim)
    # Distinctive (non-unit) content words drive retrieval + the precision
    # guard below. "minutes"/"entries" are the unit, not the subject.
    claim_distinct = {t for t in claim_content if _norm_unit(t) not in claim_units}
    numeric_viable = bool(claim_quants) and bool(claim_distinct)

    # Lexical expansion (0.7.0): version pins, sub-year dates and polarity
    # flips are verifiable the same deterministic way as quantities. A claim
    # carrying one of them (or ≥2 distinctive words — the negation case: "the
    # vendor contract is signed" has no caps/years/quantities) is viable for
    # the lexical-conflict pass even with <2 caps/years salients.
    claim_versions = _extract_versions(claim)
    claim_dates = _extract_dates(claim)
    lexical_viable = bool(claim_versions) or bool(claim_dates) or (
        len(claim_distinct) >= 2
    )

    # Gate: claim troppo generica (un solo token saliente o nessuno).
    # Esempio: "Tonegawa is a researcher." ha solo {"Tonegawa"} →
    # NON è verificabile lessicalmente, meglio dichiarare unknown.
    # Il path numerico ha la sua viabilità (quantità + ≥1 parola di
    # contesto) e NON va bloccato dal gate caps/anni.
    if salient_count < 2 and not numeric_viable and not lexical_viable:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [],
            "evidence_episodes": [],
            "advice": (
                "Claim troppo generica per validazione lessicale "
                "(servono ≥ 2 token salienti: nomi capitalized + "
                "anno)."
            ),
        }

    # Backend `SemanticMemory.search_facts` (engram/semantic.py:225) usa
    # SQL `LOWER(proposition) LIKE '%<full_query>%'`: passare la claim
    # INTERA fa praticamente sempre miss (la claim verbatim non è
    # sottostringa del fact corretto, perché il fact contiene altre
    # parole intorno). Bug pescato dal critic-orchestrator counterexample
    # worker (cycle #70 review): il fake del test era troppo generoso
    # (token-overlap) e nascondeva il problema reale in produzione.
    #
    # Fix: tokenizzare la claim ed emettere una query per ogni nome
    # capitalized (discriminanti informativi: "Tonegawa", "Newton").
    # Dedup per id. Skippiamo gli anni come chiave di ricerca: "1987"
    # da solo è troppo rumoroso (match cross-topic).
    try:
        hits: list[_FactLike] = []
        seen: set[str] = set()
        search_tokens = list(sorted(claim_caps))
        if claim_quants or lexical_viable:
            # Numeric/version/date/negation claims often have no caps → also
            # retrieve by the distinctive content words so the related fact
            # is found (longest first: more discriminating).
            search_tokens += sorted(
                claim_distinct, key=lambda t: (-len(t), t),
            )[:8]
        for token in search_tokens:
            for f in agent.semantic.search_facts(
                token, limit=10, topic=topic_hint,
            ):
                if f.id in seen:
                    continue
                seen.add(f.id)
                hits.append(f)
            if len(hits) >= 30:
                break
    except Exception as exc:  # pragma: no cover — difensivo
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [],
            "evidence_episodes": [],
            "advice": f"Errore in semantic.search_facts: {exc}",
        }

    if not hits:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [],
            "evidence_episodes": [],
            "advice": "Nessun fatto correlato trovato in memoria.",
        }

    contradicting: list[_FactLike] = []
    supporting: list[_FactLike] = []
    for f in hits:
        fact_caps, fact_years = _extract_salients(f.proposition)
        overlap = _subj_overlap(claim_caps, f.proposition)
        if overlap < threshold:
            continue
        # Anni disgiunti ⇒ contraddizione.
        if claim_years and fact_years and not (claim_years & fact_years):
            contradicting.append(f)
        else:
            supporting.append(f)

    # NAMED-VALUE contradiction pass (2026-08-01) — «X e' A» contro «X e' B»,
    # la contraddizione piu' comune di tutte, e finora invisibile.
    #
    # Perche' il ciclo sopra non poteva vederla: aggancia con
    # `_subj_overlap(claim_caps, fact)`, cioe' chiede che i SALIENTI DELLA
    # CLAIM compaiano nel fatto. Due frasi che si contraddicono differiscono
    # PROPRIO sul nome proprio, quindi l'overlap tende a zero esattamente
    # quando la contraddizione e' netta. Misurato sul prodotto vero: claim
    # «Il database di produzione e' MySQL» contro il fatto «... e' PostgreSQL»
    # -> caps {'MySQL'} contro {'PostgreSQL'}, overlap 0.0000 su soglia 0.6,
    # verdetto `unknown`.
    #
    # E' lo STESSO ragionamento che il passo numerico qui sotto fa gia' per i
    # numeri («independent of the caps-overlap gate above, which is ~0 for
    # number-only claims»): quando l'aggancio sui caps non puo' funzionare, ci
    # si aggancia al CONTESTO CONDIVISO e si cerca il conflitto sul valore.
    # Mancava la versione per i nomi.
    #
    # I due criteri NON sono nuovi e non sono una copia: sono gli stessi che
    # `quantity_match.conflict_from_parts` applica prima di confrontare due
    # valori — intersezione non vuota delle parole di contenuto («unrelated
    # subject») e attributi non contrastanti («different attribute»). Averli
    # in un posto solo e' la ragione per cui il fix del 2026-07-25 su
    # `conflict_from_parts` non e' dovuto essere replicato a mano qui.
    #
    # La guardia sul soggetto condiviso NON e' decorazione: senza, «il server
    # e' Nginx» e «il database e' PostgreSQL» — che non parlano della stessa
    # cosa — avrebbero salienti disgiunti e finirebbero in contesa. Un corpus
    # pieno di conflitti inventati e' il modo piu' rapido per far ignorare il
    # segnale.
    # RITIRATO il 2026-08-01, poche ore dopo averlo scritto. Qui c'era un
    # "named-value pass" lessicale per «X e' A» contro «X e' B». Il difetto che
    # curava e' vero, ma il WRITE PATH lo copre gia' — e meglio: su
    # un'installazione vergine, `Memory.add("... e' PostgreSQL")` seguito da
    # `Memory.add("... e' MySQL")` da' `superseded: ['edc2cc9d76e9']` e il
    # recall restituisce solo il corrente. E' il tier NLI semantico, che si
    # auto-abilita quando il modello e' su disco (README: «Entity swaps need
    # the semantic NLI tier, which auto-enables when its model is already
    # installed»).
    #
    # Tenerlo sarebbe stato un secondo rilevatore, piu' grezzo, sullo stesso
    # caso: la classe di difetto che questo repo cura da giorni (due copie che
    # divergono). E aveva gia' prodotto un falso positivo che solo la suite
    # INTERA ha preso — «la sequenza A000045 e' Fibonacci» contro «la sequenza
    # A000032 e' Lucas», due soggetti diversi dichiarati in contesa, con un
    # fatto distinto ritirato.
    #
    # Cio' che restava scoperto era la SIMULAZIONE (`verimem trust`), che non
    # passa dal write path: quello e' curato dove il difetto stava davvero —
    # l'agente che non veniva costruito, la riga `checked:` che derivava dal
    # flag, e il topic fittizio usato come filtro di ricerca.
    # NUMERIC-QUANTITY contradiction pass — independent of the caps-overlap
    # gate above (which is ~0 for number-only claims). Fires only when the
    # hit shares a DISTINCTIVE (non-unit) content word with the claim AND
    # states a different value for the SAME normalised unit. The shared-word
    # guard is what stops "ring buffer 256 entries" from contradicting
    # "cache 1024 entries" (coincidental unit, unrelated subject).
    numeric_contra: list[_FactLike] = []
    numeric_advice = ""
    numeric_agree = False
    if claim_quants:
        _year_ids = {f.id for f in contradicting}
        for f in hits:
            if f.id in _year_ids:
                continue
            f_quants = _extract_quantities(f.proposition)
            if not f_quants:
                continue
            f_content = _content_tokens(f.proposition)
            # ONE detector, not a second copy of it. This loop used to reimplement
            # the comparison inline, with its own guards — and the two drifted:
            # on 2026-07-25 a fix landed in conflict_from_parts (each side having
            # an exclusive distinctive word means another subject or another
            # attribute) and this path never saw it, so "il gate legge in 45 ms"
            # kept retiring "il gate scrive in 300 ms". Same failure mode as the
            # three divergent copies of the behavioural rules cured the same day.
            if _agreement_from_parts(claim_quants, claim_content,
                                     f_quants, f_content):
                numeric_agree = True  # same unit & value → confirmed
            f_conflict = _conflict_from_parts(
                claim_quants, claim_content, f_quants, f_content,
                ia=_event_indices(claim), ib=_event_indices(f.proposition))
            if f_conflict:
                numeric_contra.append(f)
                if not numeric_advice:
                    cu, cv, fv = f_conflict
                    numeric_advice = (
                        f"in memoria: {fv:g} {cu} (fact {f.id}), "
                        f"NON {cv:g} {cu} — controlla prima di affermare."
                    )

    # LEXICAL-EXPANSION contradiction pass (0.7.0) — version pins, sub-year
    # date moves, polarity flips. Same-subject and precision guards live in
    # the primitives themselves (shared distinctive word, named-subject
    # disjointness, contrast qualifiers, Jaccard for negation) — this loop
    # only orchestrates. Year-disjoint hits are already handled above.
    lexical_contra: list[_FactLike] = []
    lexical_advice = ""
    if claim_versions or claim_dates or lexical_viable:
        _prior_ids = ({f.id for f in contradicting}
                      | {f.id for f in numeric_contra})
        for f in hits:
            if f.id in _prior_ids:
                continue
            kind_detail: tuple[str, str] | None = None
            v = _version_conflict(claim, f.proposition)
            if v is not None:
                kind_detail = ("version", f"{v[1]} in memoria, NON {v[0]}")
            if kind_detail is None:
                d = _date_conflict(claim, f.proposition)
                if d is not None:
                    kind_detail = ("date", f"{d[1]} in memoria, NON {d[0]}")
            if kind_detail is None:
                n = _negation_conflict(claim, f.proposition)
                if n is not None:
                    kind_detail = (
                        "negation", f"polarità opposta su '{n}'")
            if kind_detail is not None:
                lexical_contra.append(f)
                if not lexical_advice:
                    lexical_advice = (
                        f"{kind_detail[1]} (fact {f.id}) — controlla "
                        "prima di affermare."
                    )

    if contradicting or numeric_contra or lexical_contra:
        contra: list[_FactLike] = list(contradicting)
        _seen_c = {f.id for f in contra}
        for f in (*numeric_contra, *lexical_contra):
            if f.id not in _seen_c:
                contra.append(f)
                _seen_c.add(f.id)
        episodes = sorted(
            {eid for f in contra for eid in f.source_episodes}
        )
        f0 = contra[0]
        f0_years = sorted(_extract_salients(f0.proposition)[1])
        claim_years_sorted = sorted(claim_years)
        if contradicting and f0_years and claim_years_sorted:
            advice = (
                f"in memoria: {', '.join(f0_years)} (fact {f0.id}), "
                f"NON {', '.join(claim_years_sorted)} — controlla "
                "prima di affermare."
            )
        elif numeric_advice:
            advice = numeric_advice
        elif lexical_advice:
            advice = lexical_advice
        else:
            advice = (
                "Evidenza contraria in memoria — controlla "
                "prima di affermare."
            )
        return {
            "verdict": "contradicted",
            "confidence": min(float(f0.confidence), 0.95),
            "evidence_facts": [f.id for f in contra],
            "evidence_episodes": episodes,
            "advice": advice,
        }

    # A claim that makes a SPECIFIC numeric assertion we could not confirm
    # against a same-subject fact must NOT be promoted to "supported" on
    # name-overlap alone — that would be false reassurance (a confab-adjacent
    # failure). Suppress support in that case → honest "unknown".
    # Same discipline for the lexical expansion: when the claim passed the
    # generic-claim gate ONLY through lexical viability (no 2 salients, no
    # numeric), it is here to be CHECKED for conflicts, never promoted —
    # "Tonegawa is a researcher." must stay unknown, not become supported.
    # TERZO caso della stessa disciplina, aggiunto 2026-08-01 su un caso reale
    # e non per principio: i due sopra coprono la claim con quantita' non
    # confermate e quella generica, ma NON la claim che asserisce una relazione
    # che nessun fatto enuncia. Sul corpus vivo erano otto confabulazioni su
    # dieci a ricevere `supported` — vedi `_qualcuno_asserisce`.
    lexical_only = salient_count < 2 and not numeric_viable
    suppress_support = bool(claim_quants) and not numeric_agree
    non_asserita = bool(supporting) and not _qualcuno_asserisce(claim, supporting)
    if (supporting and not suppress_support and not lexical_only
            and not non_asserita):
        episodes = sorted(
            {eid for f in supporting for eid in f.source_episodes}
        )
        f0 = supporting[0]
        return {
            "verdict": "supported",
            "confidence": min(float(f0.confidence), 0.95),
            "evidence_facts": [f.id for f in supporting],
            "evidence_episodes": episodes,
            "advice": "Claim coerente con la memoria.",
        }

    if non_asserita:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [f.id for f in supporting],
            "evidence_episodes": [],
            "advice": (
                "I fatti in memoria nominano gli stessi soggetti ma nessuno "
                "asserisce questa claim — il soggetto è noto, questo di lui "
                "no. Verifica prima di affermarlo."
            ),
        }

    if suppress_support and supporting:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [f.id for f in supporting],
            "evidence_episodes": [],
            "advice": (
                "Soggetto presente in memoria ma la quantità numerica "
                "della claim non è confermata da alcun fatto — verifica "
                "prima di affermare il valore."
            ),
        }

    return {
        "verdict": "unknown",
        "confidence": 0.0,
        "evidence_facts": [],
        "evidence_episodes": [],
        "advice": "Evidenza insufficiente: nessun fact ha subject overlap "
                  f"≥ threshold {threshold}.",
    }
