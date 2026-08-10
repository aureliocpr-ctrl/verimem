"""retirement_log — the window on retirements no API ever showed.

Measured 2026-08-04: after a supersession, SEVEN read surfaces say nothing —
count/get_all/quarantine_log/epistemic_health/history/recall/search. The
columns have existed since schema v2 (superseded_by/at/reason +
idx_facts_superseded_by, cycle #78); what was missing is the exposed QUERY —
the ``quarantine_log`` equivalent for retirements. On the real corpus that
silence hid 1756 retired→killer pairs, including 30 lost handoff reports in
the very topic those reports were written to.

Two functions, both read-only:

- :func:`retirement_log` — the pairs (loser, winner) newest first, each with
  topics, reason, timestamp and — since the helm — the ``undo_op_id`` handle
  that makes the row actionable, not just visible.
  LEFT JOIN on the winner: a winner that was itself retired (the ping-pong
  produces exactly such chains) must not hide the row. Metadata by default;
  ``with_text=True`` adds propositions for the local governance queue, where
  a human judges the pair — with both texts side by side that takes seconds.

- :func:`survivability_counts` — the canonical quartet written/servable/
  retired/quarantined, together. A fact disappears in TWO ways (retracted
  2026-08-04 22:32: counting only ``superseded_by IS NULL`` made a cure look
  done while it had moved the loss from one name to the other).
  SERVABLE is the canonical metric:
  ``superseded_by IS NULL AND status NOT IN ('quarantined')``.
"""
from __future__ import annotations

import time
from typing import Any


def _istante() -> float:
    """QUANDO e' stato preso il conteggio. Epoch, non una stringa leggibile.

    Il 2026-08-07 la STESSA quantita' — i quarantinati recuperabili — e'
    stata misurata quattro volte in poche ore, ottenendo `155 su 172`,
    `164 su 220`, `171 su 235` e `171 su 236` (l'ultima sei minuti dopo la
    precedente), e ne sono seguiti scambi per riconciliare i quattro referti.
    Nessuno dei quattro era sbagliato:
    i quarantinati vivi crescono di **~7,5 all'ora** (45 in sei ore, misurato
    ora per ora) e i quattro numeri sono monotoni crescenti nell'ordine in cui
    sono stati presi.

    🔑 Un conteggio su un corpus che cambia non e' un numero: e' un numero PIU'
    un istante. Senza, non e' confrontabile nemmeno con se stesso.

    Epoch e non «07/08 16:41»: una stringa leggibile non e' sottraibile e non
    dice il fuso — e queste misure viaggiano fra macchine e fra istanze.
    """
    return time.time()


__all__ = ["retirement_log", "retirement_breakdown",
           "quarantine_breakdown",
           "survivability_counts", "verdict_mismatches",
           "judged_true", "SERVABLE_WHERE"]

#: Sopra questo il moat ha detto «la fonte lo sostiene»: 90 è deliberatamente
#: prudente — a quel punteggio non si discute che il verdetto fosse positivo.
_VERDETTO_VERO = 90.0

#: LA CUT DI AMMISSIONE NON È UNA (misurato il 2026-08-05): vale 40
#: (scala claude, il ripiego) oppure 70 (la calibrata del fine-tune), e quale
#: tocchi dipende da quale giudice era disponibile in quel momento — un 55
#: entra con la prima e viene trattenuto con la seconda. Qui si usa il taglio
#: BASSO di proposito: sotto 40 un fatto è respinto da QUALUNQUE cut, quindi
#: ogni riga elencata è certa e il totale è un limite inferiore, mai gonfiato.
_VERDETTO_FALSO = 40.0
#: Fra le due cut il destino non è un'incoerenza ma un'INCERTEZZA: non «il
#: prodotto ha sbagliato» bensì «l'esito dipendeva dal minuto». Categoria a
#: parte, perché fonderla con le altre due sarebbe una scelta travestita da
#: misura. Sul corpus reale: 23 fatti, tutti trattenuti, zero serviti.
_BANDA_CONTESA_ALTA = 70.0

#: The canonical "servable" predicate — the ONE definition of "alive".
#: Two implicit definitions of the same word cost three hours on 2026-08-04;
#: every counter this module exposes states its formula.
SERVABLE_WHERE = "superseded_by IS NULL AND status NOT IN ('quarantined')"


def judged_true(score: Any) -> bool:
    """Whether the moat's verdict on this fact counts as «the source
    supports it». The ONE definition — the live feed asks it about a
    single write, :func:`verdict_mismatches` asks it of the whole corpus,
    and a threshold written twice diverges (three times in two days on
    this product). ``None`` is never judged, so never true: absence of a
    verdict is not a verdict."""
    if score is None:
        return False
    try:
        return float(score) >= _VERDETTO_VERO
    except (TypeError, ValueError):
        return False


