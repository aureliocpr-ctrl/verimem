"""Subject-based domain/agent classifier for L1 precision (design (d), 2026-07-22).

Pure, deterministic, no external deps. The L1 keyword anti-confab detectors
fire on verbs (completed/tested/deployed/secure/approved) that are ambiguous
between an AGENT's self-claim about its own software work and a third-party
PROFESSIONAL fact. The discriminator is the SUBJECT HEAD, not the verb:
'the service was deployed' (software → agent) vs 'the bridge joint was deployed'
(physical → domain).

``is_domain_professional`` returns True only for a third-person fact whose
subject head is NOT a software/work artifact. Fail-safe: first person, empty,
pronoun, or uncertain subject → False (the L1 anti-confab keeps escalating).

Used ONLY behind an env-gated, default-off carve-out in the write gate — this
module never changes behavior on its own.
"""
from __future__ import annotations

import re

# Determiners stripped from the front of a subject NP.
_DET = {"the", "a", "an", "this", "that", "these", "those", "il", "lo", "la",
        "le", "gli", "un", "una", "uno", "i"}

# First-person / agent-voice markers → never a third-party domain fact.
# T212 (25/09): anche l'italiano. «Io ho descritto la terapia» passava come fatto di
# TERZI, perche' la lista conosceva solo la prima persona inglese (classe: liste
# monolingue).
_FIRST_PERSON = re.compile(
    r"\b(?:I|we|We|my|My|our|Our|us|me"
    r"|[Ii]o|[Nn]oi|[Mm]io|[Mm]ia|[Mm]iei|[Mm]ie|[Nn]ostro|[Nn]ostra|[Nn]ostri|[Nn]ostre)\b")

# Finite verbs / copulas that terminate the leading subject NP.
_VERB_MARK = re.compile(
    r"\b(?:ha|hanno|è|sono|era|erano|viene|vengono|rejected|signed|is|are|was|were|has|have|had|expires?|expired|remains?|resolved|"
    r"reports?|reported|leads?|led|runs?|ran|opened|closed|migrated|reached|"
    r"spans?|monitors?|monitored|documented|confirmed|tested|deployed|added|"
    r"approved|completed|finished|scheduled|planned|works?|holds?|caught|"
    r"got|became|plays?|lives?|crashed|went|switched|adopted|shipped|passed|"
    r"succeeded|rated|meets?|auto-renews?|renews?|renewed|does|do|did|can|will|"
    r"would|should|may|might|must)\b"
    # ⚠️ `e'` STA FUORI DAL GRUPPO, e non e' una svista: il gruppo si chiude con
    # `\b`, e dopo un apostrofo il word-boundary NON matcha (apostrofo e spazio
    # sono entrambi non-word). Messo dentro, sarebbe morto in silenzio.
    #
    # Perche' serve: `è` c'era, `e'` no — e `e'` e' la forma ASCII con cui
    # l'italiano si scrive senza tastiera italiana. Senza marcatore di verbo
    # `subject_of()` torna vuoto, il soggetto e' «non risolvibile» e
    # `is_domain_professional` fallisce PRIMA di guardare il dominio: la
    # carve-out per i fatti di terzi non viene nemmeno raggiunta.
    #
    # Misurato prima di curare (registro dell'esame, 30/08):
    #   W7-72  isolamento a una variabile: `e'` 0/4 · `è` 4/4 · attiva 3/3
    #   W7-73  il corpus scrive `e'` 976 volte contro 357 con `è` — il TRIPLO —
    #          e 174 fatti vivi perdono il soggetto per l'apostrofo
    #   W7-74  ma ALLA PORTA l'esito cambia in 1 caso su 24: il 93,7% di quei
    #          174 sta dove `L1` non gira comunque. **Cura piccola, effetto
    #          misurato minimo** — le due cose vanno dette insieme.
    r"|\be'(?=\s)",
    re.IGNORECASE)

