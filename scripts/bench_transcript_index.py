"""Bench REALE del Tier C (engram.transcript_index) su transcript di sessione veri.

Misura, su una sessione `.jsonl` reale di Claude Code (cap a N turni):
  - throughput di ingest (turni/s) + dimensione DB
  - QUALITÀ di retrieval verbatim (self-retrieval recall@1/@5 + MRR): per un
    campione di turni, interroga con uno SLICE di 12 parole preso dal MEZZO del
    turno (non il prefisso, non il testo intero) e verifica che il turno torni
    in cima. Questo modella l'uso reale: "trova DOVE abbiamo detto questa cosa".

Hermetic: il DB del Tier C è in una temp-dir buttata a fine run; ZERO scrittura
su ~/.engram. Read-only sui transcript. NON usa la sessione live più recente.

Uso:
    python scripts/bench_transcript_index.py [path.jsonl] [--limit 400] [--sample 30]
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Portable default: the Claude Code projects root (override with
# $HIPPO_CLAUDE_PROJECTS). Was a hardcoded personal path — the bench now finds a
# transcript on ANY machine. Pass an explicit `path.jsonl` arg to pick one.
_PROJ_DIR = Path(
    os.environ.get("HIPPO_CLAUDE_PROJECTS", str(Path.home() / ".claude" / "projects"))
)


def _newest_transcript() -> Path | None:
    """Newest session transcript under the projects root, or None if none."""
    if not _PROJ_DIR.exists():
        return None
    jsonls = sorted(
        _PROJ_DIR.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True,
    )
    return jsonls[0] if jsonls else None


def _arg(flag: str, default: int) -> int:
    if flag in sys.argv:
        return int(sys.argv[sys.argv.index(flag) + 1])
    return default


def extract_turns(path: Path, limit: int):
    from engram.transcript_index import Turn
    turns = []
    with open(path, encoding="utf-8") as fh:
        for off, line in enumerate(fh):
            if len(turns) >= limit:
                break
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get("type") not in ("user", "assistant"):
                continue
            msg = o.get("message")
            if not isinstance(msg, dict):
                continue
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "\n".join(
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            else:
                text = ""
            text = (text or "").strip()
            if len(text) < 40:
                continue
            # salta rumore hook/system-reminder/tool-output incollato
            if text.startswith("<") or "system-reminder" in text[:120]:
                continue
            turns.append(Turn(
                text=text[:2000], session_id=path.name, role=role,
                source_path=str(path), source_offset=off,
            ))
    return turns


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--") and not a.isdigit()]
    if args:
        session = Path(args[0])
        if not session.is_absolute() and not session.exists():
            session = _PROJ_DIR / args[0]
    else:
        session = _newest_transcript()
        if session is None:
            print(f"[ERR] nessun transcript .jsonl sotto {_PROJ_DIR} — "
                  "passa un path esplicito o imposta $HIPPO_CLAUDE_PROJECTS")
            return 1
    limit = _arg("--limit", 400)
    sample_n = _arg("--sample", 30)

    if not session.exists():
        print(f"[ERR] sessione non trovata: {session}")
        return 1

    from engram.transcript_index import TranscriptIndex

    print(f"=== BENCH Tier C — {session.name} (cap {limit} turni) ===")
    turns = extract_turns(session, limit)
    print(f"turni estratti: {len(turns)}")
    if len(turns) < 10:
        print("[ERR] troppo pochi turni per il bench")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="tierc_bench_"))
    try:
        idx = TranscriptIndex(db_path=tmp / "transcript.db")
        t0 = time.perf_counter()
        n = idx.store_batch(turns)
        t_ingest = time.perf_counter() - t0
        db_kb = (tmp / "transcript.db").stat().st_size / 1024
        print(f"ingest: {n} turni in {t_ingest:.2f}s "
              f"({n / t_ingest:.0f} turni/s) · DB {db_kb:.0f} KB")

        # --- self-retrieval recall@k (query = slice di 12 parole dal mezzo) ---
        step = max(1, len(turns) // sample_n)
        sample = turns[::step][:sample_n]
        h1 = h5 = 0
        rr = 0.0
        examples = []
        for t in sample:
            words = t.text.split()
            if len(words) < 8:
                continue
            mid = len(words) // 4
            q = " ".join(words[mid:mid + 12])
            out = idx.recall(q, k=10)
            ids = [r[0].id for r in out]
            rank = ids.index(t.id) + 1 if t.id in ids else 0
            if rank == 1:
                h1 += 1
            if 0 < rank <= 5:
                h5 += 1
            if rank:
                rr += 1.0 / rank
            if len(examples) < 3:
                top = out[0][0].text[:70].replace("\n", " ") if out else "-"
                examples.append((q[:50], rank, top))
        m = len(sample)
        print(f"\nself-retrieval su {m} turni (query = 12-word middle-slice):")
        print(f"  recall@1 = {h1 / m:.2f}   recall@5 = {h5 / m:.2f}   MRR = {rr / m:.3f}")
        print("  esempi (query → rank → top-hit):")
        for q, rank, top in examples:
            print(f"    [{rank}] q={q!r}  →  {top!r}")
        print("\nNB: store ISOLATO (temp-dir), confidence=0, source_type=conversational_raw.")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
