"""Deterministic, zero-API entity extraction (entity-live tier 1).

WHY: the entity-KG + PPR engine (entity_kg.py) was built-not-live — the
only extractor (openie.py) needs an LLM, nothing populates the graph
from the real corpus, so entity retrieval returned 0 hits on real data
(the README said so honestly). This module is the LLM-free tier: regex
extraction tuned for THIS corpus (technical facts: code identifiers,
file paths, commit SHAs, acronyms, proper nouns), so the graph becomes
real today at zero API cost. The LLM tier (openie.py) stays as the
higher-quality opt-in on top.

Design constraints:
  * deterministic + pure (same text -> same entities), trivially testable;
  * conservative: prefer missing a borderline entity over flooding the
    graph with noise (stoplist, sentence-initial guard, per-text cap);
  * type tags are coarse on purpose: code | path | module | commit |
    acronym | proper | tech.
"""
from __future__ import annotations

import re

#: per-text cap — bounds the co-occurrence clique downstream (n*(n-1)/2).
MAX_ENTITIES_PER_TEXT = 16

# Italian + English function words that slip through Capitalized matching.
_STOPWORDS = {
    "il", "lo", "la", "le", "gli", "un", "una", "uno", "per", "con", "del",
    "della", "dei", "delle", "nel", "nella", "sul", "sulla", "questo",
    "questa", "questi", "queste", "quando", "dove", "come", "anche", "dopo",
    "prima", "senza", "sopra", "sotto", "the", "this", "that", "these",
    "those", "with", "from", "into", "over", "under", "when", "where",
    "while", "after", "before", "and", "but", "for", "not", "its", "his",
    "her", "our", "their", "are", "was", "were", "has", "have", "had",
    "all", "any", "each", "more", "most", "other", "some", "such", "only",
    "own", "same", "than", "then", "too", "very",
}

# Months/weekdays: capitalized-by-convention, never places/persons — guard for
# the conversational prepositional patterns ("in March" is a date, not a city).
_DATE_WORDS = {
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "jan", "feb", "mar",
    "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
    "sunday",
}

#: Closed list of conversational life-events (tier-1 design,
#: CONVERSATIONAL_ENTITY_DESIGN.md): temporal anchors for transitions.
_EVENT_NOUNS = (
    "promotion", "layoff", "wedding", "marriage", "divorce", "graduation",
    "retirement", "relocation", "move", "trip", "accident", "surgery",
    "launch", "opening", "expansion", "anniversary", "breakup",
)

