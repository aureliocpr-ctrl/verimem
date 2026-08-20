"""Answer-with-history — recall context that tells the TRANSITION story.

The gem capability (iter 42): competitors serve the latest value; we KEEP the
supersession chain (who replaced what, when, why — ``superseded_by`` +
``superseded_at`` + reason) and the unresolved-conflict ledger. This module turns
both into recall context, so an answer can say:

  * "changed from X to Y on <date>"  — the transition, not just the endpoint
    (HaluMem Memory-Conflict golds narrate transitions; a reconciled store that
    serves only the current value forfeits them — measured failure mode);
  * "conflicting records: A vs B (unresolved)" — an honest memory DECLARES what
    it is not sure about instead of silently picking a side.

Pure read-side, no LLM, no schema change: it composes ``SemanticMemory.recall``
+ ``direct_predecessors`` + ``ContradictionStore.list_unresolved_for_fact``.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

__all__ = ["extract_as_of", "fact_history", "history_line",
           "recall_with_history", "recall_as_of", "wants_history"]

#: Queries that benefit from the TRANSITION story (dates, change verbs, "as of",
#: tense markers) vs. plain point lookups. Routing exists because rich history
#: context has a measured abstention price on trap questions (1.000 -> 0.949,
#: docs/TRUST_MAINTENANCE.md): serve the story only where it pays. EN + IT.
_TEMPORAL_QUERY_RE = re.compile(
    r"\bas of\b|\bwhen\b|\bsince\b|\bstill\b|\bnow\b|\bcurrent|\bchange|"
    r"\bupdate|\bevolv|\btransition|\bpreviously\b|\boriginally\b|\binitially\b|"
    r"\bused to\b|\banymore\b|\bago\b|\bbefore\b|\bafter\b|\buntil\b|\bhistory\b|"
    r"\bfirst\b|\blast\b|\d{4}|january|february|march|april|may|june|july|"
    r"august|september|october|november|december|"
    # italiano: interrogativi/tempo/mutamento (il prodotto dichiara memoria
    # multilingue, G10 — il router non deve essere EN-only)
    r"\bquando\b|\bcambiat|\baggiornat|\bprima\b|\bdopo\b|\bancora\b|\badesso\b|"
    r"\bora\b|\battuale|\bfinora\b|\ball'epoca\b|\ballora\b|\bstoria\b|\bfa\b|"
    r"gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|"
    r"ottobre|novembre|dicembre", re.IGNORECASE)


def wants_history(query: str) -> bool:
    """Route a query to history-enriched recall iff its wording is temporal
    (dates, change verbs, as-of/tense markers, EN+IT). The cure for the
    measured trade: transition questions gain +16pp from the dated story while
    trap questions keep the pure abstention of the plain context."""
    return bool(_TEMPORAL_QUERY_RE.search(query or ""))


def _iso(ts: Any) -> str:
    """Epoch → ISO date (UTC); empty string on anything unparseable."""
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime(
            "%Y-%m-%d")
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


#: Query→as_of routing (cantiere attenzione 2026-07-08). Solo àncore
#: RETROSPETTIVE esplicite: "as of/on/by/until/before <data>". "after <data>"
#: apre un periodo successivo che il time-travel taglierebbe → NON instradato.
#: Misura che ha motivato il fix: su domande "as of 2025" il recall live
#: portava 6 fatti income [current since 2033-2043] in conflitto → l'answerer
#: si asteneva PUR AVENDO la risposta alla riga 2 del contesto.
_MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"])}
# 2026-08-06: i mesi italiani. `_TEMPORAL_QUERY_RE` trenta righe piu' su li ha
# dal giorno zero («EN+IT» nel suo docstring) e questa mappa, nata dopo per un
# caso inglese, non c'era mai tornata: due elenchi di mesi nello stesso file,
# uno bilingue e uno no.
_MONTHS.update({m: i + 1 for i, m in enumerate(
    ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
     "agosto", "settembre", "ottobre", "novembre", "dicembre"])})
# 2026-08-06: DE/FR/ES, per i registri di eventi datati — il buco DICHIARATO
# consegnando `date_menzionate`, e misurato prima di chiuderlo:
#     DE «12. Marz» / «20. April»       date viste []  e  []
#     ES «12 de marzo de 2026»          date viste []
#     FR «12 mars» / «20 avril»         date viste [(2026,3,12)]  e  []
# ⚠️ Il francese era PEGGIO degli altri due: `mars` passava per collisione del
# troncamento a tre (`mars[:3] == march[:3]`) e `avril` no, quindi una data
# vista e l'altra no — il discriminante taceva in modo IMPREVEDIBILE, secondo
# quali mesi capitavano nelle due frasi.
_MONTHS.update({m: i + 1 for i, m in enumerate(
    ["januar", "februar", "marz", "april", "mai", "juni", "juli",
     "august", "september", "oktober", "november", "dezember"])})
_MONTHS.update({m: i + 1 for i, m in enumerate(
    ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet",
     "aout", "septembre", "octobre", "novembre", "decembre"])})
_MONTHS.update({m: i + 1 for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
     "agosto", "septiembre", "octubre", "noviembre", "diciembre"])})
_MONTHS.update({m[:3]: i for m, i in list(_MONTHS.items())})


def _senza_accenti(parola: str) -> str:
    """`März` → `marz`, `août` → `aout`, `décembre` → `decembre`.

    Si normalizza invece di elencare le varianti accentate: una lista di
    varianti è una lista in più da tenere allineata, e questa casa ha già pagato
    tre volte per due elenchi che divergono. Così `_MONTHS` resta scritta in
    ASCII e accetta comunque come la gente scrive davvero.
    """
    return "".join(c for c in unicodedata.normalize("NFD", parola.casefold())
                   if not unicodedata.combining(c))
#: Le ancore RETROSPETTIVE, in EN e IT. ⚠️ «dopo»/«after» restano FUORI in
#: entrambe le lingue: aprono un periodo successivo che il time-travel
#: taglierebbe (esclusione deliberata del cantiere 07/08, e importarla in
#: italiano avrebbe significato riportare in una lingua un difetto che
#: nell'altra era stato evitato apposta).
#: «il» e «l'» ancorano solo perche' la regex esige una data subito dopo: da
#: soli sono gli articoli piu' comuni della lingua.
#: ⚠️ Il lookbehind non e' una rifinitura: senza, «dopo IL 2026-08-05» ancorava,
#: perche' in italiano l'ancora e' un articolo e l'articolo segue anche «dopo».
#: L'inglese non aveva questo problema — «after» non e' seguito da «the» — e la
#: prima stesura di questa cura ha importato in una lingua il difetto che
#: nell'altra era escluso per costruzione. L'ha presa il presidio
#: test_DOPO_non_ancora_niente_ne_in_IT_ne_in_EN.
_AS_OF_ANCHOR_RE = re.compile(
    r"(?<!dopo )(?<!dopo l)\b(?:as of|on|by|until|till|before"
    r"|alla data del|fino al|fino a|entro il|entro"
    r"|prima del|prima di|al|all'|il|l')\s*"
    r"(?:(\d{4})-(\d{2})-(\d{2})"                       # ISO 2025-09-04
    r"|([A-Za-zÀ-ÿ]{3,10})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})"  # Dec 21, 2025
    r"|(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-zÀ-ÿ]{3,10})\.?,?\s+(\d{4}))",  # 21 Dec 2025 · 5 agosto 2026
    re.IGNORECASE)


def extract_as_of(query: str | None) -> float | None:
    """Data esplicitamente ancorata da una domanda retrospettiva → epoch di
    FINE giornata UTC (i fatti asserted quel giorno contano come già veri),
    oppure ``None`` quando la domanda non àncora un punto temporale. Pure,
    conservativa: nessuna àncora inventata, "after <data>" escluso."""
    if not query:
        return None
    m = _AS_OF_ANCHOR_RE.search(query)
    if not m:
        return None
    try:
        if m.group(1):                      # ISO
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        elif m.group(4):                    # Month D, YYYY
            mo = _MONTHS.get(m.group(4).lower()[:3])
            if mo is None:
                return None
            d, y = int(m.group(5)), int(m.group(6))
        else:                               # D Month YYYY
            mo = _MONTHS.get(m.group(8).lower()[:3])
            if mo is None:
                return None
            d, y = int(m.group(7)), int(m.group(9))
        return datetime(y, mo, d, 23, 59, 59, tzinfo=timezone.utc).timestamp()
    except (ValueError, OverflowError):
        return None                          # data malformata: nessun routing


def _event_ts(fact) -> Any:
    """The fact's EVENT time (v13 ``asserted_at``, when it was said/true) with a
    ``created_at`` fallback — history dates must tell the story's time, not the
    ingest batch's wall clock."""
    ts = getattr(fact, "asserted_at", None)
    return ts if ts is not None else getattr(fact, "created_at", None)