#: T212 (25/09) — LE FORME FINITE SEMPLICI, NELLE DUE LINGUE. `_VERB_MARK` e' un
#: elenco chiuso: ausiliari italiani e una lista di verbi inglesi, spesso in UNA forma
#: sola. Misurato il 24/09 su 120 frasi parallele (tre soggetti di terzi, cinque verbi,
#: quattro forme): esenti col passato composto it 15/15 ed en 15/15, col passato semplice
#: it 0/15 ed en 6/15, col presente it 0/15 ed en 3/15, con l'imperfetto it 0/15. Lo
#: stesso fatto era di terzi o no secondo il TEMPO del verbo.
#: Qui ogni verbo del registro dei professionisti (riferire, prescrivere, firmare,
#: decidere, pagare…) porta TUTTE le sue forme finite: presente, passato semplice o
#: remoto, imperfetto, singolare e plurale. Il confine del soggetto e' il PRIMO fra un
#: marcatore di `_VERB_MARK` e una di queste forme.
#: ⚠️ ACCOPPIATE con le teste (vedi SOFTWARE_HEADS): un verbo in piu' rende
#: risolvibile un soggetto in piu', e se la testa e' un sistema o un codice deve stare
#: nella lista, o una frase sul proprio lavoro diventa «di terzi». Per questo i verbi del
#: registro OPERATIVO italiano (funzionare, compilare, girare, eseguire) NON stanno qui:
#: sono il registro con cui un agente parla del proprio lavoro.
#: ⚠️ Una forma che e' anche un nome («la cura», «la firma», «la visita») in PRIMA
#: posizione dopo l'articolo lascia il soggetto vuoto: la carve-out non si applica e L1
#: resta com'era. E' il verso sicuro.
_FORME_EN = """
describe describes described explain explains explained prescribe prescribes prescribed
confirm confirms recommend recommends recommended diagnose diagnoses diagnosed
suggest suggests suggested indicate indicates indicated conclude concludes concluded
decide decides decided announce announces announced propose proposes proposed
predict predicts predicted deliver delivers delivered receive receives received
examine examines examined assess assesses assessed admit admits admitted argue argues
argued say says said tell tells told find finds found give gives gave send sends sent
sell sells sold buy buys bought write writes wrote owns owned manage manages managed
teach teaches taught treats treated observe observes observed noted stated showed
estimated measured paid ordered booked visited studied reviewed discharged
verify verifies verified
"""
_FORME_IT = """
descrive descrivono descrisse descrissero descriveva descrivevano
spiega spiegano spiegò spiegarono spiegava spiegavano
prescrive prescrivono prescrisse prescrissero prescriveva prescrivevano
conferma confermano confermò confermarono confermava confermavano
riferisce riferiscono riferì riferirono riferiva riferivano
raccomanda raccomandano raccomandò raccomandarono raccomandava raccomandavano
consiglia consigliano consigliò consigliarono consigliava consigliavano
diagnostica diagnosticano diagnosticò diagnosticarono diagnosticava diagnosticavano
cura curano curò curarono curava curavano
dichiara dichiarano dichiarò dichiararono dichiarava dichiaravano
dice dicono disse dissero diceva dicevano
osserva osservano osservò osservarono osservava osservavano
nota notano notò notarono notava notavano
trova trovano trovò trovarono trovava trovavano
mostra mostrano mostrò mostrarono mostrava mostravano
suggerisce suggeriscono suggerì suggerirono suggeriva suggerivano
indica indicano indicò indicarono indicava indicavano
scrive scrivono scrisse scrissero scriveva scrivevano
sostiene sostengono sostenne sostennero sosteneva sostenevano
afferma affermano affermò affermarono affermava affermavano
conclude concludono concluse conclusero concludeva concludevano
decide decidono decise decisero decideva decidevano
stabilisce stabiliscono stabilì stabilirono stabiliva stabilivano
annuncia annunciano annunciò annunciarono annunciava annunciavano
propone propongono propose proposero proponeva proponevano
presenta presentano presentò presentarono presentava presentavano
richiede richiedono richiese richiesero richiedeva richiedevano
rinvia rinviano rinviò rinviarono rinviava rinviavano
stima stimano stimò stimarono stimava stimavano
misura misurano misurò misurarono misurava misuravano
prevede prevedono previde previdero prevedeva prevedevano
paga pagano pagò pagarono pagava pagavano
compra comprano comprò comprarono comprava compravano
vende vendono vendette vendettero vendé vendeva vendevano
riceve ricevono ricevette ricevettero riceveva ricevevano
manda mandano mandò mandarono mandava mandavano
consegna consegnano consegnò consegnarono consegnava consegnavano
ordina ordinano ordinò ordinarono ordinava ordinavano
prenota prenotano prenotò prenotarono prenotava prenotavano
visita visitano visitò visitarono visitava visitavano
firma firmano firmò firmarono firmava firmavano
approva approvano approvò approvarono approvava approvavano
respinge respingono respinse respinsero respingeva respingevano
esamina esaminano esaminò esaminarono esaminava esaminavano
valuta valutano valutò valutarono valutava valutavano
gestisce gestiscono gestì gestirono gestiva gestivano
possiede possiedono possedette possedettero possedeva possedevano
insegna insegnano insegnò insegnarono insegnava insegnavano
studia studiano studiò studiarono studiava studiavano
dimette dimettono dimise dimisero dimetteva dimettevano
ricovera ricoverano ricoverò ricoverarono ricoverava ricoveravano
opera operano operò operarono operava operavano
lamenta lamentano lamentò lamentarono lamentava lamentavano
verifica verificano verificò verificarono verificava verificavano
"""
_VERBI_FINITI = frozenset((_FORME_EN + _FORME_IT).split())
#: una parola: lettere (anche accentate) e apostrofi interni; niente cifre
_PAROLA = re.compile(r"[^\W\d_](?:[^\W\d_]|['’])*")


