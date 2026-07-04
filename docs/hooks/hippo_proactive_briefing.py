"""HippoAgent UserPromptSubmit hook — keyword-based proactive recall.

Cycle #53 (2026-05-14). Runs at the start of every user prompt.
Reads JSON from stdin (Claude Code hook protocol), extracts the
prompt, performs a KEYWORD-BASED recall against the semantic store,
and prints a short <engram-proactive> banner to stdout if hits found.

CYCLE #54 (2026-05-14): added telemetry (JSONL log) + per-session
dedup. Every firing appends one line to
`~/.engram/audit/briefing.jsonl`. Per-session cache at
`~/.engram/audit/session_seen.json` prevents the same fact from
re-appearing across turns of one session — keeps the banner novel.

WHY KEYWORD-BASED (not embedding):
The sentence-transformers cold load is 10-15s. Running it on EVERY
user prompt would block the session intolerably. Keyword overlap is
inferior to cosine similarity for semantic match, but is O(N) over
the facts table with no ML dep, completes in <50ms warm.

For full semantic recall, the host LLM can call the MCP tool
`hippo_briefing(task_text=...)` (cycle #53 extension) on-demand —
that path goes through the warm MCP server which already has the
embedding model loaded.

Skip rules:
  - prompt < 30 chars: too short to be a real task
  - chitchat regex (ciao/grazie/ok/sì/no/?): no real task
  - keywords < 2 after stopwording: nothing to recall on
  - no data dir / no semantic.db: silent
  - fact_id already shown in current session (cycle #54 dedup)

Threshold:
  Default = ≥ 2 keyword matches per fact (min_matched=2). Override
  via env ENGRAM_BRIEFING_MIN_MATCHED. The 0.55 cosine threshold
  used elsewhere does not apply here — different scoring scale.

Output format:
  <engram-proactive hits=N>
  ...short summary lines...
  </engram-proactive>
"""
from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
import sys
import time
from pathlib import Path

# Stopwords — small inline lists, IT + EN. Not exhaustive; enough to
# de-noise the most common filler tokens that would create false
# positives across most prompts.
_STOPWORDS_IT = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di",
    "da", "in", "con", "su", "per", "tra", "fra", "del", "della",
    "delle", "dei", "degli", "dello", "che", "chi", "cosa", "come",
    "quando", "dove", "perche", "perché", "non", "ma", "anche",
    "questo", "questa", "questi", "queste", "io", "tu", "lui", "lei",
    "noi", "voi", "loro", "mi", "ti", "si", "ci", "vi", "essere",
    "avere", "fare", "sono", "sei", "abbiamo", "siete", "stato",
    "stata", "stati", "tutto", "tutti", "tutta", "ogni", "ancora",
    "molto", "poco", "piu", "più", "meno", "qui", "altri",
    "altra", "altre",
}
_STOPWORDS_EN = {
    "the", "an", "and", "or", "but", "if", "of", "to", "in", "on",
    "for", "with", "by", "at", "as", "is", "are", "was", "were",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "should", "could", "can", "this", "that", "these", "those",
    "you", "he", "she", "it", "we", "they", "what", "which", "who",
    "where", "when", "why", "how", "from", "into", "about", "than",
    "then", "also", "very", "more", "less", "much", "some", "any",
    "all", "no", "not", "just", "only", "even",
}
# Cycle #56 (2026-05-14) — IDF-derived stopwords from the live corpus.
# Tokens appearing in >10% of facts that are STRUCTURAL not SEMANTIC:
# generic adverbs, JSON syntactic noise (proposition/topic/name as
# field names in serialized tool outputs), date markers. Keyword-of-
# domain tokens with high frequency (project, cycle, hippoagent,
# claude, aurelio, test, task, nexus, critic, ...) are kept — they
# discriminate among facts even if globally common.
_STOPWORDS_IDF = {
    # Italian common-noise tokens (high freq, low info)
    "solo", "senza", "reale", "zero",
    # JSON/schema syntactic tokens that leak from serialized examples
    "name", "parameter", "proposition", "topic", "output", "format",
    "default",
    # Date / numeric markers (year prefix in every timestamp)
    "2026", "2025", "2024",
}
_STOPWORDS = _STOPWORDS_IT | _STOPWORDS_EN | _STOPWORDS_IDF


