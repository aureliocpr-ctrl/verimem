"""The minimal composition loop — the ORGANISM ring inside the product.

From pairs of LIVE facts that share a pivot term, derive a NEW candidate by
DECLARED substitution (v1: the copula syllogism — "X is a Y." + "A Y is a Z."
-> "X is a Z."), push it through the SAME anti-confab gate as every other
writer (L4 source⊢fact entailment where the source is the two parents — the
composer has NO privileges: the gate that quarantined the organism's first
machine write guards this one too), and admit survivors:

  * SIGNED   — ``actor:composer:<run>`` in verified_by (P85: the engine's own
               writes never testify, never earn reputation);
  * TRACED   — ``derives_from=[parent_a, parent_b]`` (P78: the answer is a
               chain you can audit, and justified-memory can retract it if a
               parent falls);
  * LABELED  — ``epistemic = proven("qa:l4_entail_parents_score<NN>_PASS")``
               (the label names EXACTLY which machine check passed, nothing
               more — the coprime6 discipline).

Few-but-zero-false: a candidate the judge does not entail stays quarantined
(rehabilitable, visible in the ledger), never silently admitted. Generation is
pure substitution over declared patterns — zero unverified creativity; the
creative half (LLM conjectures) plugs in later behind the same gate.

Honest scope (v1): composes only where the corpus has copula structure —
world-bound by design; on a corpus of scattered notes it derives little and
says so in the report. No scheduling here: this is the RING; the nightly
daemon that calls it is a separate, later piece.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

__all__ = ["compose_once", "subject_key", "_copula_parse"]

#: A DERIVED fact needs more than the gate's minimum: the unreadable-verdict
#: fallback is a non-committal 50, which PASSES the claude-scale write cut
#: (40) — so a dead judge would silently flood the store with unverified
#: compositions. The composer floor sits ABOVE the fallback: anything the
#: judge cannot positively entail (>= 55) is quarantined, never live.
#: Env override: ENGRAM_COMPOSER_MIN_SCORE.
_MIN_SCORE_DEFAULT = 55.0


def _min_score() -> float:
    from .env_num import env_float
    return env_float("ENGRAM_COMPOSER_MIN_SCORE", _MIN_SCORE_DEFAULT)

#: Le QUATTRO LINGUE su cui il giudice del moat e' misurato (EN/IT/FR/ES). Fino
#: al 2026-07-30 la copula era ``\s+is\s+`` e basta: in italiano
#: ``_copula_parse`` restituiva None, quindi il guardian non vedeva MAI due
#: fatti come rivali e la contesa non veniva dichiarata da nessuna superficie.
#: Un prodotto che dichiara di giudicare in quattro lingue e riconosce
#: l'identita' del soggetto in una sola non protegge le altre tre.
#:
#: LA LINGUA LA DECIDE LA COPULA INCONTRATA, e ogni lingua porta i SUOI
#: articoli e le SUE preposizioni. Non e' pignoleria: «a» e' articolo in inglese
#: («is a labrador») e preposizione in italiano («e' a Roma»). Con le liste
#: mescolate, o si perde l'oggetto in inglese o si accetta un locativo italiano
#: come se fosse una classe — e un locativo scambiato per classe fa dichiarare
#: rivali due fatti che non lo sono.
_ARTICOLI_PER_LINGUA: dict[str, tuple[str, ...]] = {
    "en": ("a", "an", "the"),
    "it": ("il", "lo", "la", "i", "gli", "le", "un", "uno", "una"),
    "fr": ("le", "la", "les", "un", "une", "des"),
    "es": ("el", "la", "los", "las", "un", "una", "unos", "unas"),
}

#: parole che aprono un oggetto NON nominale ("is in Rome", "e' a Roma")
#:
#: LE FORME FUSE SONO NELLA LISTA QUANTO QUELLE NUDE. Italiano, francese e
#: spagnolo fondono la preposizione con l'articolo in UNA parola — «nel», «al»,
#: «sul», «au», «aux», «al» — e in italiano quella e' la forma piu' comune
#: delle due. Con le sole preposizioni nude la guardia esisteva sulla frase
#: semplice e spariva su quella normale: misurato il 2026-08-01, «Il gatto è a
#: Roma.» respinto e «Il server è nel datacenter di Milano.» accettato come
#: CLASSE, 7 locativi su 10. E in francese la preposizione e' `à`: `a` senza
#: accento e' il verbo avere, cioe' l'unica forma che NON serviva.
#:
#: Non e' una perdita di analisi, e' una contesa fabbricata: «Il server è nel
#: datacenter di Milano» e «Il server è un nodo di produzione» diventavano due
#: CLASSI rivali dello stesso soggetto, su tutti e cinque i moduli che leggono
#: da qui.
#:
#: L'inglese resta com'era — non fonde nulla, e nessun difetto e' stato
#: misurato li'. Allargarlo per simmetria significherebbe agire su un'ipotesi
#: invece che su un'evidenza, sul comportamento su cui gira tutto il corpus.
#: E LE IMPROPRIE QUANTO LE PROPRIE. La prima cura ha completato le forme
#: FUSE e ha lasciato fuori l'altra meta' della lista: qui c'erano solo le
#: preposizioni PROPRIE, e le improprie — quelle che sono anche avverbi o
#: participi — passavano tutte. Misurato dal vivo, 9 su 9 accettati come
#: CLASSI, inglese compreso:
#:     Il server è vicino a Roma.         -> ('il server', 'vicino a roma')
#:     Le bureau est près de la gare.     -> ('le bureau', 'près de la gare')
#:     The server is behind the firewall. -> ('the server', 'behind the firewall')
#: L'inglese entra ORA perche' ora c'e' la misura: la cura precedente lo aveva
#: lasciato fermo proprio per non muoverlo su un'ipotesi.
#:
#: TRE RESTANO FUORI DI PROPOSITO, e stanno in un test: «lungo» («Il fiume è
#: lungo trecento chilometri» — aggettivo), «salvo» («Il file è salvo» —
#: participio) e «secondo» («Il capitolo è secondo» — ordinale). Sono
#: preposizioni improprie a tutti gli effetti, e metterle costerebbe classi
#: vere su frasi che parlano davvero di una classe.
_NON_NP_PER_LINGUA: dict[str, frozenset[str]] = {
    "en": frozenset(
        "in on at from to of for with by about over under near into onto as "
        "behind inside outside next within between among against through "
        "across around during via without before after since until upon "
        "beyond throughout toward towards beneath alongside".split()),
    "it": frozenset(
        "in su a da di per con tra fra sotto sopra verso presso dentro fuori "
        # di+art · a+art · da+art · in+art · su+art · con+art
        "del dello della dei degli delle dell' "
        "al allo alla ai agli alle all' "
        "dal dallo dalla dai dagli dalle dall' "
        "nel nello nella nei negli nelle nell' "
        "sul sullo sulla sui sugli sulle sull' "
        "col coi "
        # improprie e locuzioni — senza lungo/salvo/secondo (vedi sopra)
        "vicino accanto prima dopo durante oltre attraverso intorno davanti "
        "dietro contro circa entro mediante tramite tranne eccetto "
        "nonostante malgrado rispetto".split()),
    "fr": frozenset(
        "en sur a de du des dans pour avec par sous vers chez entre "
        # à accentata (la preposizione vera) e le sue due contrazioni.
        # `l'` NON entra: in francese e' ARTICOLO («est l'animal favori» e'
        # una classe), e «est à l'hôtel» e' gia' respinto dal suo `à`.
        "à au aux d' "
        "près loin autour avant après pendant selon malgré envers hors "
        "parmi depuis contre devant derrière".split()),
    "es": frozenset(
        "en sobre a de del para con por bajo hacia entre desde hasta "
        "al "                   # `del` c'era, la sua gemella `al` no
        "cerca lejos antes después durante según excepto mediante tras ante "
        "contra dentro fuera alrededor".split()),
}

#: La copula -> la lingua. `est` prima di `es`, e `e'` prima di `es`: il regex
#: prova le alternative in ordine e la piu' lunga deve avere la precedenza.
_COPULE: dict[str, str] = {
    "is": "en", "è": "it", "e'": "it", "est": "fr", "es": "es",
}

#: Retrocompatibilita': l'inglese resta il default per chi importa il nome.
_ARTICLES = _ARTICOLI_PER_LINGUA["en"]
_NON_NP_LEADS = _NON_NP_PER_LINGUA["en"]

#: Tutti gli articoli, per ``subject_key``: li' la lingua non e' nota (si
#: normalizza un soggetto gia' estratto) e togliere un articolo di troppo e'
#: innocuo, mentre lasciarne uno fa divergere due chiavi che devono coincidere.
_ARTICOLI_TUTTI = frozenset(
    a for lista in _ARTICOLI_PER_LINGUA.values() for a in lista)

#: ``[^\W\d_]`` = una lettera qualsiasi, accenti compresi: con ``[A-Za-z]``
#: una frase che inizia per È o É non veniva nemmeno presa in esame.
#:
#: IL PUNTO FINALE E' FACOLTATIVO (2026-07-31). Era obbligatorio da sempre —
#: `4a282db4^` aveva gia' `\s*\.$` — e costava caro: `_copula_parse` alimenta
#: CINQUE moduli (composer, guardian, active_probe, source_trust,
#: ignorance_map), e un fatto che il parser non vede non entra in NESSUN
#: confronto. Due fatti contraddittori scritti senza punto coesistevano senza
#: che nessuno dichiarasse la contesa, e nessuno mette il punto per abitudine:
#: e' esattamente cio' che ha reso divergenti due prove sullo stesso codice,
#: una con le frasi punteggiate e una no.
_COPULA_RE = re.compile(
    r"^(?P<s>[^\W\d_][\w\s\-']{0,60}?)\s+(?P<c>is|est|è|e'|es)\s+"
    r"(?P<o>[^\W\d_][\w\s\-']{1,60}?)\s*\.?$",
    re.UNICODE)

#: L'oggetto di una copula e' un SINTAGMA NOMINALE. Un connettivo al suo
#: interno dice che la frase non finisce li', e quello che si estrae non e'
#: l'oggetto di niente:
#:
#:     «Il linguaggio è Rust e il database è Postgres.» -> 'rust e il database è postgres'
#:     «Se il linguaggio è Rust allora compila.»        -> 'rust allora compila'
#:
#: Entrambi MATCHAVANO GIA' prima di rendere facoltativo il punto (verificato
#: sul regex di `4a282db4`): non sono una regressione, sono un difetto che il
#: punto obbligatorio nascondeva a meta'.
#:
#: Il criterio e' conservativo per scelta: «Il colore è bianco e nero» viene
#: rifiutato insieme agli altri. Perdere un'analisi legittima costa un fatto in
#: meno nei confronti; accettarne una sbagliata mette in contesa fatti che non
#: parlano della stessa cosa — e un prodotto che esiste per non inventare
#: preferisce il primo errore al secondo.
_CONNETTIVI = (
    "e", "ed", "and", "et", "y", "o", "od", "or", "ou", "u",
    "ma", "but", "mais", "pero", "però",
    "allora", "then", "alors", "entonces",
    "perche", "perché", "because", "parce", "porque",
    "quando", "when", "quand", "cuando",
    "mentre", "while", "pendant", "mientras",
    "che", "that", "que", "se", "if", "si",
)
_CONNETTIVO_NELL_OGGETTO = re.compile(
    r"\s(?:" + "|".join(re.escape(c) for c in _CONNETTIVI) + r")\s",
    re.UNICODE | re.IGNORECASE)


def _strip_article(np: str, lingua: str | None = None) -> str:
    """Toglie l'articolo iniziale. Con ``lingua`` usa SOLO gli articoli di
    quella lingua (l'oggetto di una copula: li' «a» inglese e «a» italiano
    vogliono trattamenti opposti); senza, usa l'unione — il caso di
    ``subject_key``, dove la lingua non e' nota."""
    words = np.strip().split()
    ammessi = (_ARTICOLI_PER_LINGUA.get(lingua, ()) if lingua
               else _ARTICOLI_TUTTI)
    if words and words[0].lower() in ammessi:
        words = words[1:]
    return " ".join(words)