def _primo_verbo_finito(testo: str) -> int | None:
    """Dove comincia la prima forma di `_VERBI_FINITI`, o None."""
    for m in _PAROLA.finditer(testo):
        if m.group(0).lower() in _VERBI_FINITI:
            return m.start()
    return None

#: Adverbs that sit between the subject NP and its verb ('the team STILL runs') —
#: stripped from the NP tail so they never become a bogus head noun.
_TRAIL_ADV = {"still", "now", "already", "currently", "also", "just", "often",
              "usually", "recently", "never", "always", "typically", "fully",
              "completely", "entirely", "successfully", "perfectly",
              "thoroughly", "partially", "finally"}

#: Spelled-out number words — a head made of these ('forty-two', 'nine') is the
#: same identity-free register as a digit head (GLM evasion class, 2026-07-22).
_NUM_WORDS = frozenset({
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty", "thirty",
    "forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
    "thousand", "million", "billion"})

#: Honorific abbreviations whose trailing dot is NOT sentence punctuation —
#: without this, 'Dr. Rossi confirmed …' tripped the punct guard in
#: ``subject_of`` and the fact fail-safed to escalate (corpus residual,
#: 2026-07-22). The dot is stripped ONLY for these known titles; any other
#: mid-NP period still reads as sentence structure (fail-safe unchanged).
_HONORIFIC = re.compile(
    r"\b(Dr|Mr|Mrs|Ms|Prof|Dott|Ing|Avv|St)\.", re.IGNORECASE)

