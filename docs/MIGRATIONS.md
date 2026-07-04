# Database migrations — HippoAgent

HippoAgent uses **three SQLite databases** with independent lifecycles:

| db_id      | file                                | content                |
|------------|-------------------------------------|------------------------|
| `episodes` | `data/episodes/episodes.db`         | episodic memory + traces + causal graph |
| `skills`   | `data/skills/skills_index.db`       | skill index + lineage edges |
| `semantic` | `data/semantic/semantic.db`         | consolidated facts |

Each DB carries its own `_schema_version` table. Migrations are tracked
per-DB so the three persistence layers can evolve independently.

## Why a hand-rolled framework?

[`hippoagent/migrations/__init__.py`](../hippoagent/migrations/__init__.py)
ships a ~100-line `ensure_schema_version()` ladder instead of pulling in
[Alembic](https://alembic.sqlalchemy.org/). Reasoning:

- Alembic is opinionated about a single centralised schema; we have three.
- The existing schemas use `CREATE TABLE IF NOT EXISTS`, so the v0 → v1
  upgrade is a no-op for fresh installs.
- Auditability: a code reviewer can read the entire migration framework
  in one sitting. No transitive deps.

## Lifecycle

On import, each persistence module runs:

```python
ensure_schema_version(
    conn,
    db_id="episodes",          # one of {episodes, skills, semantic}
    target_version=1,          # current declared version
    migrations=[],             # ordered list of (version, callable)
)
```

If the DB is fresh (no `_schema_version` row) or already at the target,
the call is a no-op. Otherwise the framework runs every pending migration
in order, inside a single `BEGIN IMMEDIATE` transaction. On error the
whole upgrade rolls back; the DB stays at its pre-call version.

## Adding a migration

Suppose we want to add a `priority INTEGER` column to `episodes` in v2.

1. **Write the migration callable** in `hippoagent/memory.py`:

   ```python
   def _migrate_episodes_v2(conn: sqlite3.Connection) -> None:
       conn.execute("ALTER TABLE episodes ADD COLUMN priority INTEGER DEFAULT 0")
   ```

2. **Bump `target_version` and append** to the migrations list:

   ```python
   ensure_schema_version(
       conn,
       db_id="episodes",
       target_version=2,                                    # was 1
       migrations=[(2, _migrate_episodes_v2)],              # ordered
   )
   ```

3. **Update the test** in `tests/test_migrations.py`:

   ```python
   def test_episodes_at_v2(tmp_path):
       em = EpisodicMemory(db_path=tmp_path / "ep.db")
       with em._connect() as c:
           assert schema_version(c, "episodes") == 2
   ```

4. **Document the schema delta** under [Schema history](#schema-history)
   below.

## Recovery

If a migration fails midway, the connection rolls back. Operators see the
exception in the structured log. Recovery options:

- **For breaking changes**, keep the old DB file around (the framework
  never deletes it). After fixing the migration, restart the process.
- **For data corruption**, the JSON skill files under `data/skills/`
  remain authoritative — the SQLite index can be rebuilt from them.

## Schema history

### v1 (2026-05-08)

Initial schema captured as v1. No DDL changes from the pre-migration
codebase; the framework simply stamps existing fresh installs at v1.

| db_id      | tables |
|------------|--------|
| `episodes` | `episodes`, `traces`, `causal_edges`, `_schema_version` |
| `skills`   | `skills`, `skill_lineage`, `_schema_version` |
| `semantic` | `facts`, `_schema_version` |

### v2 — `salience_score` cache (FORGIA pezzo #6)

Adds two columns to `episodes`:

- `salience_score REAL NOT NULL DEFAULT 0.0` — Mattar-Daw replay
  priority cached at store-time so recall doesn't re-compute.
- `last_accessed_at REAL DEFAULT NULL` — recency tie-break for
  the recall pipeline.

Migration: `ALTER TABLE episodes ADD COLUMN ...`. NULL on existing
rows; populated lazily on next `compute_salience` pass.

### v3 — `dg_embedding` BLOB column (FORGIA pezzo #13)

Adds `episodes.dg_embedding BLOB DEFAULT NULL`. Stores the sparse
DG-encoded summary embedding (uint16 idx + float32 val) for the
`use_dg=True` recall path. Existing rows get a NULL value;
`_backfill_dg_embeddings()` lazily populates them on first DG recall.

### v4 — `context_embedding` BLOB column (FORGIA pezzo #14, current)

Adds `episodes.context_embedding BLOB DEFAULT NULL`. Stores the TCM
context vector active when the episode was encoded (Howard & Kahana
2002 list-context dynamics). Existing rows get a NULL value; only
new episodes encoded under `tcm_wake_enabled=True` populate it.

| db_id      | tables (v4) |
|------------|-------------|
| `episodes` | `episodes` (+ salience, last_accessed, dg_embedding, context_embedding), `traces`, `causal_edges`, `_schema_version` |
| `skills`   | `skills`, `skill_lineage`, `_schema_version` |
| `semantic` | `facts`, `_schema_version` |

Backward-compat path: every recall flag (`use_dg`, `context_emb`,
etc.) defaults OFF, so a v3 DB upgraded to v4 with NULL columns still
works for legacy callers — only new opt-in flags require the
populated columns.
