"""Evolution-vs-conflict policy for the write path (task #48 core).

The contradiction judge (lexical L3 / NLI L3-semantic) only tells us *that* a new write
clashes with a stored fact. What to DO about it depends on provenance + time:

  * the SAME source restating its own claim with a newer value is an **evolution** —
    the world changed and the old value should be superseded (keeping both is how a
    memory serves a stale, "confabulated" answer at recall time);
  * a DIFFERENT source disagreeing is a **conflict** — a real dispute; never auto-retire
    either side on the strength of a mere timestamp.

This is deterministic (canonical source + assertion time), independent of the NLI
model's temporal reasoning — which the local cross-encoder does NOT have (measured
2026-07-19: it flags a same-source value change as a contradiction). Pure and
observation-only; it decides a LABEL, it does not mutate anything.
"""
from __future__ import annotations

import re
from typing import Any

from .source_trust import canonical_source

__all__ = ["canonical_source_of", "declared_identity", "is_same_source",
           "due_fonti_dichiarate_e_diverse",
           "classify_write_relation", "references_fact"]

#: A fact id as written in prose: 12 hex chars, on its own token boundary.
#: Shorter ids are refused outright — a 3-char "id" appears by chance and would
#: turn every write into a reference, which ends supersession instead of
#: guarding it.
_MIN_ID_LEN = 8


def references_fact(new_text: Any, old_id: Any) -> bool:
    """True when the new write NAMES the stored fact's id.

    Found by dogfooding, 2026-07-25, on my own writes. The memory protocol says
    to accompany a long fact with a short "lure" so semantic recall can find it;
    the lure named the fact's id, the judge read the pair as a contradiction and
    the lure SUPERSEDED the fact it existed to make findable. Verified: recall
    returned the lure and not the 2993-char detail, so the lure became a pointer
    to something the store would no longer hand back — the very failure this
    product exists to prevent.

    A lexical or NLI judge cannot tell "see X" from "X is wrong", so this does
    not try: naming an id makes the pair AMBIGUOUS, and on ambiguity the caller
    keeps both. Losing a true fact is irreversible, keeping two is not — the
    same asymmetry :func:`quantity_match.numeric_conflict` states as "a false
    conflict downgrades a true fact, the opposite of the trust we sell".
    Lineage still records which came later.
    """
    if not new_text or not old_id:
        return False
    fid = str(old_id).strip()
    if len(fid) < _MIN_ID_LEN:
        return False
    return re.search(rf"(?<![0-9A-Za-z]){re.escape(fid)}(?![0-9A-Za-z])",
                     str(new_text), re.IGNORECASE) is not None


