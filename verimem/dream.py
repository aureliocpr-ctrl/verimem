"""Hippo Dreams — immutable consolidation à la Anthropic Dreams.

Pattern (Cycle #34, building block #1):
  create_shadow_engine(live_dirs, shadow_root) -> (SleepEngine, paths)

Snapshot-copia i live DB (skills_index.db, episodes.db, semantic.db) e la
dir skills (.md bodies) verso `shadow_root`, poi costruisce un SleepEngine
puntato esclusivamente al shadow state. Il live state NON viene mai toccato
da operazioni successive sull'engine ritornato.

Ispirazione:
  - Anthropic Dreams: immutable input / separate output store, review-then-adopt.
  - ReasoningBank (Google): extract from success AND failure (loop close).
  - MemSkill (arXiv 2605.06614): skill = meta-procedura, Designer mina hard cases.

Bottleneck risolto (audit cycle #33 → #34):
  In hosted mode (HIPPO_HOSTED=1), `hippo_consolidate` è REJECTED per non
  consumare LLM dell'host. Risultato: sleep cycle non gira da ~5 giorni
  → 196 nrem skill candidate, solo 5 promoted (2.5% conversion). Sistema
  immobile. Hippo Dreams sbloccherà evoluzione safe: utente lancia dream
  esplicitamente (cost trasparente), produce shadow, review, adopt-or-discard.

Cycle successivi:
  #35: MCP tools hippo_dream_start / status (async job).
  #36: hippo_dream_diff / hippo_dream_adopt.
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any


def _backup_sqlite(src: Path, dst: Path) -> None:
    """Hot-copia un DB SQLite usando l'API backup (safe con WAL/concurrent reader).

    Critic-found fix (cycle #34): close connections esplicitamente per evitare
    file handle leak (with sqlite3.connect commit ma non chiude).
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        # Niente da copiare; lo shadow DB verrà inizializzato vuoto da SkillLibrary etc.
        return
    src_conn = sqlite3.connect(str(src))
    try:
        dst_conn = sqlite3.connect(str(dst))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()


# Critic-found (cycle #34): WAL/SHM files devono essere esclusi dal mirror
# perché il backup API ricrea il .db completo; mirrorare gli ausiliari può
# triggerare WAL recovery inconsistente all'apertura dello shadow DB.
_SQLITE_AUX_PATTERNS = ("*.db-wal", "*.db-shm", "*.db-journal")


def _ignore_sqlite_aux(_dir: str, names: list[str]) -> list[str]:
    """shutil.copytree ignore filter — esclude file SQLite ausiliari."""
    skip = []
    for n in names:
        for pat in _SQLITE_AUX_PATTERNS:
            if Path(n).match(pat):
                skip.append(n)
                break
    return skip


def _mirror_dir(src: Path, dst: Path) -> None:
    """Copia ricorsiva di una directory (skills/ contiene .md bodies).

    Critic-found (cycle #34): filtra file ausiliari SQLite (.db-wal/.db-shm)
    perché vengono ricreati via backup API e mirrorarli causa inconsistenza.
    """
    if not src.exists():
        dst.mkdir(parents=True, exist_ok=True)
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore_sqlite_aux)


def _is_overlap(child: Path, parent: Path) -> bool:
    """True se `child` è uguale a `parent` o nested dentro `parent`. Resolve simboli."""
    child = child.resolve()
    parent = parent.resolve()
    if child == parent:
        return True
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_no_overlap(shadow_root: Path, live_paths: list[Path]) -> None:
    """Raise ValueError se shadow_root copre alcun live path (parent o uguale).

    Critic-found CATASTROFICO (cycle #34): senza questa validation, passare
    shadow_root == live_root portava shutil.rmtree a distruggere il live DB.
    """
    sr = shadow_root.resolve()
    for live in live_paths:
        live_resolved = live.resolve() if live.exists() else live
        # Caso 1: shadow_root sotto un live dir
        if live_resolved.is_dir() and _is_overlap(sr, live_resolved):
            raise ValueError(
                f"shadow_root {sr} overlaps live path {live_resolved} "
                f"(same or nested inside) — aborting to protect live data"
            )
        # Caso 2: shadow_root copre un live file (cioè è una dir che lo contiene)
        if _is_overlap(live_resolved, sr):
            raise ValueError(
                f"shadow_root {sr} contains live path {live_resolved} — "
                f"aborting to protect live data"
            )