#: Subject heads that mark an AGENT's own software / work artifact — the register
#: the L1 detectors exist to police. A subject with one of these heads is NOT a
#: domain fact (it escalates). Kept deliberately software/work-scoped; ordinary
#: physical/legal/medical/financial nouns are absent on purpose.
SOFTWARE_HEADS = frozenset({
    # LE TESTE SOFTWARE ITALIANE (2026-08-26) — vanno INSIEME ai marcatori di
    # verbo qui sopra, mai da sole: con i soli verbi `subject_head` trova
    # «migrazioni» ma il classificatore non la riconosce come software, quindi
    # `_is_domain_professional_fact` torna True, L1 viene DECLASSATO e la
    # self-claim entra. E' successo il 25/08 (`1900b83b`), 17 test rossi,
    # revertito il 26/08 (`dd904750`).
    # LE TESTE METRICHE (2026-08-26 22:24) — sono la seconda meta' dello stesso
    # difetto, e stamattina ne avevo fatta una sola. Con i verbi accentati
    # `subject_head` trova «latenza» in «La latenza è 40 ms.»; se «latenza» non
    # e' qui, il classificatore la legge come FATTO PROFESSIONALE DI TERZI,
    # `_is_domain_professional_fact` torna True, L1 viene DECLASSATO e la
    # metrica senza evidenza ENTRA. Rosso misurato in
    # `test_un_accento_non_decide_se_il_gate_scatta` (2 failed, 22:23).
    # Una metrica non e' un terzo professionista: e' una grandezza tecnica.
    "latenza", "latenze", "copertura", "coperture",
    "memoria", "precisione", "prestazione", "prestazioni", "velocita",
    "migrazione", "migrazioni", "modulo", "moduli", "servizio", "servizi",
    "verifica", "verifiche", "modifica", "modifiche", "libreria", "librerie",
    "flusso", "flussi", "classe", "classi", "analisi",
    # 2026-09-03 — TERZA VOLTA DELLA STESSA FORMA, e le prime due stanno qui
    # sopra: ogni volta che si allarga il riconoscimento del VERBO italiano,
    # emergono TESTE italiane mancanti. Il 26/08 furono le metriche (commento
    # sopra); il 30/08 la cura `c857752e` aggiunse `e'` ai marcatori, e da quel
    # giorno «La funzionalita' funziona ed e' verificata.» e «L'implementazione
    # e' finita e collaudata.» ENTRANO SERVIBILI (cella rossa 33648de6): con un
    # marcatore in piu' il soggetto diventa risolvibile, e senza la testa in
    # questa lista il classificatore le legge come fatti di TERZI.
    # ⇒ Marcatori e teste sono ACCOPPIATI: chi tocca gli uni misuri le altre.
    # Non e' una stop-list ad hoc: «funzionalita'» e «implementazione» sono il
    # registro con cui un agente parla del PROPRIO lavoro, esattamente come
    # `feature`/`implementation` che sono gia' fra le teste inglesi.
    "funzionalita", "funzionalità", "funzionalita'",
    "implementazione", "implementazioni",
    # T212 (25/09) — QUARTA VOLTA, e questa volta insieme ai verbi: le forme finite
    # semplici rendono risolvibili «Il sistema descrive…», «L'applicativo confermò…».
    # Le teste italiane del registro software che mancavano, SOLO quelle univoche.
    # ⚠️ Le teste a doppio uso restano FUORI, come la regola delle teste inglesi dice
    # sotto: «collaudo» e' anche il collaudo di un impianto fatto da una commissione
    # (lo ha preso `test_e_apostrofo_e_un_marcatore_di_verbo`, rosso quando c'era),
    # «codice» il codice civile, «applicazione» quella di una norma, «componente» il
    # membro di un consiglio, «rilascio» quello di un permesso. Una frase sul proprio
    # lavoro con una di queste teste e un verbo del lessico resta un limite noto:
    # i verbi OPERATIVI (funziona, compila, gira) non sono nel lessico, quindi «Il
    # codice funziona» continua a non avere un soggetto e L1 la trattiene.
    "sistema", "sistemi", "applicativo", "applicativi", "software", "deploy",

    "service", "services", "migration", "migrations", "build", "builds",
    "deployment", "deployments", "feature", "features", "endpoint", "endpoints",
    "api", "apis", "app", "apps", "application", "applications", "codebase",
    "code", "module", "modules", "function", "functions", "pipeline",
    "pipelines", "job", "jobs", "task", "tasks", "release", "releases",
    "patch", "patches", "database", "databases", "server", "servers",
    "backend", "frontend", "model", "models", "script", "scripts",
    "container", "containers", "cluster", "clusters", "pod", "pods",
    "commit", "commits", "branch", "branches", "repository", "repositories",
    "repo", "repos", "pr", "prs", "schema", "schemas", "query", "queries",
    "cache", "config", "rollout", "refactor", "merge", "sdk", "cli", "ui",
    "gateway", "webhook", "daemon", "worker", "workers", "workflow",
    "workflows", "test", "tests", "suite", "integration", "component",
    "components", "handler", "handlers", "middleware", "binary", "package",
    # software SYSTEM + performance metrics/attributes (the register of an
    # agent's own-work perf claims: 'throughput reached...', 'the system works').
    # Measured leak-closers (real test corpus, 2026-07-22) — a category, not the
    # two literal words: 'system' is mildly ambiguous (ventilation/immune system)
    # but never a subject head in the vertical corpus, and the carve-out is
    # observe-first behind an env, so the residual FP is measurable not shipped.
    "system", "systems", "throughput", "latency", "uptime", "downtime",
    "qps", "rps", "availability", "performance", "bandwidth", "response",
    "responses", "runtime", "load", "memory", "cpu",
    # ADVERSARIAL leak-closers — the critic-orchestrator counterexample worker
    # (job 8f6d0ec5, 2026-07-22) proved the denylist above was NOT exhaustive:
    # these software/ML/web-register heads were absent, so an agent self-claim
    # ('the algorithm was tested and passed') read as domain and had its L1
    # escalation wrongly suppressed. Only CLEARLY-software heads are added; a few
    # genuinely dual-use heads (protocol/transformer/network/agent/driver/site)
    # are LEFT OUT on purpose — adding them would quarantine legitimate clinical/
    # legal/engineering facts (a false positive), and a lexical denylist cannot be
    # exhaustive either way. This is the proven ceiling of lexical subject
    # classification; the honest promotion gate is the measured corpus + default
    # OFF + observe-first, NOT the completeness of this frozenset.
    "algorithm", "algorithms", "platform", "platforms", "product", "products",
    "website", "websites", "portal", "portals", "parser", "parsers",
    "compiler", "compilers", "heuristic", "heuristics", "dashboard",
    "dashboards", "page", "pages", "library", "libraries", "framework",
    "frameworks", "plugin", "plugins", "widget", "widgets", "kernel", "kernels",
    "microservice", "microservices", "lambda", "dataset", "datasets",
    "embedding", "embeddings", "tokenizer", "tokenizers", "classifier",
    "classifiers", "checkpoint", "checkpoints", "optimizer", "optimizers",
    "prompt", "prompts", "chatbot", "chatbots", "bot", "bots", "crawler",
    "crawlers", "scraper", "scrapers", "indexer", "indexers", "orchestrator",
    "orchestrators",
    # GLM-5.2 + Kimi-K3 convergent evasion classes (2026-07-22, verified
    # leaking + confirmed by 11 full-suite reds): work-collectives (self-claim
    # by proxy), bug-tracker register, work-process/outcome nouns, spelled
    # synonyms of denylisted heads. Dual-register heads that name REAL
    # legal/clinical/engineering facts (review, audit, compliance,
    # certification, cause, results) are LEFT OUT on purpose — over-adding
    # them would re-open the 86.7% vertical FP this cure closed.
    "team", "teams", "group", "groups", "bug", "bugs", "ticket", "tickets",
    "issue", "issues", "regression", "regressions", "fix", "fixes",
    "coverage", "stabilization", "transition", "transitions", "cutover",
    "cutovers", "deploying", "staging", "monolith", "monoliths", "canary",
    "canaries", "runbook", "runbooks", "playbook", "playbooks", "shard",
    "shards", "replica", "replicas", "flag", "flags", "rollback", "rollbacks",
    "deadline", "deadlines", "slo", "sla", "backlog", "sprint", "sprints",
    "verification", "validation", "signoff", "production", "production-ready",
    "prod",
})