def subject_key(subject: str) -> str:
    """The ONE definition of "the same subject", for every reader that groups
    rival facts — the guardian's conflict detection and the active probe's
    counter-evidence search.

    It existed twice and the copies disagreed (2026-07-28): the probe normalised
    the article, the guardian did not, so one store holding "Rex is a labrador."
    and "The Rex is a poodle." was a fatal contradiction for the probe (which
    applied its ABSORBING ``refuted``) and no contradiction at all for the
    guardian (which served "labrador" as unchallenged). The same evidence cannot
    be both. Subject identity is one question, so it gets one answer here.

    Deliberately shallow — article + case + surrounding space, the normalisation
    ``_copula_parse`` already performs on the OBJECT. It does not resolve
    pronouns, aliases or morphology: "Rexy" is not "Rex", and a reader must not
    infer that it is.
    """
    return _strip_article(
        normalizza_apostrofi(subject or "")).strip().lower()


def _apre_un_locativo(parola: str, lingua: str) -> bool:
    """La prima parola dell'oggetto e' una preposizione di ``lingua``?

    Confronta PAROLE INTERE, non prefissi: `nel` e' una preposizione, `Nelson`
    e `nelle` no. E' la forma di difetto gia' pagata su questo repo (un nome
    trovato dentro un'altra parola), e qui la tentazione c'e' tutta, perche'
    le forme articolate sono corte e frequenti come inizio di nome.

    L'ELISIONE va sciolta a mano: `split()` restituisce `nell'archivio` in un
    pezzo solo, quindi «Il documento è nell'archivio.» sfuggiva a una lista
    che pure contiene `nell'`. Si guarda il troncone fino all'apostrofo — e
    solo quello, perche' `d'` francese e' preposizione mentre `l'` e'
    articolo, e la lista lo sa gia'.

    MA UN COGNOME NON E' UNA PREPOSIZIONE. Sciogliendo l'elisione sempre,
    «Il senatore è Dell'Utri.» veniva respinta come locativo, e con lei
    Dall'Ara, Dell'Orto, Dall'Oglio: una classe chiusa ma reale di cognomi
    italiani, che prima di questa funzione veniva analizzata correttamente.
    Trovato da un critic avversario, verificato dal vivo, e non era coperto
    dal test che pure sorvegliava questa forma di difetto — quel test provava
    `nel` contro `Nelson`, cioe' le forme SENZA apostrofo, che sono le uniche
    che il confronto su parole intere gia' proteggeva.

    Il segnale disponibile e' la MAIUSCOLA dopo l'apostrofo, e la ragione per
    cui basta e' che non regredisce nulla: «nell'Archivio di Stato» resta
    analizzato come classe, ma lo era GIA' PRIMA che questa funzione
    esistesse, mentre «Dell'Utri» funzionava e si era rotto. Si guadagna il
    caso minuscolo — quello comune — senza perdere terreno su nessun altro.
    Il limite resta dichiarato in un test invece che nascosto: un locativo
    seguito da nome proprio non e' distinguibile da un cognome senza un
    dizionario, e questo modulo non ne ha uno.
    """
    p = parola.lower()
    prep = _NON_NP_PER_LINGUA[lingua]
    if p in prep:
        return True
    tronco, sep, resto = parola.partition("'")
    if not sep or (resto[:1].isupper() if resto else False):
        return False
    return (tronco.lower() + "'") in prep