def retirement_log(
    sm,
    *,
    limit: int = 50,
    since: float | None = None,
    topic: str | None = None,
    reason: str | None = None,
    cross_topic: bool | None = None,
    with_text: bool = False,
) -> list[dict[str, Any]]:
    """The retirements, newest first, as (loser, winner) PAIRS.

    Args:
        sm: a :class:`~verimem.semantic.SemanticMemory`.
        limit: max rows (newest first by ``superseded_at``).
        since: epoch seconds — only retirements at/after this instant.
        topic: prefix filter on the LOSER's topic (``LIKE topic%``).
        reason: exact match on ``superseded_reason``.
        with_text: include ``loser_text``/``winner_text``. Default False —
            the network/UI feed carries metadata, never content; the
            governance queue opts in locally where judging needs the words.

    Returns:
        list of dicts: loser_id/topic/status/created_at, winner_id/topic/
        status/created_at, reason, superseded_at, reversible, undo_op_id.
        ``reversible`` is True iff a not-yet-undone, not-expired
        ``facts_undo_log`` row of op_type='supersede' exists for the loser —
        rows retired BEFORE the helm existed report False honestly.
    """
    where = ["f.superseded_by IS NOT NULL"]
    params: list[Any] = []
    if since is not None:
        where.append("f.superseded_at >= ?")
        params.append(float(since))
    if topic is not None:
        where.append("f.topic LIKE ?")
        params.append(topic + "%")
    if reason is not None:
        where.append("f.superseded_reason = ?")
        params.append(reason)
    if cross_topic is not None:
        # Chi implementa «versionare invece di ritirare» deve poter
        # GUARDARE i 266 ritiri dentro-topic uno per uno, non solo contarli:
        # il versionamento serve a loro, non ai 1538 che attraversano i
        # topic (misurato e riprodotto il 2026-08-07). Il confronto sta in
        # SQL e non a valle perche' filtrare dopo il LIMIT restituirebbe
        # meno righe del richiesto senza dirlo.
        where.append("w.topic IS NOT NULL AND f.topic "
                     + ("<> w.topic" if cross_topic else "= w.topic"))
    text_cols = (",\n               f.proposition AS loser_text,"
                 "\n               w.proposition AS winner_text"
                 if with_text else "")
    sql = f"""
        SELECT f.id            AS loser_id,
               f.topic         AS loser_topic,
               f.status        AS loser_status,
               f.created_at    AS loser_created_at,
               f.superseded_by AS winner_id,
               f.superseded_at AS superseded_at,
               f.superseded_reason AS reason,
               w.topic         AS winner_topic,
               w.status        AS winner_status,
               w.superseded_by AS winner_superseded_by,
               w.created_at    AS winner_created_at,
               u.op_id         AS undo_op_id,
               u.undone_at     AS undo_undone_at,
               u.ttl_expires_at AS undo_ttl,
               -- CHI ha ritirato. Il dato c'era: ogni supersessione scrive
               -- il principal in `audit_mutations`, nella STESSA
               -- transazione della mutazione — e questo registro non lo
               -- leggeva. Il piu' recente, perche' un fatto puo' avere
               -- piu' righe d'audit (aggiornamento del motivo).
               (SELECT m.principal FROM audit_mutations m
                 WHERE m.resource_id = f.id AND m.action = 'supersede'
                 ORDER BY m.ts DESC LIMIT 1) AS retired_by{text_cols}
        FROM facts f
        LEFT JOIN facts w ON w.id = f.superseded_by
        -- lo scatto PIU' RECENTE per questo fatto, uno solo. Il join
        -- filtrava «vivo e non scaduto», e cosi' faceva due cose
        -- sbagliate insieme: due scatti vivi DUPLICAVANO la riga (un
        -- registro che conta due volte lo stesso ritiro e' peggio di uno
        -- che tace, e il caso e' entrato in un test), e i tre modi di
        -- NON essere annullabile finivano tutti in un NULL indistinto.
        LEFT JOIN facts_undo_log u ON u.op_id = (
            SELECT op_id FROM facts_undo_log
            WHERE fact_id = f.id AND op_type = 'supersede'
            ORDER BY created_at DESC LIMIT 1)
        WHERE {" AND ".join(where)}
        ORDER BY f.superseded_at DESC, f.created_at DESC
        LIMIT ?
    """
    # ORDER BY sulla COLONNA, non su COALESCE(colonna, 0): un'espressione non
    # può usare un indice, e SQLite scansionava tutta la tabella ordinando in
    # memoria per restituire cinquanta righe (200k righe: 63.6ms contro 0.1ms
    # con idx_facts_superseded_at — 600x). L'ordine non cambia: in SQLite NULL
    # è minore di tutto, quindi in DESC finisce in fondo esattamente dove lo
    # metteva lo zero (verificato), e sul corpus reale i ritiri senza data
    # sono 0 su 1794.
    import time as _time
    with sm._connect() as conn:
        # facts_undo_log may not exist on very old stores — create it the
        # same lazy way semantic.py does, so the JOIN never crashes.
        from .undo_log import ensure_undo_table
        ensure_undo_table(conn)
        # audit_mutations puo' mancare su uno store molto vecchio: la
        # sotto-query lo farebbe fallire, e un registro che sparisce perche'
        # una colonna in piu' non c'e' e' peggio di uno senza quella colonna
        from .mutation_audit import TABLE_SQL as _AUDIT_DDL
        conn.execute(_AUDIT_DDL)
        rows = conn.execute(sql, (*params, int(limit))).fetchall()
    ora = _time.time()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = {k: r[k] for k in r.keys()}
        _ttl = d.pop("undo_ttl", None)
        _undone = d.pop("undo_undone_at", None)
        # TRE modi di non essere annullabile, e l'operatore fa cose diverse
        # in ciascuno: nessuno scatto = la build che ha eseguito il ritiro
        # non lascia appigli (i cinque ritiri della manutenzione automatica
        # del 2026-08-05 sono tutti cosi'); finestra scaduta = lo scatto
        # c'era e il prodotto ha funzionato, sono passati i sette giorni;
        # gia' annullato = c'e' stato un ping-pong, e cercare l'undo e'
        # cercare la cosa sbagliata. Un solo False per i tre e' un'etichetta
        # che non distingue il ramo.
        if d.get("undo_op_id") is None:
            d["reversible"], d["irreversible_because"] = False, "no snapshot"
        elif _undone is not None:
            d["reversible"], d["irreversible_because"] = False, "already undone"
        elif (_ttl or 0) <= ora:
            d["reversible"] = False
            d["irreversible_because"] = "undo window expired"
        else:
            d["reversible"], d["irreversible_because"] = True, None
        # «RITIRATO IN FAVORE DI X» si legge come «l'informazione vive in
        # X», e sul corpus reale per 1177 righe su 1805 X e' a sua volta
        # ritirato o quarantinato (misurato il 2026-08-07). La riga non lo
        # diceva: portava `winner_status` e toccava a chi legge saperlo
        # interpretare. `winner_missing` e' un caso a parte — sul corpus
        # reale ce n'e' UNO, un `superseded_by` che punta a un id che non
        # esiste — e assente non e' «non servibile»: e' un dato rotto, e
        # None lo dice mentre False lo mimetizzerebbe fra i normali.
        d["winner_missing"] = (d.get("winner_id") is not None
                               and d.get("winner_status") is None)
        d["winner_servable"] = (
            None if d["winner_missing"] or d.get("winner_id") is None
            else (d.get("winner_superseded_by") is None
                  and d.get("winner_status") != "quarantined"))
        d.pop("winner_superseded_by", None)
        # L'OSSERVABILE, non l'interpretazione. «Attraversa i topic» e' il
        # confronto di due stringhe salvate: certo. «Housekeeping» e'
        # un'INTERPRETAZIONE, misurata al 95.1% su questo corpus, e vive
        # nella dichiarazione del riassunto — non qui, perche' un'etichetta
        # per riga sarebbe falsa in un caso su venti.
        # None quando il vincitore non esiste: i topic non si possono
        # confrontare, e False direbbe «stesso topic».
        d["cross_topic"] = (None if d.get("winner_topic") is None
                            else d.get("loser_topic") != d.get("winner_topic"))
        if not d["reversible"]:
            # l'appiglio NON viaggia quando non e' usabile: un op_id che
            # `undo` rifiuta si legge come una riparazione disponibile
            d["undo_op_id"] = None
        out.append(d)
    return out