_LEXICAL_CAP = 8192


def subject_of(text: str) -> str:
    """Leading noun-phrase subject: tokens before the first finite-verb marker,
    minus a leading determiner. '' when no clear subject NP is present."""
    t = (text or "")[:_LEXICAL_CAP].strip()
    if not t:
        return ""
    t = _HONORIFIC.sub(lambda m: m.group(0)[:-1], t)
    m = _VERB_MARK.search(t)
    confine = m.start() if m else None
    #: T212: il confine e' il PRIMO fra un marcatore e una forma finita del lessico
    forma = _primo_verbo_finito(t)
    if forma is not None and (confine is None or forma < confine):
        confine = forma
    if confine is None or confine == 0:
        return ""
    np = t[:confine].strip().rstrip(",;:")
    toks = np.split()
    if toks and toks[0].lower() in _DET:
        toks = toks[1:]
    while toks and toks[-1].lower() in _TRAIL_ADV | {"and", "or", "but", "nor"}:
        toks = toks[:-1]
    if not toks or len(toks) > 6 or any(c in np for c in ".!?"):
        return ""
    return " ".join(toks)


def subject_head(text: str) -> str:
    """The head noun of the subject NP (rightmost content token). '' if none."""
    subj = subject_of(text)
    toks = [re.sub(r"[^\w-]", "", t).lower() for t in subj.split()]
    toks = [t for t in toks if t and t not in _DET]
    return toks[-1] if toks else ""