#: Gli apostrofi che una TASTIERA non produce ma un EDITOR si': `U+2019` e'
#: quello che mettono Word, macOS e iOS al posto di `'`, e senza questa riga il
#: testo scritto da una persona si comportava diversamente da quello scritto in
#: un editor di codice. Misurato: «Il senatore è Dell'Utri» parsato col dritto
#: e None col curvo, e con lui si perdeva anche «Il gatto è l'animale
#: preferito», che e' una classe vera.
#:
#: Il danno piu' sottile non e' la perdita: `subject_key` e' «la UNICA
#: definizione di stesso soggetto» per il guardian e per la contro-evidenza, e
#: senza normalizzare «Dell'Utri» e «Dell’Utri» sono due soggetti DIVERSI —
#: due fatti sulla stessa persona non finiscono mai in contesa, e basta che uno
#: arrivi incollato da un documento e l'altro digitato a mano.
#:
#: Solo APOSTROFI: le virgolette doppie non si toccano, qui serve che una
#: parola elisa resti una parola, non ripulire la punteggiatura.
_APOSTROFI = str.maketrans({"’": "'", "‘": "'",
                            "ʼ": "'", "´": "'", "＇": "'"})


def normalizza_apostrofi(text: str) -> str:
    """Porta ogni variante tipografica di apostrofo su `U+0027`."""
    return (text or "").translate(_APOSTROFI)