def fact_history(sm, fact_id: str, *, max_hops: int = 5) -> list:
    """Predecessors of a live fact, most recent first — the main line of the
    story. At each hop the most recently retired direct predecessor is followed
    (N-to-1 merges keep only the main line; bounded, cycle-safe). Empty for a
    root fact or an unknown id."""
    out: list = []
    seen: set[str] = {fact_id}
    cursor = fact_id
    for _ in range(max(0, int(max_hops))):
        preds = [p for p in sm.direct_predecessors(cursor)
                 if p.id not in seen]
        if not preds:
            break
        head = preds[0]
        out.append(head)
        seen.add(head.id)
        cursor = head.id
    return out


def history_line(fact, history: list, *, disputes: list[str] | None = None) -> str:
    """Render one recall-context line: current value (+since date), then the
    transition story, then any DECLARED unresolved disputes."""
    prop = (getattr(fact, "proposition", "") or "").strip()
    since = _iso(_event_ts(fact))
    line = f"{prop} [current, since {since}]" if since else prop
    # 2026-07-30: questa riga e' il canale con cui un modello legge la memoria
    # e decide quanto fidarsi, e non diceva se il fatto fosse stato verificato.
    # Si marca SOLO quando il verdetto c'e': nel payload JSON il campo esce
    # sempre, anche null, perche' lo legge una macchina e distinguere «assente»
    # da «mai giudicato» costa zero — qui ogni token e' contesto tolto a chi
    # legge, e sul corpus vivo i fatti giudicati sono una minoranza, quindi
    # marcare l'assenza su quasi ogni riga sommergerebbe il segnale.
    _gs = getattr(fact, "grounding_score", None)
    if isinstance(_gs, (int, float)) and not isinstance(_gs, bool):
        line += f" [verificato: la fonte lo implica, {float(_gs):.1f}]"
    for p in history:
        p_prop = (getattr(p, "proposition", "") or "").strip()
        asserted = _iso(_event_ts(p))
        until = _iso(getattr(p, "superseded_at", None))
        span = ", ".join(x for x in (f"asserted {asserted}" if asserted else "",
                                     f"until {until}" if until else "") if x)
        line += f" | PREVIOUSLY: '{p_prop}'" + (f" ({span})" if span else "")
    for d in disputes or []:
        d = (d or "").strip()
        if d:
            line += f" | DISPUTED: conflicting record '{d}' (unresolved)"
    return line