def canonical_source_of(fact: Any) -> str:
    """The reputation key of a fact's writer: the ``canonical_source`` of its
    ``verified_by`` when that names a source, else its ``source_signature``, else
    ``"user"``.

    L'ORDINE E' IL CONTENUTO DELLA REGOLA: una penna DICHIARATA decide, e la
    firma della source entra solo dove il ``verified_by`` non dice niente —
    dove cioe' ``canonical_source`` ripiega su ``"user"`` per tutti e «stessa
    fonte» sarebbe vero per costruzione. Aggiunge risoluzione dentro
    l'anonimato; non ne toglie a chi si e' dichiarato.

    ⚠️ DAL 2026-09-06 LEGGE ``source_signature``, e la storia di questa riga sta
    tutta qui sotto perche' e' cambiata tre volte: il docstring prometteva la
    signature fino al 2026-08-21 senza che il codice la leggesse, la cura che
    gliela faceva leggere e' stata scritta e RITIRATA il 2026-08-04, e il
    2026-09-06 la misura che l'aveva fatta ritirare si e' rivelata un misuratore
    sbagliato (l'ultimo blocco). Chi legge parta dalla riga sopra, non dai
    paragrafi storici.

    Il comportamento che il docstring prometteva e il codice non aveva, fino al
    2026-08-21:

        canonical_source_of(<verified_by=None, source_signature="sha256:AAAA">) -> "user"
        canonical_source_of(<verified_by=None, source_signature="sha256:BBBB">) -> "user"
        is_same_source(a, b) -> True          # firme DIVERSE, stesso bucket

    ⚠️ COSA COSTA, misurato sul corpus vivo il 2026-08-21: due fatti anonimi
    (``writer_role='user'``, nessun ``verified_by``) sono SEMPRE «stessa fonte»,
    quindi uno puo' ritirare l'altro come ``same-source evolution`` anche se le
    loro fonti sono diverse. Due casi reali, con l'id:

        bc63e008787f  grounding 99.98  ritirato da  74a11ff32dea  (nessuna source)
        7a0fbf8ad953  grounding 99.83  ritirato da  83407efc3a25  (nessuna source)

    e in entrambi il ``source_signature`` dei due lati ERA DIVERSO: il dato che
    li distingueva esisteva, e non veniva letto.

    PERCHE' LA SIGNATURE (2026-08-04, da un caso su un registro pazienti).
    «Il paziente Rossi pesa 70 kg» veniva RITIRATO da «Il paziente Bianchi pesa
    95 kg», reason `same-source evolution`. Il banco, una variabile per volta:

        topic DIVERSI, nessuna source        entrambi vivi
        stesso topic, source DIVERSE         NE RESTA UNO
        stesso topic, verified_by diversi    entrambi vivi

    La riga di mezzo era il difetto: chi scrive passa `source=` credendo di
    dichiarare la provenienza — e' cio' che il prodotto raccomanda, ed e' cio'
    che accende il moat — e qui si guardava solo `verified_by`, quindi due
    fatti senza ref erano entrambi `"user"` e il secondo «evolveva» il primo.
    Sul corpus vivo 500 fatti su 6075 hanno un `verified_by`: per gli altri
    5575 qualunque coppia nello stesso topic era un candidato al ritiro,
    qualunque cosa dicesse.

    Non si inventa un criterio nuovo: si smette di buttare via cio' che chi
    scrive ha gia' dichiarato.

    ⛔ LA CURA E' STATA SCRITTA, MISURATA E RITIRATA IL 2026-08-04. Leggere la
    ``source_signature`` qui dentro colpisce il bersaglio e rompe il presidio:

        caso                                riga attuale   con la signature
        source DIVERSE (due cartelle)          1 vivo         2 vivi   ✅
        STESSA source, valore aggiornato       1 vivo         2 vivi   ❌
        nessuna source (compatibilita')        1 vivo         1 vivo   ✅

    La seconda riga e' una regressione vera: l'aggiornamento legittimo smette
    di ritirare. E la funzione, chiamata da sola, e' CORRETTA in tutti e tre i
    casi — stessa signature -> ``evolution``, diverse -> ``conflict``, assente
    -> ``evolution``; e il fatto riletto dal DB espone davvero l'attributo. Il
    comportamento cambia piu' a valle, in un punto che non e' stato isolato.

    Una cura che colpisce il bersaglio per una ragione che non si sa spiegare
    non si consegna: e' la stessa lezione di «misurare una cura a livello di
    FUNZIONE», dove il verdetto isolato diceva il contrario dell'end-to-end.
    Resta il pezzo che CONSERVA l'impronta in ``client.add`` — additivo, non
    cambia comportamento — e il test la documenta come xfail strict.

    ═══ 2026-09-06: LA RIGA SOPRA E' STATA RIMESSA, E LA «REGRESSIONE» NON C'ERA.

    Il presidio del 04/08 misurava **«quanti fatti restano vivi»** e dava 1-1-1 sui
    tre casi. Rimisurato separando i due meccanismi::

        caso                        vivi  superseded  quarantined  layer
        source DIVERSE                1        1           0       L3-supersession
        STESSA source, valore nuovo   1        0           1       **L4.1**
        nessuna source                1        1           0       L3-supersession

    Il caso di mezzo **non passava dalla supersessione**: `L4.1` lo quarantinava, ed
    era giusto — la source era quella VECCHIA e il valore nuovo non ci stava dentro.
    Non era «l'aggiornamento legittimo che la cura rompeva»: era un claim non
    sostenuto dalla sua fonte. **Un numero che fonde ritiro e quarantena non e' un
    misuratore**, ed e' per questo che la regressione «non si sapeva spiegare».

    Rifatto BENE — source aggiornata INSIEME al valore, quindi testo e firma diversi
    — i cinque casi del presidio danno tutti `superseded=1, quarantined=0` dallo
    stesso ramo. La cura non rompe nulla di misurato, e il difetto che cura e' stato
    riprodotto in laboratorio: due bracci di un A/B («GRADED_ADMISSION acceso: 296
    falsi» / «spento: 40 falsi», due source distinte) e il secondo ritira il primo.
    Sul corpus: **155 ritiri** con `same-source evolution` fra due firme diverse,
    **0 prima del default ON del 19/07 e 155 dopo**, 153 con grounding >= 85, e
    **54 sbagliati su 60 letti uno per uno**.

    Il banco: `docs/stato-reale/banchi/il-presidio-con-le-due-colonne.py`.

    ⚠️ MA UNA REGRESSIONE C'ERA, e non era quella: l'ha trovata
    `test_CONTROLLO_quando_supersede_DAVVERO_l_avviso_ci_deve_essere` mezz'ora
    dopo. La prima stesura tornava la firma PRIMA di guardare il `verified_by`, e
    cosi' la stessa penna dichiarata che corregge il proprio valore — «100 euro»
    -> «150 euro», citando ogni volta il testo nuovo come `source` — smetteva di
    ritirare: due prezzi vivi, uno vecchio. E' l'aggiornamento piu' comune che
    esista. Da li' l'ordine attuale, che e' il contenuto della regola: **la penna
    decide, la firma discrimina solo dentro l'anonimato** — cioe' esattamente
    dove stanno i 155.

    🔑 Vale la pena dirlo perche' e' la seconda volta in un giorno: il 04/08 la
    cura fu ritirata per una regressione che il misuratore mostrava e che non
    c'era; il 06/09 e' stata consegnabile solo perche' un controllo positivo ne
    ha mostrata una VERA che il presidio non copriva. Lo stesso presidio, due
    verdetti sbagliati in versi opposti.
    """
    _base = canonical_source(getattr(fact, "verified_by", None) or None)
    if _base == "user":
        # ⚠️ IL RIPIEGO SU `"user"` NON VUOL DIRE «non ha dichiarato niente»:
        # `canonical_source` riconosce solo `source-doc:X:...` e `doc:X`, quindi
        # `['contratto']`, `['Cartella clinica']` e perfino `['commit:abc123']`
        # finiscono tutti li' dentro — misurato il 06/09. Prima di scendere alla
        # firma si guarda il `verified_by` GREZZO: se c'e', E' una dichiarazione,
        # anche in una forma che il canonicalizzatore non sa leggere.
        _raw = [str(x) for x in (getattr(fact, "verified_by", None) or [])]
        if _raw:
            return "vb:" + "|".join(_raw)
    if _base != "user":
        # ⚠️ UNA PENNA DICHIARATA DECIDE, E LA FIRMA NON LA SCAVALCA. La prima
        # stesura di questa cura tornava la `source_signature` per prima, e
        # rompeva l'aggiornamento piu' comune che esista: la STESSA fonte
        # (`verified_by=["source-doc:billing:1"]`) che corregge il proprio
        # valore — «100 euro» -> «150 euro» — citando ogni volta il testo nuovo
        # come `source`. Due firme diverse, UNA penna sola: con la firma davanti
        # i due prezzi restavano entrambi vivi e il recall ne serviva due.
        # L'ha vista cadere `test_CONTROLLO_quando_supersede_DAVVERO_l_avviso_ci_deve_essere`,
        # che e' li' esattamente per questo (2026-09-06 08:35).
        return _base
    _sig = getattr(fact, "source_signature", None)
    if isinstance(_sig, str) and _sig.strip():
        # NIENTE PENNA DICHIARATA: qui `canonical_source` ripiega su `"user"` per
        # TUTTI, e «stessa fonte» diventa vero per costruzione — e' la
        # popolazione dei 155 ritiri. La firma non sostituisce il `verified_by`:
        # aggiunge risoluzione dove il `verified_by` non ne ha nessuna.
        return _sig.strip()
    return _base


