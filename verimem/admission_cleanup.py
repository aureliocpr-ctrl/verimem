"""Reversible backlog cleanup for the admission gate (verimem.admission_cleanup).

The admission gate (verimem.admission_gate) governs only NEW writes. This
routes the EXISTING telemetry-topic facts OUT of the curated ``facts`` table into
the ``telemetry`` table — reclaiming the corpus that the gate would have kept
clean from the start (measured 2026-06-04: ~55% of the live store was telemetry).

NB since 0.7.0 the decision reuses the DECLARED prefixes
(``ENGRAM_TELEMETRY_PREFIXES``, e.g. ``builtin`` for our stack's list): with the
env unset this pass finds nothing, by design — a name is never a verdict unless
the operator declared it (external-corpora bench, 2026-07-20).

Safety contract:
  - ``dry_run=True`` by DEFAULT: only reports, mutates nothing.
  - Decision reuses ``admission_gate.classify_admission`` (single source of truth)
    and acts ONLY on ROUTE_TELEMETRY. Duplicates / low-provenance are left alone
    (more judgment needed; out of scope for this safe first pass).
  - The authoritative UNDO is the pre-cleanup full DB backup (VACUUM INTO). Moved
    rows keep their essentials in ``telemetry`` (id/topic/proposition/created_at/
    writer_role); embeddings are dropped (telemetry is never semantically recalled).
  - Run with the MCP server STOPPED (coordinate with restart) to avoid racing live
    writes.
"""
from __future__ import annotations

import json
import sqlite3

from ._call_telemetry import is_call_telemetry
from .admission_gate import ROUTE_TELEMETRY, classify_admission
from .retirement_log import _istante

#: Embedding BLOB columns dropped from the archived payload — telemetry is never
#: recalled semantically, so re-embeddable vectors are pure bloat (same choice as
#: the fact gate, which drops embeddings too).
_EPISODE_EMBED_COLS = ("summary_embedding", "dg_embedding", "context_embedding")

#: Sotto questo punteggio il moat ha detto «la fonte non lo sostiene», e
#: `requalify_quarantined` NON lo riporta nel recall. E' la piu' ALTA
#: delle due cut di ammissione (40 col giudice di ripiego, 70 col
#: calibrato, misurato il 2026-08-05): davanti al dubbio si recupera di
#: meno. I NULL restano eleggibili — «mai giudicato» non e' «bocciato».
_MOAT_MIN_RECOVER = 70.0


def cleanup_telemetry(db_path, *, principal: str, dry_run: bool = True) -> dict:
    """Route existing telemetry facts out of ``facts`` into ``telemetry``.

    Reference-aware since 2026-07-20 (task #61 — the live corpus measured 90
    ``superseded_by`` pointers into the 291 candidates and ~4.6k
    ``contradictions`` rows citing them; a naive DELETE strands both):

      - a candidate that is the TARGET of another fact's ``superseded_by``
        is SKIPPED (never break a chain), counted in ``skipped_referenced``;
      - UNRESOLVED ``contradictions`` rows citing a moved fact are pruned
        (scan output, regenerable); RESOLVED rows carry curated state
        (``resolved_at``/``resolution_note``) and stay;
      - the FTS index follows the DELETE via the existing ``facts_fts_*``
        triggers (proven in tests, not assumed).

    Returns ``{scanned, telemetry_found, moved, skipped_referenced,
    contradictions_pruned, dry_run}``. With ``dry_run=True`` (default)
    nothing is mutated.

    ``principal`` is MANDATORY (0.8 mutation audit): each row moved out of
    ``facts`` is recorded in the tamper-evident chain, same transaction
    (fail-closed).
    """
    from .mutation_audit import TABLE_SQL, record_mutation, require_principal
    require_principal(principal)
    conn = sqlite3.connect(db_path)
    conn.execute(TABLE_SQL)  # legacy DBs never opened via SemanticMemory
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, topic, proposition, status, writer_role, source_episodes, "
            "created_at FROM facts WHERE superseded_by IS NULL"
        ).fetchall()
        to_move = [
            r for r in rows
            if classify_admission(
                topic=r["topic"], proposition=r["proposition"], status=r["status"],
                writer_role=r["writer_role"], source_episodes=r["source_episodes"],
            ).decision == ROUTE_TELEMETRY
        ]
        referenced: set[str] = set()
        if to_move:
            ids = [r["id"] for r in to_move]
            ph = ",".join("?" * len(ids))
            referenced = {
                row[0] for row in conn.execute(
                    "SELECT DISTINCT superseded_by FROM facts "
                    f"WHERE superseded_by IN ({ph})", ids)
            }
        movable = [r for r in to_move if r["id"] not in referenced]
        result = {
            "scanned": len(rows),
            "telemetry_found": len(to_move),
            "moved": 0,
            "skipped_referenced": len(to_move) - len(movable),
            "contradictions_pruned": 0,
            "dry_run": dry_run,
        }
        if dry_run or not movable:
            return result

        conn.execute(
            "CREATE TABLE IF NOT EXISTS telemetry (id TEXT PRIMARY KEY, topic TEXT, "
            "proposition TEXT, created_at REAL, writer_role TEXT)"
        )
        # created_at is read defensively (always present in the live schema, but
        # the unit-test fixture may omit it).
        for r in movable:
            keys = r.keys()
            created = r["created_at"] if "created_at" in keys else None
            conn.execute(
                "INSERT OR REPLACE INTO telemetry(id, topic, proposition, "
                "created_at, writer_role) VALUES(?,?,?,?,?)",
                (r["id"], r["topic"], r["proposition"], created, r["writer_role"]),
            )
            conn.execute("DELETE FROM facts WHERE id = ?", (r["id"],))
            # 0.8 mutation audit — same transaction as the DELETE
            # (fail-closed); the moved text lives on in the telemetry
            # table, never in the chain.
            record_mutation(conn, principal=principal, action="delete",
                            resource_id=r["id"],
                            detail={"moved_to": "telemetry"})
        moved_ids = [r["id"] for r in movable]
        has_contra = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='contradictions'"
        ).fetchone() is not None
        if has_contra and moved_ids:
            ph = ",".join("?" * len(moved_ids))
            cur = conn.execute(
                "DELETE FROM contradictions WHERE resolved_at IS NULL AND "
                f"(fact_a_id IN ({ph}) OR fact_b_id IN ({ph}))",
                moved_ids + moved_ids,
            )
            result["contradictions_pruned"] = cur.rowcount
        conn.commit()
        result["moved"] = len(movable)
        return result
    finally:
        conn.close()


