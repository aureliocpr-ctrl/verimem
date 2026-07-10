"""Ingest dei transcript ``.jsonl`` di Claude Code nel Tier C (idempotente).

Usa l'``uuid`` per-messaggio come ID stabile del turno → re-ingest = no-op
(``INSERT OR REPLACE``), niente duplicati a scala (requisito anti-inquinamento).
``ts`` dal campo ``timestamp`` ISO per ordinamento/retention. Estrae SOLO testo
conversazionale (record ``user``/``assistant``), saltando ``queue-operation`` /
``system`` e il rumore degli hook (``<...>`` / ``system-reminder``).

Read-only sui file di transcript; scrive solo nel DB isolato del Tier C.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
from datetime import datetime
from pathlib import Path

from .redaction import redact_secrets
from .transcript_index import TranscriptIndex, Turn

#: Root di default dei transcript di Claude Code.
DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"

#: Lunghezza minima del testo di un turno per essere indicizzato.
MIN_TURN_CHARS = 40

#: Cap di caratteri per turno (l'embedding tronca comunque; tiene il DB bounded).
MAX_TURN_CHARS = 4000


def _parse_ts(value) -> float:
    """ISO-8601 (con 'Z') → epoch float. 0.0 se assente/illeggibile."""
    if not isinstance(value, str) or not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def _extract_text(content) -> str:
    """Testo conversazionale da ``message.content`` (str o lista di block).

    Dai content-block tiene SOLO i blocchi ``type == 'text'`` (ignora
    ``tool_use`` / ``tool_result`` / immagini): è il *verbatim* detto, non il
    rumore degli strumenti.
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return ""


def _is_noise(text: str) -> bool:
    """Filtra turni inutili come fonte conversazionale (troppo corti / hook)."""
    if len(text) < MIN_TURN_CHARS:
        return True
    head = text[:120]
    return text.startswith("<") or "system-reminder" in head


def parse_turns(jsonl_path, limit: int | None = None) -> list[Turn]:
    """Estrai ``Turn`` idempotenti (id = uuid del record) da un ``.jsonl``."""
    path = Path(jsonl_path)
    out: list[Turn] = []
    with open(path, encoding="utf-8") as fh:
        for off, line in enumerate(fh):
            if limit is not None and len(out) >= limit:
                break
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") not in ("user", "assistant"):
                continue
            if o.get("isSidechain") is True:
                continue  # WF3: subagent/sidechain turns are not the main conversation
            msg = o.get("message")
            if not isinstance(msg, dict):
                continue
            text = _extract_text(msg.get("content"))
            if _is_noise(text):
                continue
            # maschera segreti/credenziali PRIMA di persistere (finding HIGH del
            # review: la chat puo' contenere API key/token/private key incollati)
            text, _ = redact_secrets(text)
            # ID stabile = uuid del record (idempotente). Fallback (record senza
            # uuid): hash CONTENT-based (sessionId+text), NON l'offset posizionale
            # — così lo stesso contenuto mantiene lo stesso id anche se il file
            # viene riscritto/prependato (no duplicati a scala).
            uid = o.get("uuid") or (
                "h:" + hashlib.sha1(
                    ((o.get("sessionId") or path.stem) + "|" + text).encode("utf-8"),
                    usedforsecurity=False,
                ).hexdigest()[:16]
            )
            out.append(Turn(
                text=text[:MAX_TURN_CHARS],
                session_id=o.get("sessionId") or path.stem,
                role=msg.get("role") or o.get("type"),
                ts=_parse_ts(o.get("timestamp")),
                source_path=str(path),
                source_offset=off,
                id=uid,
            ))
    return out


def ingest_session(jsonl_path, index: TranscriptIndex,
                   limit: int | None = None) -> dict:
    """Indicizza una sessione. Idempotente: ``added==0`` al re-ingest."""
    turns = parse_turns(jsonl_path, limit=limit)
    before = index.count()
    stored = index.store_batch(turns)
    after = index.count()
    return {
        "session": Path(jsonl_path).stem,
        "parsed": len(turns),
        "stored": stored,
        "added": after - before,  # 0 su re-ingest = idempotente
        "total": after,
    }


