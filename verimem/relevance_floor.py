"""Self-calibrating relevance floor — the store measures its own noise band.

Why (external measurement, HaluEval 2026-07-10, results/external_readpath_*):
e5 cosine scores live in [0.73, 0.95] — answerable and unanswerable queries
are almost perfectly separable (AUROC 0.997 dev / 0.9935 held-out) but ANY
fixed ``min_relevance`` default is wrong somewhere: below the band it never
abstains (false_answer 1.0 — the measured read-path hole), above it it eats
coverage. The right floor depends on the embedder AND the store's content.

So the store estimates it: scrambled in-domain probes — words sampled across
DIFFERENT stored facts, shuffled into nonsense — score like irrelevant
queries (lexically in-domain, semantically nothing). The floor is a high
quantile of that noise band. In-domain scrambling is deliberately
conservative: off-domain probes would score lower and put the floor too low.

Cost: n_probes recall calls at estimation time (~32 embeds, daemon-warm ≈
ms). Deterministic given a seed. Wiring into ``explain(min_relevance="auto")``
is a separate step — this module is the measured mechanism, validated
against the external benchmark store before any default changes.
"""
from __future__ import annotations

import os
import random

__all__ = ["scrambled_probes", "estimate_relevance_floor", "env_floor",
           "env_floor_if_set"]

_FLOOR_OFF = {"off", "none", "0", "0.0", ""}


def env_floor(var: str = "ENGRAM_MIN_RELEVANCE") -> float | str:
    """Resolve a read-path abstention floor from an env var: ``auto`` (the store
    self-calibrates), a float, or off (0.0). The single switch that turns "knows when
    it doesn't know" ON across every surface (SDK ``explain()``, console, gateway).

    Default unset → ``auto`` since 2026-07-29. It used to be 0.0 — permissive,
    backward-compatible, and nothing in the tree ever set the variable, so the
    product's headline behaviour was off for every SDK, console and gateway
    caller while the MCP surface (a1f5e778) abstained. One store, two answers.

    Flipped on measurement, not on principle. Twenty questions against the live
    store — twelve it can support, eight plausible inventions:

        gate OFF   0 wrong abstentions   2 expected facts missed   0/8 caught   1.22s
        gate ON    0 wrong abstentions   2 expected facts missed   8/8 caught   4.21s

    The two misses are the SAME two in both columns: they were outside the
    retrieval top-k to begin with, so the gate costs no answer the store could
    have given. It withheld nothing it should have served, and caught every
    invention. The price is ~3s on a deliberate custody check.

    An explicit value still wins in both directions — ``off``/``0`` keeps the old
    permissive behaviour for whoever depends on it.

    WHERE THE DEFAULT ACTUALLY LANDS. "Across every surface" was the intent and
    for a year it was not the fact: this function had ONE caller in the product,
    ``Memory.explain``. Measured live 2026-08-02 with the floor at 0.99 — high
    enough that nothing can pass — on a three-fact store and a question outside
    it::

        search   -> 3 hit  best=0.7548
        recall   -> 3 hit
        ask      -> intent=find  3 risultati
        explain  -> abstained=True  min_relevance=0.99

    Which is the same "one store, two answers" written above, with ``explain``
    where the MCP surface used to be: the 2026-07-29 cure landed on the SITE and
    not on the CLASS. ``search``/``recall``/``ask`` now honour an EXPLICITLY SET
    variable (via ``env_floor_if_set``), so the switch means on those surfaces
    what it says. What they do NOT take is the unset ``auto`` default: the 8/8
    measurement above ran through ``explain``'s CE gate, and turning abstention
    on by default for a path nobody measured is the shape of the 2026-07-30
    mistake (``max(floor, noise_floor)``, written, measured and withdrawn for
    muting the ignorance map). Whoever never sets the variable gets byte-identical
    recall."""
    raw = os.environ.get(var, "").strip().lower()
    if raw == "auto":
        return "auto"
    if not raw:
        return "auto"
    if raw in _FLOOR_OFF:
        return 0.0
    # finite_or, not float(): an INFINITE floor abstains on every query ever
    # asked, and this site only survived `nan` by the argument order of max()
    from .env_num import finite_or
    return max(0.0, finite_or(raw, 0.0))