#: pronoun heads carry no domain identity → uncertain → fail-safe to NOT-domain.
#: Includes INDEFINITE pronouns ('Everything works perfectly…' — a full-suite
#: red the flip exposed: 'everything' was not in this list and read as domain).
_PRONOUNS = frozenset({"it", "they", "he", "she", "this", "that", "you",
                       "i", "we", "one", "someone", "something", "everything",
                       "anything", "nothing", "everyone", "anyone", "somebody",
                       "nobody", "none", "all", "both", "each", "several",
                       "many", "most", "others",
                       # T212 (25/09): anche i pronomi italiani, che con le forme
                       # finite del lessico diventano teste risolvibili
                       "io", "tu", "lui", "lei", "noi", "voi", "loro", "esso",
                       "essa", "essi", "esse", "questo", "questa", "questi",
                       "queste", "quello", "quella", "quelli", "quelle", "tutto",
                       "tutti", "tutte", "niente", "nulla", "qualcuno",
                       "qualcosa", "ognuno", "ciascuno", "nessuno", "alcuni",
                       "molti", "altri", "ciò"})


def _subject_tokens(text: str) -> list[str]:
    """Lowercased content tokens of the subject NP (determiners stripped;
    possessives normalized: "Tom's" -> "tom", so the entity matches its bare
    mention on the other side)."""
    subj = re.sub(r"'s\b", "", subject_of(text))
    # ⚠️ L'ARTICOLO ELIDATO RESTAVA ATTACCATO AL SOSTANTIVO. La riga sotto
    # toglie i non-word SENZA separare, quindi «L'implementazione» diventava il
    # token `limplementazione` — che non e' una parola e non puo' incontrare
    # NESSUNA testa della lista. Misurato il 2026-09-03 sulla cella rossa
    # 33648de6: con la sola aggiunta di «implementazione» a SOFTWARE_HEADS il
    # banco restava 1 failed, perche' il token non ci arrivava mai.
    # Si toglie l'articolo, non si separa: `_DET` contiene «lo/la/un», non «l»,
    # quindi separando resterebbe un token spurio «l».
    subj = re.sub(r"\b(?:l|dell|nell|all|dall|sull|un|quest|quell)'",
                  " ", subj, flags=re.IGNORECASE)
    toks = [re.sub(r"[^\w-]", "", t).lower() for t in subj.split()]
    return [t for t in toks if t and t not in _DET]


def same_subject(a: str, b: str) -> bool:
    """True iff the two propositions are ABOUT the same subject — the L3-semantic
    NLI pre-filter (P2, 2026-07-22). Rule: same HEAD noun (rightmost content
    token) AND modifier agreement (overlap, subset, or one side bare). An
    empty/pronoun/uncertain subject is a WILDCARD -> True (fail-open: a conflict
    we cannot attribute must still reach the judge, never be silently skipped).
    Measured motivation: the cosine 0.7 pre-filter is inert (595/595 corpus
    pairs clear it) and the NLI over-flags different-subject pairs. Pure and
    symmetric; the gate wiring is separate and env-gated default-off."""
    ta, tb = _subject_tokens(a), _subject_tokens(b)
    if not ta or not tb or ta[0] in _PRONOUNS or tb[0] in _PRONOUNS:
        return True                      # wildcard -> compare (fail-open)
    ha, ma = ta[-1], set(ta[:-1])
    hb, mb = tb[-1], set(tb[:-1])
    if ha != hb:
        # cross-entity containment ("Tom's startup" ~ "Tom"): heads differ but
        # one side's head is a token of the other's subject -> same subject
        # sphere, compare. Applies ONLY on differing heads, so shared-head
        # pairs ('payments team' vs 'design team') still take the modifier
        # branch below and stay separated.
        return ha in tb or hb in ta
    if not ma or not mb:
        return True                      # bare head on one side -> assume same
    return bool(ma & mb) or ma <= mb or mb <= ma