#: Le code di `writer_principal` che NON sono un'identita': dicono da quale
#: canale e' entrato il fatto, non chi l'ha scritto.
_ANONIME = frozenset({"local", "unbound", "unknown", "anonymous", ""})


def declared_identity(principal: Any) -> str | None:
    """L'identita' DICHIARATA in un ``writer_principal``, o ``None``.

    ⚠️ IL CAMPO CONTIENE DUE COSE DIVERSE, e distinguerle e' tutto il punto.
    Sul corpus vero, 7852 fatti::

        6253  <NULL>          1454  cli:local
         143  mcp:unbound        2  sdk:local

    Sono CANALI: dicono da dove e' entrato il fatto, non chi l'ha scritto. Ma
    `Memory(principal="anna")` ci mette una PERSONA. Trattare le due cose allo
    stesso modo renderebbe «due autori diversi» la stessa persona che scrive da
    CLI e aggiorna da MCP — cioe' romperebbe l'aggiornamento legittimo, che e'
    il presidio su cui e' caduta la cura della `source_signature` (vedi
    `canonical_source_of`).

    Il formato canonico e' ``<prefisso>:<segmenti>`` (`orchestration.
    agent_principal`), quindi la coda dopo i due punti dice se un'identita' c'e':
    `mcp:alice` e' alice via MCP, `mcp:unbound` non e' nessuno.

    Conseguenza voluta: sul corpus di casa i quattro principal sono TUTTI
    anonimi, quindi questa funzione vi ritorna sempre ``None`` e nulla cambia.
    Morde solo dove un'identita' e' stata dichiarata davvero."""
    if not isinstance(principal, str):
        return None
    p = principal.strip().lower()
    if not p:
        return None
    coda = p.split(":", 1)[1] if ":" in p else p
    if coda.strip() in _ANONIME:
        return None
    return p