def env_floor_if_set(var: str = "ENGRAM_MIN_RELEVANCE") -> float | str | None:
    """``env_floor``, but ``None`` when the variable is NOT SET.

    ``env_floor`` cannot answer this question: it returns ``"auto"`` both when
    the caller typed ``auto`` and when the caller typed nothing, and those are
    two different intentions. Surfaces that had no floor before adopt the switch
    through here — an explicit value applies, silence keeps them as they were."""
    if not os.environ.get(var, "").strip():
        return None
    return env_floor(var)

_MIN_FACTS = 2          # cross-fact scrambling needs at least two sources
_PROBE_WORDS = 10       # ~question-length probes
_MAX_POOL_FACTS = 200   # cap the word pool: enough diversity, bounded cost


_MAX_WORDS_PER_FACT = 2

#: Oltre questa lunghezza un "token" non è una parola: è un pezzo di frase che
#: nessuno spazio ha separato. Misurato il 2026-08-04 su segnalazione,
#: che provava il prodotto in cinese, giapponese e thai: `text.split()` su una
#: scrittura senza spazi restituisce **un token solo, la frase intera**, quindi
#: il cap di due parole per fatto ne concedeva due… di cui una era tutto il
#: fatto. Dodici sonde su dodici contenevano un fatto intero.
#:
#: La soglia non identifica una lingua e non contiene una lista di alfabeti: si
#: limita a dire che una sequenza lunga e senza spazi va spezzata prima di
#: poterla chiamare "una parola". Vale per il cinese come per il thai, il lao,
#: il khmer e per qualunque scrittura a cui nessuno ha ancora pensato — che è
#: il punto, visto quante volte questo progetto ha pagato una lista tarata su
#: una lingua sola.
_MAX_TOKEN_CHARS = 12
#: In quanti pezzi spezzarlo. Tre caratteri sono abbastanza per non essere
#: rumore puro e abbastanza pochi perché due pezzi non ricostruiscano il senso.
_TOKEN_PIECE = 3


def _parole(testo: str) -> list[str]:
    """Le unità da cui pescare, anche dove gli spazi non separano le parole."""
    fuori: list[str] = []
    for tok in testo.split():
        if len(tok) <= _MAX_TOKEN_CHARS:
            fuori.append(tok)
            continue
        fuori.extend(tok[i:i + _TOKEN_PIECE]
                     for i in range(0, len(tok), _TOKEN_PIECE))
    return fuori


def scrambled_probes(sm, *, n: int = 32, seed: int = 0) -> list[str]:
    """Deterministic nonsense probes from the store's OWN vocabulary.

    Stratified CROSS-FACT sampling: each probe takes at most
    ``_MAX_WORDS_PER_FACT`` words from any single fact. Without the cap a
    probe can draw 3-4 words from ONE fact and nearly reconstruct it — the
    "noise" band then contains signal and the floor eats real queries (caught
    by the lexical test stub, which scores exactly that failure mode). A
    probe that collides with a stored proposition is discarded outright."""
    return scrambled_probes_da_testi(
        [(getattr(f, "proposition", "") or "") for f in sm.all()[:_MAX_POOL_FACTS]],
        n=n, seed=seed)


def scrambled_probes_da_testi(testi, *, n: int = 32,
                              seed: int = 0) -> list[str]:
    """La stessa costruzione, su TESTI qualsiasi invece che su fatti.

    Estratta il 2026-07-31 mentre si misurava il rumore di un indice di
    DOCUMENTI. Quella misura si e' poi rivelata inutile allo scopo (il
    pavimento veniva 0.8706, sopra TUTTE le query comprese quelle con
    risposta) e non e' stata tenuta — ma la separazione fra «da dove prendo le
    parole» e «su cosa cerco» resta giusta di per se': prima la funzione
    sapeva leggere solo un `SemanticMemory`, e un secondo chiamante avrebbe
    dovuto riscriverne la logica.
    """
    testi = list(testi)
    if len(testi) < _MIN_FACTS:
        return []
    words_by_fact: list[list[str]] = []
    originals: set[str] = set()
    for t in testi:
        text = (t or "").strip()
        originals.add(text.lower())
        ws = [w for w in _parole(text) if len(w) > 2]
        if ws:
            words_by_fact.append(ws)
    if len(words_by_fact) < _MIN_FACTS:
        return []
    rng = random.Random(seed)
    probes: list[str] = []
    for _ in range(n * 2):          # headroom for collision discards
        if len(probes) >= n:
            break
        order = list(range(len(words_by_fact)))
        rng.shuffle(order)
        words: list[str] = []
        for fi in order:            # round-robin over facts, capped per fact
            if len(words) >= _PROBE_WORDS:
                break
            ws = words_by_fact[fi]
            take = min(_MAX_WORDS_PER_FACT, len(ws),
                       _PROBE_WORDS - len(words))
            words.extend(rng.sample(ws, take))
        if len(words) < min(_PROBE_WORDS, 4):
            continue
        rng.shuffle(words)
        probe = " ".join(words)
        # SI SCARTA PER INCLUSIONE, NON PER UGUAGLIANZA (2026-08-04). Il
        # controllo era `probe.lower() not in originals`, cioè cadeva solo se
        # la sonda coincideva ESATTAMENTE con un fatto: una sonda che ne
        # contiene uno intero più qualche parola d'altro non è uguale a
        # niente, e passava. È la seconda rete, indipendente dalla
        # segmentazione qui sopra, e regge anche per una scrittura che quella
        # non sapesse spezzare — il rumore non deve MAI contenere segnale.
        basso = probe.lower()
        if not any(o and o in basso for o in originals):
            probes.append(probe)
    return probes