def create_shadow_engine(
    live_dirs: dict[str, Any],
    *,
    shadow_root: Path,
    llm: Any | None = None,
) -> tuple[Any, dict[str, Path]]:
    """Crea un SleepEngine puntato a snapshot shadow dei live DB.

    Args:
        live_dirs: dict che descrive il live state. Chiavi richieste:
            - "skills_db" (Path): live skills_index.db
            - "episodes_db" (Path): live episodes.db
            - "semantic_db" (Path): live semantic.db
            Chiave opzionale:
            - "skills_dir_path" (Path): dir bodies .md (default = skills_db.parent)
        shadow_root: directory dove materializzare snapshot.
            Creata se non esiste. NON deve sovrapporsi a live paths.
        llm: provider LLM opzionale (None = default get_llm()).

    Returns:
        (engine, paths) dove engine è un SleepEngine usabile per cycle()
        e paths è il dict dei file shadow per future ispezioni/diff.

    Safety:
        I live DB e skills dir NON vengono mai modificati. Tutte le scritture
        dell'engine ritornato vanno nello shadow_root.
    """
    from verimem.memory import EpisodicMemory
    from verimem.semantic import SemanticMemory
    from verimem.skill import SkillLibrary
    from verimem.sleep import SleepEngine

    shadow_root = Path(shadow_root)

    # 1. CRITIC-FOUND CATASTROFICO (cycle #34): valida che shadow_root NON
    # sovrapponga nessun live path. Senza questo, _mirror_dir con src==dst
    # distrugge i live DB via shutil.rmtree.
    live_skills_db = Path(live_dirs["skills_db"])
    live_skills_dir = Path(
        live_dirs.get("skills_dir_path", live_skills_db.parent)
    )
    live_paths_to_protect = [
        live_skills_db,
        live_skills_dir,
        Path(live_dirs["episodes_db"]),
        Path(live_dirs["semantic_db"]),
    ]
    _validate_no_overlap(shadow_root, live_paths_to_protect)

    shadow_root.mkdir(parents=True, exist_ok=True)
    shadow_skills_dir = shadow_root / "skills"
    shadow_skills_db = shadow_skills_dir / "skills_index.db"
    shadow_episodes_db = shadow_root / "episodes.db"
    shadow_semantic_db = shadow_root / "semantic.db"

    # 2. Mirror skills directory (bodies .md/.json) + DB snapshot
    _mirror_dir(live_skills_dir, shadow_skills_dir)
    # _mirror_dir potrebbe aver già copiato il DB se è dentro skills_dir,
    # ma rifacciamo via backup API per sicurezza WAL.
    _backup_sqlite(live_skills_db, shadow_skills_db)

    # 2. Snapshot episodes + semantic DB
    _backup_sqlite(Path(live_dirs["episodes_db"]), shadow_episodes_db)
    _backup_sqlite(Path(live_dirs["semantic_db"]), shadow_semantic_db)

    # 3. Costruisci handle store puntati al shadow
    shadow_skills = SkillLibrary(
        dir_path=shadow_skills_dir, db_path=shadow_skills_db,
    )
    shadow_memory = EpisodicMemory(db_path=shadow_episodes_db)
    shadow_semantic = SemanticMemory(db_path=shadow_semantic_db)

    # 4. Costruisci SleepEngine puntato a shadow handle
    engine = SleepEngine(
        memory=shadow_memory,
        skills=shadow_skills,
        semantic=shadow_semantic,
        llm=llm,
    )

    paths = {
        "shadow_root": shadow_root,
        "skills_db": shadow_skills_db,
        "skills_dir": shadow_skills_dir,
        "episodes_db": shadow_episodes_db,
        "semantic_db": shadow_semantic_db,
    }
    return engine, paths