def is_same_source(a: Any, b: Any) -> bool:
    """Due fatti vengono dalla stessa penna? (la `canonical_source` del loro
    `verified_by`).

    ⛔ QUI DENTRO C'E' STATO L'ASSE DELL'AUTORE, PER TRE ORE, ED E' RITIRATO.
    L'idea: due `writer_principal` dichiarati e diversi non si ritirano a
    vicenda — nasceva dal caso «in una memoria di team il fatto di bruno
    archivia quello di anna». Curava quel caso e ne ROMPEVA uno piu' comune,
    misurato sulla matrice completa poche ore dopo::

        caso                        vivi  atteso  esito
        un autore,  due entita'       1      2    x  il buco storico, non chiuso
        due autori, due entita'       2      2    ok la cura sull'autore
        un autore,  aggiornamento     1      1    ok presidio
        due autori, aggiornamento     2      1    REGRESSIONE

    anna scrive «Il paziente Rossi pesa 70 chilogrammi», bruno corregge «78», e
    restavano vivi entrambi: in un'organizzazione **la correzione di un collega
    smetteva di sovrascrivere il dato sbagliato**, che e' il caso piu' comune
    che esista. E togliendo l'asse dal solo gate senza toglierlo da qui il
    risultato peggiorava ancora: la correzione finiva in QUARANTENA e restava
    servito il valore vecchio.

    🔑 «Autori diversi» non implica «cose diverse». Due persone che parlano
    dello STESSO paziente parlano della stessa cosa: l'autore era un proxy
    debole per l'asse che conta, cioe' L'ENTITA' — e quello vive in
    `anti_confab_gate._entita_diverse`, che confronta i codici di record e
    copre anche il caso anna/bruno per cui questa cura era nata.

    `declared_identity` resta esportata: e' corretta, e distinguere un CANALE
    (`cli:local`, `mcp:unbound`) da una PERSONA serve a chi mostra la
    provenienza. Non serve a decidere un ritiro.
    """
    return canonical_source_of(a) == canonical_source_of(b)