def recall_as_of(sm, query: str, *, when: float, k: int = 5,
                 include_beliefs: bool = False) -> list[tuple]:
    """Time-travel recall over the bi-temporal store: the facts that were
    CURRENT at ``when`` — asserted on/before it (event time, ``asserted_at``
    with ``created_at`` fallback) and not yet superseded by then
    (``superseded_at`` after ``when`` counts as still-current at ``when``).

    "What did we know in March?" — point-in-time reconstruction for lawyers
    (state of knowledge at signature date), researchers (literature as of a
    date), real estate (the price back then). Composes deep recall (age hiding
    lifted — the past is old by definition) over the FULL archive including
    superseded rows, oversampled so the as-of filter doesn't starve top-k.
    Returns the same ``(Fact, score, ...)`` tuples recall returns."""
    when = float(when)
    # include_beliefs (Giro 2): time travel composes the live recall, so the
    # opt-in forwards — a flag silently dropped on one branch is the exact
    # asymmetry class the cold-fallback hunt (#3) documented.
    hits = sm.recall(query or "", k=max(k * 6, k), deep=True,
                     include_superseded=True, include_beliefs=include_beliefs)
    out: list[tuple] = []
    for hit in hits:
        f = hit[0]
        born = getattr(f, "asserted_at", None)
        born = float(born) if born is not None else float(
            getattr(f, "created_at", 0.0) or 0.0)
        if born > when:
            continue                      # not yet asserted at `when`
        died = _died_event_ts(sm, f)
        if died is not None and died <= when:
            continue                      # already superseded by `when`
        out.append(hit)
        if len(out) >= k:
            break
    return out