def ingest_dir(projects_dir=None, index: TranscriptIndex | None = None,
               limit_per_session: int | None = None,
               glob_pat: str = "**/*.jsonl") -> dict:
    """Indicizza tutti i ``.jsonl`` sotto ``projects_dir`` (ricorsivo)."""
    base = Path(projects_dir) if projects_dir else DEFAULT_PROJECTS_DIR
    if index is None:
        index = TranscriptIndex()
    files = [f for f in sorted(glob.glob(str(base / glob_pat), recursive=True))
             if _is_real_session_file(Path(f))]   # WF3: drop subagent/journal tapes
    summary = {"sessions": 0, "parsed": 0, "added": 0, "errors": 0, "total": 0}
    for f in files:
        try:
            r = ingest_session(f, index, limit=limit_per_session)
            summary["sessions"] += 1
            summary["parsed"] += r["parsed"]
            summary["added"] += r["added"]
        except Exception:
            summary["errors"] += 1
    summary["total"] = index.count()
    return summary


def _is_real_session_file(p: Path) -> bool:
    """A real top-level interactive session, NOT a subagent/sidechain tape or journal.
    WF3: --current was grabbing transient `agent-*.jsonl` / sidechain files (1 turn) instead
    of the live conversation, so capture missed the actual session."""
    name = p.name
    if name == "journal.jsonl" or name.startswith("agent-"):
        return False
    return "subagents" not in p.parts


def find_current_session(projects_dir=None) -> Path | None:
    """The most recent REAL top-level session ``.jsonl`` (by mtime) — excluding subagent /
    sidechain / journal files that pollute a naive newest-by-mtime pick (WF3)."""
    base = Path(projects_dir) if projects_dir else DEFAULT_PROJECTS_DIR
    files = [p for p in base.glob("**/*.jsonl") if _is_real_session_file(p)]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def main(argv: list[str] | None = None) -> int:
    """CLI: ingesta i transcript di Claude Code nel Tier C.

    Un SessionEnd hook può chiamare ``python -m engram.transcript_ingest``
    (default ``--current``) per la cattura automatica. Onora
    ``HIPPO_TRANSCRIPT_DB`` per la destinazione dello store.
    """
    ap = argparse.ArgumentParser(
        prog="engram.transcript_ingest",
        description="Ingest Claude Code session transcripts into the Tier C index.",
    )
    ap.add_argument("--all", action="store_true",
                    help="ingesta tutte le sessioni sotto --projects-dir")
    ap.add_argument("--session", help="ingesta un singolo file .jsonl")
    ap.add_argument("--current", action="store_true",
                    help="ingesta la sessione più recente (default)")
    ap.add_argument("--projects-dir", default=None)
    ap.add_argument("--limit", type=int, default=None,
                    help="cap di turni per sessione")
    args = ap.parse_args(argv)

    index = TranscriptIndex()  # path di default (onora HIPPO_TRANSCRIPT_DB)
    if args.all:
        print(f"[tier-c ingest --all] "
              f"{ingest_dir(args.projects_dir, index, limit_per_session=args.limit)}")
        return 0
    if args.session:
        print(f"[tier-c ingest] {ingest_session(args.session, index, limit=args.limit)}")
        return 0
    cur = find_current_session(args.projects_dir)
    if cur is None:
        print("[tier-c ingest] nessuna sessione trovata")
        return 1
    print(f"[tier-c ingest --current] "
          f"{ingest_session(cur, index, limit=args.limit)}")
    return 0


__all__ = [
    "parse_turns", "ingest_session", "ingest_dir", "find_current_session",
    "main", "DEFAULT_PROJECTS_DIR",
]


if __name__ == "__main__":
    raise SystemExit(main())