def source_signature_of(source_text: Any) -> str | None:
    """L'impronta di un TESTO di fonte, o ``None`` se testo non ce n'e'.

    ``"sha256:"`` + i primi 16 hex dello sha256 del testo normalizzato negli
    spazi. La source puo' essere un log di migliaia di righe: qui serve solo
    distinguere due origini, non rileggerle.

    ⚠️ ESISTE PERCHE' IL CALCOLO ERA IN UN POSTO SOLO E SERVIVA IN DUE, e la
    seconda copia sarebbe stata la classe di difetto piu' frequente che
    abbiamo — «una copia invece della superficie unica». Il primo posto e'
    ``client.add``, che l'impronta la CONSERVA sul fatto; il secondo e'
    ``anti_confab_gate._route_evolutions``, che deve poterla calcolare per il
    candidato AL VOLO, perche' li' il fatto non e' ancora stato scritto e
    quello che circola e' il testo della source.

    🔑 Chi la cambia cambia il significato di «stessa fonte» per TUTTO il
    corpus gia' scritto: due fatti sono la stessa fonte se le loro impronte
    coincidono, e un'impronta calcolata con un'altra regola non coincide con
    nessuna di quelle in archivio.
    """
    if source_text is None:
        return None
    _t = " ".join(str(source_text).split())
    if not _t:
        return None
    import hashlib
    return "sha256:" + hashlib.sha256(_t.encode("utf-8")).hexdigest()[:16]