# Ordered patterns: first match wins per span (path before module before
# snake_case so "engram/semantic.py" doesn't shatter into pieces).
# Patterns with a CAPTURE GROUP contribute group(1) as the entity name
# (the anchor word — preposition/verb — is context, not part of the name).
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # file path with extension: engram/semantic.py, benchmark\x.py
    ("path", re.compile(r"\b[\w.-]+[/\\][\w/\\.-]*\.\w{1,6}\b")),
    # dotted module: verimem.provider_registry (>=2 dotted lowercase parts)
    ("module", re.compile(r"\b[a-z_][\w]*(?:\.[a-z_][\w]+)+\b")),
    # snake_case identifier (>=2 segments): community_detector
    ("code", re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")),
    # CamelCase: SemanticMemory, LongMemEval, McNemar
    ("code_camel", re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")),
    # commit-ish hex, 7-12 chars, not a pure number
    ("commit", re.compile(r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,12}\b")),
    # acronym / all-caps tag, 2-6 letters: MCP, PPR, TDD, CI, MRR
    ("acronym", re.compile(r"\b[A-Z]{2,6}\b")),
    # tech token with digits: mem0, gpt4o, qwen3 (len >= 3, starts alpha)
    ("tech", re.compile(r"\b[a-z]{2,}[0-9][a-z0-9]*\b")),
    # --- conversational tier-1 (2026-07-08): relationally-anchored, so they
    # never fire on sentence-initial grammar capitals. Before "proper" so the
    # span gets the SPECIFIC type. Guarded against date words below.
    # organization: proper-noun run ending in a business suffix
    ("org", re.compile(
        r"\b([A-Z][\w&à-ÿ]*(?:\s+[A-Z][\w&à-ÿ]*){0,3}\s+"
        r"(?:B&B|Hotel|Inn|Ltd|Inc|Corp|Company|Agency|Studio|Café|Cafe|"
        r"Restaurant|University|College|Institute))\b")),
    # person: capitalized name right after a companion/relation anchor
    ("person", re.compile(
        r"\b(?:with|alongside|met|married|dating|befriended)\s+"
        r"([A-Z][a-zà-ÿ]+(?:\s+[A-Z][a-zà-ÿ]+)?)\b")),
    # place: capitalized name after a locative anchor (dates guarded)
    ("place", re.compile(
        r"\b(?:in|to|from|at|near|visited|visiting|toured)\s+"
        r"([A-Z][a-zà-ÿ]+(?:\s+[A-Z][a-zà-ÿ]+)?)\b")),
    # life event from the closed list, with or without a determiner
    ("event", re.compile(
        r"\b(?:the|his|her|their|my|a|an)\s+(" + "|".join(_EVENT_NOUNS) + r")\b"
        r"|(?<=[Aa]fter )(" + "|".join(_EVENT_NOUNS) + r")\b",
        re.IGNORECASE)),
    # activity/artifact: lowercase noun chunk after an offer/adopt verb
    ("activity", re.compile(
        r"\b(?:offers?|offered|introduced|launched|enjoys?|enjoyed|started|"
        r"owns?|owned|bought|adopted|hosts?|hosted|joined)\s+"
        r"((?:[a-z][\wà-ÿ-]*\s+){0,3}[a-z][\wà-ÿ-]*)"
        r"(?=[,.;:]|\s+(?:in|on|at|to|for|with|by|from)\b|$)")),
    # Capitalized proper noun runs: Claude Code, Engram
    ("proper", re.compile(
        r"\b[A-Z][a-zà-ÿ]+(?:\s+[A-Z][a-zà-ÿ]+){0,3}\b")),
]

_SENTENCE_START = re.compile(r"(?:^|[.!?:;]\s+|\n\s*)$")


def _is_sentence_initial(text: str, start: int) -> bool:
    """True when the match begins a sentence (Capitalized-by-grammar).

    SECURITY (opus CodeQL triage 2026-07-18, alert [29]): the old
    ``_SENTENCE_START.search(text[:start])`` re-scanned the ENTIRE prefix for
    every entity match — quadratic on ``fact.proposition`` (up to 64KB, NOT
    capped by the L1 gate), a tenant DoS vector. Only the handful of chars
    immediately before ``start`` decide sentence-initiality, so inspect a
    bounded window: O(1) per call, O(n) overall instead of O(n²).
    """
    if start <= 0:
        return True
    window = text[max(0, start - 64):start]
    return bool(_SENTENCE_START.search(window))


def extract_entities_lite(text: str) -> list[dict[str, str]]:
    """Extract entities from `text`. Returns [{"name", "type"}, ...].

    Deterministic, never raises, [] on empty input. Conservative by
    design — see module docstring for the noise/recall trade-off.
    """
    if not text or not text.strip():
        return []

    taken: list[tuple[int, int]] = []  # claimed spans, first-match-wins
    out: list[dict[str, str]] = []
    seen_lower: set[str] = set()

    def _claim(start: int, end: int) -> bool:
        for s, e in taken:
            if start < e and end > s:
                return False
        taken.append((start, end))
        return True

    for etype, pat in _PATTERNS:
        for m in pat.finditer(text):
            # capture-group patterns (conversational tier-1): the entity is
            # group 1+ (the anchor word is context); span-claim on the group
            # so the anchor stays free for other patterns.
            if m.lastindex:
                g = next((i for i in range(1, m.lastindex + 1) if m.group(i)),
                         None)
                if g is None:
                    continue
                name = m.group(g).strip().strip(".,;:()[]{}\"'")
                span = m.span(g)
            else:
                name = m.group(0).strip().strip(".,;:()[]{}\"'")
                span = m.span(0)
            if not name or len(name) < 2:
                continue
            low = name.lower()
            if low in _STOPWORDS or low in seen_lower:
                continue
            if name.isdigit():
                continue
            # Una PAROLA FUNZIONALE urlata non e' una sigla (2026-08-01).
            # `("acronym", r"\b[A-Z]{2,6}\b")` prende qualunque parola di 2-6
            # lettere tutta maiuscola, e nei nostri fatti le maiuscole sono
            # ENFASI: «il gate NON ha girato». Misurato sul grafo vero (8625
            # entita', 87879 archi): «NON» era l'acronimo con piu' fatti
            # collegati (416) e il terzo nodo per grado dell'INTERO grafo
            # (1494 archi, dietro solo «Loop» 1962 e «HippoAgent» 1761) — e il
            # PPR ci cammina sopra per fare retrieval.
            #
            # PERIMETRO, dichiarato perche' non si legga come «grafo pulito»:
            # questo chiude le parole FUNZIONALI, cioe' il caso dominante,
            # riusando la lista che `document_index` ha gia'. Restano fuori le
            # parole PIENE urlate (PASS, MASTER, CYCLE, LIVE): separarle vuole
            # un dizionario della lingua. La «quota di occorrenze maiuscole»
            # sembrava il criterio ovvio ed e' stata misurata — separa non
            # 0.325 / fix 0.068 da tdd 0.997 / llm 0.889, ma sbaglia su pass
            # 0.742 e master 0.843. Un taglio a occhio li' e' l'errore gia'
            # pagato tre volte questa settimana.
            if etype == "acronym":
                from .document_index import _PAROLE_VUOTE
                if low in _PAROLE_VUOTE:
                    continue
            # ⚠️ `proper` E' NELL'ELENCO DAL 2026-08-25, e la sua assenza era un
            # difetto misurabile: «A Tuesday standup was added.» produceva
            # `Tuesday` (type=proper), e «The Rovigo warehouse was audited in
            # May.» produceva `May` — cioe' l'UNICA entita' estratta da quella
            # frase era la data, mentre il nome proprio andava perso. Il ramo
            # sotto lo copriva solo per person/place, e i mesi/giorni che
            # arrivano qui come `proper` passavano indisturbati.
            if etype in ("person", "place", "proper") and (
                    low in _DATE_WORDS or low.split()[0] in _DATE_WORDS):
                continue  # "in March" / "with Sunday brunch" = date, not entity
            if etype == "proper":
                # single Capitalized word at sentence start = grammar, not
                # entity — unless the same word also appears mid-sentence.
                if " " not in name and _is_sentence_initial(text, m.start()):
                    mid = re.search(
                        r"(?<![.!?:;]\s)(?<!^)\b" + re.escape(name) + r"\b",
                        text[m.end():],
                    )
                    if not mid:
                        continue
                first_word = name.split()[0].lower()
                if first_word in _STOPWORDS:
                    # ⚠️ NON si scarta il match: si scarta il DETERMINANTE.
                    # Fino al 2026-08-25 qui c'era `continue`, e con la parola
                    # funzionale se ne andava il nome proprio attaccato:
                    # «The Rovigo warehouse» -> NESSUNA entita', misurato su
                    # otto frasi su otto. In verimem un fatto senza entita' non
                    # ha con che essere distinto da un altro, e due fatti EN su
                    # magazzini DIVERSI finivano per supersedersi a vicenda.
                    #
                    # Il resto ripassa da TUTTE le difese che lo scarto saltava
                    # — ed e' li' che stava il rischio di questa cura: togliere
                    # il determinante e basta avrebbe promosso «The Monday
                    # meeting» a entita' «Monday». Misurate entrambe le
                    # popolazioni prima di consegnare: 8/8 guadagnati, 0/8
                    # difese rotte, piu' un falso positivo PREESISTENTE chiuso.
                    pezzi = name.split(None, 1)
                    if len(pezzi) < 2:
                        continue
                    resto = pezzi[1]
                    basso = resto.lower()
                    if (not resto[:1].isupper()
                            or basso in _STOPWORDS
                            or basso in seen_lower
                            or basso in _DATE_WORDS
                            or basso.split()[0] in _DATE_WORDS):
                        continue
                    # Lo `span` resta quello del match INTERO di proposito: la
                    # regione «The Rovigo» va prenotata tutta, o il determinante
                    # resterebbe libero per un altro pattern.
                    name, low = resto, basso
            if not _claim(*span):
                continue
            seen_lower.add(low)
            out.append({"name": name, "type": etype})
            if len(out) >= MAX_ENTITIES_PER_TEXT:
                return out
    return out


__all__ = ["extract_entities_lite", "MAX_ENTITIES_PER_TEXT"]