# Chitchat: short greeting/acknowledgment/single-question patterns.
# Case-insensitive whole-prompt match. Order matters only for clarity.
_CHITCHAT_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (
        r"^\s*(ciao|salve|buongiorno|buonasera|hi|hello|hey|yo)"
        r"\s*[,!.?]*\s*$",
        r"^\s*(grazie|thanks|thank\s+you|ty|thx)"
        r"\s*[,!.?]*\s*$",
        r"^\s*(ok|okay|k|si|sì|yes|yep|yeah|no|nope|fine|"
        r"sure|ofc|certo)\s*[,!.?]*\s*$",
        r"^\s*\?+\s*$",
    )
]


def _find_data_dir() -> Path | None:
    """Same priority as the SessionStart hook."""
    for env_key in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        v = os.environ.get(env_key)
        if v:
            p = Path(v)
            if (p / "semantic").exists() or (p / "semantic.db").exists():
                return p
    for cand in (Path.home() / ".engram",
                 Path.home() / ".hippoagent" / "data"):
        if (cand / "semantic").exists() or (cand / "semantic.db").exists():
            return cand
    return None


def _tokenize(text: str, *, min_len: int = 4) -> list[str]:
    text = text.lower()
    # Keep accented chars; strip everything else to space.
    text = re.sub(r"[^\w\sàèéìòùÀÈÉÌÒÙ]", " ", text)
    tokens = text.split()
    out: list[str] = []
    seen: set[str] = set()
    for t in tokens:
        if len(t) < min_len or t in _STOPWORDS:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _is_chitchat(prompt: str) -> bool:
    return any(pat.match(prompt) for pat in _CHITCHAT_PATTERNS)


def _recall_keyword(
    sem_db: Path, keywords: list[str], *,
    top_k: int = 3, min_matched: int = 2,
) -> list[tuple[str, str, str, int, float]]:
    """Keyword recall over facts. Returns list of tuples:
       (fact_id, proposition, topic, matched_count, age_days).
    Sort by matched_count desc, then age_days asc (newer wins ties)."""
    if not keywords:
        return []
    try:
        with sqlite3.connect(str(sem_db)) as conn:
            rows = conn.execute(
                "SELECT id, proposition, topic, created_at FROM facts"
            ).fetchall()
    except Exception:
        return []
    now = time.time()
    scored: list[tuple[str, str, str, int, float]] = []
    for fid, prop, topic, created in rows:
        prop_l = (prop or "").lower()
        matched = sum(1 for kw in keywords if kw in prop_l)
        if matched < min_matched:
            continue
        try:
            age_days = (now - float(created or now)) / 86400.0
        except (TypeError, ValueError):
            age_days = 9999.0
        scored.append((fid, prop or "", topic or "", matched, age_days))
    scored.sort(key=lambda r: (-r[3], r[4]))
    return scored[:top_k]


def _daemon_json_path() -> Path:
    return Path.home() / ".engram" / "daemon.json"