def due_fonti_dichiarate_e_diverse(a: Any, b: Any) -> bool:
    """I due fatti DICHIARANO ciascuno la propria fonte, e le due sono diverse.

    ⚠️ DUE CONDIZIONI, NON UNA: le firme devono essere entrambe valorizzate e
    diverse, **e nessuno dei due deve dichiarare un ``verified_by``**. Il
    perimetro e' volutamente stretto — la popolazione misurata, non tutti i casi
    concepibili — e il blocco di commento nel corpo dice quali casi restano
    fuori e dove vanno a finire.

    ⚠️ NON E' ``not is_same_source(a, b)``, e la differenza e' tutto il punto:
    quella e' vera anche quando **uno dei due non dichiara niente**, e allora
    non si sa che le fonti sono diverse — si sa solo che una non c'e'. Qui
    servono ENTRAMBE valorizzate, come i codici in
    ``anti_confab_gate._entita_diverse`` e come il presidio in
    ``hidden_records``: con un lato muto il comportamento resta quello di prima.

    🔑 A COSA SERVE: e' la QUARTA uscita del gate semantico. Fino al 2026-09-06
    una contraddizione fra due fatti aveva tre esiti — ritiro del vecchio,
    quarantena del nuovo, coesistenza per entita' diverse — e due misure
    distinte della STESSA grandezza, prese da due fonti diverse, non entrano in
    nessuno dei tre: non sono l'una l'aggiornamento dell'altra (le fonti sono
    due), non sono un'aggressione (entrambe sono dichiarate e verificabili), e
    non parlano di entita' diverse (l'oggetto misurato e' lo stesso).

    Sul corpus quelle coppie erano **155 ritiri**, 153 con grounding >= 85, e
    fra loro **le celle di uno stesso banco e i due bracci dei nostri A/B**: il
    recall serviva un braccio e taceva l'altro. Il banco che riproduce il caso e
    misura la cura: ``docs/stato-reale/banchi/il-presidio-con-le-due-colonne.py``.

    ⚠️ LEGGE ``source_signature``, NON ``canonical_source_of``: dal 2026-09-06
    quest'ultima RIPIEGA sul ``verified_by`` e poi su ``"user"``, quindi con due
    fatti senza firma direbbe «stessa fonte» — che qui e' la risposta giusta ma
    per la ragione sbagliata, e domani con un ripiego diverso non lo sarebbe
    piu'. La domanda di questa funzione e' una sola: **hanno DETTO da dove
    vengono, e hanno detto due cose diverse?**
    """
    # ⚠️ IL `verified_by` GREZZO, PRIMA DI CANONICALIZZARLO — e la ragione e' che
    # `canonical_source` riconosce SOLO `source-doc:X:...` e `doc:X`, e appiattisce
    # tutto il resto su `"user"`: misurato il 06/09,
    #
    #     ['source-doc:billing:1'] -> 'billing'      ['doc:x']          -> 'x'
    #     ['contratto']            -> 'user'         ['commit:abc123']  -> 'user'
    #     ['Cartella clinica']     -> 'user'
    #
    # cioe' **`commit:` non conta come penna dichiarata**, ed e' la forma di
    # evidenza piu' comune che abbiamo. Senza questa riga il caso T14 — lo stesso
    # `verified_by=['contratto']` che aggiorna il proprio contratto da Stripe ad
    # Adyen — smetteva di ritirare: un aggiornamento VERO letto come due fonti.
    # Due `verified_by` identici sono la stessa penna qualunque forma abbiano.
    if (getattr(a, "verified_by", None) or getattr(b, "verified_by", None)):
        # ⚠️ BASTA UN `verified_by` SU UN LATO SOLO PER USCIRE DAL PERIMETRO, e
        # la riga stretta e' una DECISIONE, non una conseguenza: la quarta uscita
        # nasce per una popolazione misurata — i **292 ritiri** in cui NESSUNO dei
        # due lati dichiara una penna e le due `source_signature` sono diverse
        # (sul corpus: `verified_by` vuoto su entrambi in **2399 ritiri su 2407**,
        # cioe' il 99,7%). Fuori di li' non c'e' misura, e una uscita nuova su un
        # caso non misurato e' un'ipotesi che ritira o tiene in vita fatti veri.
        #
        # Cosa resta fuori, e dove:
        #   · una penna sola su entrambi (`['contratto']`, `['commit:abc']`) — e'
        #     un AGGIORNAMENTO e deve ritirare: il caso T14, Stripe -> Adyen;
        #   · due penne diverse — resta il conflitto cross-source di prima
        #     (quarantena), che e' anche la guardia contro il griefing;
        #   · una penna su UN lato solo — comportamento invariato. Sul corpus
        #     sono 6 ritiri su 2407, e di quei 6 con firma su ENTRAMBI: **zero**.
        #     E' cella xfail per la 0.7.8, non un caso che si decide qui.
        #
        # 🔑 Il `verified_by` GREZZO, non `canonical_source`: quest'ultimo
        # riconosce solo `source-doc:X:...` e `doc:X` e appiattisce il resto su
        # `"user"` — misurato il 06/09, `['commit:abc123'] -> 'user'`. Chiedere
        # «canonicalizza a qualcosa?» invece di «c'e'?» lascerebbe fuori dalla
        # guardia proprio la forma di evidenza piu' comune che abbiamo.
        return False
    _a = getattr(a, "source_signature", None)
    _b = getattr(b, "source_signature", None)
    if not (isinstance(_a, str) and _a.strip()):
        return False
    if not (isinstance(_b, str) and _b.strip()):
        return False
    return _a.strip() != _b.strip()


def _coerce_ts(v: Any) -> float | None:
    if isinstance(v, bool):  # guard: bool is an int subclass
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)  # numeric-looking string
    except (TypeError, ValueError):
        return None


def _when_true(fact: Any) -> float | None:
    """WHEN the fact is asserted TRUE — ``asserted_at`` (bi-temporal valid-time) when
    present, else ``created_at`` (write-time). Valid-time is what must order an
    evolution: the candidate's write-time is always *now*, so ordering by write-time
    alone would call a BACKFILL (re-asserting an OLD value) a newer 'evolution' and
    retire the current value (opus critic, 2026-07-19)."""
    for attr in ("asserted_at", "created_at"):
        t = _coerce_ts(getattr(fact, attr, None))
        if t is not None:
            return t
    return None