def _copula_match(text: str) -> re.Match | None:
    m = _COPULA_RE.match(normalizza_apostrofi(text).strip())
    if not m:
        return None
    # La frase continua oltre l'oggetto: non e' una proposizione semplice e
    # cio' che si estrarrebbe non e' l'oggetto di nessuna delle sue clausole.
    if _CONNETTIVO_NELL_OGGETTO.search(" " + m.group("o").strip() + " "):
        return None
    lingua = _COPULE.get(m.group("c").lower(), "en")
    obj_words = m.group("o").strip().split()
    if not obj_words or _apre_un_locativo(obj_words[0], lingua):
        return None                      # "is in Rome" / "e' a Roma" — locativo
    if not _strip_article(m.group("o"), lingua):
        return None                      # bare article, no head noun
    return m


def _copula_parse(text: str) -> tuple[str, str, str] | None:
    """``"Rex is a labrador."`` -> ``("rex", "labrador", "a labrador")`` —
    (subject lowered as written, object head lowered WITHOUT article, object
    lowered WITH its article). None for anything that is not a clean
    copula-over-noun-phrase sentence. Pure; the contract the tests pin."""
    m = _copula_match(text)
    if not m:
        return None
    lingua = _COPULE.get(m.group("c").lower(), "en")
    return (m.group("s").strip().lower(),
            _strip_article(m.group("o"), lingua).lower(),
            m.group("o").strip().lower())