#: Heads whose modifiers PARTITION rather than identify: 'the payments team'
#: and 'the design team' are genuinely different subjects. Only these heads are
#: eligible for the NLI pre-skip. Artifact heads (app/platform/service…) carry
#: identity in the MODIFIER ('the Twitter app' ~ 'the X app' = a rebrand, the
#: critic bfa3bce6 counterexample) and must always reach the judge. Residual
#: documented FN: a rebranded ORG UNIT ('Twitter team' ~ 'X team') still skips
#: — the lexical ceiling; entity resolution is the 0.8 cure.
_ORG_UNIT_HEADS = frozenset({
    "team", "teams", "group", "groups", "squad", "squads", "department",
    "departments", "division", "divisions", "committee", "committees",
    "unit", "units", "office", "offices", "desk", "desks", "chapter",
    "chapters", "guild", "guilds", "crew", "crews",
})


def nli_prefilter_skip(a: str, b: str) -> bool:
    """True = SAFE to skip the NLI judge for this pair. Converged GLM-5.2 +
    Kimi-K3 rule (2026-07-22), NARROWED by critic bfa3bce6's brand-as-modifier
    counterexample: skip ONLY when both subjects share the same
    ORGANIZATIONAL-UNIT head (whose modifiers partition: 'payments team' vs
    'design team') with both-sided DISJOINT modifiers. Everything else reaches
    the judge: head mismatch (alias signature, 35.2% FN measured on Wikidata
    altLabels), artifact heads ('Twitter app' ~ 'X app' — the modifier IS the
    identity), bare heads, pronoun/empty subjects. FPs quarantine
    (recoverable); FNs poison (permanent) — the asymmetry decides every
    uncertain case."""
    ta, tb = _subject_tokens(a), _subject_tokens(b)
    if not ta or not tb or ta[0] in _PRONOUNS or tb[0] in _PRONOUNS:
        return False
    ha, ma = ta[-1], set(ta[:-1])
    hb, mb = tb[-1], set(tb[:-1])
    if ha != hb or ha not in _ORG_UNIT_HEADS or not ma or not mb:
        return False
    return not (ma & mb)


def is_domain_professional(text: str) -> bool:
    """True iff ``text`` reads as a THIRD-PARTY professional/domain fact that the
    L1 keyword anti-confab should treat as advisory rather than escalate.

    True requires ALL of: not first-person; a resolvable subject NP; a subject
    head that is NOT a software/work artifact and NOT a bare pronoun. Any
    uncertainty resolves to False so the anti-confab keeps escalating (the safe
    default). Pure and deterministic."""
    t = (text or "")[:_LEXICAL_CAP]
    if not t.strip() or _FIRST_PERSON.search(t):
        return False
    head = subject_head(t)
    if not head or head in _PRONOUNS:
        return False
    # A digit-bearing head carries NO domain identity: 'Cycle 999', '999-beta',
    # 'Milestone M13', 'Sprint 42a', 'Release R2', 'Phase 2b' are the agent's
    # own version/milestone register. Flip-delta 2026-07-22 caught the pure-
    # numeric case; critic 7a7bd87d then defeated a digits-only test with
    # alphanumeric suffixes — so the rule is ANY digit in the head → fail-safe
    # to escalate. (A rare legitimate digit-head like '737-MAX' over-quarantines
    # — the safe direction, recoverable.) Spelled-out numbers ('forty-two') are
    # the same register (GLM evasion, 2026-07-22).
    if any(c.isdigit() for c in head):
        return False
    if head in _NUM_WORDS or all(p in _NUM_WORDS for p in head.split("-") if p):
        return False
    # ANY-TOKEN rule (Kimi nominalization class, 2026-07-22): a software/work
    # artifact ANYWHERE in the subject NP marks the agent register —
    # 'Verification of the MIGRATION is complete', 'the PIPELINE group',
    # 'test COVERAGE'. Head-only checking let the nominalized head launder the
    # software token into a domain read.
    if any(tok in SOFTWARE_HEADS for tok in _subject_tokens(t)):
        return False
    return True