def estimate_relevance_floor(sm, *, n_probes: int = 32, quantile: float = 0.95,
                             seed: int = 0, k: int = 5) -> float:
    """The store's noise ceiling: ``quantile`` of the max recall score of
    scrambled probes. 0.0 (floor off) when the store is too small to measure
    — a floor guessed from nothing would be worse than none."""
    probes = scrambled_probes(sm, n=n_probes, seed=seed)
    if not probes:
        return 0.0
    maxima: list[float] = []
    for p in probes:
        # 🔑 `rerank=False`: una sonda del pavimento misura il RUMORE, e il
        # cross-encoder non serve a misurarlo. Misurato in A/B il 2026-08-19 su
        # 8 sonde: pavimento 0.8321 con rerank e 0.8321 senza, tempo 0.87s
        # contro 0.26s. ⇒ Il valore non cambia, il costo si'.
        # ⚠️ E il costo vero era piu' alto di quello dichiarato qui sopra
        # («~32 embeds»): le sonde sono CORTE, quindi passano il gate AUTO del
        # rerank — che esiste per non pagare il CE su una query lunga — e
        # caricavano il cross-encoder una volta per sonda. Misurato dal banco
        # `test_rerank_auto_default`: `{'load': 32, 'score': 96}` su UNA
        # ricerca dell'utente, che a sua volta era stata correttamente saltata.
        hits = sm.recall(p, k=k, rerank=False)
        maxima.append(max((float(s) for _, s, *_ in hits), default=0.0))
    if not maxima:
        return 0.0
    maxima.sort()
    idx = min(len(maxima) - 1, max(0, round(quantile * (len(maxima) - 1))))
    return round(maxima[idx], 4)


def rinfresca_se_stantio(mem) -> tuple[bool, float]:
    """Ricalcola il pavimento se il corpus e' cresciuto oltre la deriva.

    Restituisce ``(ha_ricalcolato, valore)``.

    PERCHE' ESISTE, e perche' NON sta dentro una lettura. La stima costa
    24169 ms sul corpus vero di 14382 fatti (misura di casa, una esecuzione),
    e la chiamata che la innesca sta nel percorso di OGNI ``search``: l'avviso
    di rilevanza chiede il pavimento fuori da ogni ``if``. Finche' il ricalcolo
    stava li', **la prima ricerca dopo una crescita del 5% pagava 24 secondi**
    — anche una ricerca che non chiedeva nessun pavimento e non tagliava
    niente.

    Ora la lettura serve il valore persistito anche quando e' vecchio, e alza
    ``_floor_stantio``. Questa funzione e' l'altra meta': la chiama chi ha il
    costo ATTESO — ``verimem warmup``, un daemon, una manutenzione — dove 24
    secondi sono annunciati e non sorprendono nessuno.

    ⚠️ L'OBIEZIONE A CUI RISPONDE, scritta da chi ha fatto il pavimento
    persistito: *«se il corpus cambia in modo sostanziale e il valore resta
    congelato, serviamo un pavimento sbagliato per sempre — che e' peggio di
    uno lento»*. E' giusta, ed e' il motivo per cui questa funzione esiste
    **nello stesso commit** della cura: senza un rimedio, «non ricalcolare in
    lettura» diventa «congelato per sempre». Il rimedio e' esplicito, il
    ``doctor`` dice quando serve, e il ``warmup`` lo esegue.
    """
    val = mem._auto_relevance_floor()
    if not getattr(mem, "_floor_stantio", False):
        return False, val
    return True, mem._auto_relevance_floor(rinfresca=True)