def propose_dream_tasks(
    live_dirs: dict[str, Any],
    *,
    shadow_root: Path,
    max_clusters: int = 20,
    min_cluster_size: int = 2,
    cluster_threshold: float = 0.55,
    instructions: str | None = None,
) -> dict[str, Any]:
    """CYCLE #35 redesign — Hippo Dreams subscription-first.

    Prepara cluster di episodi + prompt structured per skill synthesis SENZA
    chiamare LLM internamente. Claude Code (host) consuma i prompt e fa le
    LLM call con la subscription dell'utente, poi passa result via cycle #36
    `hippo_dream_submit_result` (TBD).

    Direttiva fondamentale (fact preferences/aurelio d4dd857b1eea, 2026-05-13):
    subscription = base sempre. API key separata = opt-in per public users.

    Args:
        live_dirs: stessi requisiti di create_shadow_engine.
        shadow_root: dir target. Validation overlap protegge live.
        max_clusters: cap di sicurezza sul numero di pending tasks generati.
        min_cluster_size: min episodi per cluster (default 2).
        cluster_threshold: cosine similarity soglia per clustering greedy.
        instructions: hint stile Anthropic Dreams (logged, non incorporato nel
            prompt template in cycle #35; cycle #36 lo userà).

    Returns:
        dict con:
          - dream_id (uuid hex prefix)
          - shadow_root (str path)
          - pending_tasks: list[dict] con task_id, kind, system_prompt,
            user_prompt, context_episode_ids
          - summary: dict con counts diagnostici
          - instructions: echo dell'input

    Safety:
        - Live DB MAI modificati (validation + shadow snapshot).
        - Zero LLM call: subscription-first guarantee.
        - Artifact file dream_tasks.json salvato per audit/replay.
    """
    import json as _json
    import uuid

    from verimem.memory import EpisodicMemory
    from verimem.prompts import DREAMER_NREM_SYSTEM, DREAMER_NREM_USER_TEMPLATE

    shadow_root = Path(shadow_root)

    # 1. Validation overlap (riuso safety cycle #34).
    live_skills_db = Path(live_dirs["skills_db"])
    live_skills_dir = Path(
        live_dirs.get("skills_dir_path", live_skills_db.parent)
    )
    live_paths_to_protect = [
        live_skills_db,
        live_skills_dir,
        Path(live_dirs["episodes_db"]),
        Path(live_dirs["semantic_db"]),
    ]
    _validate_no_overlap(shadow_root, live_paths_to_protect)

    # 2. Snapshot shadow (zero LLM, solo sqlite3 backup API + shutil mirror).
    shadow_root.mkdir(parents=True, exist_ok=True)
    shadow_skills_dir = shadow_root / "skills"
    shadow_skills_db = shadow_skills_dir / "skills_index.db"
    shadow_episodes_db = shadow_root / "episodes.db"
    shadow_semantic_db = shadow_root / "semantic.db"
    _mirror_dir(live_skills_dir, shadow_skills_dir)
    _backup_sqlite(live_skills_db, shadow_skills_db)
    _backup_sqlite(Path(live_dirs["episodes_db"]), shadow_episodes_db)
    _backup_sqlite(Path(live_dirs["semantic_db"]), shadow_semantic_db)

    # 3. Apri shadow stores DIRETTAMENTE — NO SleepEngine (evita get_llm side effect).
    shadow_memory = EpisodicMemory(db_path=shadow_episodes_db)

    # 4. Cluster gli episodi su shadow memory. cluster_similar è LLM-free
    # (usa solo embedding già pre-calcolati nel DB).
    n_episodes_snapshot = shadow_memory.count()
    clusters = shadow_memory.cluster_similar(eps_threshold=cluster_threshold)
    clusters = [c for c in clusters if len(c) >= min_cluster_size]
    n_clusters_found = len(clusters)

    # 5. Sort by cluster size desc (proxy per replay priority semplice;
    # cycle #36+ può raffinare con replay_priority completo).
    clusters.sort(key=lambda c: -len(c))
    clusters = clusters[:max_clusters]

    # 6. Genera dream task per ogni cluster (prompt structured per LLM-host).
    dream_id = uuid.uuid4().hex[:12]
    pending_tasks: list[dict[str, Any]] = []
    for cluster in clusters:
        task_id = uuid.uuid4().hex[:12]
        n_success = sum(1 for e in cluster if e.outcome == "success")
        n_failure = sum(1 for e in cluster if e.outcome == "failure")
        body = "\n\n".join(
            f"### Episode {i+1}\n{e.trajectory_text()}"
            for i, e in enumerate(cluster[:5])
        )
        user_prompt = DREAMER_NREM_USER_TEMPLATE.format(
            episodes=body, n_success=n_success, n_failure=n_failure,
        )
        pending_tasks.append({
            "task_id": task_id,
            "kind": "nrem_skill_from_cluster",
            "system_prompt": DREAMER_NREM_SYSTEM,
            "user_prompt": user_prompt,
            "context_episode_ids": [e.id for e in cluster],
            "context_size": len(cluster),
            "n_success": n_success,
            "n_failure": n_failure,
            "status": "pending",
        })

    # 7. Persist artifact su disk per audit/replay (cycle #36 lo leggerà).
    artifact = {
        "dream_id": dream_id,
        "shadow_root": str(shadow_root),
        "pending_tasks": pending_tasks,
        "instructions": instructions,
        "summary": {
            "n_episodes_snapshot": n_episodes_snapshot,
            "n_clusters_found": n_clusters_found,
            "n_tasks_generated": len(pending_tasks),
            "max_clusters_cap": max_clusters,
            "min_cluster_size": min_cluster_size,
            "cluster_threshold": cluster_threshold,
        },
    }
    artifact_path = shadow_root / "dream_tasks.json"
    artifact_path.write_text(_json.dumps(artifact, indent=2, default=str))

    return artifact