def verdict_mismatches(sm, *, limit: int = 50,
                       topic: str | None = None) -> dict[str, Any]:
    """Where the moat's verdict and the fact's fate disagree, both ways.

    Measured on the real corpus 2026-08-05: 11 quarantined facts carry a
    verdict >= 90 (ten of them >= 99), and 10 served facts carry one below
    the admission cut — down to 0.22. Two opposite anomalies, and no view
    named either:

    - ``judged_true_but_withheld`` — the moat spent ~42 seconds to say "the
      source supports this" and the fact is kept out anyway. Work paid for
      and data lost; these were traced to reports that DOCUMENT a defect,
      blocked because they contain the defect's own words.
    - ``judged_false_but_served`` — the moat said the source does not
      support it and the memory returns it as its own. The graver one for
      whoever reads: a product that serves what its own judge rejected.

    It decides nothing: it lists, like the retirement log lists pairs. The
    thresholds travel in the result because "true" and "false" here are two
    cuts, and a number without its definition is the defect this branch cures.
    """
    where_t = "AND topic LIKE ?" if topic else ""
    par: list[Any] = [topic + "%"] if topic else []
    q_true = f"""
        SELECT id AS fact_id, topic, status, grounding_score, created_at
        FROM facts
        WHERE superseded_by IS NULL AND status IN ('quarantined')
          AND grounding_score IS NOT NULL AND grounding_score >= ?
          {where_t}
        ORDER BY grounding_score DESC LIMIT ?
    """
    q_false = f"""
        SELECT id AS fact_id, topic, status, grounding_score, created_at
        FROM facts
        WHERE {SERVABLE_WHERE}
          AND grounding_score IS NOT NULL AND grounding_score < ?
          {where_t}
        ORDER BY grounding_score ASC LIMIT ?
    """
    q_banda = f"""
        SELECT id AS fact_id, topic, status, grounding_score, created_at
        FROM facts
        WHERE superseded_by IS NULL
          AND grounding_score >= ? AND grounding_score < ?
          {where_t}
        ORDER BY grounding_score ASC LIMIT ?
    """
    with sm._connect() as conn:
        veri = [dict(r) for r in conn.execute(
            q_true, (_VERDETTO_VERO, *par, int(limit)))]
        falsi = [dict(r) for r in conn.execute(
            q_false, (_VERDETTO_FALSO, *par, int(limit)))]
        banda = [dict(r) for r in conn.execute(
            q_banda, (_VERDETTO_FALSO, _BANDA_CONTESA_ALTA, *par, int(limit)))]
    return {
        "measured_at": _istante(),
        "judged_true_but_withheld": veri,
        "judged_false_but_served": falsi,
        "contested_band": banda,
        "topic": topic,
        "thresholds": (
            f"judged_true = grounding_score >= {_VERDETTO_VERO:.0f} AND "
            f"quarantined · judged_false = grounding_score < "
            f"{_VERDETTO_FALSO:.0f} AND servable (LOWER BOUND: below "
            f"{_VERDETTO_FALSO:.0f} any cut rejects) · contested_band = "
            f"{_VERDETTO_FALSO:.0f}–{_BANDA_CONTESA_ALTA:.0f}, where the "
            f"outcome depended on which judge was up, not on the text"),
    }