def _died_event_ts(sm, fact) -> float | None:
    """EVENT time a fact stopped being current: its successor's asserted_at —
    NOT ``superseded_at``, which is transaction time (a batch ingest today of a
    2024 history supersedes everything today, making every version look
    still-current at any past ``when`` — review 5-lenti C2). Fallback to
    ``superseded_at`` when the successor is unreadable (dangling link) or
    carries no event time. None = still current."""
    succ_id = getattr(fact, "superseded_by", None)
    tx = getattr(fact, "superseded_at", None)
    if not succ_id and tx is None:
        return None
    if succ_id:
        try:
            succ = sm.get(succ_id)
        except Exception:  # noqa: BLE001 — read enrichment, degrade to tx time
            succ = None
        if succ is not None:
            ev = _event_ts(succ)
            if ev is not None:
                return float(ev)
    return float(tx) if tx is not None else None


def recall_with_history(sm, query: str, *, k: int = 5, max_hops: int = 3,
                        with_disputes: bool = True,
                        as_of: float | None = None,
                        min_relevance: float | None = None) -> list[str]:
    """Live top-k recall, each hit enriched with its transition story and its
    declared unresolved conflicts. Best-effort: a history/dispute lookup error
    degrades that hit to its plain proposition — recall itself never breaks.

    ``as_of`` (epoch) — point-in-time context for retrospective questions:
    the hits come from the bi-temporal time-travel (``recall_as_of``) and each
    line is labelled ``[as of <date>]`` instead of the live transition story
    (a "[current since 2043]" label is exactly the noise that drowned the
    answer on as-of questions — measured, cantiere attenzione 2026-07-08).
    Pair with ``extract_as_of(query)`` for automatic routing."""
    if as_of is not None:
        stamp = _iso(as_of)
        out: list[str] = []
        for hit in recall_as_of(sm, query or "", when=float(as_of), k=k):
            f = hit[0]
            prop = getattr(f, "proposition", "")
            if not prop:
                continue
            line = f"{prop} [as of {stamp}]"
            # v2 (misurato: 14/21 residui erano gold di TRANSIZIONE): la
            # storia dei predecessori è ≤ as_of per definizione — legittima
            # nel punto temporale. Era il label live "[current since
            # <futuro>]" il rumore, non la transizione.
            try:
                for prev in fact_history(sm, f.id, max_hops=max_hops):
                    p_prop = getattr(prev, "proposition", "")
                    if p_prop:
                        span = _iso(_event_ts(prev))
                        line += (f" | PREVIOUSLY: '{p_prop}'"
                                 + (f" (asserted {span})" if span else ""))
            except Exception:  # noqa: BLE001 — enrichment must never break recall
                pass
            out.append(line)
        return out
    hits = sm.recall(query or "", k=k)
    # ⚠️ IL PAVIMENTO ARRIVA ANCHE QUI, e senza era il buco piu' visibile che
    # restasse sul canale degli agenti. Misurato, stesso store e stesso
    # istante, sulla domanda fuori tema «quale database usa il cluster di
    # produzione» con un pavimento che nulla puo' superare::
    #
    #     hippo_facts_recall    items=0   si astiene
    #     hippo_recall_history  n=3       «Il supporto risponde in 24 ore.»
    #
    # Due tool sulla STESSA superficie e sullo STESSO corpus, uno che si
    # astiene e uno che serve tre fatti scorrelati. E' la classe «la cura
    # nasce su una superficie e le altre restano indietro» — qui dentro la
    # stessa superficie — e la cura del pavimento su MCP e' del 02/08.
    #
    # Il filtro sta QUI e non nell'handler perche' questa funzione restituisce
    # righe gia' formattate: a valle lo score non esiste piu'. Un solo recall,
    # non due.
    if min_relevance:
        _pav = float(min_relevance)
        hits = [h for h in hits
                if float((h[1] if len(h) > 1 else 0.0) or 0.0) >= _pav]
    cs = None
    if with_disputes:
        try:
            from verimem.contradiction import ContradictionStore
            cs = ContradictionStore(sm.db_path)
        except Exception:  # noqa: BLE001 — disputes are an enrichment, never fatal
            cs = None
    lines: list[str] = []
    for f, *_ in hits:
        try:
            hist = fact_history(sm, f.id, max_hops=max_hops)
            disputes: list[str] = []
            if cs is not None:
                for c in cs.list_unresolved_for_fact(f.id):
                    other_id = (c.fact_b_id if c.fact_a_id == f.id
                                else c.fact_a_id)
                    other = sm.get(other_id)
                    if other is not None and not getattr(
                            other, "superseded_by", None):
                        disputes.append(getattr(other, "proposition", ""))
            lines.append(history_line(f, hist, disputes=disputes))
        except Exception:  # noqa: BLE001 — enrichment must never break recall
            lines.append(getattr(f, "proposition", ""))
    return lines