def _pid_alive(pid: int) -> bool:
    """Check if a PID is alive on Windows (and POSIX, defensive).
    Returns False if pid <= 0 or any error."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            h = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid,
            )
            if not h:
                return False
            try:
                code = ctypes.c_ulong(0)
                ok = ctypes.windll.kernel32.GetExitCodeProcess(
                    h, ctypes.byref(code),
                )
                return bool(ok) and code.value == STILL_ACTIVE
            finally:
                ctypes.windll.kernel32.CloseHandle(h)
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def _read_daemon_info() -> dict | None:
    """Return daemon json if file exists, parseable, AND pid still alive.
    Stale daemon.json (file present but pid dead — Windows kill case)
    counts as "no daemon". Returns None in that case."""
    p = _daemon_json_path()
    if not p.exists():
        return None
    try:
        info = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not _pid_alive(int(info.get("pid", -1))):
        return None
    return info


def _recall_via_daemon(
    prompt: str, host: str, port: int, *,
    top_k: int = 3, threshold: float = 0.5,
    excluded_ids: set[str] | None = None,
    timeout_s: float = 0.6,
) -> list[tuple[str, str, str, float, float]] | None:
    """Cycle #60: one-shot RPC to the daemon, server-side cosine.
    Returns list of (id, proposition, topic, similarity, age_days)
    or None on any failure (so caller can fall back to keyword).
    Empty list = daemon OK but zero matches above threshold."""
    excluded_ids = excluded_ids or set()
    req = {
        "prompt": prompt,
        "top_k": int(top_k),
        "threshold": float(threshold),
        "excluded_ids": sorted(excluded_ids),
    }
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout_s)
        try:
            s.connect((host, int(port)))
            payload = json.dumps(req).encode("utf-8") + b"\n"
            s.sendall(payload)
            buf = b""
            while b"\n" not in buf:
                chunk = s.recv(65536)
                if not chunk:
                    break
                buf += chunk
                if len(buf) > 5_000_000:
                    return None
        finally:
            try:
                s.close()
            except Exception:
                pass
        line = buf.split(b"\n", 1)[0].decode("utf-8", errors="replace")
        resp = json.loads(line)
        if "error" in resp:
            return None
        hits_raw = resp.get("hits", [])
        now = time.time()
        out: list[tuple[str, str, str, float, float]] = []
        for h in hits_raw:
            try:
                created = float(h.get("created_at", now))
            except (TypeError, ValueError):
                created = now
            age_days = (now - created) / 86400.0
            out.append((
                str(h.get("id", "")),
                str(h.get("proposition", "")),
                str(h.get("topic", "")),
                float(h.get("similarity", 0.0)),
                age_days,
            ))
        return out
    except Exception:
        return None


def _audit_paths(data_dir: Path) -> tuple[Path, Path]:
    """Return (jsonl_log_path, session_seen_json_path)."""
    audit = data_dir / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    return audit / "briefing.jsonl", audit / "session_seen.json"


# Session = sliding 1-hour window. After 1h of silence, the cache
# resets so memory of "shown facts" doesn't bleed across hours-apart
# sessions.
_SESSION_TTL_S = 60 * 60


def _load_session_seen(seen_path: Path) -> tuple[set[str], float]:
    """Return (seen_fact_ids, session_start_ts). Fresh if file
    missing or TTL expired."""
    now = time.time()
    if not seen_path.exists():
        return set(), now
    try:
        data = json.loads(seen_path.read_text(encoding="utf-8"))
    except Exception:
        return set(), now
    started = float(data.get("session_start_ts", 0.0))
    if now - started > _SESSION_TTL_S:
        return set(), now
    return set(data.get("fact_ids_seen", [])), started


def _save_session_seen(
    seen_path: Path, seen_ids: set[str], session_start_ts: float,
) -> None:
    try:
        seen_path.write_text(
            json.dumps({
                "session_start_ts": session_start_ts,
                "fact_ids_seen": sorted(seen_ids),
                "last_update_ts": time.time(),
            }),
            encoding="utf-8",
        )
    except Exception:
        pass


def _append_telemetry(
    jsonl_path: Path, *,
    prompt: str, n_keywords: int, n_hits: int,
    n_dup_filtered: int, top_matched: int, top_id: str,
    min_matched_used: int, latency_ms: float,
) -> None:
    """Append one structured record. Silent on failure."""
    rec = {
        "ts": time.time(),
        "prompt_excerpt": prompt[:80].replace("\n", " "),
        "n_keywords": n_keywords,
        "n_hits": n_hits,
        "n_dup_filtered": n_dup_filtered,
        "top_matched": top_matched,
        "top_id": top_id,
        "min_matched_used": min_matched_used,
        "latency_ms": round(latency_ms, 1),
    }
    try:
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def _format_banner_keyword(
    hits: list[tuple[str, str, str, int, float]],
    n_keywords: int,
) -> str:
    out = [f"<engram-proactive mode=keyword hits={len(hits)}>"]
    out.append(
        "PATTERN MATCH from your persistent memory "
        "(keyword fallback — daemon offline; for stronger recall: "
        "hippo_briefing(task_text=...) or hippo_recall):"
    )
    for fid, prop, topic, matched, age_days in hits:
        ratio = matched / max(1, n_keywords)
        prefix = (
            f"[matched {matched}/{n_keywords} kw "
            f"({ratio:.0%}), {int(age_days)}d ago]"
        )
        topic_str = f"{topic} — " if topic else ""
        excerpt = prop.strip().replace("\n", " ")[:160]
        out.append(f"- {prefix} {topic_str}{excerpt}")
    out.append(
        "  (full lineage: hippo_lineage_trace start_id=<fact_id> "
        "kind=fact direction=backward)"
    )
    out.append("</engram-proactive>")
    return "\n".join(out)


def _format_banner_semantic(
    hits: list[tuple[str, str, str, float, float]],
) -> str:
    """Cycle #59: banner for semantic-via-daemon path."""
    out = [f"<engram-proactive mode=semantic hits={len(hits)}>"]
    out.append(
        "PATTERN MATCH from your persistent memory "
        "(semantic cosine via embedding daemon):"
    )
    for fid, prop, topic, sim, age_days in hits:
        prefix = (
            f"[cosine {sim:.2f}, {int(age_days)}d ago]"
        )
        topic_str = f"{topic} — " if topic else ""
        excerpt = prop.strip().replace("\n", " ")[:160]
        out.append(f"- {prefix} {topic_str}{excerpt}")
    out.append(
        "  (full lineage: hippo_lineage_trace start_id=<fact_id> "
        "kind=fact direction=backward)"
    )
    out.append("</engram-proactive>")
    return "\n".join(out)