def compose_once(mem: Any, *, topic: str | None = None, run_id: str | None = None,
                 max_candidates: int = 50) -> dict[str, Any]:
    """One composition pass over the live store. Returns an honest report:
    ``{eligible, candidates, admitted, rejected_gate, skipped_known,
    admitted_ids}`` — every bound and every skip is counted, never silent."""
    run = run_id or uuid.uuid4().hex[:8]
    facts = [f for f in mem.semantic.all()
             if not f.superseded_by
             # Giro 2: 'user_belief' excluded — composing over an unverified
             # user assertion would LAUNDER it: the derived fact carries the
             # belief's content without its low-trust label (worse than
             # serving the belief itself, the origin disappears).
             and f.status not in ("quarantined", "orphaned", "user_belief")
             and not (f.epistemic or {}).get("kind") == "refuted"]
    # parse the copula facts once; keep the ORIGINAL casing for candidate text
    parsed = []
    for f in facts:
        m = _copula_match(f.proposition)
        if m:
            parsed.append((f, m))
    known = {" ".join(f.proposition.lower().split()) for f in facts}

    report = {"eligible": len(facts), "copula_facts": len(parsed),
              "candidates": 0, "admitted": 0, "rejected_gate": 0,
              "rejected_noncommittal": 0, "skipped_known": 0,
              "admitted_ids": [], "run_id": run}
    for a, ma in parsed:
        pivot_a = _strip_article(ma.group("o")).lower()
        for b, mb in parsed:
            if a.id == b.id:
                continue
            # a parent never composes with its own derivative (trivial loops)
            if a.id in (b.derives_from or []) or b.id in (a.derives_from or []):
                continue
            if subject_key(mb.group("s")) != pivot_a:   # the shared definition
                continue
            subj_a = ma.group("s").strip()
            obj_b = mb.group("o").strip()
            if _strip_article(subj_a).lower() == _strip_article(obj_b).lower():
                continue                             # X is X — vacuous
            candidate = f"{subj_a} is {obj_b}."
            if report["candidates"] >= max_candidates:
                report["truncated"] = True           # bound declared, not silent
                return report
            report["candidates"] += 1
            if " ".join(candidate.lower().split()) in known:
                report["skipped_known"] += 1
                continue
            res = mem.add(
                candidate,
                topic=topic or a.topic or "derived",
                source=f"{a.proposition} {b.proposition}",
                ground=True,
                verified_by=[f"actor:composer:{run}"],
            )
            if not res.get("stored") or res.get("status") == "quarantined":
                report["rejected_gate"] += 1
                continue
            fid = res.get("id")
            gs = res.get("grounding_score")
            if gs is None or float(gs) < _min_score():
                # the judge did not POSITIVELY entail (None = never ran; ~50 =
                # the unreadable-verdict fallback): a derived fact does not go
                # live on a shrug — quarantine, rehabilitable, visible.
                try:
                    mem.semantic.quarantine_fact(
                        fid, deciso_da="composer",
                        reason=(f"composer: judge score "
                                     f"{gs if gs is not None else 'None'} below "
                                     f"floor {_min_score():.0f} — a derived "
                                     "fact needs positive entailment"))
                except Exception:  # noqa: BLE001 — best-effort demotion
                    pass
                report["rejected_noncommittal"] += 1
                continue
            mem.semantic.set_derives_from(fid, [a.id, b.id])
            from .epistemic import make_proven
            mem.semantic.set_epistemic(fid, make_proven(
                f"qa:l4_entail_parents_score{int(gs)}_PASS"))
            known.add(" ".join(candidate.lower().split()))
            report["admitted"] += 1
            report["admitted_ids"].append(fid)
    return report