#: Etichetta per i ritiri di cui NON esiste una riga d'audit: «non
#: registrato» non e' «nessuno», ed e' la stessa distinzione per cui un
#: `grounding_score` nullo non e' uno zero. Sul corpus reale sono 1631
#: ritiri su 1805 — la maggioranza.
_NON_REGISTRATO = "(not recorded)"

#: Etichetta per i ritiri senza motivo registrato. Raggrupparli sotto una
#: stringa vuota li manderebbe in fondo alla tabella con un nome che non si
#: legge — e sono la maggioranza dei ritiri storici.
_SENZA_MOTIVO = "(no reason recorded)"


#: Oltre questo numero di supersessioni le catene non si seguono e il
#: risultato lo DICHIARA invece di tacere: un limite silenzioso si legge
#: come «ho guardato tutto». Sul corpus reale sono 1805.
_MAX_CATENE = 50_000


def _esito_delle_catene(sm, *, topic: str | None = None) -> dict[str, Any]:
    """Dove FINISCE la catena delle supersessioni, non solo il primo passo.

    «Ritirato in favore di X» si legge come «l'informazione vive in X», ma
    X puo' essere a sua volta ritirato. Seguendo la catena fino in fondo
    sul corpus reale (2026-08-07): 673 ritiri su 1805 (37.3%) finiscono su
    un fatto servibile, 1131 no, 1 punta a un id inesistente, zero cicli,
    profondita' massima 13 e media 1.11.

    ⚠️ E l'aggregato da solo ACCUSA il prodotto di una cosa che non fa —
    per questo esce sempre insieme allo split per motivo::

        same-source evolution              107 · viva 107 (100.0%)
        heal_contradictions: numeric        21 · viva  21 (100.0%)
        exact-text dedup                   202 · viva 133 ( 65.8%)
        autohook-snapshot daily collapse  1463 · viva 406 ( 27.8%)

    Il write path ordinario non lascia MAI una catena morta: il 62.7% che
    muore e' quasi tutto la manutenzione del 2 luglio. Un numero che si
    ribalta quando lo dividi non va consegnato da solo.

    In Python e non in SQL ricorsivo: i passi sono pochi (media 1.11) e la
    guardia sui cicli qui e' esplicita e leggibile. Un ciclo non manda in
    loop — si conta — perche' un registro che si impianta su un dato
    sporco e' peggio di uno che lo dichiara.
    """
    with sm._connect() as conn:
        n_sup = int(conn.execute(
            "SELECT COUNT(*) FROM facts WHERE superseded_by IS NOT NULL"
        ).fetchone()[0])
        if n_sup > _MAX_CATENE:
            return {"status": f"skipped: {n_sup} supersessions > "
                              f"{_MAX_CATENE} cap — chains not followed"}
        sup = dict(conn.execute(
            "SELECT id, superseded_by FROM facts "
            "WHERE superseded_by IS NOT NULL"))
        motivo = dict(conn.execute(
            "SELECT id, COALESCE(superseded_reason, ?) FROM facts "
            "WHERE superseded_by IS NOT NULL", (_SENZA_MOTIVO,)))
        vivi = {r[0] for r in conn.execute(
            f"SELECT id FROM facts WHERE {SERVABLE_WHERE}")}
        esistono = {r[0] for r in conn.execute("SELECT id FROM facts")}
        _tp = dict(conn.execute(
            "SELECT id, topic FROM facts WHERE superseded_by IS NOT NULL"))

    conti = {"ends_servable": 0, "ends_dead": 0, "ends_missing": 0,
             "cycles": 0}
    per_motivo: dict[str, list[int]] = {}
    prof_max = 0
    for start in sup:
        if topic is not None and not str(_tp.get(start, "")).startswith(topic):
            continue
        cur, visti = start, set()
        while cur in sup and cur not in visti:
            visti.add(cur)
            cur = sup[cur]
        prof_max = max(prof_max, len(visti))
        k = motivo[start]
        voce = per_motivo.setdefault(k, [0, 0])
        voce[0] += 1
        if cur in visti:
            conti["cycles"] += 1
        elif cur not in esistono:
            conti["ends_missing"] += 1
        elif cur in vivi:
            conti["ends_servable"] += 1
            voce[1] += 1
        else:
            conti["ends_dead"] += 1
    return {
        **conti,
        "max_depth": prof_max,
        "by_reason": [
            {"reason": k, "n": v[0], "ends_servable": v[1],
             "share": round(v[1] / v[0], 4) if v[0] else None}
            for k, v in sorted(per_motivo.items(), key=lambda x: -x[1][0])],
        "formula": ("follow superseded_by to the end of the chain; "
                    "ends_servable = the tip is servable. The aggregate "
                    "ships WITH the per-reason split on purpose: on the "
                    "real corpus it reads 37% overall and 100% for "
                    "same-source evolution — a number that flips when you "
                    "divide it must not travel alone"),
    }


