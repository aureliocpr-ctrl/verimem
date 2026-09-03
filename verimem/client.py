"""verimem.Memory — the turnkey SDK: add()/search() in a few lines, WITH the moat on.

mem0/Zep expose ``add(messages)`` / ``search(query)`` and store whatever the extractor
emits. Engram's ``add()`` routes every write through the anti-confabulation gate (L1
lexical + optional L3 contradiction + optional L4 source-entailment) — so a fact that
isn't supported is downgraded/refused, not silently stored — and ``search()`` returns
the per-fact PROVENANCE (status, grounding_score) so the caller can trust-condition.
That gate is the capability no competitor's SDK has.

    from verimem import Memory
    mem = Memory()
    mem.add("The deployment uses PostgreSQL 16.")          # L1 lexical screen (always)
    hits = mem.search("which database?")                    # [{text, status, grounding_score, score}]

    mem.add(fact, source=src, ground=True)                  # + L4 source⊢fact entailment

Local SQLite, subscription/offline by default (no external key). The L1 lexical
screen runs on every add(); the L4 entailment moat (AUROC 0.971) runs per-call
when you pass ``source=`` and ``ground=True`` (needs a grounding_llm or the
local distilled CE, ENGRAM_GROUNDING_BACKEND=local).
"""
from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from .anti_confab_gate import run_validation_gate
from .flow_events import emit_flow as _emit_flow
from .semantic import Fact, SemanticMemory

_LOG = logging.getLogger(__name__)

#: Gate presets (packaging 2026-07-08): the gate's knobs existed for months
#: (validate off/fast/full, gate_mode downgrade/reject, ground L4) but you had
#: to know them. Three declarative modes; ``balanced`` = the historic default,
#: byte-identical. Any explicit per-call parameter always wins over the preset.
_GATE_PRESETS: dict[str, dict[str, Any]] = {
    "strict":     {"validate": "full", "gate_mode": "reject",    "ground": True},
    # balanced = the default. validate="full" (2026-07-19): the cross-fact contradiction
    # + same-source EVOLUTION moat is ON by default, not a dormant opt-in — a memory that
    # keeps a contradicted/stale value is the product's whole anti-thesis. The lexical L3
    # (numeric/version/date/negation, deterministic) carries this; the heavier NLI layer
    # stays opt-in (ENGRAM_SEMANTIC_CONFLICT). Drop to "fast" for a write-heavy path that
    # cannot afford the same-topic scan.
    "balanced":   {"validate": "full", "gate_mode": None,        "ground": True},
    "permissive": {"validate": "off",  "gate_mode": None,        "ground": False},
}

#: Grounding-verified answering (asse madre, anti-hallucination read-path). The
#: generator answers ONLY from retrieved facts; a local cross-encoder then
#: verifies the answer is entailed by one of them and abstains otherwise.
_ANSWER_SYSTEM = (
    "Answer the question using ONLY the provided facts. Be concise: just the "
    "answer, no preamble. If the facts do not contain the answer, reply exactly: "
    "NO ANSWER.")
#: Case-B resolution prompt (trust-conditioned answering). Measured on the
#: well-grounded-distractor bench (sonnet-5, 2026-07-16, n=12 + 2 unresolvable):
#: bare facts C=0.17/H=0.33 → tagged facts C=0.92/H=0.08, and it abstained 2/2
#: on same-metadata conflicts. Wording = the bench's resolution prompt PLUS one
#: trailing no-facts→NO ANSWER sentence (inert on the bench — every case's
#: answer IS in a fact — kept for parity with the v1 prompt's contract; critic
#: 2026-07-16 flagged the earlier "EXACTLY the bench's" comment as imprecise).
#: The verbose tie-rule variant measurably regressed (described the conflict
#: instead of the bare NO ANSWER), so don't "improve" this without re-measuring.
_ANSWER_TRUST_SYSTEM = (
    "Answer the question using ONLY the provided facts. Each fact is tagged "
    "[when | source | status]. If facts conflict, resolve by metadata: a "
    "'verified' fact beats an unverified one; a more recent fact beats an older "
    "one; a first-hand source beats hearsay. If the conflict cannot be resolved "
    "by the metadata, reply exactly: NO ANSWER. Be concise: just the answer. If "
    "the facts do not contain the answer, reply exactly: NO ANSWER.")


def _fact_trust_line(h: dict[str, Any]) -> str:
    """One tagged fact line for the trust-conditioned answer prompt:
    ``[when | source | status] text``. Honest formatting: the date comes from
    ``asserted_at`` (event time) falling back to ``created_at`` (always real);
    the source is the first source episode, else the verifiers, else the
    explicit word "unrecorded" — never an invented provenance."""
    import time as _time
    ts = h.get("asserted_at") or h.get("created_at")
    when = _time.strftime("%Y-%m-%d", _time.gmtime(float(ts))) if ts else "undated"
    src = h.get("source") or ", ".join(h.get("verified_by") or []) or "unrecorded"
    return f"[{when} | {src} | {h.get('status', 'model_claim')}] {h['text']}"
#: CE score above which the answer counts as fact-supported. Distinct from the
#: WRITE gate's 99.64 (Youden on source⊢fact hard negatives): the probe
#: 2026-07-16 measured answering-facts ~91-94 vs distractors ~1-3, so any cut in
#: (3, 90) separates; 40 is its own CE-scale cut (the write gate's claude-scale
#: WRITE_DEFAULT_THRESHOLD is 70 and unrelated). Recalibrate on the bench.
_ANSWER_VERIFY_THRESHOLD = 40.0

#: Pavimento dell'AVVISO `sotto_il_pavimento` — SEPARATO da quello del TAGLIO.
#: Misurato il 2026-09-02 sul corpus vivo (17 279 fatti): 80 query vere, 17
#: domande in tema senza risposta, 10 fuori tema.
#:
#:     soglia 0,8805 (il calibrato)  VERE marcate 47/80 (58,8%)  LONTANE 10/10  VICINE 17/17
#:     soglia 0,839  (questa)        VERE marcate  3/80 ( 3,8%)  LONTANE 10/10  VICINE  3/17
#:
#: Col calibrato l'avviso si accendeva su SEI RISPOSTE BUONE SU DIECI: un
#: segnale che esce quasi sempre non informa. ⚠️ NON E' GRATIS: la copertura
#: sulle domande vicine scende da 17/17 a 3/17 — si scambia copertura con
#: precisione, e i due numeri vanno detti insieme.
#: ⚠️ E' UN NUMERO FISSO E NON `auto` di proposito: tre stime del pavimento
#: calibrato sullo stesso store hanno dato 0,8797 · 0,8805 · 0,8853, cioe'
#: un'escursione di 5,6 millesimi contro una finestra utile di 13 (0,833-0,845).
#: Un parametro che oscilla per meta' della finestra che deve centrare non puo'
#: essere la soglia di un avviso.
#: ⛔⛔ E NON E' IL DEFAULT, PERCHE' LA MISURA DICE DI NO. Provato ad accenderlo
#: il 2026-09-02: ha rotto quattro controlli di
#: `test_il_recall_rispondeva_anche_quando_non_sapeva.py`, dove domande CON
#: risposta corretta hanno `score_migliore` `0,7715` e `0,603` — molto sotto
#: `0,839`. Su quel corpus la soglia segnalerebbe come «probabilmente non in
#: memoria» risposte che ci sono e sono giuste. ⇒ **le due popolazioni di
#: punteggi non vivono sulla stessa scala fra corpora diversi**, e un numero
#: fisso non e' trasferibile: sul corpus vivo le vere stanno a 0,858-0,90, su
#: quel banco a 0,60-0,77. Il pavimento ADATTIVO per corpus e' lavoro 0.8.0;
#: fino ad allora questo valore e' un OPT-IN documentato, non un default.
#: Chi ha il corpus giusto lo accende con `ENGRAM_AVVISO_MIN_RELEVANCE=0.839`
#: dopo aver rimisurato con `scripts/banco_avviso_marcatura.py`.
_AVVISO_FLOOR_MISURATO = 0.839
_AVVISO_FLOOR_VAR = "ENGRAM_AVVISO_MIN_RELEVANCE"


def _pavimento_avviso(pav_calibrato: float) -> float:
    """La soglia che l'AVVISO dichiara quando non c'e' stato un taglio.

    Senza la variabile restituisce il pavimento calibrato, cioe' il
    comportamento di sempre. Con la variabile impostata usa quel valore.

    ⛔ NON tocca `_auto_relevance_floor`, e il motivo e' un conteggio: quella
    funzione ha 10 chiamate in 6 file — il taglio di `search`, `explain`, il
    guardian, quattro punti del server MCP e la mappa dell'ignoranza. Spostarne
    il valore per curare l'avviso le muoverebbe tutte, ed e' l'incidente del
    2026-07-30: `max(floor, noise_floor)`, scritto, misurato e RITIRATO perche'
    aveva mutato la mappa dell'ignoranza.
    """
    import os

    grezzo = os.environ.get(_AVVISO_FLOOR_VAR, "").strip()
    if grezzo:
        from .env_num import finite_or
        return max(0.0, finite_or(grezzo, _AVVISO_FLOOR_MISURATO))
    return float(pav_calibrato)


def _frase_origine_soglia(soglia: float, calibrato: float) -> str:
    """COME SI CHIAMA il numero che l'avviso dichiara, in una frase sola.

    ⚠️ E' UNA SUPERFICIE UNICA DI PROPOSITO, usata da SDK, porta MCP e CLI.
    Il 03/09 la stessa forma — *una cura applicata a una superficie sola* — e'
    comparsa TRE volte in un pomeriggio: la soglia messa solo sull'SDK, poi
    curata solo su MCP, poi il TESTO dell'origine curato solo sulla CLI. Le
    prime due sono state curate a mano; questa funzione esiste perche' non ci
    sia una quarta.

    ⚠️ E NON E' COSMETICA: dire «calibrata su questo corpus» accanto a un valore
    che arriva da una variabile d'ambiente fa leggere all'utente una taratura
    del suo store dove c'e' una sua impostazione. E' una frase falsa dentro una
    ricevuta, in un prodotto cha ha come promessa di dire come fa a sapere le
    cose. Presidio: `tests/test_tre_porte_una_risposta_sul_pavimento.py`.
    """
    if float(soglia) == float(calibrato):
        return "calibrata su questo corpus"
    return f"impostata con {_AVVISO_FLOOR_VAR}"


#: Il default documentato di `ENGRAM_LONG_FACT_WARN_CHARS` (~512 token
#: conservativi). Oltre questa soglia l'embedder vede solo la testa del fatto.
_LONG_FACT_DEFAULT = 2000


def soglia_fatto_lungo() -> int:
    """La soglia oltre la quale un fatto eccede la finestra dell'embedder.

    UNA FUNZIONE SOLA, di proposito. Lo stesso numero e' letto anche in
    `semantic.py` (che emette l'avviso nel log): due letture dell'ambiente in
    due posti sono gia' due copie in attesa di divergere, ed e' la classe che
    questa casa paga di piu'. Quando `semantic.py` verra' toccato potra'
    chiamare questa invece di rileggere `os.environ` per conto suo.

    `0` disattiva l'avviso, come documentato; un valore illeggibile torna al
    default invece di far esplodere una scrittura.
    """
    import os
    try:
        return int(os.environ.get("ENGRAM_LONG_FACT_WARN_CHARS",
                                  str(_LONG_FACT_DEFAULT)))
    except ValueError:
        return _LONG_FACT_DEFAULT


#: Oltre quante righe il controllo del duplicato costa troppo per pagarlo a
#: OGNI scrittura. Misurato: 0.08 ms sul corpus reale (7950 righe), 9.89 ms a
#: 50k, 21.36 ms a 200k — e' una scansione, perche' `proposition` non ha
#: indice. `0` disattiva del tutto e in silenzio (scelta esplicita).
_DUP_CHECK_MAX_DEFAULT = 50_000


def soglia_controllo_duplicati() -> int:
    """Il tetto di righe sotto cui il controllo del duplicato esatto si fa.

    UNA FUNZIONE SOLA, come `soglia_fatto_lungo`: la stessa soglia letta in due
    posti sono gia' due copie in attesa di divergere.
    """
    import os
    try:
        return int(os.environ.get("ENGRAM_DUP_CHECK_MAX_FACTS",
                                  str(_DUP_CHECK_MAX_DEFAULT)))
    except ValueError:
        return _DUP_CHECK_MAX_DEFAULT