def cleanup_episode_telemetry(db_path, *, principal: str,
                              dry_run: bool = True) -> dict:
    """Route existing call-telemetry episodes out of ``episodes`` into
    ``episode_telemetry`` — the gemello of :func:`cleanup_telemetry` for the
    EPISODE backlog (the live ``episodes`` carry ~22% auto-saved cross-LLM call
    records: ``[agy-call …]``, ``[gemini-call …]``).

    Decision reuses :func:`verimem._call_telemetry.is_call_telemetry` — the SAME
    predicate the live write-gate (``memory._store_episode_telemetry``) uses, so
    cleanup and gate can never disagree on what counts as telemetry.

    Non-lossy on the meaningful fields: the full row (task_text, outcome,
    final_answer, notes, critique, …) plus any linked ``traces`` rows are preserved
    as a JSON ``payload`` (the live gate serializes ``Episode.traces`` too, so this
    keeps cleanup and gate byte-compatible); only the re-embeddable embedding BLOBs
    are dropped (telemetry is never recalled semantically). The linked ``traces``
    are then deleted EXPLICITLY — not relying on ``PRAGMA foreign_keys`` — so no
    orphan trace can survive the episode delete (critic counterexample 2026-06-14).
    The schema matches the table the live gate writes. ``dry_run`` defaults True;
    the authoritative undo is the pre-run DB backup. Idempotent.

    Returns ``{scanned, telemetry_found, moved, dry_run}``.

    ``principal`` is MANDATORY (0.8 mutation audit): each episode moved out
    of ``episodes`` leaves one chained row in this DB's ``audit_mutations``,
    same transaction (fail-closed).
    """
    from .mutation_audit import TABLE_SQL, record_mutation, require_principal
    require_principal(principal)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(TABLE_SQL)  # legacy DBs never opened via EpisodicMemory
        cols = [r[1] for r in conn.execute("PRAGMA table_info(episodes)").fetchall()]
        rows = conn.execute("SELECT * FROM episodes").fetchall()
        to_move = [r for r in rows if is_call_telemetry(r["task_text"] or "")]
        result = {
            "scanned": len(rows),
            "telemetry_found": len(to_move),
            "moved": 0,
            "dry_run": dry_run,
        }
        if dry_run or not to_move:
            return result

        has_traces = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='traces'"
        ).fetchone() is not None
        conn.execute(
            "CREATE TABLE IF NOT EXISTS episode_telemetry (id TEXT PRIMARY KEY, "
            "task_text TEXT, outcome TEXT, created_at REAL, payload TEXT)"
        )
        keep = [c for c in cols if c not in _EPISODE_EMBED_COLS]
        for r in to_move:
            payload = {c: r[c] for c in keep}
            if has_traces:
                # archive the linked traces in the payload (non-lossy, mirrors the
                # gate's Episode.traces), then delete them so none is left orphaned.
                trs = conn.execute(
                    "SELECT * FROM traces WHERE episode_id = ? ORDER BY step",
                    (r["id"],),
                ).fetchall()
                if trs:
                    payload["_traces"] = [dict(t) for t in trs]
            conn.execute(
                "INSERT OR REPLACE INTO episode_telemetry"
                "(id, task_text, outcome, created_at, payload) VALUES(?,?,?,?,?)",
                (
                    r["id"],
                    r["task_text"],
                    r["outcome"] if "outcome" in cols else None,
                    r["created_at"] if "created_at" in cols else None,
                    json.dumps(payload, default=str),
                ),
            )
            if has_traces:
                conn.execute("DELETE FROM traces WHERE episode_id = ?", (r["id"],))
            conn.execute("DELETE FROM episodes WHERE id = ?", (r["id"],))
            # 0.8 mutation audit — same tx as the DELETE (fail-closed); the
            # moved payload lives on in episode_telemetry, never the chain.
            record_mutation(conn, principal=principal, action="delete",
                            resource_id=r["id"],
                            detail={"moved_to": "episode_telemetry"})
        conn.commit()
        result["moved"] = len(to_move)
        return result
    finally:
        conn.close()