def _validate_skill_json(skill_json: Any) -> dict[str, str]:
    """CYCLE #36 — lenient schema validation (decisa con Aurelio 2026-05-13).

    Required: name, trigger, body — tutti non-empty str.
    Optional: rationale — str (default "" se mancante).
    Extra fields silently ignored (LLM output può variare creativamente).

    Returns dict pulito con i 4 campi normalizzati.
    Raises ValueError con messaggio diagnostico se invalido.
    """
    if not isinstance(skill_json, dict):
        raise ValueError(
            f"skill_json validation failed: expected dict, got {type(skill_json).__name__}"
        )
    required = ("name", "trigger", "body")
    for k in required:
        if k not in skill_json:
            raise ValueError(
                f"skill_json validation failed: required field '{k}' is missing"
            )
        v = skill_json[k]
        if not isinstance(v, str):
            raise ValueError(
                f"skill_json validation failed: field '{k}' must be str, "
                f"got {type(v).__name__}"
            )
        if not v.strip():
            raise ValueError(
                f"skill_json validation failed: field '{k}' is empty"
            )
    rationale = skill_json.get("rationale", "")
    if rationale is not None and not isinstance(rationale, str):
        raise ValueError(
            f"skill_json validation failed: 'rationale' must be str or null, "
            f"got {type(rationale).__name__}"
        )
    return {
        "name": skill_json["name"].strip(),
        "trigger": skill_json["trigger"].strip(),
        "body": skill_json["body"].strip(),
        "rationale": (rationale or "").strip(),
    }


def submit_dream_result(
    *,
    shadow_root: Path,
    task_id: str,
    skill_json: dict[str, Any],
    tokens_used: int = 0,
    model_name: str = "",
) -> dict[str, Any]:
    """CYCLE #36 — Hippo Dreams: persist skill output del LLM sul shadow.

    Pipeline subscription-first: Claude Code (host) ha già fatto la LLM call
    con la sua subscription. Questa funzione SOLO valida + persiste + aggiorna
    l'artifact. Zero LLM call interno.

    Decisioni design (confermate con Aurelio 2026-05-13):
    - Lenient validation: required name+trigger+body, extra fields ignored.
    - Reject hard se task già done: idempotency safety.

    Args:
        shadow_root: dir creata da propose_dream_tasks (cycle #35).
        task_id: id del pending task da risolvere.
        skill_json: output del LLM (deve avere name+trigger+body str non-empty).
        tokens_used: token consumati dalla LLM call (per audit cost).
        model_name: modello usato (default opus-4-7; alternative possibili se
            l'utente le sceglie esplicitamente, ma il default resta opus-4-7).

    Returns:
        {ok, skill_id, dream_id, remaining_pending, model_name}.

    Raises:
        FileNotFoundError: shadow_root o artifact non esiste.
        ValueError: dream_tasks.json corrotto, task_id sconosciuto, task già
            done, skill_json invalido.

    Safety:
        - Live state MAI modificato (persist solo su shadow_skills).
        - Zero LLM call: subscription-first guarantee.
    """
    import json as _json
    import time as _time

    from verimem.skill import Skill, SkillLibrary

    shadow_root = Path(shadow_root)
    if not shadow_root.exists() or not shadow_root.is_dir():
        raise FileNotFoundError(
            f"unknown_dream: shadow_root {shadow_root} does not exist"
        )
    artifact_path = shadow_root / "dream_tasks.json"
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"unknown_dream: artifact {artifact_path} missing — "
            f"shadow_root non è un dream valido"
        )

    try:
        artifact = _json.loads(artifact_path.read_text())
    except _json.JSONDecodeError as exc:
        raise ValueError(f"dream artifact corrupted: {exc}") from exc

    # Find task by id.
    pending_tasks = artifact.get("pending_tasks", [])
    matching = [t for t in pending_tasks if t.get("task_id") == task_id]
    if not matching:
        raise ValueError(
            f"unknown_task: task_id {task_id!r} not found in dream "
            f"{artifact.get('dream_id', '?')}"
        )
    task = matching[0]

    # Idempotency: reject hard se already done.
    if task.get("status") == "done":
        existing_skill_id = task.get("skill_id", "?")
        raise ValueError(
            f"already_submitted: task {task_id} is already done "
            f"(skill_id={existing_skill_id}). Use cycle #38 adopt to retry."
        )

    # Validate schema lenient.
    clean = _validate_skill_json(skill_json)

    # Construct Skill con provenance dai context_episode_ids del task.
    new_skill = Skill(
        name=clean["name"],
        trigger=clean["trigger"],
        body=clean["body"],
        rationale=clean["rationale"],
        stage="nrem",
        status="candidate",
        provenance_episodes=list(task.get("context_episode_ids", [])),
    )

    # Persist sul SHADOW SkillLibrary (NON live).
    shadow_skills_dir = shadow_root / "skills"
    shadow_skills_db = shadow_skills_dir / "skills_index.db"
    shadow_skills = SkillLibrary(
        dir_path=shadow_skills_dir, db_path=shadow_skills_db,
    )
    shadow_skills.store(new_skill)

    # Update artifact: marca task done + metadata audit.
    task["status"] = "done"
    task["skill_id"] = new_skill.id
    task["tokens_used_reported"] = int(tokens_used)
    task["model_name"] = str(model_name)
    task["submitted_at"] = _time.time()
    artifact_path.write_text(_json.dumps(artifact, indent=2, default=str))

    remaining = sum(
        1 for t in artifact["pending_tasks"] if t.get("status") == "pending"
    )

    return {
        "ok": True,
        "skill_id": new_skill.id,
        "dream_id": artifact.get("dream_id"),
        "remaining_pending": remaining,
        "tokens_used_reported": int(tokens_used),
        "model_name": str(model_name),
    }


