"""Generate realistic synthetic data for performance testing.

Produces:
  - 1000 skills with embeddings and varied trigger texts
  - 5000 episodes with traces and summary embeddings
  - 500 semantic facts

The data is written to a temp directory passed in by the caller; nothing
under `data/` is touched.

This module deliberately bypasses sentence-transformers (it's heavy to load
and offline-unfriendly) and uses the same hashing-trick stub as the unit
tests. The clustering / similarity behaviour matches the real model
qualitatively because the stub still produces texts that share tokens with
high cosine similarity.
"""
from __future__ import annotations

import hashlib
import random
import re
import time
import uuid
from pathlib import Path

import numpy as np

_EMBED_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def stub_vector(text: str) -> np.ndarray:
    """Deterministic 384-d L2-normalized vector via hashing trick."""
    v = np.zeros(_EMBED_DIM, dtype=np.float32)
    tokens = _TOKEN_RE.findall((text or "").lower())
    if not tokens:
        digest = hashlib.sha256((text or "").encode("utf-8", errors="replace")).digest()
        seed = int.from_bytes(digest[:8], "big") % (2**32 - 1)
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(_EMBED_DIM).astype(np.float32)
    else:
        for tok in tokens:
            d = hashlib.sha256(tok.encode("utf-8")).digest()
            bucket = int.from_bytes(d[:4], "big") % _EMBED_DIM
            sign = 1.0 if d[4] & 1 else -1.0
            v[bucket] += sign
    norm = np.linalg.norm(v)
    if norm > 0:
        v = v / norm
    return v.astype(np.float32, copy=False)


_DOMAINS = [
    "python", "javascript", "rust", "go", "sql", "react", "vue",
    "docker", "kubernetes", "aws", "git", "linux", "bash", "shell",
    "test", "debug", "refactor", "performance", "security", "auth",
    "api", "graphql", "rest", "websocket", "grpc", "asyncio", "thread",
    "regex", "json", "yaml", "csv", "xml", "html", "css", "tailwind",
    "fastapi", "django", "flask", "express", "nextjs", "vite", "webpack",
    "postgres", "sqlite", "mysql", "redis", "mongodb", "elasticsearch",
    "ssh", "tcp", "udp", "http", "https", "tls", "oauth", "jwt",
    "numpy", "pandas", "matplotlib", "torch", "transformer", "embedding",
]
_VERBS = [
    "configure", "implement", "fix", "optimize", "refactor", "test",
    "deploy", "monitor", "debug", "build", "extract", "synthesize",
    "validate", "parse", "render", "compile", "package", "publish",
]
_OBJECTS = [
    "endpoint", "service", "function", "module", "schema", "migration",
    "container", "image", "queue", "cache", "stream", "pipeline",
    "transformer", "router", "controller", "model", "view", "template",
    "form", "field", "index", "constraint", "trigger", "view",
]


def _make_text(rng: random.Random, n_tokens_min: int = 4, n_tokens_max: int = 12) -> str:
    n = rng.randint(n_tokens_min, n_tokens_max)
    return " ".join(
        rng.choice(_DOMAINS + _VERBS + _OBJECTS) for _ in range(n)
    )


def _make_clustered_text(
    rng: random.Random, anchor_tokens: list[str], n_extra: int = 4
) -> str:
    extras = [rng.choice(_DOMAINS + _VERBS + _OBJECTS) for _ in range(n_extra)]
    return " ".join(anchor_tokens + extras)