def classify_write_relation(new_fact: Any, old_fact: Any) -> str:
    """``"evolution"`` iff ``new_fact`` is the SAME canonical source as ``old_fact`` and
    strictly NEWER in VALID-TIME (``asserted_at`` when present, else ``created_at``);
    otherwise ``"conflict"`` — a different source, or no clear time order. Conservative:
    any ambiguity → conflict, so a fact is never auto-retired unless it is the same source
    superseding itself with a later valid-time.

    ⚠️ WHERE THAT CONSERVATISM DOES NOT HOLD (measured 2026-08-26, pure functions,
    no writes). When NEITHER fact carries ``asserted_at``, ``_when_true`` falls back to
    ``created_at`` — and a candidate's write-time is always *now*, so the order is not
    ambiguous-then-resolved-to-conflict: it is INVENTED, and the verdict is
    ``"evolution"``::

        both facts unsourced, no asserted_at   → "evolution"   ← the real-world case
        same asserted_at on both               → "conflict"
        candidate's asserted_at is earlier     → "conflict"

    The first row is the common one: no write path fills ``asserted_at`` and no extractor
    derives it from the text (measured 2026-08-26: L4.1 recognises 6 numeric
    forms out of 12 and that DATES — «3 aprile», «2019-04-03» — are not among them). With
    ``canonical_source_of`` collapsing unsourced writes to the ``"user"`` bucket, BOTH
    conditions are then satisfied by construction, and a genuine contradiction is filed as
    an update: «the patient died on 30 July» coexists with «the patient was discharged on
    30 July» (see in `docs/stato-reale/banchi/` the bench «la causa radice e' un
    fallback che inventa un ordine», and the class measured in «la contraddizione
    implicita»).

    ⛔ Do NOT "fix" this by dropping the fallback: that would route almost every pair to
    conflict, and TRUE facts pay for it — two were already rejected with no change at all
    in the bench «antonimi: si ferma, il resto no». Whoever touches it must measure BOTH
    populations.

    SECURITY — the enforce wiring (``ENGRAM_SUPERSEDE_SAME_SOURCE``, task #48) has NO
    source authentication, and this function provides NONE. ``verified_by`` is
    caller-controlled and spoofable (even the ``actor:`` self-provenance prefix is a bare
    string), and unsourced writes collapse to the ``"user"`` bucket, so a same-source
    verdict is only as trustworthy as the writers in a tenant. What actually makes enforce
    safe is therefore NOT authentication (unbuilt) but: (a) the TENANCY isolation boundary
    (cross-tenant writes are already blocked); (b) a single-agent-per-tenant assumption
    (the sole agent superseding its OWN values is the intended feature). A
    multi-agent-per-tenant deployment enabling it accepts intra-tenant griefing (the
    unbuilt per-agent-auth gap). Cross-source clashes never reach the supersede path
    (they classify as ``"conflict"``).

    CORRECTED 2026-07-20 (independent red-team audit): this docstring still claimed
    "it is DEFAULT-OFF — a knowing opt-in" as safety argument (a). That was STALE — the
    default flipped to **ON** on 2026-07-19 (``anti_confab_gate._supersede_same_source_on``,
    ``ENGRAM_SUPERSEDE_SAME_SOURCE`` defaults to "1"). A reader was being told the guard
    rested on an opt-in that no longer exists.

    OPEN RISK, not yet decided: assumption (b) is exactly what the architecture-A thin
    tier breaks. N agent sessions behind ONE shared server share ONE tenant key, so
    "single agent per tenant" is false by construction there, and one compromised session
    can retire another's true values. Until per-writer auth ships, a shared-server
    deployment that cannot trust every session should set
    ``ENGRAM_SUPERSEDE_SAME_SOURCE=0``."""
    if not is_same_source(new_fact, old_fact):
        return "conflict"
    tn, to = _when_true(new_fact), _when_true(old_fact)
    if tn is None or to is None or tn <= to:
        return "conflict"
    return "evolution"