def _esiste_gia_identico(sm, testo: str, topic: str | None,
                         escludi: str | None = None) -> bool:
    """C'e' gia' un fatto SERVIBILE con questo identico testo in questo topic?

    Uguaglianza esatta, non similarita': il giudizio sulla similarita' e' un
    altro mestiere e ha gia' il suo strumento (`find_duplicate_facts`).

    ⚠️ SCANSIONE, non indice — `proposition` non ne ha uno. E' il motivo per
    cui il chiamante controlla prima quanto e' grande il corpus: 0.08 ms su
    7950 righe, 21.36 ms su 200 000.

    ⚠️ E NON SI USA `facts_fts` QUI, benche' sia indicizzato: misurato, su una
    FRASE INTERA la phrase query costa 5.33 ms contro 0.01 ms della scansione,
    perche' deve verificare l'adiacenza di decine di token. FTS vince sui
    termini corti e selettivi (un codice di record), perde sulle frasi lunghe.
    """
    import sqlite3
    try:
        con = sqlite3.connect(f"file:{sm.db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        # ⚠️ `escludi` E' IL FATTO APPENA SCRITTO, e senza di lui il controllo
        # trovava SE STESSO: ogni scrittura risultava un duplicato. Il codice
        # gira dopo la persistenza (li' c'e' la ricevuta da comporre), quindi
        # la riga nuova e' gia' nel database. Preso dai due presidi che
        # cadevano — «un fatto nuovo non porta avvisi» e «lo stesso testo in
        # un altro topic non e' un duplicato» — non dal caso che curavo.
        riga = con.execute(
            "SELECT id FROM facts WHERE proposition = ? AND topic IS ? "
            "AND superseded_by IS NULL AND status != 'quarantined' "
            "AND id IS NOT ? LIMIT 1",
            (testo, topic, escludi)).fetchone()
        return riga is not None
    except sqlite3.Error:
        return False
    finally:
        con.close()


def _remote_cls():
    """Lazy import hook (monkeypatchable in tests) for the thin client."""
    from .remote import RemoteMemory
    return RemoteMemory


def open_memory(path: Any = None, **kwargs: Any):
    """The ONE constructor consumers should use (architecture A, 2026-07-20).

    With ``VERIMEM_SERVER_URL`` set (+ ``VERIMEM_SERVER_KEY``), returns a
    :class:`verimem.remote.RemoteMemory` THIN client — no model load, no
    SQLite handle: N sessions share the one server that owns both. The server
    is probed once (/v1/health, ``VERIMEM_SERVER_TIMEOUT_S`` default 5s); an
    unreachable server falls back to the embedded :class:`Memory` with a
    logged warning — a memory consumer is never stranded. No env -> embedded,
    exactly as before.
    """
    import os as _os
    url = _os.environ.get("VERIMEM_SERVER_URL", "").strip()
    if url:
        key = _os.environ.get("VERIMEM_SERVER_KEY", "").strip()
        try:
            timeout = float(_os.environ.get("VERIMEM_SERVER_TIMEOUT_S", "5") or 5)
        except ValueError:
            timeout = 5.0
        try:
            rm = _remote_cls()(url, key, timeout_s=timeout)
            if rm.health():
                return rm
            _LOG.warning(
                "verimem server %s unreachable - falling back to embedded", url)
        except PermissionError:
            # Kimi audit F1: server reachable but REJECTS our key. Handing back
            # an embedded store would quietly write somewhere the caller never
            # asked for. Fail-closed: the caller wanted the shared server.
            _LOG.error(
                "verimem server %s rejected the API key - refusing to fall "
                "back to a local store (fix VERIMEM_SERVER_KEY, or unset "
                "VERIMEM_SERVER_URL to use the embedded store)", url)
            raise
        except Exception as exc:  # noqa: BLE001 -- fail-soft to embedded
            _LOG.warning(
                "verimem thin client init failed (%s) - falling back to "
                "embedded", type(exc).__name__)
    return Memory(path, **kwargs) if path is not None else Memory(**kwargs)


class Risultati(list):
    """I risultati di una ricerca, con l'avviso quando NESSUNO supera il pavimento.

    IL DIFETTO CHE LA MOTIVA (misurato): su 5 domande la cui risposta NON
    è nel corpus, `recall` risponde 5 volte su 5, con punteggi di grounding fino
    a 99.93 — risposte plausibili nella forma e scollegate nel merito, che un
    agente riceve come fatti verificati. Il pavimento che le separa **esiste ed
    è già usato** da `trust_report` ed `explain`, che si astengono; questa porta
    no.

    ⚠️ Dichiara e non taglia: su un banco il pavimento cadeva dentro il margine
    fra le due popolazioni (0 falsi tagli), su un altro cadeva **sopra** il
    minimo delle domande rispondibili (1 falso taglio su 5). La taratura dipende
    dal corpus, e un veto costerebbe un fatto vero dove un avviso costa un
    avviso.

    È una `list` VERA: chi non legge l'attributo non si accorge di niente, e
    `search` ha una quantità di consumatori che la iterano e ne fanno `len()`.
    """

    __slots__ = ("sotto_il_pavimento", "trattenuti", "letto_al_passato",
                 "tagliati_dal_pavimento")

    def __init__(self, iterable=(), *, sotto_il_pavimento=None,
                 trattenuti=None, letto_al_passato=None,
                 tagliati_dal_pavimento=None) -> None:
        super().__init__(iterable)
        #: ``{quando, quando_leggibile, nota}`` quando la domanda e' stata
        #: interpretata DA SOLA come una domanda sul passato, il filtro
        #: temporale ha svuotato il risultato e chi legge non ha modo di
        #: saperlo. ⚠️ CAMPO SEPARATO DA `sotto_il_pavimento` APPOSTA: sono due
        #: cause diverse dello stesso vuoto — la soglia che taglia e il tempo
        #: che non contiene nulla — e un solo segnale per due significati e'
        #: il difetto che questo modulo passa il tempo a curare.
        self.letto_al_passato = letto_al_passato
        #: ``{pavimento, score_migliore, nota}`` quando nessun risultato supera
        #: la soglia di rilevanza; ``None`` quando almeno uno la supera.
        self.sotto_il_pavimento = sotto_il_pavimento
        #: ``{pavimento, tagliati, rimasti, score_migliore, nota}`` quando il
        #: pavimento ha tolto dei fatti; ``None`` quando non ne ha tolto
        #: nessuno.
        #:
        #: ⚠️ NON E' UN DOPPIONE DI `sotto_il_pavimento`, ed e' nato da un
        #: difetto misurato: quell'avviso esce solo se il MIGLIORE e' sotto la
        #: soglia, cioe' solo quando il pavimento ha portato via TUTTO. Una
        #: lettura che perde quattro fatti su cinque e conserva il migliore non
        #: diceva niente — chi legge vedeva una risposta buona senza sapere che
        #: il materiale sotto era stato ridotto, e l'assenza del campo si legge
        #: come «non ha tagliato».
        #:
        #: ⚖️ I DUE SIGNIFICATI RESTANO SEPARATI: `sotto_il_pavimento` e'
        #: un'ASTENSIONE («non mi fido di niente di quello che ho»), questo e'
        #: un DATO («ho tolto N di M»). Nello stesso campo sarebbero un solo
        #: segnale per due significati, e l'astensione — che vale perche' e'
        #: rara — diventerebbe rumore.
        self.tagliati_dal_pavimento = tagliati_dal_pavimento
        #: ``{quanti, nota}`` quando il gate ha TRATTENUTO fatti sull'argomento
        #: chiesto; ``None`` quando non ce n'e' nessuno (2026-08-08).
        #:
        #: PERCHE'. Nel corpus di casa 746 fatti su 8999 sono in quarantena.
        #: Non tornano dalle letture, ed e' giusto — e' il loro mestiere, ed e'
        #: verificato su sei porte e sul briefing. Ma **il loro
        #: silenzio era indistinguibile dall'assenza**: chi ha scritto quel
        #: fatto crede di averlo salvato, chi legge crede che in memoria non ci
        #: sia niente.
        #:
        #: ⚠️ DICHIARA E NON MOSTRA. Non contiene il testo del fatto trattenuto:
        #: un fatto e' in quarantena perche' non ci si fida, e mostrarlo «per
        #: trasparenza» lo rimetterebbe in circolo dalla porta di servizio.
        self.trattenuti = trattenuti


def esito_del_moat(gate, warnings, *, source) -> str:
    """Che cosa ha fatto il moat, DERIVATO da cio' che il gate ha gia' detto.

    Non duplica la logica del gate: legge i layer che il gate ha emesso. Se un
    giorno cambiano quei nomi, il test dei quattro casi distinti lo prende.
    """
    _layers = {str(w.get("layer", "")) for w in warnings}
    if not source:
        return "not_run:no_source"
    if "L4-skipped" in _layers:
        return "not_run:no_judge"
    if gate.grounding_score is None:
        return "not_run:unknown"
    if "L4-grounding" in _layers:
        return "failed"
    return "passed"


def chi_ha_quarantinato(moat: str, warnings, *, agito=()) -> str:
    """Quale layer ha deciso la quarantena: ``moat`` / ``L1`` / ``gate``.

    ⚠️ LA PRECEDENZA NON SI TOCCA (la ragione sta per esteso al call site del
    write path): L1 esiste per intercettare le auto-affermazioni, e una fonte
    «che sostiene» puo' essere stata scritta dallo stesso agente che afferma.

    🔑 PERCHE' E' UNA FUNZIONE E NON TRE RIGHE COPIATE: la decisione ha DUE
    chiamanti — il write path di `Memory.add` e il comando `facts add`, che
    quarantina per conto suo. Finche' e' vissuta in uno solo dei due, i fatti
    scritti dall'altro entravano senza autore: misurato il 20/08 con un A/B a
    un fattore (stesso claim, stessa source, stesso punteggio 92.16) —
    `save` scriveva 'gate', `facts add` scriveva None. Sul corpus vivo erano
    1958 quarantinati senza autore su 2329.
    """
    # ⚠️ PRIMA DI TUTTO LO SCREEN DELLO STORE, e non e' un dettaglio di
    # ordine: quando il gate AMMETTE e uno screen dentro `store()` ribalta il
    # fatto, dire «gate» e' una attribuzione FALSA, non un'etichetta mancante —
    # racconta che ha deciso chi aveva detto di ammettere. Misurato sul
    # giornale: 34 scritture quarantinate su 1268 (2,7%) hanno agito cosi'.
    if "store-screen" in set(agito):
        return "store-screen"
    if moat == "failed":
        return "moat"
    # 2026-09-03 (lead): `L1-domain-precision-observe` e `L1-domain-advisory-
    # observe` INIZIANO con «L1» ma sono marcatori di osservazione («surfaced,
    # never a block reason»): da soli in ricevuta questo ramo rispondeva 'L1' e
    # nominava decisore chi aveva solo avvisato (misurato: 3 casi su 3). La
    # superficie unica della convenzione e' `_is_advisory_layer`, e questa
    # giuntura non ci passava. Presidio:
    # tests/test_un_marcatore_di_osservazione_non_e_mai_il_decisore.py
    if any(str(w.get("layer", "")).startswith("L1")
           and not _is_advisory_layer(w.get("layer", "")) for w in warnings):
        return "L1"
    # ⚠️ «gate» NON E' UN'ETICHETTA MANCANTE: E' UN'ETICHETTA CHE PORTA FUORI
    # STRADA. Il layer che ha deciso e' gia' in mano — `agito` sono i BLOCKING
    # layers (`_blocking_layers`, avvisi `*-observe` esclusi), non i warning
    # consultivi — e dire «gate» lo butta via. Misurato sul corpus il 21/08:
    #
    #     quarantinati nelle ultime 24h   25    di cui 'gate' generico  56%
    #     quarantinati negli ultimi 7g   136    di cui 'gate' generico  16%
    #
    # E il caso che l'ha fatto vedere, riprodotto alla porta:
    #
    #     claim   «Con il tetto attivo il committed e 176,6 MB.»
    #     moat    passed   grounding 99.89        <- il giudice APPROVA
    #     warning layer='L4.1'  «il claim afferma un valore che la fonte non
    #                            contiene: 6 mb, 176»
    #     scritto quarantined_by = 'gate'
    #
    # Il giorno dopo `quarantine_log(explain=True)` concludeva, in buona fede:
    # «causa NON REGISTRATA, e NON e' L4: il moat ha giudicato 99.89, cioe'
    # l'ha APPROVATA» — quando a decidere era stato L4.1. Un'etichetta generica
    # che si legge come un'assenza fa dedurre il contrario del vero.
    #
    # ⛔ LA PRECEDENZA NON CAMBIA: i tre rami sopra decidono come prima, e
    # `test_chi_ha_deciso_la_quarantena` continua a leggere 'L1' e 'moat'.
    # Qui si nomina soltanto cio' che finiva sotto 'gate'. L'ordine e' quello
    # di `_BLOCK_LAYER_PRIORITY`, lo stesso che sceglie il testo della ragione
    # in `_reason_from_warnings`, cosi' l'etichetta e la spiegazione non
    # possono indicare due layer diversi.
    for _p in _BLOCK_LAYER_PRIORITY:
        for _a in agito:
            if _a and str(_a).startswith(_p):
                return str(_a)
    for _a in agito:
        if _a:
            return str(_a)
    return "gate"


def persisti_chi_ha_quarantinato(db_path, fact_id: str, causa: str) -> bool:
    """Scrive la causa accanto al fatto. Rende Vero se ci e' riuscita.

    UPDATE mirato e non una colonna nell'INSERT: tocca solo i quarantinati, e
    se fallisce si perde la CAUSA, non il FATTO — un fatto scritto senza causa
    e' il comportamento di sempre, un fatto non scritto sarebbe un danno nuovo.
    """
    try:
        import sqlite3 as _sq
        with _sq.connect(str(db_path)) as _c:
            _c.execute("UPDATE facts SET quarantined_by=? WHERE id=?",
                       (causa, fact_id))
        return True
    except Exception:  # noqa: BLE001 — fail-open dichiarato sopra
        _LOG.debug("quarantined_by non persistito per %s", fact_id)
        return False


class Memory:
    """Turnkey persistent-memory client. Wraps SemanticMemory + the anti-confab gate."""

    def __init__(self, path: str | Path | None = None, *, grounding_llm: Any = None,
                 llm: Any = None, preset: str = "balanced",
                 repo_root: str | Path | None = None,
                 principal: str | None = None) -> None:
        if preset not in _GATE_PRESETS:
            raise ValueError(
                f"unknown gate preset {preset!r} — one of: "
                f"{', '.join(sorted(_GATE_PRESETS))}")
        self.preset = preset
        self._preset_defaults = _GATE_PRESETS[preset]
        #: P0 v9: identity stamped on every write. In-process the operator IS
        #: the trust boundary, so a declared identity is honoured; the REAL
        #: security value is at the MCP/gateway entrypoints, which stamp their
        #: own principal server-side and never accept one from the client.
        self._principal = principal or "sdk:local"
        #: ``repo_root`` scopes the verified_by hard-gate's I/O checks: a
        #: ``file:<path>:<line>`` provenance ref is verified ONLY when it resolves
        #: INSIDE this root (containment against traversal). Left ``None`` (the
        #: default, and the multi-tenant gateway's config) the gate performs NO
        #: file I/O — an absolute ref from untrusted input can neither read server
        #: files nor forge status="verified". A TRUSTED SDK caller passes its own
        #: project root to let genuine in-root file refs verify. (Security fix
        #: 2026-07-18: absolute refs used to bypass containment when root=None.)
        self.semantic = SemanticMemory(
            db_path=Path(path) if path else None,
            repo_root=Path(repo_root) if repo_root else None)
        # L'IMPRONTA SEGUE LO STORE APERTO, non la variabile d'ambiente.
        # `_store_fingerprint` deriva da `data_dir()`, e chi apre con
        # `Memory(path)` — circa nove chiamanti su dieci — scriveva altrove
        # ed emetteva eventi marcati «casa». Non serve architettura nuova:
        # `set_flow_context` esiste gia' e il gateway lo usa per `tenant` e
        # `surface`, e `_ambient` applica l'overlay come ULTIMA cosa,
        # quindi sovrascrive anche `store`.
        # ⚠️ LIMITE NOTO: e' un overlay di CONTESTO, quindi con due store
        # aperti nello stesso contesto vince l'ultimo costruito. Copre il
        # caso dominante (uno store per volta) e non il multiplexing.
        try:
            from .flow_events import impronta_di_percorso, set_flow_context
            set_flow_context(store=impronta_di_percorso(self.semantic.db_path))
        except Exception:  # noqa: BLE001 — un tag non rompe un'apertura
            pass
        #: trust odometer: persistent counters of what the gate did (admitted /
        #: quarantined / rejected / abstained) — same DB file, fail-open, no PII.
        from .trust_ledger import TrustLedger
        self._ledger = TrustLedger(self.semantic.db_path)
        #: extraction LLM for ``add(messages)`` — anything with
        #: ``.complete(system, messages, **kw)``; optional otherwise.
        self.llm = llm
        #: The moat is ON by default (preset balanced ground=True, 2026-07-17).
        #: A dedicated grounding_llm wins; else the general llm doubles as the
        #: grounding judge, so Memory(llm=x) turns the moat ON at judge quality
        #: (AUROC 0.98) with no extra wiring. With NEITHER, and no local CE, the
        #: gate has no judge and fail-opens (admits) — the flip never breaks a
        #: judge-less user.
        self.grounding_llm = grounding_llm or llm

    # ---- write -------------------------------------------------------------
    def add(
        self, content: str | list[dict], *, topic: str = "user",
        source: str | None = None,
        verified_by: list[str] | None = None, validate: str | None = None,
        ground: bool | None = None, gate_mode: str | None = None,
        # `asserted_at` non e' solo il tempo dell'evento per il time-travel:
        # decide come viene INSTRADATA una scrittura successiva sulla stessa
        # fonte. Senza, le due si ordinano per momento di SCRITTURA e la piu'
        # recente vince sempre — una correzione supersede in silenzio invece
        # di andare al giudice come conflitto
        # (`supersession_policy.classify_write_relation`, che dichiara «any
        # ambiguity -> conflict» e in assenza di questo campo non ha
        # l'ambiguita' da risolvere). Misurato il 30/08: valorizzato su 0
        # fatti su 15.978, ed e' esposto da tutte e tre le porte — la
        # conseguenza qui sopra non era dichiarata in nessuna.
        asserted_at: float | None = None, conversation_id: str | None = None,
        user_name: str | None = None,
        purpose: str | None = None,
        principal: str | None = None,
        meta_narrative: bool = False,
        lineage_to: list[str] | None = None,
        confidence: float | None = None,
        chronicle: bool = False,
        # 2026-07-30: il canale MCP li accettava e questo no, quindi sul corpus
        # vivo erano NULL su tutti e 6457 i fatti — e su di loro si reggono due
        # dei quattro trigger di hippo_justified_audit («stale» e la cascata,
        # che il tool descrive come la capacita' che nessun prodotto offre).
        # Non erano trigger silenti perche' il corpus e' sano: erano
        # irraggiungibili dal canale che lo riempie.
        valid_until: float | None = None,
        derives_from: list[str] | None = None,
        # 2026-08-05: stessa storia dei due qui sopra, nona istanza della
        # classe. `gate_router` esiste dal mandato del 10/07 e risponde alla
        # domanda «di CHI e' questo claim?»: un documento ingerito non e'
        # l'agente che si vanta, quindi i detector L1.x — che gradano la
        # sincerita' dell'AGENTE — non hanno giurisdizione. Il router era
        # cablato su 3 detector in semantic.py e i 14 layer L1.8-L1.21 non ci
        # passavano; e questa firma non lo esponeva affatto, cosi' la strada
        # che il gate stesso SUGGERISCE a chi scrive («set
        # writer_role='external_content'») era irraggiungibile: sul corpus
        # vivo, external_content = 0 fatti su 8217.
        writer_role: str | None = None,
    ) -> dict[str, Any]:
        """Store ``text`` AFTER the anti-confab gate. Returns
        ``{stored, id?, status, grounding_score, warnings, advice}``.

        Two gate layers, honest about what runs by default:

        * **L1 lexical screen — always on.** Unsupported "it works / verified /
          completed" self-claims are downgraded to ``quarantined`` (hidden from
          default recall) with no LLM call (~13 ms).
        * **L4 source⊢fact entailment — the moat, ON by default.** With the
          ``balanced`` preset (the default) ``ground`` defaults to True, so a
          write carrying a ``source`` is admitted only if the source actually
          *entails* the fact — catching confabulated *inferences* L1 can't.
          Needs a judge: the ``grounding_llm`` you built ``Memory`` with (or the
          general ``llm``, which doubles as the judge), or the local distilled
          CE (``ENGRAM_GROUNDING_BACKEND=local``). Turn it off for one call with
          ``ground=False``. Without a source OR a judge, L4 is skipped and
          ``grounding_score`` is ``None`` — fail-open, so the flip never blocks
          a judge-less user.

        ``gate_mode='reject'`` makes a below-threshold write return
        ``stored=False`` (default ``'downgrade'`` stores it quarantined).

        ``content`` may also be a **conversation** (``list`` of
        ``{"role","content"}`` messages): it is routed through the gated
        conversation ingestion — atomic extraction + consolidation, every fact
        through the gate, conversation provenance. Needs the ``llm`` the
        client was built with. ``asserted_at`` (epoch seconds) stamps the
        EVENT time (bi-temporal v13: when it was said/true — drives
        reconciliation age-gaps and answer-with-history)."""
        if isinstance(content, list):
            if self.llm is None:
                raise ValueError(
                    "add(messages) needs an extraction llm: Memory(..., llm=...)")
            from .conversation_ingest import ingest_conversation
            # the moat runs on the ingest path too (2026-07-17): the preset's
            # ground default (balanced=True) quarantines extraction confabs the
            # dialogue doesn't entail. Per-call ground= still wins.
            _ground = self._preset_defaults["ground"] if ground is None else ground
            res = ingest_conversation(
                self.semantic, content, llm=self.llm,
                conversation_id=conversation_id or "sdk",
                topic=topic if topic != "user" else "conversational/ingested",
                asserted_at=asserted_at, embed="sync",
                user_name=user_name, ground=_ground)
            # Review 2026-07-09 #1: the ingest path was INVISIBLE to the trust
            # odometer while its facts showed up in the store — ledger and
            # store contradicted each other inside one /v1/stats response.
            # Count from the facts' FINAL stored status (post store-screens).
            self._ledger_ingest_result(res, topic=topic)
            return res
        text = (content or "").strip()
        if not text:
            return {"stored": False, "status": "empty", "warnings": [], "advice": "empty text"}
        # preset defaults fill only what the call left unspecified (None):
        # an explicit per-call parameter always wins over the preset.
        if validate is None:
            validate = self._preset_defaults["validate"]
        if gate_mode is None:
            gate_mode = self._preset_defaults["gate_mode"]
        # Captured BEFORE the preset fills it in: only here does the difference
        # between "the caller asked for entailment verification" and "the preset
        # defaults to on" still exist. One line further down the two are the
        # same True and the gate cannot tell them apart — which is why the
        # advisory below is emitted here and not in the gate.
        _ground_explicitly_requested = ground is True
        if ground is None:
            ground = self._preset_defaults["ground"]
        # Continuity narrative lane (2026-07-23): meta_narrative declares a
        # retrospective session checkpoint. It relaxes ONLY the L1.x
        # self-claim family (category error on a chronicle); injection/L3/L4
        # are untouched and the row is stamped meta_narrative=1 +
        # writer_role='user' so listings can tell chronicle from screened
        # claim. In-process callers only — network handlers must never wire
        # a client-supplied flag into this parameter.
        # P0 evidence-before-belief (ciclo 2c): the gate can only ask whether
        # the cited evidence is independent if it is told WHO writes and WHERE
        # the documents live. The store is lazy — a write that never reaches
        # the question opens no connection.
        from .evidence_independence import LazyDocumentStore
        gate = run_validation_gate(
            proposition=text, verified_by=verified_by, topic=topic, agent=self,
            validate=validate, source=source, grounding_llm=self.grounding_llm,
            ground_write=ground or None, gate_mode=gate_mode, asserted_at=asserted_at,
            narrative_l1_skip=meta_narrative,
            writer_role=writer_role,
            # Superficie in-process (SDK/CLI): chi arriva qui puo' comunque
            # passare validate="off", una leva strettamente piu' forte. Il
            # canale MCP NON deve inoltrarlo — presidio in
            # test_anti_confab_gate_mcp_provenance.py.
            provenance_trusted=True,
            claimant=principal or self._principal,
            documents=LazyDocumentStore(),
        )
        warnings = list(gate.warnings)

        # Il verdetto per l'evento sta in UNA funzione sola
        # (`flow_events.emit_write`), che lo deriva dal punteggio: qui
        # basta il punteggio. Prima questa closure lo componeva a mano, e
        # la stessa composizione mancava del tutto sulla porta MCP —
        # 141 scritture ad agosto, ZERO eventi (misurato il 2026-08-07). Una
        # regola scritta due volte diverge; scritta una volta e mai
        # chiamata dalla terza porta, sparisce.
        from .flow_events import emit_write as _emit_write
        _gs_evt = getattr(gate, "grounding_score", None)


        # The mirror of the gate's own L4-skipped advisory ("say so out loud,
        # NEVER a silent skip"), for the case it never covered: a judge is
        # reachable but the write carries NO source, so L4 has nothing to check
        # the fact against and does not run. Ordinary unsourced writes stay
        # quiet — most writes have no source and annotating them all would be
        # wallpaper — but a caller who passed ground=True asked for entailment
        # verification, and being given none WITHOUT being told is how "not
        # checked" gets read as "checked and fine". Advisory only: the
        # disposition below is untouched.
        if _ground_explicitly_requested and not source:
            warnings.append({
                "layer": "L4-no-source",
                "reason": "ground=True was requested but the write carries no "
                          "source — there is nothing to check the fact "
                          "against, entailment NOT verified",
                "advice": "pass source='<the evidence text>' to run the moat. "
                          "verified_by records WHO vouches for a fact and does "
                          "not run this check.",
            })
        action = gate.action
        # IL GATE SU SOURCE-TRUST E' STATO RIMOSSO IL 2026-09-02 (voto G10, 4 SI
        # su 3 richiesti). Non perche' il meccanismo fosse sbagliato: perche' non
        # ha mai avuto materiale su cui lavorare. Misurato sul corpus vivo:
        # 0 scritture marcate su 17 279, 156 sorgenti tutte al valore iniziale
        # 0.500, tabella `source_trust` con 0 righe (l'omonima `trust_ledger` ne
        # ha 10 880 — due registri, nomi simili, e solo quello delle FONTI e'
        # vuoto). La causa sta un piano piu' sopra: `source_trust_observe`,
        # l'API pubblica che alimenta il libro, e' chiamata da 4 banchi e 5 test
        # e da ZERO porte del prodotto (0 in `cli.py`, 0 in `mcp_server.py`).
        # Finche' nessuna porta la chiama il registro resta vuoto, e questo gate
        # calcola sempre lo stesso risultato: nessuna fonte sotto soglia.
        # ⚠️ `canonical_source`, `SourceTrustBook` e il resto di
        # `source_trust.py` RESTANO: sono usati per altro (3 importatori
        # prendono `canonical_source`, 1 prende `get_book`). Se un giorno il
        # registro viene alimentato, questo gate si riscrive in ~25 righe con la
        # misura in mano.
        _layers = _blocking_layers(warnings)
        if action == "reject":
            self._record_trust("rejected", layers=_layers, topic=topic)
            _emit_write(stored=False, status="rejected", fact_id="",
                        topic=str(topic), layers=_layers,
                        grounding_score=_gs_evt)
            _adj = _adjudication(gate, disposition="rejected",
                                 verified_by=verified_by, warnings=warnings)
            self._audit_record(_adj, topic=topic, proposition=text, fact_id=None,
                               judge=getattr(gate, "judge", None), layers=_layers,
                               verified_by=verified_by)
            return {"stored": False, "status": "rejected", "warnings": warnings,
                    "advice": gate.advice, "grounding_score": gate.grounding_score,
                    "adjudication": _adj}
        fact = Fact(proposition=text, topic=topic, verified_by=verified_by or [],
                    grounding_score=gate.grounding_score, asserted_at=asserted_at,
                    grounding_span=getattr(gate, "grounding_span", None),
                    writer_principal=principal or self._principal,
                    confidence_tier=_confidence_tier(
                        gate.grounding_score, getattr(gate, "judge", None),
                        getattr(gate, "threshold", None)))
        # LA PROVENIENZA DICHIARATA NON SI BUTTA VIA (2026-08-04). Il testo di
        # `source` serve al moat per l'entailment e poi spariva: la tabella
        # `facts` non ha una colonna `source`, e `source_signature` — l'unico
        # campo di provenienza che sopravvive — nessuno la popolava (26 fatti
        # su 6075 in tutto il corpus). Conseguenza misurata su un registro
        # pazienti: «Rossi pesa 70 kg» e «Bianchi pesa 95 kg», due cartelle
        # diverse, stesso topic -> il secondo RITIRA il primo come
        # `same-source evolution`, perche' senza verified_by entrambi
        # canonicalizzano su "user".
        # L'impronta e' un hash: la source puo' essere un log di migliaia di
        # righe, e qui serve solo distinguere due origini, non rileggerle.
        if source and not getattr(fact, "source_signature", None):
            import hashlib
            fact.source_signature = "sha256:" + hashlib.sha256(
                " ".join(str(source).split()).encode("utf-8")).hexdigest()[:16]
        if confidence is not None:
            fact.confidence = float(confidence)
        if valid_until is not None:
            fact.valid_until = float(valid_until)
        if derives_from:
            fact.derives_from = [str(x) for x in derives_from if str(x).strip()]
        if lineage_to:
            fact.lineage_to = [str(x) for x in lineage_to if str(x).strip()]
        # Prima del blocco meta_narrative, che sovrascrive di proposito: quella
        # e' la superficie operatore in-process e resta l'ultima parola.
        if writer_role and str(writer_role).strip():
            fact.writer_role = str(writer_role).strip()
        if meta_narrative:
            fact.meta_narrative = True
            fact.writer_role = "user"  # in-process operator surface
        if action == "downgrade":
            fact.status = "quarantined"
        elif chronicle:
            # Orchestration/inter-agent CHRONICLE (2026-07-23): the
            # proposition is an ATTRIBUTED third-party quotation ("[agent
            # X → Y] ...") — a record that agent X said something, NOT
            # verimem asserting the content is true. Store it as
            # ``user_belief``: HIDDEN from default recall (the moat
            # promise holds — you never recall an agent's unverified
            # assertion AS a fact) yet not quarantined, so benign
            # coordination chatter is archived rather than censored (the
            # live channel is the inbox; memory is the audit trail).
            # Adversarial review convergence (glm+deepseek, findings 1+2):
            # this single classification defuses BOTH the throughput
            # collapse of full-L1-gating and the laundering of a visible
            # model_claim. A later injection screen inside store() can
            # still flip it to quarantined — the screen is lane-agnostic.
            fact.status = "user_belief"
        self.semantic.store(fact, embed="sync", purpose=purpose)
        # UNO SCREEN DENTRO `store()` HA PARLATO: lo si porta nella ricevuta.
        # `store()` scrive il verdetto sul fatto (stesso veicolo di
        # `routed_to`, letto tre righe piu' sotto) e qui diventa un warning
        # come quelli del gate — perche' chi riceve la ricevuta non deve
        # sapere QUALE modulo ha deciso per capire cosa gli e' successo.
        # Prima di questa riga lo screen dell'iniezione era l'unico layer che
        # quarantina senza dire ne' il perche' ne' il rimedio.
        _screen = getattr(fact, "screen_verdict", None)
        if _screen:
            warnings = list(warnings) + [_screen]
        # A write with a DECLARED telemetry signal (purpose tag, or a topic
        # matching ENGRAM_TELEMETRY_PREFIXES) is ROUTED inside store(): the
        # fact never entered the curated corpus, and the receipt must say
        # so — "admitted" here would be false (found by the fresh-install
        # product probe, 2026-07-20).
        _routed = getattr(fact, "routed_to", None)
        if _routed:
            self._record_trust("routed_telemetry", layers=None, topic=topic)
            _emit_write(stored=True, status="routed_telemetry",
                        fact_id=str(fact.id), topic=str(topic),
                        layers=["admission-route"], grounding_score=_gs_evt)
            _adj = _adjudication(gate, disposition="routed_telemetry",
                                 verified_by=verified_by, warnings=warnings)
            self._audit_record(_adj, topic=topic, proposition=text,
                               fact_id=str(fact.id),
                               judge=getattr(gate, "judge", None),
                               layers=["admission-route"],
                               verified_by=verified_by)
            return {"stored": True, "status": "routed_telemetry",
                    "routed_to": _routed, "warnings": warnings,
                    "advice": gate.advice,
                    "grounding_score": gate.grounding_score,
                    "adjudication": _adj}
        # Review 2026-07-09 #2/#3: count AFTER store, from the fact's FINAL
        # status — screens inside store() (injection screen: default ON) can
        # flip a fact to quarantined, and the odometer must
        # report what HAPPENED, not the gate's intention. Layer attribution
        # only when a layer actually ACTED: gate downgrade -> its layers;
        # store-screen flip -> "store-screen"; clean admit -> none (advisory
        # warnings are in the add() response, not in by_layer).
        if fact.status == "quarantined":
            _hit_layers = _layers if action == "downgrade" else ["store-screen"]
            self._record_trust("quarantined", layers=_hit_layers, topic=topic)
        else:
            _hit_layers = []
            self._record_trust("admitted", layers=None, topic=topic)
        # layers in the flow event = which defense actually ACTED (same
        # attribution as the ledger): the Live Engine Room lights the real
        # stage, not a generic box. Metadata only, never fact content.
        # `judged` accanto a `status`: senza, nel feed un fatto verificato
        # 99.9 e uno MAI GIUDICATO sono entrambi "ADMITTED" — cioè la
        # distinzione che questo prodotto vende sparisce proprio dalla
        # pagina che dovrebbe mostrarla. Il flag è esplicito perché un
        # `grounding_score: null` si legge distrattamente come zero, e
        # zero è un verdetto — il contrario dell'assenza di verdetto.
        #
        # ⚠️ ERRATA 2026-08-05: i commit `49096224` e `cc367071` motivano
        # questo campo con «le scritture che arrivano mentre il moat si
        # scalda entrano non giudicate». Era stata ricavata leggendo
        # una STRINGA di `verimem doctor`, poi MISURATA, e cade: 4
        # thread simultanei su store vergine aspettano tutti 42.60s e
        # ricevono tutti un verdetto (0 NULL su 4) — il caricamento è
        # sincrono con lock, quella finestra non esiste sul canale SDK.
        # Quello che regge, e basta a giustificare il campo: i
        # mai-giudicati ESISTONO (6 NULL su 250 scritti in un giorno, 4 dei
        # quali con una source_signature) e il feed non li distingueva.
        # La causa resta ignota, ed è meglio dirlo che spiegarla a caso.
        _emit_write(stored=True, status=str(fact.status),
                    fact_id=str(fact.id), topic=str(topic),
                    layers=_hit_layers, grounding_score=_gs_evt)
        _disposition = ("quarantined" if fact.status == "quarantined"
                        else "admitted")
        # Same-source EVOLUTION supersession (ENGRAM_SUPERSEDE_SAME_SOURCE, classified by
        # the gate): retire the OLD value(s) the new write supersedes — but ONLY when the
        # new write was actually ADMITTED. If a store-screen quarantined it, superseding
        # the old would lose BOTH (opus critic guard). supersede() keeps the old row for
        # lineage; it just drops out of the default recall filter.
        _superseded: list[str] = []
        # Since the helm landed, each real retirement carries its undo handle
        # (semantic.supersede snapshots pre-op). Surfacing the handle HERE —
        # in the add() receipt — is what turns "this write retired another
        # fact" from an invisible mutation into a reversible one for every
        # SDK/MCP/gateway caller (indicator #1, 2026-08-04).
        _superseded_undo: dict[str, str] = {}
        # admit-guard: retire the old ONLY if the new write was admitted AND is actually
        # retrievable from the CURATED store — store() can divert a non-quarantined write
        # elsewhere (admission-gate telemetry route sets no 'quarantined' status), and
        # retiring the old against a diverted new would drop BOTH from curated recall
        # (opus final critic). get() short-circuits after the cheap checks.
        # GRADED-ADMISSION GUARD (critic 514cdec3 counterexample, FAIL vote,
        # empirically reproduced): an admitted-but-GRADED write (grounding
        # shortfall admitted as low-confidence under ENGRAM_GRADED_ADMISSION)
        # must NOT unlock supersession — otherwise a score-12 claim retires a
        # grounded value from curated recall, a net loss the hard-quarantine
        # path prevented. Both values stay recallable; supersession remains
        # for writes that earned admission on their own evidence.
        _graded_admit = any(str(w.get("layer", "")).endswith("-graded")
                            for w in warnings)
        if (_disposition == "admitted" and not _graded_admit
                and not chronicle  # a hidden chronicle must not retire a curated fact
                and getattr(gate, "supersede_fact_ids", None)
                and self.semantic.get(fact.id) is not None):
            for _old_id in gate.supersede_fact_ids:
                try:
                    _sup_res = self.semantic.supersede(
                        _old_id, fact.id,
                        principal=principal or self._principal,
                        reason="same-source evolution")
                    _superseded.append(_old_id)
                    if _sup_res.get("undo_op_id"):
                        _superseded_undo[_old_id] = _sup_res["undo_op_id"]
                except Exception as exc:  # noqa: BLE001 — a supersede failure must not break the write
                    # surface it: the new fact is admitted but the old was NOT retired —
                    # the stale-beside-new state the feature exists to prevent (opus critic).
                    _LOG.warning("same-source supersede of %s failed (new %s admitted, old "
                                 "NOT retired): %s", _old_id, fact.id, exc)
        # Review-queue backpressure (P0 ciclo 2, punto 4): a write that JOINS
        # the quarantine/review backlog says how deep that backlog is. Only
        # this write — annotating an admitted one would be noise on a page
        # that has nothing to do with the queue, and noise is how a signal
        # gets ignored. Read is memoised per window and never raises.
        if fact.status == "quarantined":
            from .review_queue import backpressure_warning
            _bp = backpressure_warning(self.semantic.db_path)
            if _bp:
                warnings.append(_bp)
        _adj = _adjudication(gate, disposition=_disposition,
                             verified_by=verified_by, warnings=warnings)
        # The audit row also records a defense that STOOD DOWN (critic probe 3
        # on e41991e): an admitted-under-ENGRAM_L1_DOMAIN_ADVISORY write must be
        # distinguishable from one under an armed gate. Audit-only — the trust
        # ledger and the flow event keep their acted-only attribution.
        _stood_down = [layer for w in warnings
                       if (layer := str(w.get("layer", "")))
                       == "L1-domain-advisory-observe"]
        self._audit_record(_adj, topic=topic, proposition=text, fact_id=fact.id,
                           judge=getattr(gate, "judge", None),
                           layers=_hit_layers + _stood_down,
                           verified_by=verified_by)
        # L'AVVISO SUL FATTO TROPPO LUNGO ARRIVA A CHI SCRIVE. Esisteva già, ed
        # è ottimo — dice la dimensione, il limite e cosa fare invece — ma
        # `semantic.py` lo emette con `_LOG.warning`, quindi finiva nel log e
        # NON nella ricevuta. Misurato da utente su un fatto di 4476 caratteri:
        # il log lo diceva, `warnings` era vuoto.
        #
        # Il commento che accompagna quella guardia la chiama «non-silent
        # over-window guard»: è stata scritta apposta per non essere
        # silenziosa, ed era silenziosa esattamente per il chiamante.
        #
        # Perché conta: oltre la finestra dell'embedder si embedda solo la
        # TESTA, quindi il recall semantico non vede il resto. È la ragione per
        # cui il protocollo di casa prescrive di spezzare i fatti lunghi o di
        # usare `verimem index` — e chi scrive non poteva saperlo dal prodotto.
        # IL DUPLICATO IDENTICO SI DICE A CHI SCRIVE, ALLA SECONDA VOLTA.
        # Misurato da utente: tre `add` dello stesso testo -> 3 righe, 3
        # servibili, e il recall rende la stessa frase TRE VOLTE senza che il
        # prodotto lo abbia mai detto. Lo stesso costo, misurato dall'altro
        # lato: `slot=35 sprecati_da_duplicati=7` in un recall reale.
        #
        # Il meccanismo c'era già — `find_duplicate_facts`, esposto come
        # `hippo_find_duplicate_facts` — ma è BATCH e fa Jaccard: si usa DOPO,
        # per ripulire. Al momento della scrittura non lo chiamava nessuno.
        #
        # ⚠️ QUI SI GUARDA SOLO L'IDENTICO ESATTO, e non è pigrizia: la
        # similarità è un giudizio (e `find_duplicate_facts` esiste per
        # quello), l'uguaglianza no. Stesso testo E stesso topic — la stessa
        # frase sotto «magazzini» e sotto «verbali» sono due contesti, non una
        # svista.
        #
        # ⚠️ E IL COSTO DECIDE LA FORMA. È una scansione (`proposition` non ha
        # indice): 0.08 ms sul corpus reale, 9.89 ms a 50k, 21.36 ms a 200k.
        # Sopra la soglia NON si fa — ma si DICHIARA di non averlo fatto:
        # saltarlo in silenzio sarebbe la stessa classe di difetto che questo
        # prodotto passa la giornata a curare. Un indice su `proposition` lo
        # renderebbe O(1) (0.127 ms a 200k, 286 ms per costruirlo), ma è una
        # modifica di schema.
        # UN TOPIC CON SPAZI AI BORDI È UN SILO INVISIBILE. Misurato da utente:
        #     count(topic='az/mag')  = 1     count(topic='az/mag ') = 1
        #     count(topic=' az/mag') = 1     count(topic='AZ/MAG')  = 1
        # quattro varianti, quattro contenitori. E le due superfici hanno
        # semantiche diverse: `topic_prefix` normalizza il case e non gli
        # spazi, il topic esatto non normalizza nulla.
        #
        # ⚠️ NON SI NORMALIZZA, ed è una scelta: sul corpus vero il danno non
        # esiste ancora (5716 topic distinti, 0 con spazi ai bordi, 0
        # collisioni), e `topic` è la chiave usata anche per l'isolamento fra
        # tenant. Riscrivere una chiave del genere alle spalle di chi scrive,
        # per un difetto con zero istanze misurate, è un rischio sproporzionato.
        # Si dichiara e la decisione resta sua.
        if topic and topic != topic.strip():
            warnings = [*warnings, {
                "layer": "topic_spazi",
                "reason": (f"il topic {topic!r} ha spazi ai bordi: è un "
                           f"contenitore diverso da {topic.strip()!r} e i due "
                           f"non si trovano a vicenda"),
                "advice": ("se non era voluto, riscrivi il fatto con il topic "
                           "senza spazi — il topic è una chiave e non viene "
                           "corretto in automatico"),
            }]
        _dup_max = soglia_controllo_duplicati()
        if _dup_max:
            try:
                _n_righe = self.semantic.count()
            except Exception:  # noqa: BLE001 — un conteggio fallito non blocca
                _n_righe = 0
            if _n_righe <= _dup_max:
                if _esiste_gia_identico(self.semantic, text, topic,
                                        escludi=fact.id):
                    warnings = [*warnings, {
                        "layer": "duplicate",
                        "reason": ("un fatto identico è già servibile in questo "
                                   "topic: la memoria ne servirà due copie"),
                        "advice": ("se è una conferma va bene così; se è una "
                                   "svista, `forget` una delle due — "
                                   "`hippo_find_duplicate_facts` le elenca"),
                    }]
            else:
                warnings = [*warnings, {
                    "layer": "duplicate_check_skipped",
                    "reason": (f"il controllo dei duplicati non è stato fatto: "
                               f"{_n_righe} fatti superano il tetto {_dup_max} "
                               f"e la verifica è una scansione"),
                    "advice": ("alza ENGRAM_DUP_CHECK_MAX_FACTS, oppure crea un "
                               "indice su facts(proposition) — rende il "
                               "controllo immediato a qualunque scala"),
                }]
        _soglia = soglia_fatto_lungo()
        if _soglia and len(text or "") > _soglia:
            warnings = [*warnings, {
                "layer": "long_fact",
                "reason": (f"il fatto è di {len(text)} caratteri, oltre la "
                           f"finestra dell'embedder (~512 token): il recall "
                           f"semantico ne vedrà solo la testa"),
                "advice": ("spezzalo in fatti brevi e autonomi, oppure indicizza "
                           "il documento con `verimem index` / DocumentIndex — "
                           "chunked e citato"),
            }]
        # IL VERDETTO DEL MOAT, SEMPRE E IN CHIARO — i quattro casi che la
        # regola O3 promette («leggi il campo `moat` della ricevuta, che dice
        # quale dei quattro casi è») e che la ricevuta NON AVEVA: le sue chiavi
        # erano ['adjudication','advice','grounding_score','id','status',
        # 'stored','warnings'].
        #
        # ⚠️ IL COSTO DI QUEL SILENZIO, misurato: `grounding_score = None`
        # significa DUE cose — «non c'era una fonte» (corretto) e «c'era una
        # fonte e non ho giudicato» (difetto) — e dal corpus non si
        # distinguono. Sul corpus vero, 250 scritture in un giorno: 6 NULL, di
        # cui 2 senza fonte (giusti) e **4 con una fonte dichiarata**. Tre
        # istanze hanno bruciato CINQUE ipotesi su quei sei fatti (il gate
        # sotto carico, delegate-only, la raffica, il verified_by vuoto, la
        # source condivisa): tutte cadute, perché il verdetto esisteva al
        # momento della scrittura e non veniva conservato.
        #
        # 🔑 E IL CASO CHE CONTA È `not_run:no_judge`: quando il giudice non è
        # raggiungibile il gate emette `L4-skipped` e **il fatto entra lo
        # stesso come model_claim**, cioè ammesso. Il fail-open è la scelta
        # giusta (non si blocca una scrittura perché il modello non è su
        # disco), ma chi scrive crede di aver messo un fatto verificato e ha
        # messo un claim.
        #
        # Si DERIVA da ciò che il gate ha già detto, non si duplica la sua
        # logica: se un giorno cambiano i nomi dei layer, il test dei quattro
        # casi distinti lo prende.
        _moat = esito_del_moat(gate, warnings, source=source)
        # E CHI HA DECISO LA QUARANTENA. Trovato e poi ampliato:
        #     moat passa + parola L1 : moat=passed  gs=96.810  QUARANTINED
        #     moat passa, niente L1  : moat=passed  gs=99.278  QUARANTINED
        # Anche il secondo — una fonte che sostiene il fatto al 99,278 — viene
        # trattenuto: il MOAT dice «verificato» e uno screen lessicale lo
        # scavalca. Si lega a una misura vicina (il 90,2% della quarantena del
        # corpus viene dallo screen, 1728 su 1915) e alla precisione ~40% di L1.
        #
        # ⚠️ LA PRECEDENZA NON SI TOCCA, e non è pigrizia: L1 esiste per
        # intercettare le auto-affermazioni («ho verificato che funziona»), che
        # sono LA confabulazione tipica di un agente — e una fonte «che
        # sostiene» può essere stata scritta dallo stesso agente che afferma.
        # Ribaltare la precedenza aprirebbe esattamente quella porta, ed è una
        # decisione di prodotto, non una cura di notte.
        #
        # Si dichiara CHI ha deciso: una quarantena per contenuto falso e una
        # per scelta di parole sono due cose diverse, e chi riceve la ricevuta
        # non aveva modo di distinguerle.
        if fact.status == "quarantined":
            _out_qb = chi_ha_quarantinato(_moat, warnings,
                                          agito=_hit_layers)
            # …E SI SCRIVE, non solo si dice. Fino a qui la causa viveva SOLO
            # nella ricevuta: la vede chi scrive, nell'istante in cui scrive, e
            # un minuto dopo non esiste piu' da nessuna parte (le colonne di
            # stato erano [created_at, status, grounding_score], e
            # `audit_mutations` e' action-only per le operazioni distruttive).
            # Il costo di non averla: due fatti quarantinati in produzione con
            # grounding 99.96 e sei tentativi di riproduzione che non hanno
            # chiuso la domanda a cui questa riga risponde subito.
            # UPDATE mirato e non una colonna nell'INSERT a 25 parametri: tocca
            # solo i quarantinati, e se fallisce si perde la CAUSA, non il
            # FATTO — un fatto scritto senza causa e' il comportamento di
            # sempre, un fatto non scritto sarebbe un danno nuovo.
            persisti_chi_ha_quarantinato(
                self.semantic.db_path, fact.id, _out_qb)
        else:
            _out_qb = None
        _out = {
            "moat": _moat,
            **({"quarantined_by": _out_qb} if _out_qb else {}),
            "stored": True, "id": fact.id, "status": fact.status,
            "grounding_score": gate.grounding_score,
            "warnings": warnings, "advice": gate.advice,
            "adjudication": _adj,
        }
        # UN LAYER HA TRATTENUTO NONOSTANTE IL GIUDICE. Il campo esisteva
        # gia' — derivato in `flow_events.emit_write` e scritto nel journal —
        # ma non arrivava a chi scrive: la ricevuta diceva `moat: passed`,
        # `grounding_score: 99`, `status: quarantined` e lasciava dedurre da
        # soli che due decisori non erano d'accordo.
        # DERIVATO, mai accettato dal chiamante, e con la STESSA
        # `judged_true` del journal e della vista sul corpus: una soglia
        # scritta due volte diverge, e `None` non e' mai giudicato — un
        # giudice ancora `warming` non produce un «nonostante il giudice».
        # DESCRITTIVO, NON VALUTATIVO: `True` non vuol dire «il gate ha
        # sbagliato». Puo' essere il layer ad avere ragione — un claim quasi
        # identico alla fonte prende 99.9 dal giudice semantico e solo il
        # layer lessicale vede che la cifra e' 160 invece di 162.
        # Condizionale come `quarantined_by`: una scrittura ordinaria non
        # cambia forma.
        from .retirement_log import judged_true as _judged_true
        if (str(fact.status) in ("quarantined", "rejected")
                and _judged_true(gate.grounding_score)):
            _out["withheld_despite_judge"] = True
        if _superseded:
            _out["superseded"] = _superseded
            if _superseded_undo:
                _out["superseded_undo_ops"] = _superseded_undo
        return _out

    # ---- read --------------------------------------------------------------
    def search(self, query: str, k: int = 5, *, deep: bool = False,
               # "auto" E NON None/False: il ROUTING c'era, funzionava anche in
               # italiano, e non si accendeva mai perche' nessuna superficie
               # passava "auto". Misurato sul listino che cambia tre volte
               # (100 -> 120 -> 150), il difetto isolato cosi':
               #     quanto costava a GENNAIO -> «150 euro» rilevanza 0.8457
               #     quanto costava ad APRILE -> «150 euro» rilevanza 0.8382
               # cioe' una risposta SBAGLIATA presentata come giusta, mentre
               # `history()` aveva le tre versioni ordinate e leggibili. Il
               # prodotto dichiara «abstention over hallucination» e sull'asse
               # del tempo non lo applicava.
               # ⚠️ "auto" INSTRADA, non accende: chiede a `wants_history` /
               # `extract_as_of`, che su «quanto costa OGGI» rispondono di no.
               # E' la differenza fra curare il difetto e far pagare a tutti il
               # costo della catena.
               # 📌 TERZA VOLTA SU QUESTA SUPERFICIE, e la prima e' documentata
               # in mcp_server.py:7627 (ce_gate inerte -> 0/5 astensioni; acceso
               # -> 4/5 con ZERO astensioni false). Stessa forma, stessa cura:
               # si ribalta il default DOPO aver misurato che la popolazione
               # opposta non paga.
               as_of: float | str | None = "auto",
               with_history: bool | str = "auto",
               history_hops: int = 5,
               include_beliefs: bool = False,
               min_relevance: float | str | None = None
               ) -> list[dict[str, Any]]:
        """Recall the top-k facts for ``query``, each with its provenance — the
        differentiator: ``status`` + write-time ``grounding_score`` so a caller can
        prefer/assert grounded facts and hedge low-trust ones.

        * ``deep`` — archaeology: also search dormant memories the freshness
          half-life hides from the default view (integrity guards stay).
        * ``as_of`` (epoch seconds) — time travel: what was CURRENT at that
          moment (asserted by then, not yet superseded). No competitor has it.
          ``as_of="auto"`` routes per query: an explicit retrospective anchor
          in the question ("as of / on / by <date>") activates time travel at
          that date; without one the live recall is byte-identical. Measured
          (routed_asof_ab.json): 10/31 previously-wrong anchored questions
          flip correct, abstention 21/21 intact — the live "[current]" story
          on as-of questions was drowning the answer in future facts.
        * ``with_history`` — each hit carries its transition story
          (``history: [{text, asserted_date, until}]``) from the supersession
          chain: "changed from X to Y on <date>". ``"auto"`` routes per query
          (``wants_history``): temporal wording gets the story (+16pp measured
          on transition questions), plain lookups keep the lean context whose
          abstention on trap questions is pure (1.000 vs 0.949 — the measured
          price of always-on history, docs/TRUST_MAINTENANCE.md).
        * ``history_hops`` — quanti predecessori mostrare. Il limite serve (una
          catena di duecento schede riversata in un contesto è un'altra forma
          dello stesso danno), ma fino al 2026-08-04 era MUTO e non si poteva
          toccare: `fact_history` ha `max_hops=5` di default e questa
          superficie — la porta pubblica — non lo passava mai. Su un registro
          di 25 schede uscivano cinque voci e nessun segno delle altre
          diciannove. Ora il taglio si dichiara (``history_truncated: True``) e
          il limite si può alzare.
        * ``include_beliefs`` (anti-sycophancy read-side) — opt unverified USER
          assertions (``status='user_belief'``, produced by the ingest's
          ``tag_beliefs``) back into the result. They are OUT of the default
          view so the memory never serves an uncorroborated user claim back as
          truth; a caller opting in sees ``status`` on each hit and must caveat
          accordingly. Narrow: un-hides beliefs only.
        * ``min_relevance`` — the retrieval floor below which this surface
          returns NOTHING instead of the nearest neighbours. ``"auto"`` lets the
          store calibrate it on itself (scrambled-probe quantile, the same floor
          the ignorance map uses); a float applies as given. ``None`` (default)
          takes ``ENGRAM_MIN_RELEVANCE`` ONLY IF SET — the switch documented as
          working "across every surface", which until 2026-08-02 reached only
          ``explain``. An unset variable leaves this surface exactly as it was;
          see ``relevance_floor.env_floor`` for why the default is not adopted
          here."""
        if min_relevance is None:
            from .relevance_floor import env_floor_if_set
            min_relevance = env_floor_if_set()
        if min_relevance == "auto":
            min_relevance = self._auto_relevance_floor()
        if with_history == "auto":
            from .temporal_context import wants_history
            with_history = wants_history(query)
        # ⚠️ SI RICORDA CHE LA DATA E' STATA DEDOTTA, NON PASSATA. Chi scrive
        # `as_of=<istante>` sa di aver chiesto il passato; chi scrive una
        # domanda in cui compare una data NO — e la regola che la estrae accetta
        # l'articolo «il», quindi «cosa e' successo IL 18 luglio», dove la data
        # e' il SOGGETTO, diventa «cosa sapevamo AL 18 luglio». Se poi a quella
        # data non c'era nulla, il chiamante riceve `[]` senza un motivo.
        _as_of_dedotto = False
        if as_of == "auto":
            from .temporal_context import extract_as_of
            as_of = extract_as_of(query)
            _as_of_dedotto = as_of is not None
        # IL DEGRADO SI CONTA PRIMA E DOPO. Quando l'encoder non risponde entro
        # il budget, `SemanticMemory.recall` cade sul ramo keyword e assegna
        # `score 0.0` a TUTTI i risultati — un numero che non è una misura di
        # somiglianza, ma che ne ha la forma. Il contatore esisteva già
        # (`_recall_degraded_count`, nato apposta perché «il degrado cold-encode
        # era invisibile al caller») e nessuno lo leggeva da qui.
        _deg_prima = getattr(self.semantic, "_recall_degraded_count", 0) or 0
        _scartati_dal_tempo = 0
        if as_of is not None:
            from .temporal_context import recall_as_of
            hits = recall_as_of(self.semantic, query, when=float(as_of), k=k,
                                include_beliefs=include_beliefs)
            _scartati_dal_tempo = int(
                getattr(self.semantic, "_as_of_scartati", 0) or 0)
        else:
            hits = self.semantic.recall(query, k=k, deep=deep,
                                        include_beliefs=include_beliefs)
        _degradato = (getattr(self.semantic, "_recall_degraded_count", 0) or 0
                      ) > _deg_prima
        out: list[dict[str, Any]] = []
        for f, score, *_rest in [h if len(h) >= 2 else (h[0], 0.0) for h in hits]:
            # per-fact provenance for trust-conditioned answering (case-B
            # wire, measured 2026-07-16): event time, transaction time, first
            # source episode, and who verified. Raw values — the caller
            # formats; None == genuinely unknown, never invented.
            #
            # This USES `_fact_view` instead of restating it. It used to be a
            # hand-written copy of eight of its nine keys, and the ninth is
            # how the copy was found: `superseded_by` was added to the shared
            # view and `search` — the surface everyone actually calls — went
            # on without it, while `_fact_view`'s own docstring promised "the
            # SAME provenance surface everywhere". Two copies drift, and this
            # one already had. `score` and `confidence_tier` stay here because
            # they belong to the QUERY, not to the fact: no fact carries a
            # score until something ranks it.
            #
            # It matters most exactly where a retracted fact is meant to come
            # back: `as_of` time travel returns what was current THEN, so its
            # hits are superseded by construction — and `deep` reaches the
            # dormant ones. Without the field those arrive looking live.
            item = {
                **self._fact_view(f),
                "score": round(float(score), 4),
                "confidence_tier": getattr(f, "confidence_tier", None),
            }
            if with_history:
                from .temporal_context import _event_ts, _iso, fact_history
                # `until` PASSA DA `_iso` COME `asserted_date`. Nella prima
                # stesura usciva grezzo, e la riga di storia mostrava mezzo
                # cartello in epoch:
                #     (2026-08-02 → 1785663692.5640569)
                # due date della stessa parentesi in due formati diversi, e
                # `_iso` importata quattro righe sopra. `temporal_context` la
                # converte da sempre; questa superficie, nata oggi, no.
                #
                # `None` resta `None` e non diventa la stringa vuota che `_iso`
                # darebbe: un fatto ancora valido NON ha una data di fine, e
                # «nessuna fine» non è «fine sconosciuta».
                # ⚠️ SI CHIEDE UN SALTO IN PIÙ DI QUELLI CHE SI MOSTRANO. Il
                # limite serve — una catena di duecento schede riversata in un
                # contesto è un'altra forma dello stesso danno — ma prima il
                # taglio era MUTO: su un registro di 25 schede uscivano cinque
                # voci e nessun segno che ce ne fossero altre diciannove, e chi
                # legge conclude che la storia sia quella.
                #
                # Il salto in più costa un hop, non un conteggio della catena:
                # se torna, il taglio c'è stato e si dichiara. `max_hops` era
                # il default di `fact_history` che questa superficie — la porta
                # pubblica — non passava mai, quindi non poteva né alzarlo né
                # sapere di averlo.
                hops = max(0, int(history_hops))
                catena = fact_history(self.semantic, item["id"],
                                      max_hops=hops + 1)
                if len(catena) > hops:
                    item["history_truncated"] = True
                    catena = catena[:hops]
                item["history"] = [
                    {"text": getattr(p, "proposition", ""),
                     "asserted_date": _iso(_event_ts(p)),
                     "until": (None if getattr(p, "superseded_at", None) is None
                               else _iso(p.superseded_at) or None)}
                    for p in catena
                ]
            out.append(item)
        # Il taglio sta QUI e non prima del ranking: `score` appartiene alla
        # query, non al fatto, e nessun fatto ne ha uno finché qualcosa non lo
        # ordina. Filtrare a valle tiene il pavimento fuori dal recupero, che
        # resta identico — quello che cambia è solo se il risultato si serve.
        # ⚠️ IL PAVIMENTO NON SI APPLICA A UN RANKING DEGRADATO, ed è un errore
        # di categoria non un caso limite: sul ramo keyword lo `score` è 0.0 per
        # costruzione — non «nessuna somiglianza», ma «somiglianza NON MISURATA»
        # — e confrontarlo con una soglia di somiglianza taglia tutto.
        #
        # Misurato il 2026-08-05, stesso store, stessa domanda:
        #     a caldo      [0.8995] risposta giusta · min_relevance=0.5 -> 1
        #     degradato    [0.0]    STESSA risposta · min_relevance=0.5 -> 0
        #
        # Per un prodotto la cui promessa di punta è «abstention over
        # hallucination» questo è il modo peggiore di sbagliare: si astiene per
        # un motivo che non ha nulla a che vedere con l'evidenza — l'encoder era
        # lento — e chi legge non ha modo di distinguerlo da un'astensione vera.
        # Trovato usando il prodotto sul corpus vero: `[0.00]` su ogni riga.
        # ⚠️ IL PRIMA DEL TAGLIO SI CONSERVA, e il motivo e' il pezzo (i) del
        # blocco CURA-PAVIMENTO: senza questi due valori l'avviso a valle non
        # puo' dire ne' QUANTI ne ha tagliati ne' quanto valeva il migliore —
        # `out` e' stato riassegnato e il prima e' perso. Il massimo ricalcolato
        # dopo varrebbe `0.0` su una lista vuota, cioe' un numero INVENTATO: il
        # punteggio migliore esisteva, era solo sotto la soglia.
        _n_prima = len(out)
        _best_prima = max((float(i.get("score") or 0.0) for i in out),
                          default=0.0)
        if min_relevance and not _degradato:
            pavimento = float(min_relevance)
            out = [i for i in out if float(i.get("score") or 0.0) >= pavimento]
        _tagliati = _n_prima - len(out)
        # E IL DEGRADO SI DICHIARA, sempre: un ranking per parole chiave che si
        # spaccia per un ranking per somiglianza è la stessa classe di difetto
        # che questo prodotto passa la notte a curare.
        if _degradato:
            for item in out:
                item["ranking"] = "keyword"
        # I FATTI NASCOSTI SU QUEL RECORD. Non cambia cosa si serve né come si
        # ordina: aggiunge un campo che dice «su S-007 c'è un fatto che non ti
        # sto dando». Serviva perché senza, su un registro di 25 schede, questa
        # superficie risponde S-025 a una domanda su S-007 con score 0.8786 —
        # sbagliata e confidente — e nulla nella risposta lo lascia sospettare.
        #
        # LA RICERCA SI FA UNA VOLTA SOLA, sulla QUERY. È informazione della
        # domanda, non del singolo risultato: farla per hit moltiplicherebbe le
        # query per k senza cambiare una virgola dell'esito.
        #
        # Il taglio sta DOPO `min_relevance`: su ciò che è già stato scartato
        # non si spende una SELECT.
        if out:
            from .hidden_records import SqliteRows, hidden_records_for
            nascosti = hidden_records_for(
                SqliteRows(self.semantic.db_path), query=query, served="")
            if nascosti:
                for item in out:
                    item["hidden_records"] = [
                        h for h in nascosti if h["text"] != item.get("text")]
        # ⚠️ IL `best` DEL JOURNAL SI PRENDE DAL PRIMA DEL TAGLIO, e il motivo e'
        # scritto trenta righe piu' su, nel commento del pezzo (i): «il massimo
        # ricalcolato dopo varrebbe 0.0 su una lista vuota, cioe' un numero
        # INVENTATO». Quella cura ha sistemato l'AVVISO e ha lasciato indietro
        # QUESTA riga, che calcolava lo stesso numero sulla stessa lista gia'
        # riassegnata (`out` e' filtrato alla riga del pavimento, sopra).
        #
        # Misurato sul journal reale, entrambe le parti (`events.jsonl` +
        # `.jsonl.1`): 2499 `flow.recall`, di cui 254 vuote (10.2%), e TUTTE E
        # 254 con `best = 0` — per costruzione, non per misura. Chi analizza il
        # journal per capire perche' una lettura non ha risposto legge quegli
        # zeri come «non ha trovato nulla», mentre parte di quelle letture
        # AVEVA trovato ed e' stata tagliata.
        #
        # 🔑 Due punti calcolavano lo stesso valore, uno e' stato curato e
        # l'altro no: `_best_prima` e `_tagliati` esistono gia' e sono in
        # scope: la cura non aggiunge stato, usa quello che c'e'.
        # ⚠️ I 254 zeri gia' scritti restano: questa riga vale da qui in avanti.
        _emit_flow("flow.recall", kind="search", n=len(out),
                   best=round(float(_best_prima), 4),
                   tagliati=_tagliati)
        # «NON LO SO» DETTO SULLA PORTA CHE LA GENTE APRE.
        #
        # Misurato su un corpus aziendale controllato: su 15 domande
        # RISPONDIBILI il primo posto e' giusto 14 volte — il retrieval
        # funziona — ma su 5 domande SENZA risposta `recall` risponde 5 volte su
        # 5, con `grounding_score` fino a 99.93. Risposte peggiori del silenzio:
        # plausibili nella forma, scollegate nel merito, e chi le riceve vede un
        # fatto verificato. Il prodotto dichiara «abstention over
        # hallucination», e questa porta non lo applicava — mentre
        # `trust_report` ed `explain` si astengono da sempre, con lo STESSO
        # pavimento. Terza asimmetria fra porte in due giorni.
        #
        # ⚠️ SI DICHIARA, NON SI TAGLIA, e la ragione e' una misura che
        # contraddice quella che ha motivato la cura:
        #     banco A  rispondibili min 0.8757 · pavimento 0.8689 -> 0 falsi tagli
        #     banco B  rispondibili min 0.8489 · pavimento 0.8491 -> 1 falso taglio su 5
        # La taratura del pavimento dipende dal corpus: come veto perderebbe un
        # fatto vero, come avviso costa un avviso. Chi vuole il taglio ha
        # `min_relevance`, che continua a funzionare esattamente come prima.
        # PEZZO (i) — L'AVVISO MANCAVA PROPRIO DOVE SERVE DI PIU'.
        #
        # La condizione era `if out and _pav and …`: con `out` VUOTO l'avviso
        # non usciva, cioe' **quando il pavimento aveva tagliato tutto**. Il
        # commento qui sopra dice «SI DICHIARA, NON SI TAGLIA … chi vuole il
        # taglio ha `min_relevance`»: le due funzioni sono pensate come
        # alternative, e nel caso `min_relevance="auto"` si ANNULLAVANO a
        # vicenda — chi chiedeva il taglio automatico perdeva la dichiarazione,
        # che era il punto. RED di produzione (corpus reale, pavimento 0.8781
        # dopo il ricalcolo automatico delle 02:52 del 2026-08-31): una domanda
        # senza risposta serviva ZERO fatti e TACEVA.
        #
        # ⚠️ Il difetto era INVISIBILE prima di quel ricalcolo: col pavimento a
        # 0.0000 il filtro non scattava e `out` non si svuotava mai. C'era da
        # sempre, e nessun banco poteva vederlo.
        #
        # 🔑 DUE `out` VUOTI, DUE SIGNIFICATI, e il criterio li separa senza
        # bandiere: `_best_prima` e' `0.0` quando la ricerca non ha trovato
        # NULLA (nessun taglio, nessun avviso) ed e' `> 0` quando qualcosa
        # c'era ed e' stato tagliato. Dire «ho tagliato tutto» dove non si e'
        # tagliato niente sarebbe il difetto opposto: rumore al posto del
        # silenzio.
        # ⚠️⚠️ LA TERZA FACCIA, e la lettura del codice NON la mostrava: l'avviso
        # era ancorato al pavimento AUTO, non a quello che ha davvero TAGLIATO.
        # Misurato sul banco: su uno store piccolo `_auto_relevance_floor()`
        # vale `0.0`, quindi con `min_relevance=0.99` che taglia tutto la
        # condizione `if _pav and …` resta FALSA e la porta tace lo stesso. E
        # quando entrambi sono attivi (auto 0.8781, esplicito 0.5) l'avviso
        # riporterebbe **la soglia che non ha morso**. ⇒ La soglia da dichiarare
        # e' quella APPLICATA: `min_relevance` se ha tagliato, il pavimento
        # calibrato quando non si e' tagliato niente e i risultati si servono
        # comunque.
        try:
            _pav = self._auto_relevance_floor()
        except Exception:  # noqa: BLE001 — un avviso non fa cadere una lettura
            return Risultati(out, trattenuti=self._trattenuti_safe(query))
        # ⚠️ QUANDO NON SI E' TAGLIATO, LA SOGLIA DELL'AVVISO E' LA SUA, non il
        # pavimento calibrato: `_pavimento_avviso()` (misurato, fisso, con la
        # sua variabile). Il ramo del TAGLIO resta invariato — `min_relevance`
        # e' la soglia di chi l'ha chiesta e va dichiarata com'e'.
        # ⚠️⚠️ `if _pav` RESTA, ed e' stato MISURATO che serve. La prima stesura
        # metteva `_pavimento_avviso()` sempre, e ha rotto SEI test — tutti
        # controlli, cioe' i test che presidiano il caso in cui l'avviso NON
        # deve uscire (`..._con_risultati_SOPRA_soglia_nessun_avviso`,
        # `..._un_vuoto_che_NON_e_un_taglio...`, e quattro parametrizzazioni di
        # `..._una_domanda_con_risposta_non_viene_segnalata`). Il motivo: su un
        # negozio piccolo `_auto_relevance_floor()` vale `0.0` perche' non ha
        # materiale per calibrarsi, e i punteggi vivono su un'altra scala —
        # confrontarli con `0.839` accende l'avviso su TUTTO. E' il limite
        # dichiarato accanto alla costante («tarato su QUEL corpus»), che si e'
        # presentato al primo giro. ⇒ dove il negozio si e' calibrato si usa la
        # soglia misurata; dove non si e' calibrato, nulla cambia.
        _soglia = (float(min_relevance) if (_tagliati and min_relevance)
                   else (_pavimento_avviso(_pav) if _pav else 0.0))
        _tutto_tagliato = not out and _tagliati > 0
        # ⚠️ L'ORIGINE DEL NUMERO SI DICHIARA, e non e' cosmetica: «calibrata su
        # questo corpus» accanto a un valore che arriva da
        # `ENGRAM_AVVISO_MIN_RELEVANCE` e' una frase FALSA in una ricevuta.
        # La frase e' una superficie unica condivisa con la porta MCP e la CLI.
        _orig = _frase_origine_soglia(_soglia, _pav or 0.0)
        _nota = (
            (f"la soglia di rilevanza {_orig} ha TAGLIATO "
             f"tutti i {_tagliati} risultati trovati: nessuno la superava, "
             "quindi probabilmente la risposta NON e' in memoria. Qui sotto "
             "non c'e' niente perche' e' stato tagliato, non perche' la "
             "ricerca non abbia prodotto nulla.")
            if _tutto_tagliato else
            (f"nessun risultato supera la soglia di rilevanza {_orig}: "
             "probabilmente la risposta NON e' in memoria. I risultati sono "
             "qui sotto, non tagliati — decidi tu."))
        # La dichiarazione del viaggio nel tempo: solo se la data l'ha DEDOTTA
        # la porta e il filtro temporale HA TOLTO QUALCOSA.
        #
        # ⚠️ ERA `not out`, cioe' SOLO SULLA RISPOSTA VUOTA — e il caso vero non
        # e' vuoto. Misurato sul corpus reale (doc 70) sui tre casi che il 67
        # aveva misurato come spenti dal routing:
        #     758425daf047  n=10  fatto giusto PERSO  dichiarazione NESSUNA
        #     0ebe9e824198  n= 2  fatto giusto PERSO  dichiarazione NESSUNA
        #     3e74902dc247  n=10  fatto giusto PERSO  dichiarazione NESSUNA
        # Zero su tre; e sui 16 fatti retrospettivi del campione non esiste UNA
        # SOLA risposta vuota, quindi la condizione non aveva mai occasione di
        # accendersi.
        #
        # 🔑 E il caso non-vuoto e' PEGGIO del vuoto: il vuoto e' onesto («non ho
        # trovato niente»), dieci fatti da cui il filtro ha tolto proprio quello
        # che rispondeva sono una risposta PLAUSIBILE E SBAGLIATA, senza nessun
        # segnale per chi legge. ⇒ La condizione e' lo SCARTO; il vuoto ne e' un
        # caso particolare (se ha tolto tutto, ne ha tolto almeno uno).
        _al_passato = None
        if _as_of_dedotto and _scartati_dal_tempo and as_of is not None:
            import datetime as _dt
            try:
                # ⚠️ IN UTC, COME L'ANCORA E' COSTRUITA. `extract_as_of` fissa
                # `datetime(y, mo, d, 23, 59, 59, tzinfo=timezone.utc)`;
                # rileggerla senza fuso la stampa in ora LOCALE, e a est di
                # Greenwich le 23:59:59 UTC sono gia' il giorno dopo. Misurato
                # in «ora legale Europa occidentale», 3 casi su 3: «il 18
                # luglio 2026» dichiarava 19/07/2026, «cosa sapevamo al 5
                # agosto» dichiarava 06/08/2026, e «al 2026-01-31» dichiarava
                # 01/02/2026 — cambiando anche il MESE.
                # 🔑 Nessuno dei due pezzi sbagliava da solo: sbagliava la
                # GIUNTURA. E il danno colpiva proprio lo scopo dell'avviso,
                # che esiste per far riconoscere a chi legge LA DATA CHE HA
                # SCRITTO: mostrargliene un'altra glielo rende piu' difficile.
                _leggibile = _dt.datetime.fromtimestamp(
                    float(as_of), _dt.timezone.utc).strftime("%d/%m/%Y")
            except Exception:  # noqa: BLE001 — una data illeggibile non fa cadere nulla
                _leggibile = str(as_of)
            _al_passato = {
                "quando": float(as_of),
                "quando_leggibile": _leggibile,
                # ⚠️ «ALMENO»: `recall_as_of` smette di esaminare gli hit appena
                # ne ha k validi, quindi oltre quel punto non sa quanti altri
                # avrebbe scartato. Dire un numero esatto sarebbe piu' preciso
                # di quanto la misura sia.
                "scartati": _scartati_dal_tempo,
                # DUE CASI, DUE NOTE. Dire «non c'era nulla» dove i risultati
                # sono stati serviti sarebbe falso — ed e' il caso PIU'
                # frequente (doc 70: 0 risposte vuote su 16 retrospettivi).
                "nota": (
                    ("la domanda nomina una data, quindi e' stata letta come "
                     f"«cosa risultava AL {_leggibile}» — e a quell'istante non "
                     "c'era nulla. Se invece la data era l'OGGETTO della "
                     "domanda («cosa e' successo quel giorno»), rifalla senza "
                     "`as_of` o togli la data.")
                    if not out else
                    ("la domanda nomina una data, quindi e' stata letta come "
                     f"«cosa risultava AL {_leggibile}»: almeno "
                     f"{_scartati_dal_tempo} risultato/i sono stati esclusi "
                     "perche' PIU' RECENTI di quella data — quello che cerchi "
                     "puo' essere fra quelli. Se la data era l'OGGETTO della "
                     "domanda («cosa e' successo quel giorno»), rifalla senza "
                     "`as_of` o togli la data.")),
            }
        return Risultati(
            out,
            trattenuti=self._trattenuti_safe(query),
            letto_al_passato=_al_passato,
            # IL TAGLIO SI DICHIARA SEMPRE CHE AVVIENE, non solo quando ha
            # tolto tutto. La guardia e' `_tagliati`, cioe' il fatto che
            # qualcosa sia stato tolto — indipendente da come e' andata al
            # migliore, che e' la domanda a cui risponde l'avviso qui sotto.
            tagliati_dal_pavimento=(
                {"pavimento": round(_soglia, 4),
                 "tagliati": _tagliati,
                 "rimasti": len(out),
                 "score_migliore": round(_best_prima, 4),
                 "nota": (f"il pavimento {round(_soglia, 4)} ha tolto "
                          f"{_tagliati} fatti su {_n_prima}: la risposta si "
                          f"regge su {len(out)}. Se ti serve il materiale "
                          "intero, rifai la lettura con `min_relevance=0`.")}
                if _tagliati else None),
            sotto_il_pavimento=(
                {"pavimento": round(_soglia, 4),
                 "score_migliore": round(_best_prima, 4),
                 "tagliati": _tagliati,
                 "nota": _nota}
                # ⚠️ LA GUARDIA E' IL CONTEGGIO, NON IL PUNTEGGIO, e la prima
                # stesura sbagliava proprio qui: usare `_best_prima` come prova
                # che «qualcosa c'era» rompe il caso in cui i risultati ci sono
                # e valgono `0.0` — col ranking DEGRADATO (o sotto lo stub dei
                # test) ogni score e' `0.0`, e quello zero significa
                # «similarita' NON MISURATA», non «nessuna similarita'». Con la
                # guardia sbagliata l'avviso spariva da un caso che funzionava
                # da prima: `test_il_recall_rispondeva_anche_quando_non_sapeva`
                # e' diventato rosso e l'ha detto.
                if _soglia and _n_prima and _best_prima < _soglia
                else None),
        )

    def count(self, *, query: str | None = None, topic: str | None = None,
              topic_prefix: str | None = None) -> int:
        """Set-size, NOT top-k — the honest primitive for aggregation queries.

        F1 surface map (retrieval-vs-set-algebra): ``search`` is similarity
        top-k, so "how many times did I mention X?" undercounts (recall k=5
        saw 5 of 12 real mentions). ``count`` SCANS the store instead, so it
        sees the WHOLE matching set:

        * ``query``        — keyword scan; every fact whose proposition
                             contains all query tokens (case-insensitive),
                             optionally within ``topic`` / ``topic_prefix``;
        * ``topic``        — exact-topic scan;
        * ``topic_prefix`` — scoped scan (e.g. one tenant);
        * none             — the whole live corpus (excludes superseded).

        Live facts only (superseded excluded), matching ``search``'s default
        view. This is the primitive; routing a natural-language counting query
        to it is a separate intent step (gateway/F2)."""
        if query is not None:
            # UN ARTICOLO NON PUÒ CAMBIARE UN CONTEGGIO. L'AND è su TUTTI i
            # token, e i token includono articoli e preposizioni: misurato
            # 2026-08-02 sul corpus vero (5333 fatti vivi),
            #     moat    207 -> del moat   134    73 persi (35%)
            #     commit 1324 -> un commit 1126   198 persi (15%)
            #     gate    942 -> il gate    877    65 persi  (7%)
            # 429 fatti persi su otto coppie, e nessuno parlava di altro:
            # parlavano dello stesso argomento senza quell'articolo. Questo
            # metodo promette «the WHOLE matching set» — con una preposizione
            # nella domanda ne vedeva due terzi.
            #
            # È lo SPECULARE della cura in `2f2c667e`: nel ramo OR le parole
            # funzionali ALLARGANO a caso, qui nel ramo AND RESTRINGONO a
            # caso. E corregge un ragionamento di quel commit, dove avevo
            # scritto che `require_all_tokens` «è il percorso di precisione,
            # dove una funzionale in più STRINGE invece di allargare» e
            # l'avevo chiuso come non-problema: per una RICERCA è vero, per un
            # CONTEGGIO il cui contratto è vedere tutto l'insieme, no.
            #
            # Sta QUI e non in `search_facts` apposta: la ricerca deve
            # continuare a stringere. `_tokens` di bm25_rank, non una copia.
            from .bm25_rank import _tokens as _informativi
            _q = " ".join(_informativi(query)) if query.strip() else query
            if query.strip() and not _q:
                # Solo parole funzionali: non c'è nessun insieme da contare.
                # Zero, non «tutto» — che è ciò che una query vuota darebbe.
                return 0
            return len(self.semantic.search_facts(
                _q, limit=1_000_000, require_all_tokens=True,
                topic=topic, topic_prefix=topic_prefix))
        if topic_prefix is not None:
            return len(self.semantic.search_facts(
                "", limit=1_000_000, topic_prefix=topic_prefix))
        # I DUE RAMI RIMASTI INDIETRO. Il 2026-08-02 avevo spostato `query` e
        # `topic_prefix` da `list_facts` a `search_facts` per allineare le
        # popolazioni; questi due erano restati, e contavano anche i
        # QUARANTINATI — che il prodotto tiene fuori dal recall di default.
        # Misurato sul corpus vero: 5428 qui contro i 4834 del default di
        # `search`, cioe' i 594 quarantinati vivi, mentre la docstring qui
        # sopra promette «matching search's default view».
        # Si passa da SQL e non da `search_facts('')`: stesso risultato, ma
        # 0.00s invece di 0.45s su 7000 fatti, e un conteggio che si paga mezzo
        # secondo smette di essere una primitiva.
        if topic is not None:
            return self.semantic.count(topic=topic, include_quarantined=False)
        return self.semantic.count(include_quarantined=False)

    # ------------------------------------------------------------------ docs
    # Il tier DOCUMENTI mancava SOLO qui. Misurato il 2026-08-21::
    #
    #     MCP   7 tool  (hippo_document_index_file / _search / _semantic_search / ...)
    #     CLI   2 comandi  (`verimem index`, `verimem search-docs`)
    #     SDK   [x for x in dir(Memory) if "doc" in x.lower()]  ->  []
    #
    # E' il canale che un'APPLICAZIONE usa per integrare verimem: la superficie
    # piu' scoperta delle tre. `tests/test_le_promesse_valgono_appena_installato`
    # lo SKIPPAVA con «SDK: nessun metodo per i documenti (MCP e CLI ce l'hanno)
    # — e' un finding non una resa»: quello skip e' il RED di questi due metodi,
    # e sparisce da solo ora che esistono.
    #
    # Zero logica nuova: `DocumentIndex` e' gia' collaudato e lo usano gia'
    # entrambe le altre porte. Qui si espone, non si reimplementa.

    @property
    def documents(self):
        """Il tier documenti, costruito alla prima richiesta.

        ⚠️ NESSUN ``db_path``, DI PROPOSITO — e la prima stesura ne passava uno.
        Il 2026-08-21 questa property apriva l'indice ACCANTO ai fatti::

            db_path=Path(self.semantic.db_path).parent / "document_index.db"

        La motivazione era l'isolamento: una ``Memory(tmp_path)`` in un test non
        deve scrivere nell'indice documenti vero. Il problema e' che risolveva
        l'isolamento rompendo l'interoperabilita', e con ``Memory()`` nudo —
        l'uso normale — i due store divergevano lo stesso::

            SDK    : <data_dir>\\semantic\\document_index.db
            SISTEMA: <data_dir>\\documents\\document_index.db
            indicizzato dall'SDK, cercato da `hippo_document_search`: NON trovato

        Un utente che indicizza da qui e poi cerca da Claude Code non trovava
        niente. ``DocumentIndex()`` senza argomenti fa gia' la cosa giusta: legge
        ``HIPPO_DOCINDEX_DB`` se c'e', altrimenti deriva dal ``DocumentStore`` di
        sistema — che vive nella data dir CORRENTE, quindi in un test con
        ``HIPPO_DATA_DIR`` su tmp resta isolato per costruzione. Passare un
        ``db_path`` esplicito saltava entrambi, env compreso.

        🔑 L'isolamento lo da' la data dir, non il percorso del db: era gia'
        risolto, e la riga in piu' rompeva una cosa per proteggerne un'altra che
        non era in pericolo.
        """
        _idx = getattr(self, "_documents", None)
        if _idx is None:
            from .document_index import DocumentIndex
            _idx = DocumentIndex()
            self._documents = _idx
        return _idx

    def index_document(self, path: str | Path, source_id: str | None = None):
        """Indicizza un FILE e rende il suo id. Gemello di `verimem index`.

        ⚠️ Il nome dice «document» ma sotto chiama ``index_file``, ed e' una
        scelta dichiarata: sul tier ``index_document`` prende ``(source_id,
        content)`` — cioe' il TESTO — mentre chi usa l'SDK ha in mano un PATH.
        Il contratto lo aveva gia' fissato il test, che chiama
        ``m.index_document(str(doc))``. Allineare il nome al tier avrebbe
        significato cambiare il test per comodita' dell'implementazione.
        """
        return self.documents.index_file(path, source_id=source_id)

    def search_documents(self, query: str, k: int = 5, **kwargs):
        """Cerca nei documenti indicizzati. Gemello di `verimem search-docs`."""
        return self.documents.search(query, k=k, **kwargs)

    def answer(self, query: str, *, llm: Any, k: int = 8,
               verify_threshold: float | None = None,
               trust_conditioning: bool = True,
               max_tokens: int = 64,
               judge_verify: bool = True) -> dict[str, Any]:
        """Grounding-verified answering — the anti-hallucination read-path.

        Generate an answer from the top-``k`` retrieved facts, then verify it
        in TWO stages: a LOCAL cross-encoder (no LLM call) screens out answers
        entailed by nothing retrieved, and — because that CE never sees the
        QUESTION — a question-aware judge (one extra ``llm`` call, ~12 output
        tokens, only on answers the CE passed) checks the answer actually
        answers the question from the evidence. If either stage fails, abstain
        (``NO ANSWER``) rather than serve a probable hallucination.

        ``trust_conditioning`` (default ON) additionally tags every fact with
        the provenance the store already holds — ``[when | source | status]`` —
        and instructs the model to resolve conflicts by metadata (verified >
        unverified, recent > old, first-hand > hearsay; unresolvable → abstain).
        This is the CASE-B lever, measured on the well-grounded-distractor bench
        (sonnet-5, 2026-07-16, 12 cases where BOTH facts pass the grounding gate
        at 76-100 so grounding cannot separate them): bare answer C=0.17/H=0.33
        → trust-conditioned C=0.92/H=0.08, abstaining 2/2 on same-metadata
        conflicts. ``False`` restores the bare v1 prompt byte-identically.

        Returns ``{answer, grounded, support_score, support_fact, judge_score,
        raw_answer, reason}``. ``raw_answer`` always carries what the model
        produced (a caught hallucination is reported, never silently dropped).
        Fail-open only when the local CE is unavailable
        (``reason='ce_unavailable_failopen'``, ``grounded=False`` — served but
        explicitly UNVERIFIED) — the one honest hole, logged not hidden.

        HONEST SCOPE (measured 2026-07-21, benchmark/confabulation_corpus.py):
        the CE alone is question-blind — a confabulation that is a literal
        fragment of a stored fact ("Marco", "40") scores 96-99 against it, and
        a parroted fact scores ~100 whatever the question was; the CE alone
        stopped 3/10 scripted concise confabulations. The ``judge_verify``
        stage (default ON; the same calibrated judge as ``gate_answer``,
        threshold 85 via ENGRAM_GROUNDING_THRESHOLD) closed that to 8/10 with
        0/6 true answers lost. The measured residue: plausible-INFERENCE
        bridges the judge also endorses (causal attribution from co-occurrence,
        location transfer) — that residue is a judge-prompt axis, documented,
        not solved. A wrong fact that is ITSELF in memory is a different axis:
        that separation is what trust-conditioning buys (0.17→0.92), with its
        own residue (newer-AND-verified-but-false metadata).

        Judge failure semantics: an unreadable/erroring judge keeps the CE
        verdict for a plain answer (utility is not destroyed by a judge flake;
        ``judge_score=None`` says it did not run) — but a HYBRID abstention
        ("not mentioned, but likely X") whose judge is unreadable returns to
        its own refusal: serving the asserted half needs positive evidence.
        """
        hits = self.search(query, k=k)
        if not hits:
            return {"answer": "NO ANSWER", "grounded": False, "reason": "no_facts",
                    "support_score": None, "support_fact": None,
                    "judge_score": None, "raw_answer": None}
        facts = [h["text"] for h in hits]
        if trust_conditioning:
            lines = [_fact_trust_line(h) for h in hits]
            system = _ANSWER_TRUST_SYSTEM
        else:
            lines = [f"- {t}" for t in facts]
            system = _ANSWER_SYSTEM
        # L'AVVISO SUI RECORD TRATTENUTI. Senza, questa superficie riceve solo
        # `h["text"]` e il campo `hidden_records` — che `search` calcola — non
        # arriva mai a chi formula la risposta: una garanzia che vive nel
        # dizionario e non nella risposta è una garanzia che nessuno legge.
        # Vuota quando non c'è nulla da dichiarare, e allora il prompt resta
        # byte-identico a prima.
        from .hidden_records import withheld_notice
        user = ("Facts:\n" + "\n".join(lines) + withheld_notice(hits)
                + f"\n\nQuestion: {query}")
        resp = llm.complete(system,
                            [{"role": "user", "content": user}],
                            max_tokens=max_tokens)
        raw = (getattr(resp, "text", "") or "").strip()

        # F5 (measured 2026-07-21 on glm-4.6/kimi-k3/kimi-k2.6): a reasoning
        # model can burn the whole budget on reasoning_content and return
        # content='' with finish_reason='length'. That is a DELIVERY failure,
        # not an epistemic judgement — reporting it as 'model_abstained' made
        # the product silently mute on every question. Raise max_tokens for
        # such models.
        if not raw and getattr(resp, "finish_reason", None) == "length":
            return {"answer": "NO ANSWER", "grounded": False,
                    "reason": "llm_truncated", "support_score": None,
                    "support_fact": None, "judge_score": None, "raw_answer": ""}

        # F4: only a CLEAN abstention earns the free pass. A hybrid reply
        # ("not mentioned, but it is likely June") asserts something, so it
        # falls through to verification with its assertion intact.
        from .grounding_gate import _abstention_kind, _resolve_threshold
        kind = _abstention_kind(raw)
        if kind == "clean":
            return {"answer": "NO ANSWER", "grounded": True,
                    "reason": "model_abstained", "support_score": None,
                    "support_fact": None, "judge_score": None, "raw_answer": raw}

        # local-CE post-verification: is the answer entailed by any retrieved fact?
        from .local_grounding import try_local_score
        thr = (_ANSWER_VERIFY_THRESHOLD if verify_threshold is None
               else float(verify_threshold))
        best_ce, best_fact = -1.0, None
        for t in facts:
            r = try_local_score(t, raw)
            if r is None:  # CE model unavailable -> can't verify; fail-open, logged.
                # grounded=False is the honest receipt (F1): the answer is
                # served for utility, but NOTHING verified it.
                return {"answer": raw, "grounded": False,
                        "reason": "ce_unavailable_failopen", "support_score": None,
                        "support_fact": None, "judge_score": None,
                        "raw_answer": raw}
            if r[0] > best_ce:
                best_ce, best_fact = r[0], t
        if best_ce < thr:
            return {"answer": "NO ANSWER", "grounded": False,
                    "support_score": round(best_ce, 1), "support_fact": None,
                    "judge_score": None, "raw_answer": raw,
                    "reason": "unsupported_by_facts"}

        # F2/GLM-2 (measured 2026-07-21): the CE above is question-blind — a
        # literal fragment of a stored fact ("Marco", "40") scores 96-99 and a
        # parroted fact ~100 regardless of the question. The question-aware
        # judge the product already ships for gate_answer closes exactly that
        # class (measured: 6/8 CE escapes blocked, 6/6 true answers kept).
        judge_score: float | None = None
        if judge_verify:
            from .grounding_gate import grounding_score
            try:
                judge_score = grounding_score(llm, query, facts, raw,
                                              judge="basic", unreadable=None)
            except Exception:  # noqa: BLE001 — judge flake must not crash reads
                judge_score = None
            # receipt honesty (kimi review 2026-07-21): the CE DID find a
            # supporting fact — best_fact stays in the receipt so the audit
            # reads "CE passed on this fact; the judge stage is what failed".
            if judge_score is not None and judge_score < _resolve_threshold(None):
                return {"answer": "NO ANSWER", "grounded": False,
                        "support_score": round(best_ce, 1),
                        "support_fact": best_fact,
                        "judge_score": judge_score, "raw_answer": raw,
                        "reason": "judge_rejected"}
            if judge_score is None and kind == "hybrid":
                # The reply already declined once; serving its asserted half on
                # an unreadable judge would need evidence nobody produced —
                # and failing open here would let a judge OUTAGE reopen the F4
                # hole exactly when the second stage is down. Fail-closed.
                return {"answer": "NO ANSWER", "grounded": False,
                        "support_score": round(best_ce, 1),
                        "support_fact": best_fact,
                        "judge_score": None, "raw_answer": raw,
                        "reason": "judge_unreadable_hybrid"}
            if judge_score is None:
                # F1 (deepseek-v4-pro gate 2026-07-21): the judge was REQUESTED
                # but its verdict could not be read — only the question-BLIND CE
                # ran. Serve for utility (a judge outage must not blank every
                # answer) but grounded=False: grounded=True here would certify a
                # question-aware check that never happened.
                return {"answer": raw, "grounded": False,
                        "support_score": round(best_ce, 1),
                        "support_fact": best_fact, "judge_score": None,
                        "raw_answer": raw, "reason": "judge_unreadable"}
        # grounded=True here means: CE passed AND (judge confirmed OR the caller
        # opted out with judge_verify=False). Both are honest single/two-stage
        # verdicts — never an unreadable judge masquerading as a pass.
        return {"answer": raw, "grounded": True,
                "support_score": round(best_ce, 1), "support_fact": best_fact,
                "judge_score": judge_score, "raw_answer": raw,
                "reason": "grounded"}

    def ask(self, query: str, *, k: int = 5,
            topic_prefix: str | None = None) -> dict[str, Any]:
        """Intent-routed query — the read-path twin of the write-path
        provenance router (surface-map thesis: classify before acting).

        A cardinality question ("how many times did I discuss X?") routes to a
        full-corpus SCAN/count, not top-k recall (which undercounts — F1 saw
        5/12). Enumeration ("list all X") returns the whole matching set.
        Everything else is FIND: ordinary semantic recall, unchanged. Returns
        ``{"intent", ...}`` — ``count`` for COUNT, ``results`` otherwise — so
        the caller always knows which operation ran.

        FIND is the safe default: a misclassified query behaves exactly like
        ``search`` today. This is the dispatcher; the classifier lives in
        verimem.query_intent (lexical, EN+IT)."""
        from .query_intent import (
            COUNT,
            EXCLUDE,
            FIND,
            LIST_ALL,
            classify_query_intent,
            content_terms,
        )
        intent = classify_query_intent(query)
        if intent == COUNT:
            terms = content_terms(query)
            n = (self.count(query=terms, topic_prefix=topic_prefix)
                 if terms else self.count(topic_prefix=topic_prefix))
            out = {"intent": COUNT, "terms": terms, "count": n}
            # ⚠️ UNO ZERO SU UNA DOMANDA DI CONTEGGIO È LA RISPOSTA PEGGIORE
            # POSSIBILE: «non ho trovato niente» detto con certezza. Misurato::
            #
            #     «Quanti fatti parlano di zinco?» -> 0, con DODICI fatti che
            #     contengono zinco. Termini estratti: «fatti parlano zinco».
            #
            # `count` è un AND su TUTTI i termini, e `content_terms` lascia
            # dentro le parole funzionali che la sua stoplist non conosce
            # («parlano» manca, «parlato» c'è). Chi legge lo zero non ha modo di
            # sapere QUALE termine lo ha azzerato.
            #
            # NON si cura la stoplist — «curare tutte le 15 stoplist» è una
            # strada già falsificata in casa, perché la lista è infinita: oggi
            # «parlano», domani «citano» o «riguardano». Si cura il SILENZIO, e
            # il conteggio per singolo termine non decide nulla: MOSTRA.
            # «zinco: 12 · parlano: 0» si legge in un secondo e la diagnosi la
            # fa chi ha scritto la domanda.
            #
            # Costa una query per termine e si paga SOLO qui: conteggio a zero
            # E più di un termine, cioè l'unico caso in cui un AND può avere
            # azzerato qualcosa che c'era.
            pezzi = terms.split()
            if n == 0 and len(pezzi) > 1:
                out["per_term"] = {
                    t: self.count(query=t, topic_prefix=topic_prefix)
                    for t in pezzi}
                # ⚠️ MOSTRARE NON BASTA — misurato il 2026-08-25. `per_term` è
                # prodotto qui e consumato da `cli.py` soltanto: chi legge il
                # numero PROGRAMMATICAMENTE non lo vede mai. Il consumatore che
                # lo dimostra è in casa nostra:
                #
                #     benchmark/competitor_probe_verimem.py:30
                #         ask = mem.ask("how many times ...")["count"]
                #
                # cioè il nostro benchmark competitivo legge il campo che si
                # azzera. Un umano alla CLI vedeva «zinco: 12 · parlano: 0» e
                # capiva; un programma prendeva 0 e ci costruiva sopra.
                #
                # IL CRITERIO, e perché non inventa numeri: un termine il cui
                # conteggio INDIVIDUALE è zero non compare in nessun fatto —
                # non è un filtro, è rumore, e toglierlo dall'AND non cambia
                # l'insieme che l'AND avrebbe selezionato. Restano fuori i
                # termini che esistono ma non co-occorrono: lì lo zero è VERO
                # e va lasciato, o si risponderebbe col conteggio di un ALTRO
                # insieme di fatti (presidiato da `test_CONTROLLO_uno_zero_
                # VERO_resta_zero`).
                #
                # ⛔ E NON si cura la stoplist: «curare tutte le stoplist» è
                # già una strada falsificata in questa casa — la lista è
                # infinita («parlano» oggi, «citano» domani) e monolingue,
                # mentre questo criterio non nomina nessuna parola.
                # 🛑 IL DEGRADO AUTOMATICO È STATO PROVATO E RITIRATO nella
                # stessa ora, il 2026-08-25. La prima stesura sostituiva il
                # totale con il conteggio dei soli termini «vivi». Cade su un
                # caso che il suo stesso presidio ha trovato::
                #
                #     «Quanti fatti parlano di zinco e di alluminio?»
                #        per_term: fatti 0 · parlano 0 · zinco 12 · alluminio 0
                #        degradato -> 12,  vero -> 0
                #
                # «alluminio» ha conteggio zero perché NON ESISTE, esattamente
                # come «parlano»: nel conteggio individuale una parola
                # funzionale assente e un termine di contenuto assente sono
                # LO STESSO NUMERO. Distinguerli chiede di sapere che
                # «parlano» è funzionale — cioè la stoplist, che è la strada
                # già falsificata da cui questo codice parte.
                #
                # Quindi `count` NON si tocca: resta il totale dell'AND, che
                # è vero per definizione. Quello che si aggiunge è la risposta
                # ALTERNATIVA, esplicita e separata, perché il consumatore
                # programmatico (`benchmark/competitor_probe_verimem.py:30`
                # legge `["count"]`) possa vedere che una lettura diversa
                # esiste, senza che nessuno gliela imponga.
                #
                # ⚖️ È un limite che SOSPENDE la cura, non che l'accompagna:
                # chi legge solo `count` prende ancora lo zero. Dichiararlo
                # qui è tutto ciò che si può fare senza un dizionario.
                assenti = [t for t in pezzi if out["per_term"][t] == 0]
                presenti = [t for t in pezzi if out["per_term"][t] > 0]
                if presenti and assenti:
                    alternativo = self.count(query=" ".join(presenti),
                                             topic_prefix=topic_prefix)
                    if alternativo > 0:
                        out["count_without_absent_terms"] = alternativo
                        out["absent_terms"] = assenti
                        out["counted_terms"] = presenti
            return out
        if intent == LIST_ALL:
            terms = content_terms(query)
            rows = self.semantic.search_facts(
                terms, limit=1000, require_all_tokens=bool(terms),
                topic_prefix=topic_prefix)
            # LA STESSA VISTA DEL RAMO `find`. Questi due rami proiettavano
            # a mano tre chiavi — id, text, topic — mentre `find`, nella
            # STESSA funzione, restituisce le quindici di `_fact_view`
            # (trovato il 2026-08-07 con una grep dalle chiavi, non
            # dai letterali). Chi chiedeva «elencami tutto su X» riceveva
            # fatti in cui un `model_claim` e uno verificato erano
            # INDISTINGUIBILI: niente status, niente verdetto, niente
            # provenienza — e la stessa domanda posta in un'altra forma li
            # distingueva.
            #
            # `score` NON si aggiunge: appartiene alla query e qui non si
            # ordina niente. Uno zero direbbe «rilevanza nulla», che e'
            # un'affermazione; l'assenza dice «questo elenco non ordina».
            return {"intent": LIST_ALL, "terms": terms,
                    "results": [self._fact_view(f) for f in rows]}
        if intent == EXCLUDE:
            # Set-difference: the scoped corpus MINUS the facts matching the
            # excluded terms. Embeddings ignore "not"; this executes it as a
            # scan + removal (F1 negation fall). Base is the whole scope so a
            # generic subject never zeroes the set.
            from .query_intent import split_exclude
            _subj, excluded = split_exclude(query)
            # LA BASE E GLI ESCLUSI DEVONO ESSERE LO STESSO INSIEME. La base
            # usava `list_facts`, che include i QUARANTINATI; gli esclusi
            # `search_facts`, che non li include. Misurato 2026-08-02 su cinque
            # note di cui una quarantinata dal gate:
            #     BASE    (list_facts)  : 5 fatti
            #     ESCLUSI (search_facts): 2 fatti
            #     'tutto tranne moat' -> 3 risultati, e fra questi
            #        «Il moat giudica la fonte contro il fatto.» (quarantined)
            # Due danni, e il primo è il grave: un fatto che il gate ha
            # respinto ESCE da una superficie di lettura, contro la riga di
            # apertura del prodotto («kept OUT of default recall, so you never
            # get it back as truth»). Il secondo: ciò che sta solo nella base
            # è INESCLUDIBILE per costruzione — nessuna formulazione della
            # domanda lo fa sparire, perché l'insieme escludente non lo vede.
            base = self.semantic.search_facts(
                "", limit=10000, topic_prefix=topic_prefix)
            excl_ids: set[str] = set()
            if excluded:
                # Gli stessi token informativi di `count` (aa62e68b): «tranne
                # IL moat» deve escludere quello che esclude «tranne moat» —
                # l'articolo non fa parte del soggetto, e qui restringere
                # l'insieme escluso significa LASCIARE DENTRO ciò che l'utente
                # ha chiesto di togliere. Misurato: 2 fatti rimasti invece di 1.
                from .bm25_rank import _tokens as _informativi
                _escl = " ".join(_informativi(excluded)) or excluded
                excl_ids = {f.id for f in self.semantic.search_facts(
                    _escl, limit=10000, require_all_tokens=True,
                    topic_prefix=topic_prefix)}
            results = [f for f in base if f.id not in excl_ids]
            # stessa vista degli altri rami (vedi LIST_ALL qui sopra). Qui
            # pesa doppio: il commento del 2026-08-02 poco piu' su racconta
            # che da questo ramo e' gia' USCITO un fatto quarantinato, e
            # usciva senza `status` — cioe' indistinguibile da uno ammesso.
            # La base resta quella che e': questa cura non filtra niente,
            # rende solo VISIBILE cio' che esce.
            return {"intent": EXCLUDE, "excluded": excluded,
                    "results": [self._fact_view(f) for f in results]}
        return {"intent": FIND, "results": self.search(query, k=k)}

    def explain(self, query: str, k: int = 5, *, deep: bool = False,
                # "auto" come in `search`, e per non lasciare la cura a META'.
                # Censendo le strade "auto" non prese dal default (dopo il
                # difetto del routing temporale) questa e' saltata fuori
                # SUBITO DOPO aver curato `search`: le due porte sarebbero
                # divergite sullo stesso asse, ed `explain` e' quella che
                # promette di piu' — il dossier «how do you know?». Chi chiede
                # come faccia a sapere il prezzo di aprile riceveva la custodia
                # del prezzo di OGGI, con la catena di provenienza completa a
                # certificare il fatto sbagliato.
                as_of: float | str | None = "auto",
                min_relevance: float | str | None = None,
                llm: Any = None) -> dict[str, Any]:
        """The evidence dossier behind an answer — the trust gate made atomic:
        per fact the full chain of custody (provenance, writer, status,
        verified_by, grounding, the two clocks, what it replaced, declared
        disputes) or an EXPLICIT abstention with its reason. Judge-grade
        "how do you know?" for any query.

        ``min_relevance`` (default 0.0 = off) applies a retrieval floor so a
        query with no relevant fact abstains without an LLM.
        ``min_relevance="auto"`` lets the STORE calibrate the floor itself
        (scrambled-probe noise quantile, verimem.relevance_floor): measured on
        external data (HaluEval dev n=100, 2026-07-10) the self-calibrated
        floor landed at 0.7987 vs 0.80 hand-picked from the labeled curve —
        false_answer 1.0→0.04 at 0.10 over-abstention. A fixed default cannot
        do this: e5 scores live in [0.73, 0.95], so any constant is wrong for
        some store/embedder pair. Estimation (~32 probe recalls) is cached
        for 5 minutes. The resolved value is reported as
        ``report["min_relevance"]``.

        ``min_relevance=None`` (the default) reads the ``ENGRAM_MIN_RELEVANCE`` env —
        the single switch to turn read-path abstention ON across every surface
        (``auto`` | ``<float>`` | ``off``); unset → 0.0 (permissive, backward-compat)."""
        if min_relevance is None:
            from .relevance_floor import env_floor
            min_relevance = env_floor()
        # Only the "auto" floor delegates the abstention decision to the store —
        # route it through the CE relevance gate (reliable at any store size). An
        # explicit min_relevance float is the user's own bi-encoder floor and is
        # honored as-is (keeps the documented semantics + the HaluEval curve).
        want_ce_floor = (min_relevance == "auto")
        if min_relevance == "auto":
            min_relevance = self._auto_relevance_floor()
        if as_of == "auto":
            # Si risolve QUI e non a valle: `build_trust_report` vuole un
            # float, e la stringa ci arriverebbe come tale. Stessa riga di
            # `search`, stessa funzione — il routing e' uno solo.
            from .temporal_context import extract_as_of
            as_of = extract_as_of(query)
        from .trust_report import build_trust_report
        report = build_trust_report(self.semantic, query, k=k, deep=deep,
                                    as_of=as_of, min_relevance=min_relevance,
                                    ce_gate=want_ce_floor, llm=llm)
        report["min_relevance"] = float(min_relevance)
        # ⚠️ CHI HA DECISO, non solo con che numero. Il dossier riportava
        # `min_relevance` e basta, e con `auto` quel numero NON è la soglia che
        # ha filtrato: la decisione passa al cross-encoder e il float resta un
        # riferimento sulla scala del coseno. Misurato dal lato di chi legge,
        # ed è il modo peggiore in cui il difetto si manifesta:
        #
        #     min_relevance=None (default)  -> abstained=False  floor 0.872
        #                                      servito con relevance 0.8337
        #     min_relevance=0.872 (a mano)  -> abstained=True   n_facts=0
        #
        # cioè COPIARE IL NUMERO CHE IL PRODOTTO TI HA APPENA DATO cambia la
        # risposta, e chi legge conclude una delle due cose sbagliate: «il
        # filtro è rotto» oppure «il numero è sbagliato».
        #
        # La logica NON cambia — il CE è più accurato del coseno e lasciargli
        # l'ultima parola dimezza i falsi silenzi (misurato). Cambia che
        # il dossier lo dice. È la stessa classe dello `0.0` del ranking
        # degradato: un numero con la forma di una misura che significa altro.
        # ⚠️ COSA DICE DAVVERO, misurato il 2026-08-31: QUALE pavimento
        # deciderebbe, non che uno ABBIA filtrato. Con il pavimento SPENTO
        # (`min_relevance` risolto a 0.0 — cioe' `ENGRAM_MIN_RELEVANCE=off`,
        # che la docstring di `env_floor` dichiara come via legittima) questo
        # campo vale ancora `"cosine"`, e il participio del nome («applied»)
        # promette piu' di cosi'. Il valore NON e' cambiato di proposito: chi
        # si dirama su queste due stringhe non deve trovarne una terza senza
        # che sia stato deciso insieme. Chi vuole sapere se un pavimento abbia
        # DAVVERO tagliato legge `min_relevance` nella stessa ricevuta: e' il
        # numero che ha filtrato, oppure zero.
        report["floor_applied_by"] = (
            "cross_encoder" if want_ce_floor else "cosine")
        # IL DOSSIER DICHIARA ANCHE LA FONDATEZZA, non solo la rilevanza.
        # Emerso usando il prodotto da utente esterno, con questa diagnosi:
        #
        #     «Il pavimento misura la RILEVANZA. Il claim promette la
        #      FONDATEZZA. Sono due cose diverse, e la distanza fra le due è
        #      esattamente dove il prodotto sbaglia.»
        #
        # Un fatto scritto senza `source` ha `grounding_score = None`, che
        # significa MAI GIUDICATO — non «giudicato e passato». Le istruzioni
        # del server MCP lo dicono testuali («treat it as a claim, not a
        # fact»), e il dossier lo serviva con `abstained: False` e nessun
        # avviso: onesto NEL DATO, non NEL VERDETTO.
        #
        # ⚠️ `abstained` NON si tocca: è il verdetto sulla RILEVANZA («non ho
        # niente di abbastanza vicino») e su una domanda fuori corpus funziona
        # bene, con la sua ragione dichiarata. Si aggiunge la grandezza che
        # mancava, così le due smettono di essere confuse in un verdetto solo.
        # DUE NOMI PER LA STESSA COSA, e chi passa da una superficie all'altra
        # ci sbatte. Emerso usando il prodotto, col costo pagato sul posto: ha
        # portato sull'orlo di consegnare un «*explain sbaglia 10 su 10*» — su
        # una funzione che è corretta.
        #
        #     il TESTO      recall: `text`   ·  explain: `proposition`
        #     il PUNTEGGIO  recall: `score`  ·  explain: `relevance`
        #
        # ⚠️ SI AGGIUNGONO ALIAS, NON SI RINOMINA: `proposition` è il nome
        # della colonna nel DB e `relevance` è ciò che il dossier misura —
        # entrambi hanno una ragione, e rinominare romperebbe chi li legge già.
        # La cura non decide quale sia giusto: fa in modo che chi cerca l'altro
        # lo trovi.
        for _f in report.get("facts") or []:
            if "text" not in _f and "proposition" in _f:
                _f["text"] = _f["proposition"]
            if "score" not in _f and "relevance" in _f:
                _f["score"] = _f["relevance"]
        _fatti = report.get("facts") or []
        _senza = sum(1 for f in _fatti
                     if not isinstance(f.get("grounding_score"), (int, float))
                     or isinstance(f.get("grounding_score"), bool))
        report["ungrounded_facts"] = _senza
        report["grounding_checked"] = bool(_fatti) and _senza == 0
        # Il campo `source_trust` del dossier (task #20a) e' stato tolto insieme
        # al gate il 2026-09-02: usciva solo con `ENGRAM_SOURCE_TRUST=1`, e con
        # il registro delle fonti vuoto avrebbe riportato `0.500` per ognuna.
        # Misurato prima di toglierlo: scritto in un punto solo, letto da UN
        # test, e ZERO volte in `cli.py` e `mcp_server.py` — nessuna porta lo
        # mostrava a nessuno.
        if report.get("abstained"):
            # honest-"I don't know" counter — the read-path half of the odometer
            self._record_trust("abstained")
        _emit_flow("flow.recall", kind="explain",
                   n=len(report.get("facts") or []),
                   abstained=bool(report.get("abstained")))
        return report

    def trust_report(self, query: str, k: int = 5, **kwargs):
        """Il dossier di provenienza — lo STESSO di :meth:`explain`.

        ⚠️ ESISTE PERCHÉ IL NOME NON TORNAVA, e a segnalarlo è stato chi usava
        il prodotto da utente, dopo due giorni::

            «Ho cercato trust_report, non l'ho trovato, e stavo per scrivervi
             che mancava.»

        Le istruzioni del server MCP dicono `verimem_trust_report` — è il claim
        di marketing più forte del prodotto, quello sull'astensione — l'SDK
        aveva solo `explain`, e nessuno dei due rimandava all'altro. Chi legge
        le istruzioni e apre l'SDK fa esattamente quel percorso.

        ⚠️ E NON È UN ALIAS SECCO, di proposito: `correct = update` è un alias,
        e chiamandolo con gli argomenti sbagliati l'errore dice «Memory.update()
        missing 1 required positional argument» — nomina una funzione che chi
        scrive non ha mai chiamato e che cercherà invano nel proprio codice.
        Un metodo che delega fa sì che l'errore nomini il nome usato.
        """
        return self.explain(query, k, **kwargs)

    # ---- source trust (task #17, behind ENGRAM_SOURCE_TRUST) ----------------

    def _source_trust_book(self):
        """The process-shared per-path book (the store-side supersession hook
        mutates the SAME object — a private cache here would diverge)."""
        from .source_trust import get_book
        return get_book(self.semantic.db_path)

    def source_trust_observe(self, *, confirmation: list[str] | None = None,
                             contradiction: str | None = None,
                             outcome: tuple[str, bool, float] | None = None,
                             reports: dict[str, dict[str, str]] | None = None,
                             audited_false: tuple[str, str] | None = None,
                             ) -> dict[str, Any]:
        """Feed the per-source book and persist it. ``confirmation`` = ≥2
        distinct sources asserted the same accepted value; ``contradiction``
        = this source contradicted an accepted value; ``outcome`` =
        (source, good, weight) — weight<1 attenuates stale blame (task #18).

        ``reports`` = {source: {key: value}} that each confirmer asserted — the
        independence substrate: with ENGRAM_SOURCE_INDEPENDENCE=1 the confirmation
        needs ≥2 INDEPENDENT clusters, so copies/colluders of one feed (identical
        report vectors) collapse to one witness instead of self-confirming.
        ``audited_false`` = (key, value) an audit revealed FALSE — the do-operator
        anchor for ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND (P88): colluders co-admit
        it, honest sources do not, so honest agreement is no longer false-merged.

        RETROACTIVE DEMOTION (judge finding, seeds 12-13): reputation crosses
        the floor only after a few contradictions, so a liar's EARLY writes
        were staying admitted. When an observation sinks a source BELOW the
        floor (crossing, not every update), its already-stored facts are
        re-evaluated: quarantined — rehabilitable, never deleted (guard-rail).
        Flag-gated like the rest of the wiring."""
        from .source_trust import (
            enabled,
            independence_deconfounded,
            independence_enabled,
            save_book,
            threshold,
        )
        book = self._source_trust_book()
        if audited_false:
            book.mark_false(*audited_false)
        watched = {s for s in (contradiction,
                               outcome[0] if outcome else None) if s}
        pre = {s: book.trust(s) for s in watched}
        # trust BEFORE this observation for every source it touches (confirmers
        # included) — the recovery crossing-up is read against these.
        pre_all = {s: book.trust(s)
                   for s in set(watched) | set(confirmation or [])}
        # ⚠️ IL RIFIUTO DI UNA CONFERMA NON È PIÙ MUTO. `observe_confirmation`
        # richiede ≥2 fonti distinte — regola documentata e con una ragione
        # anti-collusione: «a single (or self-duplicated) source cannot confirm
        # itself» — e con UNA sola fonte esce senza fare nulla. Chi chiamava
        # non riceveva nessun segnale: il metodo tornava `None` e il numero non
        # si muoveva.
        #
        # Trovato dall'esterno, e la conclusione a cui si arrivava dice
        # quanto costa il silenzio: «le conferme non arrivano al ledger, una
        # fonte che sbaglia resta penalizzata per sempre». Rimisurato, è falso
        # — la reputazione RISALE (0.3333 → 0.5 → 0.6 con ≥2 conferme, e la
        # formula dichiarata torna esatta) — ma un utente esperto ci ha messo
        # mezz'ora per concludere il contrario, perché il rifiuto era invisibile.
        #
        # LA REGOLA NON SI TOCCA. Si dichiara cosa è stato registrato e cosa no.
        esito: dict[str, Any] = {}
        if confirmation:
            for src_id, kv in (reports or {}).items():
                for k, v in (kv or {}).items():
                    book.record_report(src_id, k, v)
            _prima = {s: book.trust(s) for s in confirmation}
            book.observe_confirmation(
                confirmation, require_independent=independence_enabled(),
                deconfounded=independence_deconfounded())
            _registrata = any(book.trust(s) != _prima.get(s)
                              for s in confirmation)
            esito["confirmation_recorded"] = _registrata
            if not _registrata:
                esito["reason"] = (
                    "una conferma richiede almeno 2 fonti distinte: una fonte "
                    "non può confermare sé stessa. Nessuna reputazione è "
                    "cambiata.")
        if contradiction:
            book.observe_contradiction(contradiction)
        if outcome:
            src, good, weight = outcome
            book.observe_outcome(src, good=good, weight=weight)
        save_book(self.semantic.db_path, book)
        if enabled():
            thr = threshold()
            for s in watched:
                if pre.get(s, 1.0) >= thr and book.trust(s) < thr:
                    self._retro_demote_source(s)          # crossing DOWN
        # crossing UP: a recovered source's OWN source-trust demotions reverse
        # (guard-rail rehabilitation path). confirmations are the recovery.
        if enabled() and confirmation:
            thr = threshold()
            for s in confirmation:
                if pre_all.get(s, 0.0) < thr <= book.trust(s):
                    self._rehabilitate_source(s)
        return esito

    def report_outcome(self, fact_id: str, *, good: bool,
                       weight: float = 1.0) -> bool:
        """The OUTCOME channel's application entry point: report that a stored fact
        succeeded or FAILED in use. Feeds the source's outcome reputation and — on a
        FAILURE — marks the fact's (topic, proposition) audit-revealed FALSE. That
        anchor is the do-operator that lets the deconfounded independence tell a copy
        cartel of LIARS apart from honest sources who merely agree on the truth — the
        second channel the write-path alone cannot supply (benchmark/
        independence_dense_honest.py). Returns False if the fact is unknown.

        No flag of its own: the reputation update is inert unless the gate consults it
        (ENGRAM_SOURCE_TRUST) and the audit anchor unless deconfound is on."""
        fact = self.semantic.get(fact_id)
        if fact is None:
            return False
        from .source_trust import canonical_source
        source = canonical_source(getattr(fact, "verified_by", None))
        topic = (getattr(fact, "topic", "") or "").strip()
        prop = (getattr(fact, "proposition", "") or "").strip()
        audited = (topic, prop) if (not good and topic and prop) else None
        self.source_trust_observe(outcome=(source, good, weight),
                                  audited_false=audited)
        return True

    _SOURCE_REF_PREFIXES = ("source-doc", "source", "src", "doc", "file")
    _DEMOTE_TABLE = ("CREATE TABLE IF NOT EXISTS source_trust_demotions ("
                     "fact_id TEXT PRIMARY KEY, source TEXT NOT NULL)")

    def _retro_demote_source(self, source: str) -> None:
        """Quarantine every non-quarantined fact citing ``source`` — the
        write-time gate only stops FUTURE lies; the crossing re-evaluates the
        past ones. Each demoted id is RECORDED so recovery can restore exactly
        these (never an L1/L4 quarantine). Best-effort."""
        import sqlite3 as _sq
        clauses = " OR ".join(["verified_by LIKE ?"] * len(self._SOURCE_REF_PREFIXES))
        params = [f'%"{p}:{source}:%' for p in self._SOURCE_REF_PREFIXES]
        try:
            with _sq.connect(str(self.semantic.db_path)) as conn:
                conn.execute(self._DEMOTE_TABLE)
                rows = conn.execute(
                    f"SELECT id FROM facts WHERE status != 'quarantined' "
                    f"AND ({clauses})", params).fetchall()
        except _sq.Error:
            return
        for (fid,) in rows:
            try:
                if self.semantic.quarantine_fact(
                    fid, deciso_da="source-trust",
                    reason=(f"source '{source}' trust sank below the "
                            "floor — retroactive demotion")):
                    with _sq.connect(str(self.semantic.db_path)) as conn:
                        conn.execute(
                            "INSERT OR REPLACE INTO source_trust_demotions "
                            "(fact_id, source) VALUES (?, ?)", (fid, source))
                        conn.commit()
            except Exception:  # noqa: BLE001 — best-effort per fact
                continue

    def _rehabilitate_source(self, source: str) -> None:
        """Restore ONLY the facts THIS source-trust demoted (recorded ids) —
        an L1/L4 quarantine is never touched. The reverse of the crossing."""
        import sqlite3 as _sq
        try:
            with _sq.connect(str(self.semantic.db_path)) as conn:
                conn.execute(self._DEMOTE_TABLE)
                rows = conn.execute(
                    "SELECT fact_id FROM source_trust_demotions WHERE source=?",
                    (source,)).fetchall()
        except _sq.Error:
            return
        for (fid,) in rows:
            try:
                self.semantic.restore_fact(
                    fid, reason=f"source '{source}' recovered above the floor")
            except Exception:  # noqa: BLE001 — best-effort per fact
                pass
        try:
            with _sq.connect(str(self.semantic.db_path)) as conn:
                conn.execute(
                    "DELETE FROM source_trust_demotions WHERE source=?",
                    (source,))
                conn.commit()
        except _sq.Error:
            pass

    # ---- decision chain (task #15) ------------------------------------------

    def _decisions(self):
        """Lazy DecisionStore on a sibling DB (decisions.db next to
        semantic.db — the documents.py sibling-path pattern). Built on first
        WRITE so a pure read never creates the file."""
        ds = getattr(self, "_decision_store", None)
        if ds is None:
            from pathlib import Path as _P

            from .decision_chain import DecisionStore
            ds = self._decision_store = DecisionStore(
                _P(self.semantic.db_path).with_name("decisions.db"))
        return ds

    def _decisions_ro(self):
        """Read-only handle: None if no decisions.db exists yet (a why/list
        must not materialise the store)."""
        from pathlib import Path as _P
        if getattr(self, "_decision_store", None) is not None:
            return self._decision_store
        if _P(self.semantic.db_path).with_name("decisions.db").exists():
            return self._decisions()
        return None

    def _adjudication_log(self):
        """Lazy AdjudicationLog on a sibling DB (adjudications.db next to semantic.db).
        Built on first AUDITED write, so a pure read / an audit-off deployment never
        creates the file."""
        al = getattr(self, "_adj_log", None)
        if al is None:
            from pathlib import Path as _P

            from .adjudication_log import AdjudicationLog
            al = self._adj_log = AdjudicationLog(
                _P(self.semantic.db_path).with_name("adjudications.db"))
        return al

    def _adjudication_log_ro(self):
        """Read-only handle: None if adjudications.db does not exist yet — a read must
        not materialise the store (the _decisions_ro pattern)."""
        from pathlib import Path as _P
        if getattr(self, "_adj_log", None) is not None:
            return self._adj_log
        if _P(self.semantic.db_path).with_name("adjudications.db").exists():
            return self._adjudication_log()
        return None

    def audit_log(self, *, disposition: str | tuple[str, ...] | list[str] | None = None,
                  topic: str | None = None, limit: int = 100) -> list[dict]:
        """The opt-in per-write audit trail (VERIMEM_AUDIT_LOG) as dicts, newest-first,
        filterable by disposition and/or topic. Empty when auditing was never enabled
        (a read never creates the DB). Single-proposition add() writes only — see the
        CHANGELOG note on conversation-ingest."""
        log = self._adjudication_log_ro()
        if log is None:
            return []
        return [{"id": r.id, "ts": r.ts, "topic": r.topic,
                 "disposition": r.disposition, "proposition": r.proposition,
                 "fact_id": r.fact_id, "evidence_class": r.evidence_class,
                 "judge": r.judge, "score": r.score, "threshold": r.threshold,
                 "reason": r.reason, "layers": r.layers, "pins": r.pins}
                for r in log.list(disposition=disposition, topic=topic, limit=limit)]

    def audit_verify(self) -> str | None:
        """Recompute the audit trail's tamper-evidence hash-chain: the id of the FIRST
        tampered row (an edit, an INTERIOR delete, a reorder, or a row demoted by NULLing
        its hash), or ``None`` if the chain is intact — or if auditing was never enabled
        (a read never creates the DB). It CANNOT see tail-truncation (deleting the newest
        rows) or a full rewrite; archive ``audit_head()`` off-box and compare to catch
        those."""
        log = self._adjudication_log_ro()
        return None if log is None else log.verify()

    def audit_head(self) -> str | None:
        """The audit trail's current chain head — archive it off-box (anchor-A) so a
        later `audit_verify()` plus a head comparison detects even a full-chain rewrite.
        ``None`` when the trail is empty / auditing was never enabled."""
        log = self._adjudication_log_ro()
        return None if log is None else log.head()

    def audit_head_signed(self) -> dict | None:
        """DEPRECATED — signs only the ADJUDICATION chain's BARE head. Prefer
        ``audit_anchor()``, which signs a receipt over BOTH chains and binds
        chain identity + row counts into the signature (a bare head does not,
        so a signature for one chain's head can be presented as another's).

        Anchor-B: the chain head PLUS its ed25519 signature under the operator's
        EXTERNAL key (``VERIMEM_AUDIT_SIGNING_KEY`` = path to a private PEM).
        ``None`` when no key is configured or the trail is empty; a configured
        key that cannot sign raises loudly."""
        import os as _os
        key_path = _os.environ.get("VERIMEM_AUDIT_SIGNING_KEY", "").strip()
        if not key_path:
            return None
        head = self.audit_head()
        if head is None:
            return None
        from .tamper_evidence import sign_head
        return {"head": head, "signature": sign_head(head, key_path),
                "algorithm": "ed25519"}

    def audit_anchor(self) -> dict:
        """A SIGNED anchor receipt over BOTH audit chains (mutations + gate
        adjudications) — head AND row count of each, a timestamp, and an ed25519
        signature over the canonical payload under ``VERIMEM_AUDIT_SIGNING_KEY``
        (the operator's private PEM). Archive it off-box; a later
        ``audit_verify_anchor()`` recomputes both chains and detects a full-chain
        rewrite or a tail-truncate+reinsert that an in-DB ``verify`` cannot see.

        No key configured RAISES (this method exists to sign — unlike
        ``audit_head_signed``'s honest ``None``, a silent no-op here would be a
        false sense of protection)."""
        import os as _os
        key_path = _os.environ.get("VERIMEM_AUDIT_SIGNING_KEY", "").strip()
        if not key_path:
            raise RuntimeError(
                "VERIMEM_AUDIT_SIGNING_KEY is not configured — audit_anchor "
                "exists to SIGN a receipt; set it to the operator's ed25519 "
                "private PEM path (this never silently returns None)")
        import time as _time

        from .audit_anchor import build_payload, sign_anchor
        adj = self._adjudication_log_ro()
        payload = build_payload(
            ts=_time.time(),
            mutations_head=self.semantic.audit_head(),
            mutations_rows=self.semantic.audit_count(),
            adjudications_head=adj.head() if adj is not None else None,
            adjudications_rows=adj.count() if adj is not None else 0)
        return sign_anchor(payload, key_path)

    def audit_verify_anchor(self, receipt: dict):
        """Verify a signed anchor receipt against the live chains: signature
        valid, both chains intact, row counts only grew, and each anchored head
        still sits at its anchored row count. Returns an
        ``audit_anchor.AnchorResult(ok, failures)`` naming any failing chain +
        check. The verification key is ``VERIMEM_AUDIT_PUBLIC_KEY`` (public PEM)
        or, failing that, ``VERIMEM_AUDIT_SIGNING_KEY`` (private PEM — the public
        key is derived from it)."""
        import os as _os
        key_path = (_os.environ.get("VERIMEM_AUDIT_PUBLIC_KEY", "").strip()
                    or _os.environ.get("VERIMEM_AUDIT_SIGNING_KEY", "").strip())
        if not key_path:
            raise RuntimeError(
                "no verification key configured — set VERIMEM_AUDIT_PUBLIC_KEY "
                "(public PEM) or VERIMEM_AUDIT_SIGNING_KEY (private PEM)")
        from .audit_anchor import ChainState, verify_anchor
        adj = self._adjudication_log_ro()
        mutations = ChainState(
            rows=self.semantic.audit_count(),
            intact=self.semantic.audit_verify() is None,
            head_at=self.semantic.audit_head_at)
        if adj is not None:
            adjudications = ChainState(
                rows=adj.count(), intact=adj.verify() is None,
                head_at=adj.head_at)
        else:
            adjudications = ChainState(rows=0, intact=True,
                                       head_at=lambda _k: None)
        return verify_anchor(receipt, key_path=key_path,
                             chains={"mutations": mutations,
                                     "adjudications": adjudications})

    def _content_pins(self, verified_by: Any) -> dict[str, str]:
        """Content-bound receipts (D5/#44): hash the span each ``file:`` ref
        cites, at write time. Refs that cannot be read contribute nothing —
        the pin map says what WAS read, never what merely resolved. Best
        effort: an unreadable tree must not break the write it documents."""
        try:
            from .content_pin import pin_for_ref
            root = getattr(self.semantic, "repo_root", None)
            if root is None:
                return {}
            out: dict[str, str] = {}
            for ref in (verified_by or []):
                if not isinstance(ref, str):
                    continue
                pin = pin_for_ref(ref, repo_root=root)
                if pin:
                    out[ref] = pin
                elif ref.strip().lower().startswith("file:"):
                    # Adversarial review 2026-07-25 (glm-5.2, Q6.5): silence
                    # made a post-feature row whose ref did not resolve
                    # indistinguishable from a pre-feature row, so the absence
                    # of a pin proved nothing. A file: ref that could not be
                    # read says so, on the record.
                    out[ref] = "unresolved"
            return out
        except Exception:  # noqa: BLE001 — a receipt detail, never a write blocker
            return {}

    def _audit_record(self, adjudication: dict, *, topic: Any, proposition: str,
                      fact_id: str | None, judge: Any, layers: list,
                      verified_by: Any = None) -> None:
        """Append the write's verdict to the opt-in audit trail (VERIMEM_AUDIT_LOG).
        No-op when off; never raises — persisting an audit record must never break the
        memory write it records.

        ``layers`` are the layers that ACTUALLY ACTED (the same list fed to the trust
        ledger): the caller passes ``_hit_layers`` so a store-time screen flip is
        recorded as ``['store-screen']``, not ``[]`` (opus critic F1 — ``warnings`` is
        the PRE-store gate list and misses that flip). ``judge`` is the backend string
        (local/claude), not the receipt's judge dossier. A dropped append is LOGGED, not
        swallowed silently — a gap in a trail sold as complete must be visible (F3)."""
        if not _audit_log_on():
            return
        try:
            self._adjudication_log().record(
                disposition=str(adjudication.get("disposition", "")),
                topic=str(topic or ""), proposition=str(proposition or ""),
                fact_id=fact_id,
                evidence_class=adjudication.get("evidence_class"),
                judge=judge,
                score=adjudication.get("score"),
                threshold=adjudication.get("threshold"),
                reason=str(adjudication.get("reason") or ""),
                layers=list(layers or []),
                pins=self._content_pins(verified_by),
            )
        except Exception as exc:  # noqa: BLE001 — must never break a write, but be visible
            _LOG.warning("audit append dropped (write succeeded): %s", exc)

    def record_decision(self, decision: str, *,
                        alternatives: list[str] | None = None,
                        evidence: list[str] | None = None,
                        expected: str = "", revisit_at: float | None = None,
                        topic: str = "decisions/general") -> str:
        """Record a decision as a first-class cited record — the choice, the
        alternatives rejected, the evidence (fact ids) considered, the
        expected outcome. Answerable later via ``why_decision``."""
        return self._decisions().record(
            decision=decision, alternatives=alternatives, evidence=evidence,
            expected=expected, revisit_at=revisit_at, topic=topic)

    def decision_outcome(self, decision_id: str, outcome: str, *,
                         verified_by: list[str]) -> bool:
        """Attach the MEASURED outcome to a decision — requires evidence
        (guard-rail), updates only the record, never the cited sources."""
        return self._decisions().record_outcome(
            decision_id, outcome, verified_by=verified_by)

    def why_decision(self, question: str, *, limit: int = 5) -> list[dict]:
        """"Why did we choose X?" → matching decisions with their cited
        evidence ids. Empty list when nothing was ever recorded."""
        ds = self._decisions_ro()
        if ds is None:
            return []
        return [{"id": d.id, "decision": d.decision, "topic": d.topic,
                 "alternatives": d.alternatives, "evidence": d.evidence,
                 "expected": d.expected, "outcome": d.outcome,
                 "outcome_verified_by": d.outcome_verified_by}
                for d in ds.why(question, limit=limit)]

    def source_trust(self, source: str) -> float:
        """Combined (min-of-observed-channels) trust for ``source``."""
        return self._source_trust_book().trust(source)

    def consistency_trust(self, source: str) -> float:
        return self._source_trust_book().consistency(source)

    _FLOOR_CACHE_TTL_S = 300.0

    #: Di quanto deve cambiare il corpus perché il pavimento vada ricalcolato.
    #: È la calibrazione DI QUEL corpus: finché il corpus è quello, il valore
    #: è quello. 5% su 8000 fatti = 400 scritture.
    _FLOOR_DRIFT = 0.05

    def _floor_file(self):
        from pathlib import Path
        return Path(str(self.semantic.db_path) + ".floor.json")

    def _trattenuti_safe(self, query: str | None) -> dict | None:
        """`_conta_trattenuti` blindato NEL CHIAMANTE, non solo al suo interno.

        Il metodo ha gia' un suo try/except, ma la protezione che conta e' qui:
        un avviso non deve MAI far cadere una lettura, e la lettura non puo'
        dipendere dal fatto che chi tocchera' quel metodo domani si ricordi di
        tenerci dentro un except. Difendere il punto d'uso e' l'unica forma che
        sopravvive alle modifiche altrui.
        """
        try:
            return self._conta_trattenuti(query)
        except Exception:      # noqa: BLE001 — un avviso non fa cadere una lettura
            return None

    def _conta_trattenuti(self, query: str | None,
                          topic: str | None = None) -> dict | None:
        """Quanti fatti il gate ha TRATTENUTO sull'argomento chiesto.

        Restituisce ``{quanti, nota}`` oppure ``None`` quando non ce n'e'
        nessuno — cosi' l'avviso compare solo quando c'e' qualcosa da dire, e
        non diventa rumore su ogni lettura.

        ⚠️ NON RESTITUISCE IL TESTO. Un fatto e' in quarantena perche' non ci si
        fida: mostrarlo «per trasparenza» lo rimetterebbe in circolo dalla porta
        di servizio, cioe' curerebbe un avviso mancante rompendo la garanzia che
        da' valore al prodotto.

        ⚠️ UN AVVISO NON FA CADERE UNA LETTURA. Qualunque errore qui — database
        occupato, schema di uno store vecchio, colonna assente — degrada a
        ``None`` e la ricerca restituisce comunque i suoi risultati.

        COSTO: una COUNT su una tabella gia' aperta, con LIKE sui token della
        domanda. Misurato sul corpus di casa (8999 fatti) nel commit che
        introduce questo metodo.
        """
        try:
            with sqlite3.connect(str(self.semantic.db_path)) as _c:
                sql = ("SELECT count(*) FROM facts "
                       "WHERE status='quarantined' AND superseded_by IS NULL")
                par: list = []
                if topic:
                    sql += " AND topic = ?"
                    par.append(topic)
                # i token lunghi della domanda: un LIKE per ognuno, in OR. Senza
                # token utili si conta la quarantena del topic (o si tace).
                toks = [w for w in re.findall(r"[^\W\d_]{4,}", (query or ""),
                                              re.UNICODE)][:6]
                if toks:
                    sql += " AND (" + " OR ".join(
                        ["lower(proposition) LIKE ?"] * len(toks)) + ")"
                    par += [f"%{w.lower()}%" for w in toks]
                elif not topic:
                    return None
                n = _c.execute(sql, par).fetchone()[0]
        except Exception:      # noqa: BLE001 — un avviso non fa cadere una lettura
            return None
        if not n:
            return None
        return {"quanti": int(n),
                "nota": (f"{n} fatto/i sull'argomento sono stati TRATTENUTI dal "
                         "gate e non compaiono qui: non erano sostenuti dalla "
                         "loro fonte. Non sono persi — restano nello store e si "
                         "vedono con la quarantena; ma non ti vengono serviti "
                         "come veri.")}

    def _auto_relevance_floor(self, *, rinfresca: bool = False) -> float:
        """Il pavimento auto-calibrato, PERSISTITO e servito senza ricalcoli.

        ``rinfresca=True`` forza la stima ignorando cache e file: lo chiede
        chi ha il costo atteso (`doctor`, un warmup, un daemon), MAI una
        lettura. Una lettura serve il valore persistito anche quando il
        corpus e' cresciuto oltre la deriva, e in quel caso lascia
        `_floor_stantio` a True per chi deve decidere se rinfrescare.

        ⚠️ ERA CACHED PER-ISTANZA CON UN TTL DI 5 MINUTI, e costava 57 secondi
        alla prima chiamata. Misurato sul corpus vero (8058 fatti) e
        riprodotto::

            explain chiamata 1:   56.845 ms
            explain chiamata 2:      773 ms      <- 73 volte più veloce
            recall:                  413 ms      <- nessuna cache di mezzo

        La stima fa ~32 recall di sonde giudicati dal cross-encoder. La cache
        c'era; la diagnosi dice perché non bastava:

            «Chi fa molte domande di fila paga 76 secondi UNA volta:
             tollerabile. Chi consulta il dossier OGNI TANTO paga 76 secondi
             OGNI VOLTA: inutilizzabile. E il secondo è il profilo d'uso vero —
             nessuno interroga la provenienza a raffica. Il caso ottimizzato
             dalla cache è quello che non capita mai.»

        🔑 **Il pavimento è una proprietà del CORPUS, non della query**: cambia
        quando il corpus cambia, non quando passano cinque minuti. Un TTL lo
        ricalcola per il passare del tempo invece che per una ragione.

        ⚠️ ACCANTO al DB e non DENTRO: una tabella nuova è una modifica di
        schema, e lo schema è di un'altra istanza. Un file JSON non ha
        migrazioni né lock, e se sparisce si ricalcola — perderlo costa un
        ricalcolo, non un errore. Tutto il percorso è fail-open per lo stesso
        motivo: il valore salvato è un'ottimizzazione, non un dato.
        """
        import json as _json
        import time as _time

        # ⚠️ LA DERIVA CONTA CIO' CHE LA STIMA PUO' VEDERE, e prima non era
        # cosi'. `count()` ha `include_quarantined=True` e veniva chiamata senza
        # argomenti, mentre `estimate_relevance_floor` misura passando da
        # `sm.recall`, che i quarantinati NON li restituisce (misurato
        # 2026-09-01: store da 2 fatti, `k=10`, torna 1 riga — con k maggiore
        # del corpus l'assenza non puo' essere un effetto di ranking).
        # ⇒ Un fatto quarantinato non puo' spostare il pavimento e faceva
        # avanzare l'orologio dell'invalidazione lo stesso: si pagava un
        # ricalcolo intero — 24169 ms misurati — per un fatto che non cambia il
        # risultato. Il corpus SERVIBILE resta invalidante, ed e' quello che
        # sposta il valore davvero.
        n = -1
        try:
            n = int(self.semantic.count(include_quarantined=False))
        except TypeError:  # una versione del contatore senza quel parametro
            try:
                n = int(self.semantic.count())
            except Exception:  # noqa: BLE001 — un conteggio fallito non blocca
                pass
        except Exception:  # noqa: BLE001 — un conteggio fallito non blocca
            pass

        cached = getattr(self, "_floor_cache", None)
        now = _time.time()
        if cached and not rinfresca and now - cached[0] < self._FLOOR_CACHE_TTL_S:
            return cached[1]

        f = self._floor_file()
        if n >= 0 and not rinfresca:
            try:
                d = _json.loads(f.read_text(encoding="utf-8"))
                # ⚠️ MIGRAZIONE DICHIARATA: un file scritto prima di questa cura
                # porta un `n_facts` contato su TUTTE le righe. Confrontarlo col
                # conteggio dei soli servibili metterebbe a confronto due
                # popolazioni diverse — che e' il difetto stesso, spostato di un
                # passo. Senza il marcatore il file non e' confrontabile: si
                # paga UN ricalcolo per store, una volta, e poi il file e'
                # coerente. `KeyError` sul marcatore assente cade nell'except
                # sotto, che gia' significa «si ricalcola».
                if str(d["n_metric"]) != "servibili":
                    raise ValueError("pavimento salvato con un'altra metrica")
                salvato, n_salvato = float(d["floor"]), int(d["n_facts"])
                # 🔑 LA LETTURA NON RICALCOLA, NEMMENO QUANDO IL VALORE E'
                # VECCHIO. Qui la deriva faceva cadere nel ricalcolo, e il
                # ricalcolo sta nel percorso di OGNI `search` (l'avviso di
                # rilevanza lo chiama fuori da ogni `if`): significa che la
                # prima ricerca dopo una crescita del 5% pagava la stima —
                # 24169 ms sul corpus vero di 14382 fatti, dentro la richiesta
                # di chi stava solo cercando.
                #
                # ⚖️ Un pavimento vecchio e' un'approssimazione di quello
                # nuovo; 24 secondi dentro una lettura sono un guasto. Quindi
                # si serve quello che c'e' e si DICHIARA che e' vecchio: il
                # ricalcolo lo chiede chi ha il costo atteso, con
                # `rinfresca=True`.
                #
                # ⚠️ Dichiararlo non e' un ornamento: `{"floor": 0.0}` e'
                # rimasto sul corpus vero dalle 20:32 del 30/08 alle 02:52 del
                # 31/08 — sei ore — e nulla diceva che fosse vecchio. Senza
                # questo stato, «appena misurato» e «vecchio di sei ore»
                # restano indistinguibili.
                self._floor_stantio = bool(
                    abs(n - n_salvato) > max(1, n_salvato) * self._FLOOR_DRIFT)
                self._floor_cache = (now, salvato)
                return salvato
            except Exception:  # noqa: BLE001 — file assente/corrotto: si ricalcola
                pass

        from .relevance_floor import estimate_relevance_floor

        # ⚠️ IL DEGRADO SI CONTA ANCHE QUI, e pesa piu' che nella recall.
        # `estimate_relevance_floor` misura passando da `sm.recall`, e sul ramo
        # keyword ogni risultato vale `score 0.0` (`hits_2t = [(f, 0.0) …]`):
        # 32 sonde a zero danno un quantile a zero, e quello zero non e'
        # «nessun rumore», e' «rumore NON MISURATO». Ha la forma di una misura
        # e non lo e' — la stessa distinzione di
        # `test_il_pavimento_tagliava_un_ranking_degradato`, che pero' cura la
        # LETTURA: una lettura degradata riguarda una query, un pavimento
        # degradato PERSISTITO riguarda tutte quelle che seguono, finche' il
        # corpus non deriva del 5%.
        #
        # RED di produzione, dallo store vero: `{"floor": 0.0, "n_facts":
        # 13795}` e' rimasto dalle 20:32:08 del 2026-08-30 alle 02:52:23 del
        # 2026-08-31 — SEI ORE su quasi quattordicimila fatti. E tredicimila
        # fatti non sono «uno store troppo piccolo per misurare», che e' l'unico
        # caso in cui lo zero e' documentato come scelta.
        # ⚠️ Lo zero salvato non e' inerte: e' FALSY, quindi dove lo si
        # controlla con un `if` non vale «pavimento a zero», vale «nessun
        # pavimento».
        #
        # 🔑 LA GUARDIA E' SUL DEGRADO, NON SULLO ZERO: `estimate_relevance_floor`
        # dichiara `0.0` come risposta legittima quando lo store e' troppo
        # piccolo, e quella strada deve restare aperta — un veto sul valore
        # chiuderebbe anche quella. Il contatore esiste da prima ed e' gia'
        # letto in `recall` per l'identica ragione: qui non lo leggeva nessuno.
        _deg_stima = getattr(self.semantic, "_recall_degraded_count", 0) or 0
        val = estimate_relevance_floor(self.semantic)
        if (getattr(self.semantic, "_recall_degraded_count", 0) or 0
                ) > _deg_stima:
            # Ne' su disco ne' in cache: la prossima chiamata ritenta, che e'
            # cio' che serve quando il daemon si scalda. Fail-open come tutto
            # il percorso — il valore si RESTITUISCE lo stesso, non si
            # CONSOLIDA.
            return val
        self._floor_cache = (now, val)
        # APPENA STIMATO: qualunque cosa dicesse il file, ora il valore e' di
        # questo corpus. Senza questa riga un rinfresco lascerebbe acceso il
        # segnale che deve spegnere.
        self._floor_stantio = False
        if n >= 0:
            try:
                f.write_text(
                    _json.dumps({"floor": val, "n_facts": n,
                                 "n_metric": "servibili"}),
                    encoding="utf-8")
            except Exception:  # noqa: BLE001 — non poter scrivere non è un errore
                pass
        return val

    def _record_trust(self, action: str, layers: list[str] | None = None,
                      topic: str = "") -> None:
        """Ledger write that can never cost the caller anything — defence in
        depth on top of the ledger's own fail-open (a buggy or replaced
        ledger must still not break add/explain)."""
        try:
            self._ledger.record(action, layers=layers, topic=topic)
        except Exception:
            pass

    def _ledger_ingest_result(self, res: dict, *, topic: str) -> None:
        """Count a conversation-ingest batch in the trust odometer, from the
        FINAL stored status of each fact (screens inside store() included).
        Fail-open: counting must never break the ingest that just succeeded."""
        try:
            ids = list(res.get("fact_ids") or [])
            by_status: dict[str, int] = {}
            if ids:
                qmarks = ",".join("?" * len(ids))
                with sqlite3.connect(str(self.semantic.db_path)) as con:
                    for status, n in con.execute(
                            f"SELECT status, COUNT(*) FROM facts "
                            f"WHERE id IN ({qmarks}) GROUP BY status", ids):
                        by_status[str(status)] = int(n)
            n_quar = by_status.pop("quarantined", 0)
            n_admitted = sum(by_status.values())
            if n_quar:
                self._ledger.record_many("quarantined", n_quar,
                                         layers=["ingest"], topic=topic)
            if n_admitted:
                self._ledger.record_many("admitted", n_admitted, topic=topic)
            n_rej = int(res.get("rejected") or 0)
            if n_rej:
                self._ledger.record_many("rejected", n_rej,
                                         layers=["ingest"], topic=topic)
        except Exception:
            pass

    def trust_stats(self) -> dict[str, Any]:
        """The trust odometer: what the gate DID on this store, live.

        ``ledger`` — persistent per-action counters (admitted / quarantined /
        rejected / abstained), counted from each fact's FINAL stored status
        (store-screens included) and covering the conversation-ingest path
        too; ``by_layer`` attributes only layers that actually ACTED (advisory
        warnings stay in the add() response). ``store`` — a SNAPSHOT of the
        live facts by status (a quarantined fact later deleted leaves the
        snapshot but stays in the cumulative ledger — different questions,
        both honest). ``abstained`` counts explain() abstention EVENTS (not
        deduped by query; plain search() misses are not abstentions).
        ``ledger_write_failures`` — events this process dropped because the
        ledger itself failed (fail-open stays, but visibly)."""
        out = self._ledger.stats()
        store: dict[str, int] = {}
        try:
            with sqlite3.connect(str(self.semantic.db_path)) as con:
                for status, n in con.execute(
                        "SELECT status, COUNT(*) FROM facts "
                        "WHERE superseded_by IS NULL GROUP BY status"):
                    store[str(status)] = int(n)
        except Exception:
            pass
        out["store"] = store
        # Quanti sono USCITI dal conto. `store` e' una fotografia dei vivi — lo
        # dice il docstring qui sopra — e `moat.facts` conta anch'esso solo
        # `superseded_by IS NULL`. Su una data dir temporanea con due
        # `remember` sullo stesso topic, questo payload riportava `facts: 1` su
        # un database di DUE righe e nessuna chiave nominava la seconda.
        # ⇒ Terza superficie con la stessa cecita' (dopo `epistemic_health` e il
        # pannello `status`), e la cura e' la stessa: stampare un numero che la
        # tabella ha gia'.
        # ⚖️ FUORI da `store`, non dentro: `store` ripartisce per STATUS, la
        # supersessione e' un'altra dimensione, e infilarla li' farebbe sommare
        # grandezze diverse a chi cicla sulle chiavi.
        # 📌 `None` e non 0 quando il conteggio non riesce: «non contato» e
        # «zero» sono due risposte diverse.
        superseduti: int | None = None
        try:
            superseduti = int(self.semantic.count_superseded())
        except Exception:  # noqa: BLE001 — un contatore non rompe il chiamante
            pass
        out["superseded"] = superseduti
        # How much of the corpus the MOAT actually judged — the number that
        # bounds every other number here. The entailment check only runs on a
        # write that carries a source, so a store can be full of facts none of
        # which the moat ever saw, and until now nothing said so: measured on
        # the real corpus 2026-07-28, 0 of 6414 facts had a grounding_score
        # while the product reported gate actions as usual. Provenance is
        # counted SEPARATELY because a verified_by ref records who vouches and
        # does not run the check — conflating them here would repeat, in the
        # report, the very confusion the write path avoids. Pure SQL over
        # columns already persisted: no judge, no LLM call.
        moat = {"facts": 0, "grounded": 0, "with_provenance": 0, "coverage": 0.0}
        try:
            with sqlite3.connect(str(self.semantic.db_path)) as con:
                moat["facts"] = int(con.execute(
                    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
                ).fetchone()[0])
                moat["grounded"] = int(con.execute(
                    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
                    "AND grounding_score IS NOT NULL").fetchone()[0])
                moat["with_provenance"] = int(con.execute(
                    "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL "
                    "AND verified_by IS NOT NULL AND verified_by NOT IN ('', '[]')"
                ).fetchone()[0])
            if moat["facts"]:
                moat["coverage"] = round(moat["grounded"] / moat["facts"], 3)
        except Exception:  # noqa: BLE001 — the odometer never breaks a caller
            pass
        out["moat"] = moat
        out["ledger_write_failures"] = int(
            getattr(self._ledger, "write_failures", 0) or 0)
        return out

    def quarantine_log(self, *, limit: int = 50,
                       explain: bool = False) -> list[dict[str, Any]]:
        """The blocked-claims log: live QUARANTINED facts, newest first.

        The odometer says HOW MANY the gate stopped; this says WHAT — each
        unsupported claim the gate downgraded, with topic and timestamp, so a
        human can audit the stops (and rescue a false positive via
        ``verified_by`` + update). Read-only; deleted/superseded quarantined
        facts drop out of this view but stay counted in the ledger."""
        rows: list[dict[str, Any]] = []
        try:
            with sqlite3.connect(str(self.semantic.db_path)) as con:
                con.row_factory = sqlite3.Row
                for r in con.execute(
                        # grounding_score viaggia con la riga perche' la
                        # spiegazione ne ha bisogno per NON inventare la
                        # causa: un verdetto alto su un fatto trattenuto
                        # smentisce da solo l'attribuzione a L4
                        # (misurato il 2026-08-05).
                        # `quarantined_by` viaggia con la riga perche' e'
                        # l'UNICA causa che sopravvive senza l'audit trail
                        # (VERIMEM_AUDIT_LOG e' opt-in e di default spento):
                        # senza, `reason` esce None su ogni riga e chi legge
                        # non ha niente. Misurato il 21/08:
                        # quarantine_log(limit=40) -> con reason 0 su 40.
                        # `grounding_span` viaggia con la riga perche' e'
                        # la FONTE su cui il giudice ha deciso: senza,
                        # `_spiega_le_quarantene` ricalcola il gate a mani
                        # vuote e i layer che confrontano claim E fonte —
                        # L4.1, L4.2 — non possono accendersi MAI.
                        "SELECT id, proposition, topic, created_at, status, "
                        "grounding_score, quarantined_by, grounding_span "
                        "FROM facts WHERE status = 'quarantined' "
                        "AND superseded_by IS NULL "
                        "ORDER BY created_at DESC LIMIT ?",
                        (max(1, int(limit)),)):
                    rows.append(dict(r))
        except Exception:
            pass  # read-only view: an unreadable store shows empty, not 500
        # Attach WHY each claim was blocked (reason + layers) so a human can
        # tell an L1 keyword false-positive from a real contradiction — the
        # audit trail persists it per fact_id when VERIMEM_AUDIT_LOG is on.
        # Degrades cleanly: without the trail the rows are exactly as before.
        try:
            why: dict[str, Any] = {}
            for a in self.audit_log(disposition="quarantined",
                                    limit=max(50, int(limit) * 4)):
                fid = a.get("fact_id")
                # audit_log is newest-first; keep the FIRST seen per fact so a
                # re-adjudicated claim shows its LATEST reason, not the oldest.
                if fid and fid not in why:
                    why[fid] = a
            for row in rows:
                a = why.get(row["id"])
                row["reason"] = (a or {}).get("reason") or None
                row["layers"] = (a or {}).get("layers") or []
                # L'audit trail, quando c'e', porta il TESTO e vince. Quando
                # non c'e' — il caso ordinario — la colonna sulla riga porta
                # almeno il LAYER, che e' cio' che serve per distinguere una
                # quarantena per contenuto falso da una per scelta di parole.
                # Il campo resta separato da `reason`: `reason` e' una frase
                # per un umano, questa e' un'attribuzione, e confonderle
                # farebbe passare un'etichetta per una spiegazione.
                if not row.get("layers"):
                    _qb = (row.get("quarantined_by") or "").strip()
                    if _qb and _qb not in ("gate", "moat", "store-screen"):
                        row["layers"] = [_qb]
        except Exception:  # noqa: BLE001 — enrichment must never break the view
            pass
        if explain:
            self._spiega_le_quarantene(rows)
        return rows

    @staticmethod
    def _spiega_le_quarantene(rows: list[dict[str, Any]]) -> None:
        """Ricalcola PERCHE' ogni claim e' stato fermato, e come sbloccarlo.

        Il motivo esiste gia' nella riga quando l'audit trail e' acceso, ma
        quello e' opt-in (``VERIMEM_AUDIT_LOG``) e in pratica non lo accende
        nessuno: sul corpus vivo del 2026-07-30 ci sono 513 fatti trattenuti e
        nessuno di loro ha una voce nel trail — «degrades cleanly» significa
        che la colonna resta vuota e chi guarda non sa che fare. Nemmeno
        accenderlo adesso aiuterebbe: il trail non e' retroattivo.

        Si ricalcola perche' i detector lessicali sono deterministici e non
        chiamano nessun modello: rieseguirli sulla proposizione dice quale si e'
        acceso e cosa chiede per lasciar passare il fatto. E' lo stesso metodo
        con cui il 29/07 si e' misurato che dei 164 quarantinati che citano
        un'evidenza nel testo, 42 passerebbero spostandola in ``verified_by`` e
        122 restano fermi sugli L1.

        Opt-in perche' costa: chi vuole solo l'elenco non paga il ricalcolo.
        Non tocca lo stato — e' una spiegazione, non una riabilitazione.
        """
        try:
            from .anti_confab_gate import run_validation_gate
            from .retirement_log import judged_true as _judged_true
        except Exception:  # noqa: BLE001
            return
        for row in rows:
            if row.get("reason"):
                continue  # l'audit trail sapeva gia' dirlo
            try:
                g = run_validation_gate(
                    proposition=row.get("proposition") or "",
                    verified_by=[], topic=row.get("topic"), agent=None)
                avvisi = list(getattr(g, "warnings", None) or [])
            except Exception:  # noqa: BLE001 — una spiegazione non rompe la vista
                continue
            if not avvisi:
                # Lo schermo dello STORE, che il gate di validazione non
                # attraversa: `detect_injection` gira dentro store() ed e'
                # puro e deterministico esattamente come gli L1 qui sopra.
                # Rieseguire il SOLO gate non poteva trovarlo mai — ed e'
                # per questo che il caso del 2026-08-05 finiva sul
                # ramo di default con una causa inventata, mentre la
                # ricevuta di scrittura diceva layers=['store-screen'].
                try:
                    from .prompt_injection import detect_injection
                    v = detect_injection(row.get("proposition") or "")
                except Exception:  # noqa: BLE001
                    v = None
                if v is not None and getattr(v, "is_injection", False):
                    row["layers"] = ["store-screen"]
                    row["why"] = (
                        "store-screen: prompt-injection signals "
                        f"{list(getattr(v, 'signals', []) or [])} — la frase "
                        "CITA una formula che il rilevatore riconosce. Se il "
                        "testo e' un referto che documenta l'attacco invece "
                        "di portarlo, e' un falso positivo: e' la variante "
                        "gemella del gate che trattiene i referti sul gate.")
                    continue

                # Nessuno schermo si riaccende. Qui la causa NON e' nota, e
                # fino al 2026-08-05 questo ramo la attribuiva a L4 — una
                # deduzione, non una lettura, ed e' stato misurato che e' falsa
                # su 183 record su 500: `layers` arriva vuoto, l'explain non
                # trova niente e ASSERISCE. Una superficie muta si nota, una
                # assertiva e sbagliata manda a cercare nella direzione
                # opposta. Ora si guarda l'unica cosa che la riga sa sul
                # moat — il suo verdetto — e si DICHIARA.
                # ⚠️ PRIMA DI DICHIARARE «non ricostruibile», SI RIPROVA CON
                # LA FONTE. Il ricalcolo qui sopra gira a mani vuote — niente
                # `source`, niente `ground_write` — e in quel regime L4.1 e
                # L4.2, che confrontano il claim CON la fonte, non possono
                # accendersi per costruzione. Misurato sul caso noto:
                #     nudo               -> []          grounding None
                #     ground_write=True  -> ['L4.1']    grounding 99.89
                # E sul corpus: su 20 quarantinati con grounding >=90,
                # ricalcolati con la fonte, i layer trovati sono 20 su 20
                # (L4.1 il 90%, L4.2 il 50%, L1 il 15%) — nessuno resta senza.
                #
                # ⛔ SI PAGA SOLO QUI, dove la risposta sarebbe «non lo so»:
                # il ricalcolo lessicale piu' sopra non chiama nessun modello e
                # resta la prima scelta. Il costo, MISURATO invece che dedotto:
                #
                #     primo ricalcolo   22.58s   <- carica il giudice
                #     i quattro dopo     0.04s   (media)
                #
                # Cioe' e' tutto nel CARICAMENTO, una volta per processo, e
                # ogni riga in piu' costa quattro centesimi. Per questo NON c'e'
                # un tetto al numero di righe: metterlo ridurrebbe la copertura
                # senza far risparmiare niente. (La prima lettura di questo
                # numero era «70.8s su 25 righe = 2.8s ciascuna» — una divisione
                # fatta senza guardare i tempi uno per uno.)
                #
                # Effetto sulla vista, stesso comando, `limit=25`:
                #     prima   15 righe con un layer (60%), 10 senza causa (40%)
                #     dopo    25 righe con un layer (100%), 0 senza causa
                _span = (row.get("grounding_span") or "").strip()
                if _span:
                    try:
                        _g2 = run_validation_gate(
                            proposition=row.get("proposition") or "",
                            verified_by=[], topic=row.get("topic"), agent=None,
                            source=_span, ground_write=True)
                        _av2 = [w for w in (getattr(_g2, "warnings", None) or [])
                                if w.get("layer")]
                    except Exception:  # noqa: BLE001 — una spiegazione non rompe la vista
                        _av2 = []
                    if _av2:
                        row["layers"] = [w.get("layer") for w in _av2]
                        row["why"] = "· ".join(
                            f"{w.get('layer', '?')}: "
                            f"{w.get('advice') or w.get('reason') or ''}"
                            for w in _av2[:3]).strip()
                        continue

                _gs = row.get("grounding_score")
                _coda = (
                    " Le cause tipiche di un blocco L4 sono un calcolo o una "
                    "conversione che la fonte non enuncia, e una frase che "
                    "contiene piu' affermazioni giudicate insieme: riscrivila "
                    "coi numeri come stanno nella fonte, spezzala, e "
                    "riscrivila con --source.")
                # ⚠️ PRIMA DI DICHIARARE «non ricostruibile», SI GUARDA COSA LA
                # RIGA SA. Dal 07/08 la colonna `quarantined_by` porta il layer
                # accanto al fatto, e da oggi porta quello PRECISO invece
                # dell'etichetta generica: e' esattamente il dato che questo
                # ramo dichiarava perduto. Senza questa lettura il ramo qui
                # sotto ASSERIVA «NON e' L4» su un fatto fermato da L4.1 —
                # la forma d'errore che il commento sopra voleva evitare, con
                # il segno invertito: non piu' una deduzione senza dato, ma un
                # dato presente e non letto.
                _qb = (row.get("quarantined_by") or "").strip()
                # ⚠️ `gate` E `triage` NON SONO LAYER: sono etichette di servizio.
                # `gate` e' il fallback generico del write path; `triage` e' il
                # default di `SemanticMemory.quarantine_fact` (semantic.py:5455),
                # cioe' il ribalto POST-scrittura — dice CHE qualcuno ha fermato
                # il fatto, non QUALE schermo si e' acceso ne' perche'. Trattarle
                # come una diagnosi fa dire alla riga «registra quale layer ha
                # deciso» sopra un dato che non lo registra affatto: e' la forma
                # d'errore che questo intero ramo esiste per evitare — una causa
                # ASSERITA al posto di un «non lo so» — con il segno invertito.
                # I layer veri li produce `chi_ha_quarantinato`: moat / L1 / L4.x.
                if _qb and _qb not in ("gate", "triage"):
                    row["layers"] = [_qb]
                    row["why"] = (
                        f"{_qb}: la riga REGISTRA quale layer ha deciso, e il "
                        "testo della ragione no — l'audit trail e' spento "
                        "(VERIMEM_AUDIT_LOG, opt-in). Il layer basta per "
                        "sapere DOVE guardare: accendi il trail e riscrivi il "
                        "fatto per avere anche la frase, oppure leggi la "
                        "ricevuta di `add()`, che il motivo lo dice sempre."
                        + (_coda if _qb.startswith("L4") else ""))
                    continue
                row["layers"] = []
                if _gs is None:
                    row["why"] = (
                        "causa NON REGISTRATA: nessuno schermo lessicale si "
                        "riaccende su questa frase e il moat non l'ha MAI "
                        "GIUDICATA (grounding_score assente), quindi non e' "
                        "stata fermata da L4 e il motivo esatto non e' piu' "
                        "ricostruibile da questa riga. La ricevuta di "
                        "scrittura il layer lo diceva (`layers`): riscrivila "
                        "con --source e guarda la ricevuta.")
                elif _judged_true(_gs):
                    row["why"] = (
                        f"causa NON REGISTRATA, e NON e' L4: il moat ha "
                        f"giudicato questa frase {float(_gs):.2f}, cioe' l'ha "
                        "APPROVATA, e il fatto e' trattenuto lo stesso. Il "
                        "layer che ha deciso e' un altro e non e' ricostruibile "
                        "da questa riga.")
                else:
                    row["why"] = (
                        f"causa non registrata: nessuno schermo lessicale si "
                        f"riaccende, e il moat ha giudicato {float(_gs):.2f} — "
                        "compatibile con un blocco L4, ma la riga non lo "
                        "afferma." + _coda)
                continue
            row["layers"] = [w.get("layer") for w in avvisi if w.get("layer")]
            row["why"] = " · ".join(
                f"{w.get('layer', '?')}: {w.get('advice') or w.get('reason') or ''}"
                for w in avvisi[:3]).strip()

    #: Quanti fatti guarda `epistemic_health` quando non glielo si dice.
    #:
    #: ⚠️ ERA 2000, e su questo corpus (11 383 non superseduti) significava un
    #: voto calcolato sul 18% — per giunta NON casuale, perche' `list_facts`
    #: ordina `created_at DESC` e i fatti recenti portano una source molto piu'
    #: spesso dei vecchi. Misurato sullo stesso store:
    #:
    #:     limit=2000    n=2 000    composite 0.976   provenance 0.995   0.56s
    #:     limit=100000  n=11 383   composite 0.771   provenance 0.578   1.01s
    #:
    #: Il default risparmiava 0.45 secondi e regalava venti punti di voto. Un
    #: numero che si legge come «il corpus sta benissimo» quando sta a 0.77 non
    #: vale mezzo secondo.
    #:
    #: ⛔ NON e' illimitato, e la ragione e' che non ho misurato un corpus da
    #: milioni di righe: su uno store molto piu' grande questo tetto torna a
    #: mordere, e allora `n_not_examined` sara' > 0 e il campo `sample` dira'
    #: che si sta guardando un campione ordinato. Il comportamento degrada
    #: DICHIARANDOSI, che e' l'unica cosa che il default vecchio non faceva.
    _HEALTH_LIMIT_DEFAULT = 100_000

    def epistemic_health(self, *, limit: int | None = None,
                         threshold: float = 85.0) -> dict[str, Any]:
        """Come sta messo il CORPUS, non un fatto per volta.

        `epistemic_health` era completo, con i suoi test, e irraggiungibile da
        ogni superficie: si potevano mettere i verdetti e non si poteva chiedere
        l'aggregato. Il motivo si legge nel modulo — `_source_of` cerca gli
        attributi ``source`` / ``provenance`` / ``grounding_span``, che il
        dataclass ``Fact`` non ha. E' scritto per una forma di fatto diversa da
        quella del prodotto, e collegarlo alla lettera avrebbe dato un report
        VUOTO che sembra funzionare: peggio che lasciarlo staccato.

        L'adattamento sta qui e il modulo non si tocca. La source in chiaro non
        viene conservata (verificato il 30/07 sui quarantinati), ma la sua
        IMPRONTA si' — ``source_signature`` — e il verdetto sta in
        ``grounding_score``. Quindi ``has_source`` significa «e' passato dal
        moat» e ``grounded`` riusa il punteggio persistito invece di rifare il
        giudizio: costo zero, nessun modello caricato, e aggrega esattamente
        cio' che il write-path ha gia' misurato.

        ``provenance_coverage`` e' il numero che limita gli altri: su un corpus
        che il moat non ha mai giudicato non si puo' affermare niente sulla sua
        salute, e il report lo dice invece di dare un bel voto.
        """
        from .epistemic_health import audit_one, health_report
        if limit is None:
            limit = self._HEALTH_LIMIT_DEFAULT
        audits = []
        for f in self.semantic.list_facts(limit=limit, offset=0):
            punteggio = getattr(f, "grounding_score", None)
            giudicato = isinstance(punteggio, (int, float)) and not isinstance(
                punteggio, bool)
            vista = {
                "id": getattr(f, "id", ""),
                "proposition": getattr(f, "proposition", ""),
                # `source` qui vuol dire «c'e' qualcosa contro cui e' stato
                # controllato»: senza il verdetto non e' auditabile, e va detto
                # con None invece che con uno zero.
                "source": (getattr(f, "source_signature", None) or "moat")
                          if giudicato else None,
            }
            audits.append(audit_one(
                vista, grounder=lambda _s, _p, _g=punteggio: float(_g or 0.0),
                threshold=threshold))
        report = health_report(audits)

        # SU QUANTI fatti e' stato calcolato, e quanti non ne ha aperti. `n` da
        # solo non lo dice: misurato sul corpus vivo il 2026-08-16, il referto
        # diceva `n = 2000` con `composite 0.97`, e 2000 e' il predefinito di
        # `limit` — non una proprieta' del corpus, che di righe ne aveva 11424 e
        # di non superseduti 9534. Un voto alto su un ottavo del corpus si legge
        # identico a un voto alto sul corpus.
        # Gli esclusi sono di DUE specie e vanno tenuti separate: i superseduti
        # la query non li prende mai (`superseded_by IS NULL`), i non esaminati
        # sono vivi e li taglia il limite. Confonderli direbbe «ritirati» di
        # fatti che nessuno ha ritirato.
        # Chiavi piatte, non un dizionario annidato: questo difetto e' stato
        # trovato stampando i soli valori scalari del referto, ed e' cosi' che
        # lo si guarda — un annidamento sarebbe rimasto invisibile allo stesso
        # sguardo che doveva allertare.
        # None e non 0 quando il conteggio non riesce: «non contato» e «zero»
        # sono cose diverse, ed e' la stessa distinzione che questo metodo fa
        # gia' sopra per `source`.
        # 📌 `count_superseded()` invece della query a mano: il metodo esiste
        # dal ciclo #78, fa esattamente questo conteggio, ed era chiamato SOLO
        # dal suo test. Le prime versioni di queste tre righe (referto, pannello
        # `status`, rendiconto) ripetevano la stessa SQL in tre punti mentre la
        # superficie unica c'era gia': se un giorno «superseduto» smette di
        # voler dire `superseded_by IS NOT NULL`, tre copie divergono e una sola
        # no.
        scritti: int | None = None
        ritirati: int | None = None
        try:
            ritirati = int(self.semantic.count_superseded())
            with sqlite3.connect(str(self.semantic.db_path)) as con:
                scritti = int(con.execute(
                    "SELECT COUNT(*) FROM facts").fetchone()[0])
        except Exception:  # noqa: BLE001 — un referto non rompe il chiamante
            pass
        report["n_written"] = scritti
        report["n_superseded"] = ritirati
        # `max(0, ...)`: fra la lettura dei fatti e questi due conteggi il
        # corpus puo' muoversi (piu' scrittori sullo stesso store), e un numero
        # negativo di «non esaminati» non significherebbe niente per chi legge.
        report["n_not_examined"] = (
            max(0, scritti - ritirati - len(audits))
            if scritti is not None and ritirati is not None else None)

        # ⚠️ E DI QUALI 2000 SI TRATTA. `n_not_examined` dice QUANTI restano
        # fuori; non dice che quelli dentro sono i PIU' RECENTI —
        # `list_facts` ordina `created_at DESC` — cioe' un campione NON
        # casuale, distorto in una direzione prevedibile: i fatti recenti
        # portano una source molto piu' spesso di quelli vecchi, perche' e'
        # cambiato il modo in cui li scriviamo, non il corpus.
        #
        # Quanto pesa, misurato sullo stesso store nella stessa esecuzione:
        #
        #                          default (2000)      tutto (11379)
        #     provenance_coverage       0.995              0.578
        #     composite                 0.976              0.771
        #
        # Un voto di 0.98 e uno di 0.77 mandano a fare cose diverse, e col
        # default si legge il primo. Il campo non ricalcola niente e non
        # rallenta: dichiara COME e' stato scelto cio' che si e' guardato,
        # che e' l'unica cosa che il lettore non puo' dedurre dai numeri.
        _parziale = bool(report.get("n_not_examined"))
        report["sample"] = (
            "most recent first (list_facts orders by created_at DESC) — NOT a "
            "random sample: recent facts carry a source far more often, so "
            "every fraction here reads HIGH. Pass a larger `limit` for the "
            "whole corpus."
            if _parziale else
            "whole corpus (nothing left unexamined)")
        return report

    def ignorance(self, queries: list[str], *, floor: float = 0.8,
                  k: int = 5,
                  noise_floor: float | None = None) -> dict[str, Any]:
        """Perche' non lo so: la CLASSE dell'ignoranza e cosa la curerebbe.

        L'astensione e' il claim che distingue questo prodotto, e da sola
        lascia il chiamante dov'era — sa che non sa. Qui ogni domanda torna
        classificata: `no_evidence` (non c'e' niente), `below_floor` (c'e' ma
        non regge), `quarantined_only` (l'evidenza ESISTE ed e' in quarantena —
        la cura e' una fonte o una revisione, non altro retrieval), `conflict`
        (fatti vivi che si contraddicono senza vincitore), `answerable` (non e'
        ignoranza, e si conta lo stesso perche' il denominatore sia onesto).

        Il modulo era completo, con due file di test suoi, e irraggiungibile da
        ogni superficie: zero import fuori da se', zero righe nel README. La
        sua interfaccia combacia gia' con questo client — nessun adattatore,
        a differenza di [epistemic_health][], che era scritto per una forma di
        fatto diversa.

        Sola lettura: la mappa non scrive mai.
        """
        from .ignorance_map import ignorance_map as _mappa
        return _mappa(self, list(queries), floor=floor, k=k,
                      noise_floor=noise_floor)

    def label(self, fact_id: str, kind: str, *, proof: str | None = None,
              bound: float | None = None,
              counterexample: str | None = None) -> bool:
        """Attacca a un fatto il TIPO di garanzia che lo sostiene.

        `proven` (una prova verificabile a macchina, nominata), `unbeaten`
        (ha retto fino a un limite dichiarato, e il limite puo' solo crescere),
        `refuted` (un controesempio nominato, e assorbe). «Held to 10^6» e
        «proven» non si confondono mai — e' la distinzione che il README
        promette in 18 punti.

        Il sottosistema esisteva completo e SCOLLEGATO in entrambe le direzioni:
        `set_epistemic` era chiamato solo da due moduli che nessuna superficie
        raggiunge, e sul corpus vivo del 2026-07-30 la colonna era NULL su tutti
        e 6457 i fatti. Questo e' l'ingresso che mancava; l'uscita ce l'ha gia'
        il contratto (`fact_contract.fact_payload`), e `verimem status` conta le
        etichette perche' un sottosistema fermo a zero si veda.

        L'attrito dell'API non e' smussato nel collegarlo: `proven` senza una
        prova nominata alza `ValueError`, perche' un'etichetta che ci si puo'
        auto-attribuire senza evidenza e' esattamente cio' che questo prodotto
        esiste per impedire.

        Ritorna False — senza alzare — quando la transizione e' vietata dalle
        regole monotone (un fatto `refuted` non torna `proven` perche' qualcuno
        lo richiede): non e' un errore del chiamante, e' il sistema che tiene.
        """
        from .epistemic import make_proven, make_refuted, make_unbeaten
        k = (kind or "").strip().lower()
        if k == "proven":
            etichetta = make_proven(proof or "")
        elif k == "unbeaten":
            etichetta = make_unbeaten(bound if bound is not None else 0)
        elif k == "refuted":
            etichetta = make_refuted(counterexample or "")
        else:
            raise ValueError(
                f"kind sconosciuto: {kind!r}. Sono proven | unbeaten | refuted")
        return bool(self.semantic.set_epistemic(fact_id, etichetta))

    def restore(self, fact_id: str, *, reason: str = "") -> bool:
        """Rescue a wrongly-blocked fact: un-quarantine ``fact_id`` back into the
        live recall view. The public product surface for the reversibility the
        engine already implements — a legitimate vertical fact caught by an L1
        keyword false positive (measured 2026-07-21: 86.7% of untuned
        lawyer/engineer/clinician facts) returns to recall in one call, instead
        of forcing the customer to reach into the internal store or re-add it.

        Returns ``True`` iff a QUARANTINED row existed and was restored; ``False``
        otherwise. Only quarantined facts are restorable — never un-orphans or
        un-supersedes (those are different lifecycle states with their own honest
        recovery), so this surface can't resurrect a scrubbed or superseded fact.
        The flip is audited (``fact_restored`` event) and the fact leaves the
        ``quarantine_log`` because it is live again.

        SECONDARY by design (decided 2026-07-21): the PRIMARY cure for wrongly-
        blocked facts is automatic — keyword-only quarantine is advisory by
        default (ENGRAM_L1_STRICT off), so a benign fact is not blocked in the
        first place and no human restore is needed. This is the rare manual
        escape hatch for a fact that a STRICT deployment still over-blocked.

        SAFETY (pre-commit review 2026-07-21): a human override must not
        resurrect actual poison. Before un-quarantining: (1) a SUPERSEDED fact is
        refused (restore only un-quarantines, never un-supersedes); (2) the
        proposition is re-screened with the injection detector and a text that
        still trips it is REFUSED, so an exfiltration/instruction-override
        payload stays quarantined even if a caller passes its id. HONEST LIMIT
        (deepseek review): there is no persisted per-fact quarantine REASON, so
        restore cannot fully distinguish a security quarantine from an FP — it
        re-screens for injection (the exfil class) but a markup/pollution-class
        quarantine is not separately refused. The complete fix is a persisted
        quarantine_reason column; until then the injection re-screen covers the
        security-critical class and keyword/grounding FPs restore cleanly."""
        # Read the proposition + supersession straight from the store (get()
        # does not surface the text for a quarantined fact) so the injection
        # re-screen sees the real content and a superseded fact is refused.
        text = ""
        topic = ""
        superseded = False
        try:
            with sqlite3.connect(str(self.semantic.db_path)) as con:
                row = con.execute(
                    "SELECT proposition, topic, superseded_by "
                    "FROM facts WHERE id = ?",
                    (fact_id,)).fetchone()
                text = (row[0] if row else "") or ""
                topic = (row[1] if row else "") or ""
                superseded = bool(row[2]) if row else False
        except Exception:  # noqa: BLE001 — unreadable store → restore_fact returns False
            text = ""
        # deepseek review 2026-07-21 (a): a fact that is BOTH quarantined AND
        # superseded must not be resurrected into a half-live state (status
        # flipped but superseded_by still set) — restoring only un-quarantines,
        # it never un-supersedes. Refuse it.
        if superseded:
            return False
        # Re-screen the proposition AND the topic (critic 791a151a, 2026-07-22):
        # the write gate quarantines on injection in EITHER (the topic is
        # caller-controlled and echoed verbatim on every recall hit), so a
        # benign-proposition / poison-TOPIC fact must stay quarantined — the
        # requalify sibling (admission_cleanup.py) already screens both since
        # the 2026-06-20 review; restore mirrored only the proposition and
        # re-opened the hole.
        if text or topic:
            try:
                from .prompt_injection import detect_injection
                if (detect_injection(text).is_injection
                        or detect_injection(topic).is_injection):
                    from .observability import emit as _emit
                    _emit("fact_restore_refused", fact_id=fact_id,
                          reason="injection_screen")
                    return False
            except Exception:  # noqa: BLE001 — screen failure must not crash a read
                pass
        return self.semantic.restore_fact(fact_id, to_status="model_claim",
                                          reason=reason)

    #: ``recall`` is the same operation as ``search`` (HippoAgent naming).
    recall = search


    @staticmethod
    def _fact_view(f: Any, *, fact_id: str = "") -> dict[str, Any]:
        """One fact as the SDK dict — the SAME provenance surface everywhere
        (audit mod.8: get/get_all lacked the fields search exposes, so a
        trust-conditioning caller lost verified_by the moment it re-fetched).

        ``superseded_by`` is here for the same reason, one field over: a
        retracted fact came back through every one of these surfaces looking
        EXACTLY like a live one — same status, no successor named — while the
        default recall had already stopped serving it. Measured on a virgin
        store through the SDK: the row read ``('…', 'Il piano annuale costa
        100 euro.', 'model_claim', 'a8b1b7d03471')`` and the view read
        ``status: model_claim`` with the key absent. ``update()`` promises in
        its own docstring that the old version "stays in the provenance
        chain"; it does, but consulting it did not reveal it had been
        replaced. And supersession is not only triggered by ``update()`` — the
        evolution heuristic fires on its own, so this silence is what makes a
        wrong retraction invisible to anyone not opening the DB by hand.

        It is the RAW column, deliberately, and not a friendlier ``retired``
        flag: a second name for one fact is how two truths start diverging
        (this store already carries 159 skills whose status differs between
        the index and the files). Always present, ``None`` when live — an
        absent key cannot distinguish "not superseded" from "this view does
        not say".
        """
        return {
            "id": getattr(f, "id", fact_id),
            "text": getattr(f, "proposition", ""),
            "status": getattr(f, "status", "model_claim"),
            "grounding_score": getattr(f, "grounding_score", None),
            "topic": getattr(f, "topic", ""),
            "asserted_at": getattr(f, "asserted_at", None),
            "created_at": getattr(f, "created_at", None),
            "source": (getattr(f, "source_episodes", None) or [None])[0],
            # DUE COSE DIVERSE CON LO STESSO NOME, e il README ne promette una
            # sola. La riga sopra serve l'EPISODIO di origine; chi scrive con
            # `add(testo, source="…")` non produce episodi, quindi per lui
            # `source` vale sempre `None` — misurato il 2026-08-13 su un fatto
            # con fonte GIUDICATA (`grounding_score` 98.85, `judged` True), che
            # usciva senza alcun riferimento a cio' contro cui era stato
            # controllato. La vetrina promette «Provenance on every read (who
            # wrote it, SOURCE REF, gate status)»: il primo e il terzo
            # uscivano, il secondo no.
            #
            # L'impronta esiste: il write-path la calcola e la persiste (sopra,
            # `source_signature = "sha256:" + …`) proprio perche' la source in
            # chiaro NON viene conservata. Va quindi ESPOSTA col suo nome, non
            # travestita da `source`: un lettore che trova `sha256:…` dove si
            # aspetta un testo non ha ricevuto una risposta migliore, ne ha
            # ricevuta una sbagliata — ed e' lo stesso errore, all'incontrario,
            # che ha prodotto questo difetto.
            #
            # Additivo come tutto il resto di questa vista: `None` quando il
            # fatto non e' mai passato dal moat, perche' una chiave assente non
            # distingue «senza fonte» da «questa vista non lo dice».
            "source_signature": getattr(f, "source_signature", None) or None,
            # E LA PORZIONE CITATA, che e' la parte piu' utile delle tre.
            # `source_signature` dice CHE una fonte c'era; `grounding_span`
            # dice QUALE PEZZO di quella fonte sostiene il fatto — testo
            # esatto, non un'impronta. Misurato sul corpus reale il 2026-08-14:
            # 1002 fatti su 10262 lo portano valorizzato, e un esempio letto
            # dal db e' prosa vera, non un identificativo.
            #
            # Va servito INSIEME all'impronta e non al suo posto: lo span
            # esiste solo dove il giudice ha citato, l'impronta anche dove ha
            # solo giudicato, e chi legge deve poter distinguere «non c'era
            # fonte» da «c'era e non e' stata citata alla lettera».
            "grounding_span": getattr(f, "grounding_span", None) or None,
            "verified_by": list(getattr(f, "verified_by", None) or []),
            "superseded_by": getattr(f, "superseded_by", None) or None,
            # CIO' CHE IL CANALE MCP SERVIVA E QUESTO NO. Il docstring qui
            # sopra promette «the SAME provenance surface everywhere», e il
            # 2026-08-02 quella frase aveva gia' fatto trovare `superseded_by`
            # mancante. Non bastava: sullo stesso fatto i due contratti di
            # uscita divergevano ancora su cinque campi.
            #
            #   MCP  fact_payload -> confidence confidence_tier EPISTEMIC
            #                        meta_narrative writer_principal + …
            #   SDK  _fact_view   -> (nessuno di questi)
            #
            # `epistemic` e' quello che ha fatto trovare il difetto:
            # `label(fid, 'proven', proof=…)` risponde True, il DB contiene
            # `{"kind": "proven", "proof": "listino firmato"}`, e nessuna
            # superficie SDK lo serviva — ne' `search`, ne' `get`, ne'
            # `explain`. Il tier che dice PERCHE' un fatto merita fiducia si
            # scriveva e non si rileggeva.
            #
            # ADDITIVO di proposito, non una delega a `fact_payload`: i due
            # usano nomi diversi per la stessa cosa (`text` contro
            # `proposition`), e allinearli romperebbe ogni chiamante dell'SDK.
            # Si aggiunge cio' che manca; niente sparisce.
            #
            # Sempre presenti, `None` quando non c'e': una chiave assente non
            # distingue «nessuna garanzia» da «questa vista non lo dice».
            "epistemic": getattr(f, "epistemic", None) or None,
            "confidence": getattr(f, "confidence", None),
            "confidence_tier": getattr(f, "confidence_tier", None),
            "writer_principal": getattr(f, "writer_principal", None) or None,
        }

    def get(self, fact_id: str) -> dict[str, Any] | None:
        """Fetch one stored fact by id (with its provenance), or None."""
        f = self.semantic.get(fact_id)
        if f is None:
            return None
        return self._fact_view(f, fact_id=fact_id)

    def delete(self, fact_id: str, *, purge_history: bool = False,
               principal: str | None = None) -> bool:
        """Forget a fact by id (privacy / GDPR). True iff at least a row was removed.

        ``purge_history=True`` — the GDPR-grade delete (probe-confirmed defect
        2026-07-06: a plain delete removes ONE row while superseded predecessors
        carrying the SAME sensitive datum survive and RESURFACE via deep recall
        and ``as_of`` time travel). It removes the whole supersession chain —
        predecessors (recursive) and forward successors — plus their
        unresolved-dispute ledger entries. Default False = single-row delete,
        behaviour unchanged.

        ``principal`` (0.8 mutation audit) is stamped like ``add()``'s: the
        caller may name a finer identity, otherwise this client's own
        (``sdk:local`` by default) is recorded in the tamper-evident chain —
        never None. Purged rows are audited with action ``purge``."""
        _who = principal or self._principal
        if not purge_history:
            return self.semantic.delete(fact_id, principal=_who)
        ids: set[str] = set()
        # forward: the live successors this fact was replaced by
        try:
            for f in self.semantic.get_supersession_chain(fact_id):
                ids.add(getattr(f, "id", ""))
        except Exception:  # noqa: BLE001 — best-effort walk, delete goes on
            ids.add(fact_id)
        # backward: EVERY predecessor generation (full closure, all branches —
        # a partial purge would leave sensitive rows resurrectable via as_of)
        frontier = list(ids)
        while frontier:
            nxt: list[str] = []
            for fid in frontier:
                try:
                    for p in self.semantic.direct_predecessors(fid, limit=1000):
                        pid = getattr(p, "id", "")
                        if pid and pid not in ids:
                            ids.add(pid)
                            nxt.append(pid)
                except Exception:  # noqa: BLE001
                    continue
            frontier = nxt
        removed = False
        for fid in ids:
            try:
                removed = self.semantic.delete(
                    fid, principal=_who, action="purge") or removed
            except Exception:  # noqa: BLE001 — one failed row must not stop the purge
                # NB: with the fail-closed audit this row was NOT removed
                # either (mutation and audit share one transaction) — the
                # purge is honestly partial, never silently untracked.
                continue
        # scrub the dispute ledger referencing purged facts (best-effort)
        try:
            import sqlite3

            from .contradiction import ContradictionStore
            cs = ContradictionStore(self.semantic.db_path)
            with sqlite3.connect(str(cs.db_path if hasattr(cs, "db_path")
                                     else self.semantic.db_path)) as con:
                qmarks = ",".join("?" for _ in ids)
                con.execute(
                    f"DELETE FROM contradictions WHERE fact_a_id IN ({qmarks}) "
                    f"OR fact_b_id IN ({qmarks})", (*ids, *ids))
                con.commit()
        except Exception:  # noqa: BLE001 — ledger scrub is best-effort
            pass
        return removed

    def get_all(self, *, topic: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """List stored facts (with provenance), newest-relevant first. mem0/Zep parity."""
        return [self._fact_view(f)
                for f in self.semantic.list_facts(limit=limit, topic=topic)]

    def update(self, fact_id: str, text: str, *, topic: str | None = None) -> dict[str, Any]:
        """Revise a fact. Engram facts are immutable + auditable, so an update STORES a new
        fact (through the gate) and SUPERSEDES the old one — the old version stays in the
        provenance chain (see :meth:`history`), it is not destroyed. Returns the add result
        plus ``supersedes``."""
        old = self.semantic.get(fact_id)
        if old is None:
            return {"updated": False, "reason": "not found"}
        res = self.add(text, topic=topic or getattr(old, "topic", "user"))
        _undo_id: str | None = None
        if res.get("stored") and res.get("id"):
            try:
                _sup = self.semantic.supersede(fact_id, res["id"],
                                               principal=self._principal,
                                               reason="sdk update")
                _undo_id = _sup.get("undo_op_id")
            except Exception as exc:  # noqa: BLE001
                return {**res, "updated": True, "supersedes": fact_id, "supersede_warning": str(exc)}
        # ⚠️ L'handle poteva gia' esserci, sotto un ALTRO NOME. `add()` supersede
        # da solo quando riconosce un'evoluzione della stessa fonte, e in quel
        # caso l'op reversibile la crea LUI: la chiamata esplicita qui sopra
        # trova il vecchio gia' superseduto e non ne apre una seconda, quindi
        # `_undo_id` resta vuoto. Misurato il 2026-08-16 su `update()`::
        #
        #     flow.supersession  reason='same-source evolution' reversible=True
        #                        undo_op_id=fcc15331752c4d33
        #     ricevuta:  superseded_undo_ops {'130697c37e61': 'fcc15331752c4d33'}
        #                undo_op_id          ASSENTE
        #
        # ⇒ Chi corregge un fatto NON poteva tornare indietro con la chiave che
        # `undo()` documenta — e l'informazione c'era, a due chiavi di distanza.
        # 🔑 Non e' un dato mancante: e' lo stesso dato con due nomi, e la
        # promessa era scritta su quello che questo percorso non riempie.
        if _undo_id is None:
            _undo_id = (res.get("superseded_undo_ops") or {}).get(fact_id)
        out = {**res, "updated": bool(res.get("stored")), "supersedes": fact_id}
        if _undo_id is not None:
            out["undo_op_id"] = _undo_id
        return out

    def retirement_log(self, *, limit: int = 50, since: float | None = None,
                       topic: str | None = None, reason: str | None = None,
                       with_text: bool = False) -> list[dict[str, Any]]:
        """The retirements, newest first, as (loser, winner) pairs — the
        ``quarantine_log`` equivalent for supersessions. Each row carries
        topics, reason, timestamp, and the ``undo_op_id`` handle when the
        retirement is reversible (``undo(op_id)`` reverses it). Measured
        2026-08-04: seven read surfaces said nothing about a retirement;
        this is the window. Metadata by default; ``with_text=True`` adds
        the propositions for local judging."""
        from .retirement_log import retirement_log as _rlog
        return _rlog(self.semantic, limit=limit, since=since, topic=topic,
                     reason=reason, with_text=with_text)

    def tier_inventory(self) -> dict[str, Any]:
        """Where each tier actually lives, how many rows it holds, and
        which nearby files carry its name without being it.

        Measured 2026-08-05: the five entity tables inside ``semantic.db``
        are an empty migration shell — the graph lives in
        ``entity_kg/entity_kg.db`` with 9078 entities and 87387 edges, and
        counting the shell produced "the entity tier is empty". A missing
        store reads ``unavailable``, never ``0``: an empty container and
        an absent one return the same number, and only the second
        announces itself."""
        from .tier_inventory import tier_inventory as _ti
        return _ti(data_dir=Path(self.semantic.db_path).resolve().parent.parent)

    def verdict_mismatches(self, *, limit: int = 50,
                           topic: str | None = None) -> dict[str, Any]:
        """Where the moat's verdict and the fact's fate disagree, both ways:
        judged true and withheld, judged false and served, plus the
        contested band where the outcome depended on which judge was up.

        It decides nothing — it lists, like the retirement log lists pairs.
        The thresholds travel in the result because "true" and "false" here
        are two cuts, and a number without its definition is the defect this
        branch cures. Measured on the real corpus 2026-08-05: 11 quarantined
        facts carry a verdict >= 90 and 10 served facts carry one below the
        admission cut, down to 0.22."""
        from .retirement_log import verdict_mismatches as _vm
        return _vm(self.semantic, limit=limit, topic=topic)

    def survivability(self, *, topic: str | None = None) -> dict[str, Any]:
        """The canonical quartet written/servable/retired/quarantined with
        its formula. A fact disappears in TWO ways; any 'alive' count that
        ignores one of them hides half the loss (retracted 2026-08-04)."""
        from .retirement_log import survivability_counts as _scounts
        return _scounts(self.semantic, topic=topic)

    def undo(self, op_id: str) -> dict[str, Any]:
        """Reverse a destructive op (forget / supersede) by its handle —
        the handle arrives in ``add()['superseded_undo_ops']``,
        ``update()['undo_op_id']`` or ``retirement_log()`` rows. Restores
        the pre-op row; the winner of a supersession stays alive (the
        ping-pong ends with BOTH facts, not another retirement)."""
        return self.semantic.undo_destructive_op(op_id)

    def history(self, fact_id: str) -> list[dict[str, Any]]:
        """The FULL supersession trail of the lineage containing ``fact_id`` —
        the provenance trail no cosine-only store has:
        ``[{id, text, status, superseded_by}, …]`` oldest→newest.

        Any id in the chain returns the same trail (audit mod.8, reproduced
        2026-07-17): the walk was forward-only, so the id a caller most
        naturally holds — the CURRENT fact, e.g. from ``search`` — returned a
        1-entry "trail" while the oldest id returned the whole story. Now the
        walk first rewinds to the lineage root (``direct_predecessors``,
        following the primary — most recently retired — predecessor at each
        step; a multi-predecessor MERGE keeps its side branches reachable via
        their own ids), then plays forward as before."""
        start = self.semantic.get(fact_id)
        if start is None:
            return []
        # rewind to the lineage root (cycle-guarded like the forward walk)
        root = start
        back_seen = {getattr(start, "id", "")}
        while True:
            try:
                preds = self.semantic.direct_predecessors(
                    getattr(root, "id", ""), limit=1)
            except Exception:  # noqa: BLE001 — degrade to the forward-only view
                break
            if not preds or getattr(preds[0], "id", "") in back_seen:
                break
            root = preds[0]
            back_seen.add(getattr(root, "id", ""))
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        cur = root
        while cur is not None and getattr(cur, "id", None) not in seen:
            cid = getattr(cur, "id", "")
            seen.add(cid)
            nxt = getattr(cur, "superseded_by", None)
            # ⚠️ RISOLUZIONE DI UN CONFLITTO (2026-08-09) — PREVALE IL LATO DI
            # MAIN, e la ragione e' che l'altro era SBAGLIATO PER QUESTA
            # SUPERFICIE. Lo stesso difetto (history rendeva quattro campi
            # invece di quattordici) era stato curato su un ramo usando
            # `fact_contract.fact_payload`, che e' il contratto della porta
            # MCP. Ma `Memory.history` e' SDK, e il commento di `_fact_view`
            # dichiara che la divergenza fra le due viste e' DELIBERATA:
            # «ADDITIVO di proposito, non una delega a `fact_payload`: i due
            # usano nomi diversi per la stessa cosa (`text` contro
            # `proposition`), e allinearli romperebbe ogni chiamante dell'SDK».
            # ⇒ Quella versione avrebbe portato nell'SDK i campi che sono solo
            #   dell'MCP (confidence_tier, meta_narrative, writer_principal) e
            #   lasciato fuori `epistemic`. Il merge ha trovato un errore, non
            #   una scelta fra due lati pari.
            # LA VISTA CONDIVISA, non la TERZA copia scritta a mano.
            #
            # Qui c'era `{id, text, status, superseded_by}`: quattro chiavi
            # contro le quattordici che `get`/`get_all`/`search` garantiscono
            # (censite). Su quelle superfici la promessa «provenance on
            # every read» regge; qui cadevano tutte insieme — provenienza,
            # verdetto, tempo, autore.
            # ⚠️ E colpisce cio' che si e' appena acceso: col routing temporale
            # su "auto" (2aa8a4b1) la storia ARRIVA, ma serviva versioni senza
            # fonte, senza grounding, senza data e senza scrittore. Chi deve
            # SCEGLIERE FRA VERSIONI — l'unico motivo per cui si chiama
            # `history` — aveva in mano due testi e nessun criterio.
            # 🔑 E' la terza copia della stessa vista, e la seconda era gia'
            # costata: accanto all'uso di `_fact_view` in `search` sta scritto
            # come fu trovata — «superseded_by was added to the shared view and
            # search went on without it. Two copies drift, and this one already
            # had». Per questo la cura e' la PROIEZIONE e non quattro campi
            # aggiunti a mano, che sarebbe la quarta copia.
            # Additivo: le quattro chiavi storiche restano (`text` non e' nella
            # vista condivisa, che usa `text` come alias di `proposition`).
            _voce = dict(self._fact_view(cur))
            _voce.update({"id": cid, "text": getattr(cur, "proposition", ""),
                          "status": getattr(cur, "status", ""),
                          "superseded_by": nxt})
            chain.append(_voce)
            cur = self.semantic.get(nxt) if nxt else None
        return chain

    #: I VERBI DELLA RIGA DI COMANDO, sull'SDK con lo stesso nome. Percorrendo
    #: il ciclo di vita di un fatto come lo farebbe chi usa il prodotto —
    #: scrivo, rileggo, correggo, dimentico — le due capacità c'erano ma con
    #: un altro nome, e `Memory.correct` sollevava AttributeError mentre
    #: `verimem correct` esisteva. Il docstring di `delete` si apre perfino con
    #: «Forget a fact by id»: usava la parola della CLI per descrivere un
    #: metodo chiamato in un altro modo.
    #:
    #: Non mancava una capacità — mancava il nome con cui l'utente la cerca, e
    #: il cricchetto sulle capacità (`4cea1aa8`) non poteva vederlo perché
    #: confronta i NOMI e `update` esiste. Alias e non reimplementazioni, come
    #: `recall`: due implementazioni della stessa operazione divergono.
    correct = update
    forget = delete

    def forget_with_report(self, fact_id: str) -> dict[str, Any]:
        """Delete a fact AND say where it is still readable.

        ``forget`` clears every live table (the entity graph included —
        verified), but the Auto-Dream worker keeps whole-DB copies:
        rotating ones for a few hours, MANUAL ones forever (one from May 12
        still holds 60 facts the live store dropped). The deletion is real
        and its effect is partial, and until now no surface said so — the
        same class as the invisible retirements this release cures.

        Returns ``{removed, fact_id, residual_copies: [...]}``; each copy
        carries ``rotates`` so "for a few hours" and "forever" are
        distinguishable. Reporting NEVER blocks the erasure: a scan failure
        degrades to an empty list."""
        from .residual_copies import forget_with_report as _fwr
        return _fwr(self.semantic, fact_id, principal=self._principal or "sdk")


#: Alias for users who expect a ``Client`` name (mem0/Zep ergonomics).
Client = Memory

__all__ = ["Memory", "Client"]

# --- adjudication receipt (Phase 0.1/0.2) --------------------------------------

def _evidence_class(gate: Any, verified_by: Any, warnings: list) -> str:
    """How this write was adjudicated - the HONEST tier label.

    * ``cross_encoder`` / ``llm_judge`` - an L4 entailment judge scored it (the
      local CE vs an injected llm). A probabilistic filter, NOT a proof.
    * ``ungated`` - a source was given but no judge was reachable: entailment
      NOT verified (never passed off as verified).
    * ``receipt_declared`` - verified_by refs were declared but not (yet)
      content-verified on this path.
    * ``lexical_only`` - only the L1 lexical screen ran (no source, no judge).
    """
    judge = getattr(gate, "judge", None)
    if judge is not None:
        return "cross_encoder" if judge == "local" else "llm_judge"
    if any(str(w.get("layer", "")).startswith("L4-skipped") for w in warnings):
        return "ungated"
    if verified_by:
        return "receipt_declared"
    return "lexical_only"


#: Which blocking layer OWNS the verdict, most-decisive first. The reason is
#: taken from the highest-priority layer that actually fired - decision-dependent,
#: NOT the last-appended warning (which can be an advisory L4-skipped note that
#: masks the real block). L4-skipped/SOURCE_TRUST are advisory-most, last.
#: L'ordine in cui un blocco si prende la ragione mostrata. ⚠️ `L4.1` c'e'
#: perche' senza finiva IN FONDO (rank di default) e perdeva contro
#: `L4-skipped`, che NON e' un blocco ma l'avviso «il giudice non e' girato»:
#:
#:     warnings ['L4.1', 'L4-skipped']
#:       prima ->  «nessun giudice disponibile, controllo non eseguito»
#:       dopo  ->  «il claim afferma un valore che la fonte non contiene: …»
#:
#: E i due COESISTONO davvero, non e' un caso di laboratorio: L4.1 e' un
#: controllo lessicale sui numeri e gira anche quando il giudice non c'e'.
#: Sta dopo `L1` e non prima, per la stessa precedenza di
#: `chi_ha_quarantinato` — le due superfici devono ordinare uguale, o
#: l'etichetta e la spiegazione indicano due layer diversi.
#:
#: ⛔ Ci sta SOLO `L4.1`, che e' stato misurato bloccare. `L4.2` no: sui 7
#: fatti salvati il 21/08 ne accompagna 5 e tutti e 5 sono AMMESSI — e' un
#: avviso, e metterlo qui gli farebbe prendere il merito di blocchi non suoi.
_BLOCK_LAYER_PRIORITY = ("L3", "L4-grounding", "L1", "L4.1",
                         "SOURCE_TRUST", "L4-skipped")


def _is_advisory_layer(layer: str) -> bool:
    """An ``*-observe`` layer (``L3-semantic-observe``, ``SOURCE_TRUST-observe``) is an
    OBSERVE-mode advisory: it surfaces a would-be block for MEASUREMENT but does not
    cause the disposition. It must never own a receipt's block reason nor be credited
    in the trust ledger — otherwise observe mode measures itself as the blocker and its
    whole purpose (gauge a layer's block rate BEFORE enforcing) is defeated. NB: the
    layer string ``L3-semantic-observe`` also ``.startswith("L3")`` (rank 0), so without
    this guard it would out-rank a real L1/L4 block in ``_reason_from_warnings``.

    ``*-graded`` layers (``L4-grounding-graded``, ``L4-review-graded``, graded
    admission — design bf5d322) are the same class from the ledger's point of
    view: they record an ADMISSION decision, never a block, so crediting one as
    an acting blocker (critic 514cdec3 falsification caveat 4: possible when
    ANOTHER layer quarantines the same write) would pollute exactly the
    attribution the pre-registered flip A/B has to read."""
    s = str(layer)
    return s.endswith("-observe") or s.endswith("-graded")


def _blocking_layers(warnings: list) -> list[str]:
    """Sorted distinct layers that ACTED on the write — advisory ``*-observe`` layers
    excluded, so the trust ledger ``by_layer`` never credits an observe advisory for a
    block it did not cause."""
    return sorted({layer for w in warnings
                   if (layer := str(w.get("layer", "")))
                   and not _is_advisory_layer(layer)})


def _audit_log_on() -> bool:
    """Opt-in per-write adjudication audit trail (VERIMEM_AUDIT_LOG). Default OFF: it
    persists every write's verdict AND proposition to a sibling DB — a data-retention
    choice the operator makes explicitly, and extra write-path I/O they opt into."""
    import os
    return os.environ.get("VERIMEM_AUDIT_LOG", "").strip().lower() in (
        "1", "on", "true", "yes")


def _reason_from_warnings(warnings: list) -> str:
    """The human reason for a block, from the highest-priority BLOCKING layer
    that carries text - so a fact quarantined by L1 is not explained by an
    advisory L4-skipped note that merely happened to be appended later. Advisory
    ``*-observe`` layers are excluded: they did not cause the block (an admitted
    write whose only note is an observe advisory has no block reason -> "")."""
    def _rank(w: dict) -> int:
        layer = str(w.get("layer", ""))
        for i, p in enumerate(_BLOCK_LAYER_PRIORITY):
            if layer.startswith(p):
                return i
        return len(_BLOCK_LAYER_PRIORITY)
    acting = [w for w in warnings
              if (w.get("advice") or w.get("reason"))
              and not _is_advisory_layer(str(w.get("layer", "")))]
    if not acting:
        return ""
    best = min(acting, key=_rank)
    return best.get("advice") or best.get("reason") or ""


def _judge_of_record_dict(judge: Any) -> dict[str, Any] | None:
    """Judge-of-record: backend + (for the local CE) the model identity that
    actually loaded - the CE's known 7% Spanish entity-substitution escape is
    model-SPECIFIC, so naming the model lets a caller assess exposure. The
    injected-llm model id is not visible at the gate layer (None, honest, not
    invented); ``version`` is a per-file fingerprint enriched in a follow-up."""
    if judge is None:
        return None
    model = None
    if judge == "local":
        try:
            from .local_grounding import get_local_judge
            model = get_local_judge().model_dir.name
        except Exception:  # noqa: BLE001 - identity is best-effort, never fatal
            model = "local_gate_ce"
    return {"backend": judge, "model": model, "version": None}


def _confidence_tier(score: Any, judge: Any, thr: Any) -> str:
    """Coarsened, judge-agnostic trust label (delegates to the gate's band)."""
    from .grounding_gate import confidence_tier
    return confidence_tier(score, judge, thr)


def _adjudication(gate: Any, *, disposition: str, verified_by: Any,
                  warnings: list) -> dict[str, Any]:
    """The write verdict, ALWAYS returned to the caller: what decided, how
    confident (score/threshold/margin), and - when blocked - WHY. A quarantine
    is a visible verdict here, never a silent exclusion.

    NB ``margin = score - threshold`` is INTRA-JUDGE only: the local-CE and the
    llm judge use different score scales (threshold is resolved per-judge at
    decision time), so margins are NOT comparable across ``evidence_class``
    values. ``judge.backend`` distinguishes them. A judge-agnostic
    ``confidence_tier`` is the follow-up. ``evidence_class`` reports the single
    STRONGEST evidence actually exercised (a judge score outranks a declared
    receipt); it is not a full evidence list."""
    score = getattr(gate, "grounding_score", None)
    thr = getattr(gate, "threshold", None)
    judge = getattr(gate, "judge", None)
    reason = ""
    if disposition != "admitted":
        # 1) the deciding layer's own words; 2) the gate's advice; 3) synthesize
        # from the numbers; 4) a generic non-empty verdict. Never empty.
        reason = _reason_from_warnings(warnings) or (getattr(gate, "advice", "") or "")
        if not reason:
            if score is not None and thr is not None and score < thr:
                # only claim "below threshold" when it actually IS below — a fact the
                # judge ADMITTED (score>=thr) that a store-time screen later flipped
                # must not be labelled a grounding failure (opus critic F1 facet).
                tier = "cross_encoder" if judge == "local" else "judge"
                reason = f"{tier} score {score:g} below threshold {thr:g}"
            elif disposition == "quarantined":
                reason = ("quarantined by a store-time integrity screen "
                          "(e.g. prompt-injection); kept out of default recall")
            elif disposition == "routed_telemetry":
                reason = ("machine-telemetry topic routed to the telemetry "
                          "table by the admission gate (non-lossy)")
            else:
                reason = "rejected by the write gate"
    return {
        "disposition": disposition,
        "evidence_class": _evidence_class(gate, verified_by, warnings),
        "judge": _judge_of_record_dict(judge),
        "score": score,
        "threshold": thr,
        "margin": (None if score is None or thr is None
                   else round(float(score) - float(thr), 4)),
        "reason": reason,
        "confidence_tier": _confidence_tier(score, judge, thr),
    }