def main() -> int:
    t0 = time.time()
    # Read stdin payload (Claude Code hook protocol — JSON object).
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except Exception:
        return 0

    # Claude Code's UserPromptSubmit payload exposes the prompt under
    # `prompt` (most builds) or nested in `userMessage`. Be permissive.
    prompt = (
        payload.get("prompt")
        or (payload.get("userMessage") or {}).get("text")
        or payload.get("text")
        or ""
    )
    prompt = (prompt or "").strip()

    if len(prompt) < 30 or _is_chitchat(prompt):
        return 0

    data_dir = _find_data_dir()
    if data_dir is None:
        return 0
    sem_db = data_dir / "semantic" / "semantic.db"
    if not sem_db.exists():
        sem_db = data_dir / "semantic.db"
    if not sem_db.exists():
        return 0

    keywords = _tokenize(prompt)
    if len(keywords) < 2:
        return 0

    # Cycle #56 (2026-05-14): default raised from 2 → 3 based on the
    # cycle #54 bench (precision@3 = 47% with min_matched=2 was too
    # permissive) and the briefing_stats heuristic (system itself
    # suggested 3). Override via env ENGRAM_BRIEFING_MIN_MATCHED.
    try:
        min_matched = int(os.environ.get("ENGRAM_BRIEFING_MIN_MATCHED", "3"))
    except (ValueError, TypeError):
        min_matched = 3
    min_matched = max(1, min_matched)

    # Cycle #54: per-session dedup. Load cache before either path.
    jsonl_path, seen_path = _audit_paths(data_dir)
    seen_ids, session_start_ts = _load_session_seen(seen_path)

    # Cycle #60: SEMANTIC path via the multilingual daemon.
    # Daemon uses paraphrase-multilingual-MiniLM-L12-v2 (separate
    # encoder from production engram MiniLM-L6) → keeps its own
    # in-memory cache of fact vectors in the new representation space.
    # Hook makes ONE RPC: daemon returns ranked hits directly.
    # If daemon unreachable / unhealthy / no hits → fallback keyword.
    #
    # Threshold default 0.40 — calibrated empirically against the live
    # 421-fact corpus (cycle #60 bench): @0.50 hit_rate dropped to 73%
    # because ~27% of prompts top-cosine sits in [0.40, 0.50); @0.40
    # hit_rate is 100%, precision@3 = 57.8%, recall@1 = 66.7%.
    # Critic-found regression 2026-05-14 (job 7d176a8527c3f224): the
    # previous hardcoded default was 0.50, relying on env override that
    # didn't propagate to child processes — production was silently
    # running at 0.50, suppressing banners on the [0.40, 0.50) band
    # WITHOUT keyword fallback (because semantic_hits=[] != None
    # short-circuits the fallback at line below). Hardcoded fix
    # eliminates the env-propagation footgun.
    semantic_hits: list[tuple[str, str, str, float, float]] | None = None
    daemon_info = _read_daemon_info()
    if daemon_info is not None:
        try:
            threshold_sem = float(
                os.environ.get("ENGRAM_BRIEFING_THRESHOLD", "0.40")
            )
        except (ValueError, TypeError):
            threshold_sem = 0.40
        threshold_sem = max(0.0, min(1.0, threshold_sem))
        semantic_hits = _recall_via_daemon(
            prompt, daemon_info["host"], int(daemon_info["port"]),
            top_k=3, threshold=threshold_sem,
            excluded_ids=seen_ids,
            timeout_s=0.6,
        )

    # Cycle #60: if the daemon answered (even with []), trust its verdict.
    # Don't fall back to keyword — that would mix scoring scales and
    # produce inconsistent banners across consecutive prompts.
    # Fall back ONLY if daemon was unreachable (None).
    if semantic_hits is not None:
        latency_ms = (time.time() - t0) * 1000.0
        _append_telemetry(
            jsonl_path,
            prompt=prompt, n_keywords=len(keywords),
            n_hits=len(semantic_hits), n_dup_filtered=0,
            top_matched=0,  # semantic path: no integer kw match count
            top_id=semantic_hits[0][0] if semantic_hits else "",
            min_matched_used=min_matched, latency_ms=latency_ms,
        )
        if not semantic_hits:
            return 0  # daemon said zero matches; respect that
        for hit in semantic_hits:
            seen_ids.add(hit[0])
        _save_session_seen(seen_path, seen_ids, session_start_ts)
        print(_format_banner_semantic(semantic_hits))
        return 0

    # FALLBACK: daemon unreachable → keyword path (cycle #53 + #56).
    raw_hits = _recall_keyword(
        sem_db, keywords, top_k=10, min_matched=min_matched,
    )
    deduped_hits: list[tuple[str, str, str, int, float]] = []
    n_dup = 0
    for hit in raw_hits:
        fid = hit[0]
        if fid in seen_ids:
            n_dup += 1
            continue
        deduped_hits.append(hit)
        if len(deduped_hits) >= 3:
            break

    latency_ms = (time.time() - t0) * 1000.0
    top_matched = deduped_hits[0][3] if deduped_hits else 0
    top_id = deduped_hits[0][0] if deduped_hits else ""
    _append_telemetry(
        jsonl_path,
        prompt=prompt, n_keywords=len(keywords),
        n_hits=len(deduped_hits), n_dup_filtered=n_dup,
        top_matched=top_matched, top_id=top_id,
        min_matched_used=min_matched, latency_ms=latency_ms,
    )

    if not deduped_hits:
        return 0

    for hit in deduped_hits:
        seen_ids.add(hit[0])
    _save_session_seen(seen_path, seen_ids, session_start_ts)
    print(_format_banner_keyword(deduped_hits, n_keywords=len(keywords)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