def retirement_breakdown(sm, *, limit: int = 10,
                         topic: str | None = None,
                         since: float | None = None) -> dict[str, Any]:
    """Dove si ADDENSANO i ritiri: per motivo e per giorno.

    Misurato il 2026-08-07 sul corpus reale, e ribalta una storia
    che circolava da giorni («un terzo della memoria non risponde»)::

        per mese  05: 7 · 06: 5 · 07: 1701 · 08: 92
        07-02: 1665 (ore 21 -> 1665 su 1665) · ogni altro giorno <= 12
        autohook-snapshot daily collapse 1463 · exact-text dedup 202

    Un'ora sola contiene il 92% dei ritiri di tutta la storia del corpus, e
    i due motivi principali non sono verdetti di qualita': sono
    manutenzioni.

    :func:`retirement_log` la risposta ce l'aveva — elenca le coppie e sa
    filtrare per ``reason`` — ma solo per chi SOSPETTAVA gia'. Mancava la
    domanda al contrario: «raggruppa e dimmi dove si addensano». Senza,
    un evento singolo si legge come un tasso, ed e' successo davvero.

    ``concentration`` non decide niente: e' la quota del giorno piu'
    affollato, col suo denominatore e la sua definizione accanto. Su un
    corpus senza ritiri vale ``None`` e non 100% — zero su zero non e' una
    percentuale.
    """
    where = ["f.superseded_by IS NOT NULL"]
    par: list[Any] = []
    if topic is not None:
        where.append("f.topic LIKE ?")
        par.append(topic + "%")
    # LA FINESTRA. Senza, ogni rapporto di questa superficie e' calcolato su
    # TUTTA la storia del corpus, e un evento di massa la domina per sempre:
    # misurato il 2026-08-07, il 2026-07-02 porta da solo 1665 ritiri contro
    # le poche decine di ogni altro giorno, e produce il «7,6% di
    # attribuzione» che avevo consegnato come se descrivesse lo stato
    # dell'audit — mentre dal 24/07 la copertura e' 100% ogni giorno.
    # `retirement_log`, nello stesso modulo, aveva `since` dal primo giorno:
    # due funzioni sulla stessa tabella e una sola sapeva farlo.
    if since is not None:
        where.append("f.superseded_at >= ?")
        par.append(float(since))
    w = " AND ".join(where)
    with sm._connect() as conn:
        from .mutation_audit import TABLE_SQL as _AUDIT_DDL
        conn.execute(_AUDIT_DDL)
        attori = [
            {"principal": r[0] or _NON_REGISTRATO, "n": int(r[1])}
            for r in conn.execute(
                f"""SELECT (SELECT m.principal FROM audit_mutations m
                             WHERE m.resource_id = f.id
                               AND m.action = 'supersede'
                             ORDER BY m.ts DESC LIMIT 1),
                           COUNT(*)
                    FROM facts f WHERE {w}
                    GROUP BY 1 ORDER BY COUNT(*) DESC""", par)]
        # QUANTA PARTE dei ritiri `by_principal` riesce ad attribuire, come
        # RAPPORTO e non come conteggio. Sullo store vero il 2026-08-07:
        # 137 su 1814, il 7,6%. Chi legge «cli:local 111» accanto a
        # «(not recorded) 1677» puo' calcolare 111/137 = 81% invece di
        # 111/1814 = 6%: due letture, un ordine di grandezza di distanza.
        _attribuiti = int(conn.execute(
            f"""SELECT COUNT(*) FROM facts f WHERE {w}
                AND EXISTS (SELECT 1 FROM audit_mutations m
                            WHERE m.resource_id = f.id
                              AND m.action = 'supersede')""",
            par).fetchone()[0])
        _tot_ritiri = int(conn.execute(
            f"SELECT COUNT(*) FROM facts f WHERE {w}", par).fetchone()[0])
        motivi = [
            {"reason": r[0] or _SENZA_MOTIVO, "n": int(r[1]),
             "first_at": r[2], "last_at": r[3]}
            for r in conn.execute(
                f"""SELECT f.superseded_reason, COUNT(*),
                           MIN(f.superseded_at), MAX(f.superseded_at)
                    FROM facts f WHERE {w}
                    GROUP BY f.superseded_reason
                    ORDER BY COUNT(*) DESC LIMIT ?""", (*par, int(limit)))]
        # il giorno in ora LOCALE: chi legge il registro guarda il proprio
        # calendario, e un raggruppamento in UTC spezza un evento serale in
        # due giorni diversi — che e' esattamente il caso qui (ore 21)
        giorni = [
            {"day": r[0], "n": int(r[1])}
            for r in conn.execute(
                f"""SELECT date(f.superseded_at, 'unixepoch', 'localtime'),
                           COUNT(*)
                    FROM facts f WHERE {w} AND f.superseded_at IS NOT NULL
                    GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT ?""",
                (*par, int(limit)))]
        totale = int(conn.execute(
            f"SELECT COUNT(*) FROM facts f WHERE {w}", par).fetchone()[0])
        _sc = conn.execute(
            f"""SELECT
                  SUM(CASE WHEN f.topic = w.topic THEN 1 ELSE 0 END),
                  SUM(CASE WHEN f.topic <> w.topic THEN 1 ELSE 0 END),
                  SUM(CASE WHEN w.id IS NULL THEN 1 ELSE 0 END)
                FROM facts f LEFT JOIN facts w ON w.id = f.superseded_by
                WHERE {w}""", par).fetchone()
    top = giorni[0] if giorni else None
    return {
        "measured_at": _istante(),
        "by_reason": motivi,
        "by_day": giorni,
        "by_principal": attori,
        # La finestra USATA, accanto ai numeri che ha prodotto: due risposte
        # identiche nella forma descrivono popolazioni diverse, e senza questo
        # campo nessuno se ne accorge. Stessa ragione di `measured_at`.
        "since": since,
        "attribution": {
            "attributed": _attribuiti,
            "unattributed": _tot_ritiri - _attribuiti,
            # zero su zero non e' una percentuale — stessa regola di
            # `concentration`, che su un corpus senza ritiri vale None.
            "share": (round(_attribuiti / _tot_ritiri, 4)
                      if _tot_ritiri else None),
            "note": (
                "`principal` names the PORT that performed the retirement, "
                "not the actor: verimem/cli.py stamps 'cli:local' for every "
                "caller, so N instances of the CLI collapse into one row. "
                "Since 2026-08-07 a caller that sets VERIMEM_ACTOR is "
                "stamped 'cli:local/<actor>' — an env-supplied LABEL, never "
                "an authenticated identity. Rows written before that date "
                "carry the port alone"),
        },
        "by_scope": {"same_topic": int(_sc[0] or 0),
                     "cross_topic": int(_sc[1] or 0),
                     "winner_missing": int(_sc[2] or 0)},
        # L'INTERPRETAZIONE STA QUI, col suo numero e col suo margine — non
        # in un'etichetta per riga, che sarebbe falsa in un caso su venti.
        # CORRETTA il 2026-08-07, un'ora dopo averla consegnata. Diceva
        # «95.1% housekeeping» e si leggeva come una rassicurazione: il
        # meccanismo e' automatico (vero, l'hook e' stato trovato nel
        # codice) ma NON e' senza perdita. Due misure indipendenti, con
        # metodi diversi, lo stesso giorno — e il precedente «housekeeping
        # funziona come deve» e' stato ritirato: era un giudizio non
        # misurato, che classificava la causa e ne deduceva l'innocenza.
        "scope_means": (
            "cross_topic is an OBSERVABLE (two stored strings differ), not a "
            "verdict. On this corpus 1463 of the 1538 cross-topic "
            "retirements are `autohook-snapshot daily collapse` — an "
            "automatic housekeeping hook, measured 2026-08-07 and reproduced "
            "independently. ⚠️ HOUSEKEEPING NAMES THE MECHANISM, NOT THE "
            "OUTCOME: on the master that retired 389 of them the 389 losers "
            "had 389 DISTINCT topics (separate checkpoints, not versions of "
            "one fact), 1,053,033 characters were replaced by 2,694 — 0.26% "
            "of the text survives — and 0 of 8 specific pointers (fact ids, "
            "pull-request URLs, paths) are in the master. A second method "
            "over 1463 pairs found 88.7% of the vocabulary lost, 3695 of the "
            "lost tokens being ids/paths/flags. It is NOT compression, it is "
            "SUBSTITUTION. The same-topic 266 are where supersession is a "
            "real editorial act, and the ones a versioning scheme must keep"),
        # IL LIMITE ACCANTO AL DATO. Un campo che sembra rispondere «chi»
        # senza dire cosa misura e' peggio di un campo assente, e qui i
        # limiti sono due: (1) il principal nomina la PORTA — `cli:local`
        # e' lo stesso valore per tutti i processi che scrivono su questo
        # corpus (misurato il 2026-08-07); (2) sul corpus reale solo 174
        # supersessioni su 1805 hanno una riga d'audit, quindi il resto e'
        # «non registrato», che non e' «nessuno».
        "principal_means": (
            "the acting principal names the PORT the action came through "
            "(cli:local, sdk:local, mcp:unbound), not the person or the "
            "instance — six agents share cli:local on this corpus. "
            "'(not recorded)' means no audit row exists for that "
            "retirement, which is not the same as nobody: on the real "
            "corpus 174 of 1805 retirements carry one. system:heal is the "
            "exception that identifies a real actor — the unattended "
            "maintenance pass"),
        "chain": _esito_delle_catene(sm, topic=topic),
        "total_retired": totale,
        "concentration": {
            "day": top["day"] if top else None,
            "n": top["n"] if top else None,
            "share": (round(top["n"] / totale, 4)
                      if (top and totale) else None),
            "formula": ("share = retirements on the busiest day / all "
                        "retirements — a rate and a one-off event look the "
                        "same until someone reads the distribution"),
        },
        "topic": topic,
    }