#: Le date NOMINATE dentro una proposizione — non quando è stata scritta, ma di
#: quale giorno PARLA. Serve al gate per sapere se due fatti sono due EVENTI o
#: due versioni dello stesso: un registro di consegne non è un valore che si
#: aggiorna.
#:
#: 🔑 IL DIFETTO CHE L'HA MOTIVATA, misurato scrivendo la stessa cosa in tre
#: forme (tre consegne in tre date, stesso topic)::
#:
#:     ISO «2026-03-12/04-20/05-30»          scritti 3 -> VIVI 1
#:     mese IT «12 marzo/20 aprile/30 maggio» scritti 3 -> VIVI 1
#:     mese EN «12 March/20 April/30 May»     scritti 3 -> VIVI 3
#:
#: La guardia che teneva vivi i tre inglesi è `_entita_diverse`, che riconosce
#: le entità dalle MAIUSCOLE: `March` e `April` diventano `proper` e distinguono
#: i fatti, `marzo` e `aprile` no, e una data ISO non ha nemmeno una parola.
#: L'inglese non era protetto meglio — era protetto per un accidente
#: ortografico. Qui il discriminante diventa la data in quanto tale.
_DATA_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATA_NUM_RE = re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b")
#: ⚠️ `(?:de |di |von )?` non è cosmesi: lo spagnolo scrive «12 DE marzo DE
#: 2026», e senza le particelle il pattern non vede la data — non per la lista
#: dei mesi, per ciò che sta in mezzo. Il `\.?` dopo il giorno copre il «12.»
#: tedesco. Allargare la lista senza allargare la FORMA sarebbe stato inutile.
_DATA_MESE_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\.?\s+(?:de |di |von |d'|of )?"
    r"([^\W\d_]{3,10})\.?,?\s+(?:de |di |von |of )?(\d{4})\b"
    r"|\b([^\W\d_]{3,10})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
    re.IGNORECASE)


def date_menzionate(testo: str | None) -> set[tuple[int, int, int]]:
    """Le date di cui il testo PARLA, come ``{(anno, mese, giorno)}``.

    Normalizzate in tuple e non in stringhe, così «2026-03-12», «12/03/2026»,
    «12 marzo 2026» e «12 March 2026» sono LA STESSA data: senza questo, il
    criterio direbbe che due scritture della stessa giornata sono due eventi
    diversi solo perché una è in italiano.

    I mesi vengono da ``_MONTHS``, l'unica mappa del modulo (EN+IT): una seconda
    copia divergerebbe, ed è la lezione che questa casa ha già pagato con tre
    elenchi di regole e due di negatori.
    """
    if not testo:
        return set()
    fuori: set[tuple[int, int, int]] = set()
    for m in _DATA_ISO_RE.finditer(testo):
        fuori.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in _DATA_NUM_RE.finditer(testo):
        # giorno/mese/anno: l'ordine europeo. Una data ambigua (05/08) resta
        # ambigua in entrambi i fatti che si confrontano, quindi il CONFRONTO
        # regge anche dove la lettura assoluta sbaglierebbe.
        fuori.add((int(m.group(3)), int(m.group(2)), int(m.group(1))))
    for m in _DATA_MESE_RE.finditer(testo):
        g, nome, a = ((m.group(1), m.group(2), m.group(3)) if m.group(1)
                      else (m.group(5), m.group(4), m.group(6)))
        _n = _senza_accenti(str(nome))
        mese = _MONTHS.get(_n) or _MONTHS.get(_n[:3])
        if mese:
            fuori.add((int(a), int(mese), int(g)))
    return fuori