def requalify_quarantined(db_path, *, dry_run: bool = True,
                          principal: str | None = None) -> dict:
    """Re-evaluate quarantined facts with the CURRENT gate and promote to
    ``model_claim`` the ones no detector trips anymore — recovering real
    knowledge that a SINCE-FIXED false positive (e.g. the 2026-06-14 L1.18/L1.9
    fixes) had hidden from recall (the recall path hard-excludes quarantined rows).

    Three checks must pass — and ⚠️ THEY ARE NOT ALL THE QUARANTINE SOURCES,
    which is what this docstring used to claim:
      (1) no L1.x anti-confab warning (``_l1_warnings`` empty),
      (2) not flagged by ``prompt_injection.detect_injection`` (security TP),
      (3) the admission gate admits it to the curated corpus (not telemetry,
          not REJECT_POLLUTED / FLAG_INJECTION).

    ⚠️ **L3 (contradiction with the corpus) and L4 (the entailment moat) are
    NOT among them.** ``classify_admission`` is called with topic /
    proposition / status / writer_role / source_episodes — the grounding
    score never reaches it. A fact the moat REJECTED satisfies all three and
    comes back into recall with nobody re-reading why it was stopped.

    Measured on the real corpus 2026-08-07, on 717 live quarantined facts:
    209 carry a moat verdict and **158 of those score below 40** — the moat
    said the source does not support them. Read in the code by ws4; the
    numbers and the characterization tests
    (``tests/test_le_tre_condizioni_non_sono_le_tre_fonti.py``) are ws7's.

    The word this docstring opened with — SAFE — is removed deliberately: the
    behaviour is unchanged, the claim was not true, and three of us had
    recommended the tool on the strength of that word.
    So genuine positives (injection, polluted, telemetry) stay quarantined.
    ``dry_run`` default; the authoritative undo is the pre-run DB backup.

    ``principal`` is MANDATORY to apply (never to preview): re-admitting facts
    in bulk is a deliberate administrative mutation of what the product serves,
    so it lands in ``audit_mutations`` as ``restore`` — one row per fact, in the
    SAME transaction as the promotion (both land or neither does). Until
    2026-08-09 this function did a bare UPDATE: 265 facts could return to the
    live view on a corpus whose audit chain held 443 rows and not one of them a
    ``restore``, while ``cleanup_episode_telemetry`` eighty lines above recorded
    every single delete. The sibling surface — ``SemanticMemory.restore_fact``
    (single-fact) — still only emits telemetry; and unlike it, this path does
    not bump the recall cache. Both are open.

    ``by_moat`` splits the recoverable set by the judge's verdict already stored
    on each row, because the three conditions above do NOT read it: on the home
    corpus 165 of 265 recoverable facts carry ``grounding_score < 40`` — a
    source WAS checked against them and it refused them. A caller who reads only
    the total is about to re-admit those too.

    Returns ``{scanned, recoverable, promoted, dry_run, by_moat}``.
    """
    from . import __version__
    from .anti_confab_gate import (
        _has_dev_context,
        _has_personal_context,
        _l1_warnings,
    )
    from .mutation_audit import TABLE_SQL, record_mutation, require_principal
    from .prompt_injection import detect_injection

    # Refuse BEFORE touching a row: an anonymous bulk re-admission is exactly
    # the silent operation this audit exists to prevent, and refusing after the
    # UPDATE would leave the mutation without its receipt.
    if not dry_run:
        require_principal(principal)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # `grounding_score` puo' MANCARE su uno store vecchio: la colonna e'
        # arrivata con lo schema, e questo e' uno strumento di RECUPERO — chi
        # lo esegue ha spesso proprio uno store vecchio. Senza questa
        # tolleranza la chiamata muore con `OperationalError: no such column`
        # invece di lavorare.
        # ⚠️ Difetto MIO: l'ho introdotto con la cura `f1431950` di stamattina
        # aggiungendo la colonna alla SELECT, e ho consegnato senza accorgermi
        # che quattro prove erano rosse.
        _colonne = {r[1] for r in conn.execute("PRAGMA table_info(facts)")}
        _ha_punteggio = "grounding_score" in _colonne
        rows = conn.execute(
            "SELECT id, topic, proposition, verified_by, writer_role, "
            # ⚠️ RISOLUZIONE (ws7, 2026-08-09) — COMPLEMENTARI, si tengono
            # entrambi: la colonna CONDIZIONALE e' mia (uno store vecchio non
            # ha `grounding_score` e la SELECT fissa lo fa morire con
            # `OperationalError` — questo strumento e' di RECUPERO, chi lo
            # esegue ha spesso proprio uno store vecchio), il dizionario
            # `grounding` e' di ws1 e serve alla ripartizione `by_moat`.
            "source_episodes"
            + (", grounding_score" if _ha_punteggio else "")
            + " FROM facts WHERE status='quarantined' AND superseded_by IS NULL"
        ).fetchall()
        recoverable: list[str] = []
        held_by_moat = 0
        grounding: dict[str, float | None] = {}
        for r in rows:
            prop = r["proposition"] or ""
            try:
                vb = json.loads(r["verified_by"]) if r["verified_by"] else []
            except (ValueError, TypeError):
                vb = []
            if not isinstance(vb, list):
                vb = []
            # Consistent with run_validation_gate (2026-06-19): an L1 hit on a PERSONAL fact
            # with no dev signal is a false positive that no longer escalates, so it must NOT
            # block recovery — else historical personal-fact FPs ('dentist appointment
            # scheduled', quarantined before the gate fix) could never be un-quarantined.
            if _l1_warnings(prop, vb) and not (
                _has_personal_context(prop) and not _has_dev_context(prop)
            ):
                continue  # still trips an ESCALATING L1.x detector (dev-claim, not personal FP)
            if (detect_injection(prop).is_injection
                    or detect_injection(r["topic"] or "").is_injection):
                # genuine prompt-injection in the proposition OR the topic — keep
                # quarantined. The live write path quarantines on prop-OR-topic
                # (semantic.py: `_iv.is_injection or _iv_topic.is_injection`); requalify
                # checked only the proposition, so a benign-prop / injection-TOPIC fact
                # was re-promoted and its poison topic re-entered recall (review 2026-06-20).
                continue
            verdict = classify_admission(
                topic=r["topic"], proposition=prop, status="model_claim",
                writer_role=(r["writer_role"] or "agent_inference"),
                source_episodes=r["source_episodes"],
            )
            if verdict.decision == ROUTE_TELEMETRY or not verdict.admit_to_curated:
                continue  # telemetry / polluted / flagged — keep quarantined
            # ⚠️ IL QUARTO PRESIDIO, che i tre controlli non guardano.
            # Il verdetto di L4 e' gia' persistito qui e non serve il
            # giudice per leggerlo. Misurato da ws4 il 2026-08-07: dei
            # 172 recuperabili dalle tre condizioni, 138 avevano gs
            # sotto 40 e 17 fra 40 e 70 — 155 su 172, il 90,1%, erano
            # stati BOCCIATI DAL MOAT e sarebbero tornati nel recall
            # senza che nessuno riguardasse la ragione.
            #
            # Non e' un cambio di politica: lo scopo dichiarato qui
            # sopra e' recuperare «real knowledge that a SINCE-FIXED
            # false positive had hidden», e un fatto che il moat boccia
            # OGGI non e' un falso positivo gia' curato.
            #
            # I NULL restano DENTRO: «mai giudicato» non e' «bocciato».
            # La soglia e' 70 e non 40 perche' la cut di ammissione non
            # e' una (40 col giudice di ripiego, 70 col calibrato,
            # misurato il 2026-08-05): davanti al dubbio si recupera di
            # meno.
            _gs = r["grounding_score"] if _ha_punteggio else None
            if _gs is not None and float(_gs) < _MOAT_MIN_RECOVER:
                held_by_moat += 1
                continue
            recoverable.append(r["id"])
            # `_gs`, non `r["grounding_score"]`: su uno store senza la colonna
            # la riga di ws1 rimetterebbe il crash che la tolleranza qui sopra
            # ha appena tolto. E' la GIUNTURA — due lati entrambi giusti che
            # combinati rompono — e l'auto-merge non poteva vederla.
            grounding[r["id"]] = _gs
        # What the JUDGE thinks of what we are about to re-admit. The three
        # conditions never read it, so without this split the caller sees one
        # number that hides the only distinction that matters here: a fact whose
        # source was checked and REFUSED it is not the same case as one a fixed
        # false positive had hidden. Thresholds are the product's own 40/70.
        by_moat = {"respinti": 0, "incerti": 0, "approvati": 0,
                   "mai_giudicati": 0}
        for fid in recoverable:
            gs = grounding.get(fid)
            if gs is None:
                by_moat["mai_giudicati"] += 1
            elif gs < 40:
                by_moat["respinti"] += 1
            elif gs < 70:
                by_moat["incerti"] += 1
            else:
                by_moat["approvati"] += 1
        result = {
            "scanned": len(rows),
            "recoverable": len(recoverable),
            # Un conteggio che cala senza spiegazione si legge «ce
            # n'erano meno»: chi guarda deve vedere che la differenza
            # e' una SCELTA, e quale.
            "held_by_moat": held_by_moat,
            # Su uno store senza la colonna, `held_by_moat` vale 0 — e uno
            # zero senza spiegazione si legge «il moat non ha bocciato
            # nessuno», che e' l'opposto di «non ho potuto guardare».
            "moat_available": _ha_punteggio,
            "moat_rule": (
                f"a quarantined fact is NOT recovered when the moat "
                f"judged it below {_MOAT_MIN_RECOVER:.0f}; NULL means "
                f"never judged, not rejected, so it stays eligible. "
                f"The cut is the HIGHER of the two admission cuts "
                f"(40 fallback / 70 calibrated): facing a doubt, "
                f"recover less"),
            "promoted": 0,
            "dry_run": dry_run,
            # QUANDO. Il 2026-08-07 tre istanze hanno misurato proprio questo
            # `recoverable` e hanno ottenuto 172, 220, 235 e 236 — e nessuna
            # era in errore: i quarantinati vivi crescono di ~7,5 all'ora e i
            # quattro numeri sono monotoni nell'ordine in cui furono presi.
            # Un conteggio su un corpus che cambia e' un numero PIU' un
            # istante. Vedi `retirement_log._istante`.
            "measured_at": _istante(),
            # E COSA NE PENSA IL GIUDICE (ws1): senza questa ripartizione il
            # chiamante vede UN numero che nasconde l'unica distinzione che
            # conta qui — un fatto la cui fonte e' stata controllata e
            # RIFIUTATA non e' lo stesso caso di uno che un falso positivo
            # gia' curato aveva nascosto.
            # ⇒ I due campi rispondono a domande diverse e stanno insieme:
            #   `measured_at` dice QUANDO, `by_moat` dice COSA.
            "by_moat": by_moat,
        }
        if dry_run or not recoverable:
            return result
        conn.execute(TABLE_SQL)  # legacy DBs never opened via SemanticMemory
        for fid in recoverable:
            conn.execute(
                "UPDATE facts SET status='model_claim' WHERE id=?", (fid,)
            )
            # AFTER the write, on the same connection/transaction: the receipt
            # and the mutation are atomic together (mutation_audit's contract).
            record_mutation(
                conn, principal=principal, action="restore", resource_id=fid,
                detail={"from": "quarantined", "to": "model_claim",
                        "by": "requalify_quarantined",
                        "version": __version__,
                        "grounding_score": grounding.get(fid)},
            )
        conn.commit()
        result["promoted"] = len(recoverable)
        return result
    finally:
        conn.close()


__all__ = [
    "cleanup_telemetry",
    "cleanup_episode_telemetry",
    "requalify_quarantined",
]