def _load_artifact(shadow_root: Path) -> dict[str, Any]:
    """Load + validate dream_tasks.json. Helper condiviso da review tools.

    Raises:
        FileNotFoundError se shadow_root o artifact non esiste.
        ValueError se JSON corrotto.
    """
    import json as _json
    if not shadow_root.exists() or not shadow_root.is_dir():
        raise FileNotFoundError(
            f"unknown_dream: shadow_root {shadow_root} does not exist"
        )
    artifact_path = shadow_root / "dream_tasks.json"
    if not artifact_path.exists():
        raise FileNotFoundError(
            f"unknown_dream: artifact {artifact_path} missing"
        )
    try:
        return _json.loads(artifact_path.read_text())
    except _json.JSONDecodeError as exc:
        raise ValueError(f"dream artifact corrupted: {exc}") from exc


def dream_status(*, shadow_root: Path) -> dict[str, Any]:
    """CYCLE #37 — Status summary di un dream.

    Returns:
        {dream_id, shadow_root, n_total, n_done, n_pending,
         total_tokens_used, models_used (set as list), instructions, created_at}.

    Zero LLM, zero modifica. Read-only.
    """
    shadow_root = Path(shadow_root)
    artifact = _load_artifact(shadow_root)
    tasks = artifact.get("pending_tasks", [])
    n_total = len(tasks)
    n_done = sum(1 for t in tasks if t.get("status") == "done")
    n_pending = sum(1 for t in tasks if t.get("status") == "pending")
    total_tokens = sum(int(t.get("tokens_used_reported", 0) or 0) for t in tasks)
    models = sorted({
        str(t.get("model_name", "") or "")
        for t in tasks if t.get("model_name")
    })
    artifact_path = shadow_root / "dream_tasks.json"
    return {
        "dream_id": artifact.get("dream_id"),
        "shadow_root": str(shadow_root),
        "n_total": n_total,
        "n_done": n_done,
        "n_pending": n_pending,
        "total_tokens_used": total_tokens,
        "models_used": models,
        "instructions": artifact.get("instructions"),
        "summary": artifact.get("summary"),
        "artifact_mtime": artifact_path.stat().st_mtime if artifact_path.exists() else None,
    }