def quarantine_breakdown(sm, *, limit: int = 10,
                         topic: str | None = None) -> dict[str, Any]:
    """La stessa domanda dei ritiri, girata alla quarantena — esito opposto.

    Sui ritiri la distribuzione ha ribaltato la storia (un'ora sola conteneva
    il 92%). Qui la risposta e' NO, e va detta perche' un negativo misurato
    vale quanto una cura::

        quarantinati vivi 705 · giorno piu' affollato 88 (12.5%)

    Nessun evento: e' distribuita, quindi «tasso di quarantena» e' una parola
    giusta — al contrario di «tasso di ritiro», che non lo era.

    ⚠️ Ma la stessa query mostra quello che nessuna superficie diceva: **il
    tasso oscilla di venti volte fra un giorno e l'altro**::

        scritti 621 · quarantinati 68 (11.0%)  2026-08-04
        scritti 430 · quarantinati  1 ( 0.2%)  2026-05-31

    Un singolo numero — «il 10.2% viene quarantinato» — descrive gli ultimi
    giorni e non il prodotto. Il PERCHE' non e' qui: puo' essere il gate che
    e' cambiato o cosa scriviamo che e' cambiato, e distinguerli e' del write
    path. Questa vista mostra la serie, non la causa.

    Ogni riga porta scritti E quarantinati: il conteggio da solo non dice
    niente, 68 su 621 e 68 su 100 sono due prodotti diversi. E si contano
    solo i quarantinati NON ritirati — la stessa definizione del quartetto,
    dove le tre uscite restano separate per costruzione.
    """
    _w = "AND topic LIKE :topic" if topic is not None else ""
    par: dict[str, Any] = {"topic": topic + "%"} if topic is not None else {}
    quar = f"status IN ('quarantined') AND superseded_by IS NULL {_w}"
    with sm._connect() as conn:
        tot = int(conn.execute(
            f"SELECT COUNT(*) FROM facts WHERE {quar}", par).fetchone()[0])
        giorni = [
            {"day": r[0], "written": int(r[1]), "quarantined": int(r[2]),
             "rate": round(r[2] / r[1], 4) if r[1] else None}
            for r in conn.execute(
                f"""SELECT date(created_at,'unixepoch','localtime'),
                           COUNT(*),
                           SUM(CASE WHEN {quar} THEN 1 ELSE 0 END)
                    FROM facts
                    WHERE 1=1 {_w}
                    GROUP BY 1 HAVING SUM(CASE WHEN {quar} THEN 1 ELSE 0 END) > 0
                    ORDER BY 3 DESC LIMIT :lim""",
                {**par, "lim": int(limit)})]
    top = giorni[0] if giorni else None
    return {
        "measured_at": _istante(),
        "quarantined": tot,
        "by_day": giorni,
        "concentration": {
            "day": top["day"] if top else None,
            "n": top["quarantined"] if top else None,
            "share": (round(top["quarantined"] / tot, 4)
                      if (top and tot) else None),
            # lo stesso campo dei ritiri, e serve nei DUE versi: la' mostrava
            # un evento, qui mostra che un evento NON c'e'
            "formula": ("share = quarantines on the busiest day / all live "
                        "quarantines — the same field the retirement view "
                        "uses, and it earns its place in both directions: "
                        "there it showed one hour holding 92%, here it shows "
                        "there is no such event"),
        },
        "topic": topic,
    }