# ── LA DATA COME VALORE, NON COME IDENTIFICATORE DELL'EVENTO ──────────────
#
# `date_menzionate` dice SE c'è una data. Questo dice a che cosa serve, e la
# distinzione è già enunciata nel commento del ramo DATE di `_entita_diverse`:
# «un registro di consegne NON è un valore che si aggiorna: è una serie di
# EVENTI». Un evento ACCADUTO è identificato dalla sua data e si accumula; un
# appuntamento PROGRAMMATO ha la data come attributo, e spostarlo lo aggiorna.
#
# ⚠️ SI CHIEDE UNA PROVA POSITIVA, non l'assenza della prova opposta. La forma
# «non è al passato ⇒ è programmato» è quella che viene in mente per prima ed è
# sbagliata in modo COSTOSO: una lingua che questi elenchi non conoscono non è
# al passato *per ignoranza nostra*, e con quella polarità un registro spagnolo
# o tedesco verrebbe FUSO — cioè si perdono fatti, che è il nodo più caro che
# abbiamo. Misurato il 20/08 su un banco a due popolazioni in quattro lingue::
#
#     polarità «non passato»    ES/DE registro   2 scritti -> VIVI 1   PERDITA
#     polarità «prova positiva» ES/DE registro   2 scritti -> VIVI 2   invariato
#
# Il prezzo di questa scelta è dichiarato: in una lingua non coperta la data
# programmata NON viene riconosciuta e il vecchio resta vivo accanto al nuovo.
# È un fatto obsoleto in più, non un fatto vero in meno.
_PASSATO_COMPIUTO = re.compile(
    r"\b(e['’]?\s*avvenut\w*|e['’]?\s*stat\w*|ha\s+avuto\s+luogo|fu\b|venne\b"
    r"|took\s+place|happened|occurred|has\s+been|have\s+been|was\b|were\b)",
    re.IGNORECASE)

_APPUNTAMENTO = re.compile(
    r"\b(is\s+on|is\s+scheduled|will\s+be\s+on|e['’]?\s+il\b|e['’]?\s+fissat\w*"
    r"|si\s+terrà|sarà\s+il)",
    re.IGNORECASE)

_UNA_DATA_QUALSIASI = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\s+\w+\s+\d{4}\b|\b\d{1,2}\s+\w+\b",
    re.IGNORECASE)


def _forma_programmata(testo: str | None) -> bool:
    """True solo con una prova POSITIVA che la data è un appuntamento.

    Lingue coperte: italiano, inglese. Altrove torna False — di proposito.
    """
    if not testo:
        return False
    return bool(_APPUNTAMENTO.search(testo)) and not _PASSATO_COMPIUTO.search(testo)


def stessa_frase_altra_data(a: str | None, b: str | None) -> bool:
    """Due frasi identiche tranne le date, ed entrambe un appuntamento.

    È volutamente STRETTA: «l'audit è stato spostato al …» non la attiva. Una
    riformulazione resta scoperta, e il costo è misurato — 2 dei 4 casi della
    popolazione «devono ritirare» restano rossi.
    """
    if not (_forma_programmata(a) and _forma_programmata(b)):
        return False
    na = re.sub(r"\s+", " ", _UNA_DATA_QUALSIASI.sub("<D>", a)).strip().lower()
    nb = re.sub(r"\s+", " ", _UNA_DATA_QUALSIASI.sub("<D>", b)).strip().lower()
    return na == nb