def dream_list_pending(*, shadow_root: Path) -> list[dict[str, Any]]:
    """CYCLE #37 — Lista task ancora pending, completa di system_prompt+user_prompt.

    Il chiamante (Claude/host) leggerà questi e farà LLM call con la sua
    subscription, poi chiamerà submit_dream_result per ognuno.

    Zero LLM, zero modifica. Read-only.
    """
    shadow_root = Path(shadow_root)
    artifact = _load_artifact(shadow_root)
    pending = [
        t for t in artifact.get("pending_tasks", [])
        if t.get("status") == "pending"
    ]
    return pending


def _skill_signature(sk: Any) -> tuple:
    """Dream-mutable fields of a skill, for shadow-vs-live change detection
    (audit#3-r3 R13). Excludes id + time/usage fields (created_at,
    last_used_at) so ONLY a real retire / promote / revision / practice change
    registers — never a spurious timestamp delta."""
    return (
        sk.name, sk.trigger, sk.body, sk.rationale,
        sk.stage, sk.status,
        int(getattr(sk, "trials", 0)),
        int(getattr(sk, "successes", 0)),
        round(float(getattr(sk, "avg_tokens", 0.0)), 3),
    )


def dream_diff(
    *, shadow_root: Path, live_dirs: dict[str, Any]
) -> dict[str, Any]:
    """CYCLE #37 — Differenze shadow vs live: skill nuove pronte da adottare.

    Returns:
        {new_skills: [{shadow_id, name, trigger, body, rationale,
        stage, status, provenance_episodes, fitness_mean}],
         n_new_skills, n_shadow_skills, n_live_skills}.

    Una skill è "new" se il suo `id` è nello shadow ma NON nel live.
    Match by id (univoco). Cycle #38 (adopt) le inserirà nel live.

    Zero LLM, zero modifica. Read-only.
    """
    from verimem.skill import SkillLibrary
    shadow_root = Path(shadow_root)
    # Verifica artifact prima di accedere skills
    _load_artifact(shadow_root)
    shadow_skills_dir = shadow_root / "skills"
    shadow_skills_db = shadow_skills_dir / "skills_index.db"
    if not shadow_skills_db.exists():
        raise FileNotFoundError(
            f"unknown_dream: shadow skills DB {shadow_skills_db} missing"
        )
    shadow_lib = SkillLibrary(
        dir_path=shadow_skills_dir, db_path=shadow_skills_db,
    )
    live_skills_dir = Path(
        live_dirs.get("skills_dir_path", Path(live_dirs["skills_db"]).parent)
    )
    live_lib = SkillLibrary(
        dir_path=live_skills_dir, db_path=Path(live_dirs["skills_db"]),
    )
    shadow_ids = {s.id for s in shadow_lib.all()}
    live_ids = {s.id for s in live_lib.all()}
    new_ids = shadow_ids - live_ids
    new_skills = []
    for sid in new_ids:
        sk = shadow_lib.get(sid)
        if sk is None:
            continue
        new_skills.append({
            "shadow_id": sk.id,
            "name": sk.name,
            "trigger": sk.trigger,
            "body": sk.body,
            "rationale": sk.rationale,
            "stage": sk.stage,
            "status": sk.status,
            "provenance_episodes": list(sk.provenance_episodes),
            "fitness_mean": float(sk.fitness_mean),
        })
    # Ordinamento deterministico per nome
    new_skills.sort(key=lambda x: x["name"])
    # audit#3-r3 R13: a FULL delta, not add-only. Skills present in BOTH shadow
    # and live but RETIRED / PROMOTED / REVISED during the dream are "changed"
    # and must be carried back to live on adopt. Previously only shadow-only ids
    # were surfaced, so the dream's edits to existing skills were silently lost.
    changed_skills = []
    for sid in (shadow_ids & live_ids):
        s_sk = shadow_lib.get(sid)
        l_sk = live_lib.get(sid)
        if s_sk is None or l_sk is None:
            continue
        if _skill_signature(s_sk) != _skill_signature(l_sk):
            changed_skills.append({
                "shadow_id": s_sk.id,
                "name": s_sk.name,
                "stage": s_sk.stage,
                "status": s_sk.status,
                "fitness_mean": float(s_sk.fitness_mean),
            })
    changed_skills.sort(key=lambda x: x["name"])
    return {
        "new_skills": new_skills,
        "changed_skills": changed_skills,
        "n_new_skills": len(new_skills),
        "n_changed_skills": len(changed_skills),
        "n_shadow_skills": len(shadow_ids),
        "n_live_skills": len(live_ids),
    }