def survivability_counts(sm, *, topic: str | None = None) -> dict[str, Any]:
    """The canonical quartet, together: written / servable / retired /
    quarantined(-not-retired). ``written = servable + retired + quarantined``
    by construction — the three ways a write can end, none hidden behind
    another. ``formula`` states the servable predicate so no dashboard can
    show the number without its definition (two implicit definitions of
    'alive' is exactly the defect class measured on 2026-08-04)."""
    where = ""
    params: list[Any] = []
    if topic is not None:
        # segnaposto NOMINATO: la query porta anche `:ora` per la finestra
        # di undo, e mescolare `?` e nomi nella stessa istruzione non si fa
        where = "WHERE topic LIKE :topic"
        params.append(topic + "%")
    sql = f"""
        SELECT COUNT(*)                                          AS written,
               SUM(CASE WHEN {SERVABLE_WHERE} THEN 1 ELSE 0 END) AS servable,
               SUM(CASE WHEN superseded_by IS NOT NULL
                        THEN 1 ELSE 0 END)                       AS retired,
               SUM(CASE WHEN superseded_by IS NULL
                         AND status IN ('quarantined')
                        THEN 1 ELSE 0 END)                       AS quarantined,
               -- how many of the SERVED ones the moat ever judged: the
               -- question this product is sold on, and the quartet did not
               -- answer it. On the real corpus 2026-08-05: 1360 of 5631
               -- servable (24.2%) — i.e. 4271 facts served without a verdict.
               -- Counted on the servable ones only: a retired or quarantined
               -- fact is served to nobody, and including it would pad the
               -- denominator in exactly the flattering direction.
               SUM(CASE WHEN {SERVABLE_WHERE}
                         AND grounding_score IS NOT NULL
                        THEN 1 ELSE 0 END)                       AS judged,
               -- quanti dei RITIRATI si possono ancora annullare: la
               -- finestra di riparazione ha una dimensione, e «1796
               -- ritirati» non diceva se se ne recupera uno o mille.
               SUM(CASE WHEN superseded_by IS NOT NULL AND EXISTS (
                        SELECT 1 FROM facts_undo_log u
                        WHERE u.fact_id = facts.id
                          AND u.op_type = 'supersede'
                          AND u.undone_at IS NULL
                          AND u.ttl_expires_at > :ora)
                        THEN 1 ELSE 0 END)                 AS retired_reversible
        FROM facts {where}
    """
    import time as _time
    with sm._connect() as conn:
        from .undo_log import ensure_undo_table
        ensure_undo_table(conn)
        _p = {"ora": _time.time(), **({"topic": params[0]} if params else {})}
        row = conn.execute(sql, _p).fetchone()
        # LA RIPARTIZIONE, perche' `judged` da solo e' una MEDIA fra due
        # mondi. Il 2026-08-07 e' stato misurato che `clp save` non chiama
        # il gate — INSERT diretto con `status` fisso — e per la stessa
        # ragione un referto e' stato corretto: e' la trappola del
        # DENOMINATORE. Sul corpus reale: `model_claim` 3074 servibili
        # con 1800 verdetti (58.6%), `user_manual` 2493 con ZERO. Sommarli
        # descrive una media che non corrisponde a nessuna delle due, e fa
        # sembrare il gate peggiore di com'e'.
        #
        # ⚠️ NON si inventa l'etichetta «mai passato dal gate»: quale status
        # venga da quale porta lo sa chi possiede il write path, e lo
        # status e' l'OSSERVABILE, non la causa. Stessa distinzione che ho
        # gia' sbagliato oggi con la parola «housekeeping».
        per_status = [
            {"status": r[0], "servable": int(r[1]), "judged": int(r[2])}
            for r in conn.execute(
                f"""SELECT status, COUNT(*),
                           SUM(CASE WHEN grounding_score IS NOT NULL
                                    THEN 1 ELSE 0 END)
                    FROM facts
                    WHERE {SERVABLE_WHERE}
                      {"AND topic LIKE :topic" if topic is not None else ""}
                    GROUP BY status ORDER BY COUNT(*) DESC""", _p)]
    # English keys: this dict travels over every port of an international
    # product (monolingual surfaces are a measured defect class here).
    return {
        "measured_at": _istante(),
        "written": int(row["written"] or 0),
        "servable": int(row["servable"] or 0),
        "retired": int(row["retired"] or 0),
        "retired_reversible": int(row["retired_reversible"] or 0),
        "quarantined": int(row["quarantined"] or 0),
        "judged": int(row["judged"] or 0),
        "judged_by_status": per_status,
        "topic": topic,
        "formula": (f"servable = {SERVABLE_WHERE} · "
                    f"judged = servable AND grounding_score IS NOT NULL "
                    f"(NULL means never judged, not judged and failed) · "
                    f"⚠️ the aggregate `judged` MIXES populations with "
                    f"different rules — see judged_by_status: on the real "
                    f"corpus 2026-08-07 `model_claim` was judged 1800/3074 "
                    f"(58.6%) while `user_manual` was 0/2493, so the mixed "
                    f"figure describes neither and makes the gate look worse "
                    f"than it is. Which status comes from which write path "
                    f"is for the write-path owner to say; status is the "
                    f"observable, not the cause · "
                    f"retired_reversible = retired AND a live undo snapshot "
                    f"exists (the size of the repair window: 'retired' alone "
                    f"does not say whether one can be recovered or a thousand)"),
    }