def seed_skills(skills_dir: Path, db_path: Path, n: int = 1000, seed: int = 42) -> None:
    """Write n skills directly to JSON files + the SQLite index.

    Bypasses SkillLibrary.store() to keep this fast — we want the *data*, not
    the embedding-encoding overhead which would dominate seed time.
    """
    import json
    import sqlite3

    rng = random.Random(seed)
    skills_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema = """
    CREATE TABLE IF NOT EXISTS skills (
        id TEXT PRIMARY KEY, version INTEGER NOT NULL, name TEXT NOT NULL,
        trigger TEXT NOT NULL, stage TEXT NOT NULL, status TEXT NOT NULL,
        trials INTEGER NOT NULL, successes INTEGER NOT NULL,
        avg_tokens REAL NOT NULL, created_at REAL NOT NULL,
        updated_at REAL NOT NULL, trigger_embedding BLOB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS skill_lineage (
        parent_id TEXT NOT NULL, child_id TEXT NOT NULL,
        relation TEXT NOT NULL, created_at REAL NOT NULL,
        PRIMARY KEY (parent_id, child_id, relation)
    );
    CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status);
    CREATE INDEX IF NOT EXISTS idx_skills_stage ON skills(stage);
    """
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    cur = conn.cursor()

    # Build a few thematic clusters so similarity computations have signal,
    # not pure white noise.
    cluster_anchors = [
        rng.sample(_DOMAINS + _VERBS, 2) for _ in range(20)
    ]
    now = time.time()
    rows = []
    for i in range(n):
        sid = uuid.uuid4().hex[:12]
        # 70% of skills belong to a thematic cluster, 30% are random
        if rng.random() < 0.7:
            anchor = rng.choice(cluster_anchors)
            name = _make_clustered_text(rng, anchor, n_extra=2)[:80]
            trigger = _make_clustered_text(rng, anchor, n_extra=4)[:300]
        else:
            name = _make_text(rng, 3, 6)[:80]
            trigger = _make_text(rng, 6, 12)[:300]
        body = _make_text(rng, 20, 60)
        rationale = _make_text(rng, 8, 16)
        emb = stub_vector(f"{name}\n{trigger}")
        trials = rng.randint(0, 20)
        successes = rng.randint(0, trials)
        avg_tokens = rng.uniform(100, 2000)
        status = rng.choice(["candidate", "candidate", "candidate", "promoted"])
        stage = rng.choice(["nrem", "nrem", "rem", "manual"])
        ts = now - rng.uniform(0, 86400 * 30)

        skill = {
            "id": sid, "version": 1, "name": name, "trigger": trigger,
            "body": body, "rationale": rationale, "stage": stage,
            "provenance_episodes": [], "parent_skills": [], "status": status,
            "trials": trials, "successes": successes, "avg_tokens": avg_tokens,
            "created_at": ts, "updated_at": ts,
            "learned_embedding": None, "compiled_macro": None,
            "is_counterfactual": False, "practice_prompts": [],
        }
        (skills_dir / f"{sid}.json").write_text(
            json.dumps(skill, indent=2), encoding="utf-8"
        )
        rows.append((
            sid, 1, name, trigger, stage, status, trials, successes,
            avg_tokens, ts, ts, emb.tobytes(),
        ))
    cur.executemany(
        """INSERT OR REPLACE INTO skills
        (id, version, name, trigger, stage, status, trials, successes,
         avg_tokens, created_at, updated_at, trigger_embedding)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()


def seed_episodes(db_path: Path, n: int = 5000, seed: int = 43) -> None:
    """Write n episodes with summary embeddings and a few traces each."""
    import json
    import sqlite3

    rng = random.Random(seed)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = """
    CREATE TABLE IF NOT EXISTS episodes (
        id TEXT PRIMARY KEY, task_id TEXT NOT NULL, task_text TEXT NOT NULL,
        outcome TEXT NOT NULL, final_answer TEXT NOT NULL,
        tokens_used INTEGER NOT NULL, skills_used TEXT NOT NULL,
        created_at REAL NOT NULL, notes TEXT NOT NULL, critique TEXT NOT NULL,
        summary_embedding BLOB NOT NULL
    );
    CREATE TABLE IF NOT EXISTS traces (
        episode_id TEXT NOT NULL, step INTEGER NOT NULL, thought TEXT NOT NULL,
        action TEXT NOT NULL, action_input TEXT NOT NULL, observation TEXT NOT NULL,
        PRIMARY KEY (episode_id, step),
        FOREIGN KEY (episode_id) REFERENCES episodes(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS causal_edges (
        src_episode_id TEXT NOT NULL, dst_episode_id TEXT NOT NULL,
        via_skill_id TEXT NOT NULL, weight REAL NOT NULL,
        PRIMARY KEY (src_episode_id, dst_episode_id, via_skill_id)
    );
    CREATE INDEX IF NOT EXISTS idx_episodes_task ON episodes(task_id);
    CREATE INDEX IF NOT EXISTS idx_episodes_outcome ON episodes(outcome);
    CREATE INDEX IF NOT EXISTS idx_episodes_created ON episodes(created_at);
    """
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.execute("PRAGMA journal_mode=WAL;")
    cur = conn.cursor()

    now = time.time()
    ep_rows = []
    trace_rows = []
    for i in range(n):
        eid = uuid.uuid4().hex[:12]
        task_text = _make_text(rng, 8, 18)
        summary = f"task: {task_text}; result"
        emb = stub_vector(summary)
        outcome = rng.choice(["success", "success", "success", "failure"])
        final_answer = _make_text(rng, 5, 20)
        tokens_used = rng.randint(50, 5000)
        skills_used = json.dumps([uuid.uuid4().hex[:12] for _ in range(rng.randint(0, 3))])
        ts = now - rng.uniform(0, 86400 * 30)
        ep_rows.append((
            eid, f"task_{i}", task_text, outcome, final_answer, tokens_used,
            skills_used, ts, "", "", emb.tobytes(),
        ))
        for step in range(rng.randint(2, 5)):
            trace_rows.append((
                eid, step,
                _make_text(rng, 4, 8),  # thought
                _make_text(rng, 1, 3),  # action
                _make_text(rng, 4, 10), # action_input
                _make_text(rng, 8, 25), # observation
            ))
    cur.executemany(
        """INSERT OR REPLACE INTO episodes
        (id, task_id, task_text, outcome, final_answer, tokens_used,
         skills_used, created_at, notes, critique, summary_embedding)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        ep_rows,
    )
    cur.executemany(
        """INSERT INTO traces
        (episode_id, step, thought, action, action_input, observation)
        VALUES (?,?,?,?,?,?)""",
        trace_rows,
    )
    conn.commit()
    conn.close()


def seed_facts(db_path: Path, n: int = 500, seed: int = 44) -> None:
    """Write n semantic facts with embeddings."""
    import sqlite3

    rng = random.Random(seed)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema = """
    CREATE TABLE IF NOT EXISTS facts (
        id TEXT PRIMARY KEY, proposition TEXT NOT NULL, topic TEXT NOT NULL,
        confidence REAL NOT NULL, source_episodes TEXT NOT NULL,
        created_at REAL NOT NULL, embedding BLOB NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_facts_topic ON facts(topic);
    """
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    cur = conn.cursor()

    now = time.time()
    rows = []
    for _ in range(n):
        fid = uuid.uuid4().hex[:12]
        prop = _make_text(rng, 8, 20)
        topic = rng.choice(_DOMAINS)
        emb = stub_vector(prop)
        rows.append((
            fid, prop, topic, rng.uniform(0.3, 0.95), "",
            now - rng.uniform(0, 86400 * 14), emb.tobytes(),
        ))
    cur.executemany(
        """INSERT OR REPLACE INTO facts
        (id, proposition, topic, confidence, source_episodes, created_at, embedding)
        VALUES (?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()


def seed_repo(root: Path, n_files: int = 1000, seed: int = 45) -> None:
    """Generate a synthetic repo with n Python files of varied size."""
    rng = random.Random(seed)
    root.mkdir(parents=True, exist_ok=True)
    pkgs = ["core", "utils", "models", "services", "handlers", "tests"]
    for p in pkgs:
        (root / p).mkdir(parents=True, exist_ok=True)
        (root / p / "__init__.py").write_text("", encoding="utf-8")

    for i in range(n_files):
        pkg = rng.choice(pkgs)
        sub = rng.randint(0, 4)
        sub_dir = root / pkg
        for _ in range(sub):
            sub_dir = sub_dir / f"sub{rng.randint(0,5)}"
            sub_dir.mkdir(parents=True, exist_ok=True)
            (sub_dir / "__init__.py").write_text("", encoding="utf-8")
        path = sub_dir / f"mod_{i:04d}.py"
        n_classes = rng.randint(0, 3)
        n_funcs = rng.randint(2, 12)
        lines = [
            "from __future__ import annotations",
            "import os, sys, json",
            "",
        ]
        for c in range(n_classes):
            lines.append(f"class Klass{i}_{c}:")
            lines.append("    def __init__(self, x: int, y: int) -> None:")
            lines.append("        self.x, self.y = x, y")
            lines.append("    def method_a(self, arg: str) -> str:")
            lines.append("        return arg")
            lines.append("")
        for f in range(n_funcs):
            lines.append(f"def func_{i}_{f}(arg: int, opt: str = 'x') -> int:")
            lines.append(f"    return arg + {f}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")


def seed_all(
    base: Path,
    n_skills: int = 1000,
    n_episodes: int = 5000,
    n_facts: int = 500,
    n_repo_files: int = 1000,
) -> dict[str, Path]:
    """Seed everything under `base`. Returns the paths used."""
    skills_dir = base / "skills"
    skills_db = base / "skills" / "skills_index.db"
    episodes_db = base / "episodes" / "episodes.db"
    semantic_db = base / "semantic" / "semantic.db"
    repo_root = base / "repo"

    seed_skills(skills_dir, skills_db, n=n_skills)
    seed_episodes(episodes_db, n=n_episodes)
    seed_facts(semantic_db, n=n_facts)
    seed_repo(repo_root, n_files=n_repo_files)

    return {
        "skills_dir": skills_dir,
        "skills_db": skills_db,
        "episodes_db": episodes_db,
        "semantic_db": semantic_db,
        "repo_root": repo_root,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--skills", type=int, default=1000)
    parser.add_argument("--episodes", type=int, default=5000)
    parser.add_argument("--facts", type=int, default=500)
    parser.add_argument("--repo-files", type=int, default=1000)
    args = parser.parse_args()
    paths = seed_all(
        Path(args.base),
        n_skills=args.skills, n_episodes=args.episodes,
        n_facts=args.facts, n_repo_files=args.repo_files,
    )
    for k, v in paths.items():
        print(f"{k}: {v}")