def _backup_live_skills(
    live_skills_db: Path,
    live_skills_dir: Path,
    backup_dir: Path,
) -> Path:
    """Backup atomico di skills_index.db + dir skills (.md bodies) prima di adopt.

    Returns:
        backup_dir path. Contiene skills_index.db + tutti i .md della live dir.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    # Backup DB via sqlite3 backup API (WAL-safe).
    backup_db = backup_dir / "skills_index.db"
    _backup_sqlite(live_skills_db, backup_db)
    # Mirror la dir skills (bodies .md), filtra WAL/SHM (cycle #34 lesson).
    for src in live_skills_dir.iterdir():
        if src.is_file():
            # Skip il DB (già copiato via backup API) e gli aux WAL/SHM.
            if src.name == live_skills_db.name:
                continue
            if any(src.name.endswith(suf) for suf in ("-wal", "-shm", "-journal")):
                continue
            shutil.copy2(src, backup_dir / src.name)
    return backup_dir


def _restore_live_skills(backup_dir: Path, live_skills_dir: Path) -> None:
    """Restore live skills_index.db + skills dir dal backup. Best-effort.

    CRITIC-FOUND CYCLE #38 (counterexample 0.85): "wipe orphan + restore from backup"
    invece di "overwrite-only". Senza wipe:
    (1) .db-wal/.db-shm della scrittura parziale sopravvivono → SQLite all'apertura
        può re-applicare frame WAL contro il DB-old (reintroduce skill rolled-back)
        oppure segnalare "database disk image is malformed" (salt mismatch).
    (2) Body file <skill_id>.json scritti da SkillLibrary.store PRIMA della raise
        rimangono orfani nella live skills_dir (il backup non li contiene).

    Fix: identifica i file del live che NON sono nel backup → unlink (incluso WAL/SHM
    e body file orfani). Poi copia tutti i file backup sopra live.
    """
    if not backup_dir.exists():
        return
    backup_names = {p.name for p in backup_dir.iterdir() if p.is_file()}
    # 1. Wipe orphans (WAL/SHM/journal + body file delle skill non rolled-back).
    for live_file in list(live_skills_dir.iterdir()):
        if live_file.is_file() and live_file.name not in backup_names:
            try:
                live_file.unlink()
            except Exception:  # noqa: BLE001
                pass
    # 2. Copia tutti i file backup sopra live (skills_index.db + bodies pre-state).
    for src in backup_dir.iterdir():
        if src.is_file():
            try:
                shutil.copy2(src, live_skills_dir / src.name)
            except Exception:  # noqa: BLE001
                pass


def _write_artifact_durable(path: Path, artifact: dict[str, Any]) -> None:
    """Write the dream artifact atomically + fsync so an adoption marker
    survives a hard crash: write tmp -> flush + fsync -> os.replace (atomic)."""
    import json as _json
    import os as _os

    tmp = path.with_name(path.name + ".tmp")
    data = _json.dumps(artifact, indent=2, default=str)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        _os.fsync(fh.fileno())
    _os.replace(tmp, path)


def adopt_dream(
    *,
    shadow_root: Path,
    live_dirs: dict[str, Any],
    backups_root: Path,
) -> dict[str, Any]:
    """CYCLE #38 — adopt atomico delle new_skills del shadow nel live.

    Steps:
        1. Verifica artifact non già adopted (idempotency hard).
        2. Compute diff: new_skills shadow vs live (via shadow_id set).
        3. Backup skills_index.db + skills/ in backups_root/pre_dream_<id>_<ts>/.
        4. Per ogni new_skill: insert in live SkillLibrary (try/except).
        5. Se errore mid-apply → restore dal backup + raise.
        6. Mark artifact adopted_at + adopted_skill_ids.
        7. Return {ok, n_adopted, backup_path, dream_id, adopted_skill_ids}.

    Args:
        shadow_root: dir creata dalla pipeline propose/submit.
        live_dirs: dict come per create_shadow_engine.
        backups_root: dir parent per i backup (es. CONFIG.data_dir/backups).

    Raises:
        FileNotFoundError: shadow non esiste.
        ValueError: already adopted, artifact corrupted.
        Exception: errore mid-apply → rollback eseguito prima del raise.

    Zero LLM call. Modifica LIVE (è il suo scopo), ma sempre con backup pre-apply.
    """
    import time as _time

    from verimem.skill import SkillLibrary

    shadow_root = Path(shadow_root)
    artifact = _load_artifact(shadow_root)

    # Idempotency hard.
    if artifact.get("adopted_at") is not None:
        raise ValueError(
            f"already_adopted: dream {artifact.get('dream_id')} adopted at "
            f"timestamp {artifact['adopted_at']}. Run a fresh dream to retry."
        )

    # Crash-safety: a started-but-not-completed marker means a PRIOR attempt
    # crashed after mutating live but before marking adopted_at. Refuse a blind
    # retry — it would re-backup the already-mutated live and lose the baseline.
    if artifact.get("adoption_started_at") is not None:
        raise ValueError(
            f"adoption_interrupted: dream {artifact.get('dream_id')} started "
            f"adoption at {artifact['adoption_started_at']} but never completed "
            f"(backup at {artifact.get('backup_path')}). Live skills may be "
            f"partially mutated — restore from that backup or run a fresh dream."
        )

    # Compute diff (riuso dream_diff per coerenza).
    diff = dream_diff(shadow_root=shadow_root, live_dirs=live_dirs)
    new_skills_data = diff["new_skills"]
    # audit#3-r3 R13: also adopt CHANGED existing skills (retire/promote/revise).
    changed_skills_data = diff.get("changed_skills", [])

    # Backup live ANCHE se n_new_skills == 0 (audit trail + uniformità).
    live_skills_db = Path(live_dirs["skills_db"])
    live_skills_dir = Path(
        live_dirs.get("skills_dir_path", live_skills_db.parent)
    )
    backups_root = Path(backups_root)
    dream_id = artifact.get("dream_id", "unknown")
    backup_dir = backups_root / f"pre_dream_{dream_id}_{int(_time.time())}"
    # Durable adoption marker BEFORE any live mutation, so a crash in the
    # mutate->mark gap is detectable on retry (prevents baseline clobber).
    artifact_path = shadow_root / "dream_tasks.json"
    artifact["adoption_started_at"] = _time.time()
    artifact["backup_path"] = str(backup_dir)
    _write_artifact_durable(artifact_path, artifact)
    _backup_live_skills(live_skills_db, live_skills_dir, backup_dir)

    # Carica le shadow skill (object full) per id.
    shadow_skills_dir = shadow_root / "skills"
    shadow_skills_db = shadow_skills_dir / "skills_index.db"
    shadow_lib = SkillLibrary(
        dir_path=shadow_skills_dir, db_path=shadow_skills_db,
    )

    # Open live SkillLibrary.
    live_lib = SkillLibrary(
        dir_path=live_skills_dir, db_path=live_skills_db,
    )

    adopted_ids: list[str] = []
    updated_ids: list[str] = []
    try:
        for sk_data in new_skills_data:
            sid = sk_data["shadow_id"]
            sk = shadow_lib.get(sid)
            if sk is None:
                # Edge: shadow_id presente in diff ma scomparso da shadow_lib?
                # Skip (race condition improbabile, log).
                continue
            live_lib.store(sk)
            adopted_ids.append(sk.id)
        # audit#3-r3 R13: carry CHANGED existing skills back to live too — a
        # shadow retire/promote/revision was otherwise dropped. Same backup
        # already covers rollback if any store fails.
        for sk_data in changed_skills_data:
            sid = sk_data["shadow_id"]
            sk = shadow_lib.get(sid)
            if sk is None:
                continue
            live_lib.store(sk)
            updated_ids.append(sk.id)
    except Exception:
        # Rollback dal backup, poi re-raise.
        _restore_live_skills(backup_dir, live_skills_dir)
        # Baseline restored -> clear the in-progress marker so a legitimate
        # retry is allowed (live is no longer partially mutated).
        artifact["adoption_started_at"] = None
        _write_artifact_durable(artifact_path, artifact)
        raise

    # Mark artifact (durable). Adoption completed -> clear the in-progress marker.
    artifact["adopted_at"] = _time.time()
    artifact["adoption_started_at"] = None
    artifact["adopted_skill_ids"] = adopted_ids
    artifact["updated_skill_ids"] = updated_ids
    artifact["backup_path"] = str(backup_dir)
    _write_artifact_durable(artifact_path, artifact)

    return {
        "ok": True,
        "n_adopted": len(adopted_ids),
        "n_updated": len(updated_ids),
        "backup_path": str(backup_dir),
        "dream_id": dream_id,
        "adopted_skill_ids": adopted_ids,
        "updated_skill_ids": updated_ids,
    }


__all__ = [
    "create_shadow_engine",
    "propose_dream_tasks",
    "submit_dream_result",
    "dream_status",
    "dream_list_pending",
    "dream_diff",
    "adopt_dream",
]
