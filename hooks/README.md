# HippoAgent SessionStart hook (FORGIA #211)

`hippo_session_start.py` is a Claude Code SessionStart hook that
**injects HippoAgent memory context** at the start of every session
(CLI or desktop), without requiring the model to first call any
`hippo_*` tool.

## Why

The MCP server `hippoagent` is launched automatically by Claude Code
(via `~/.mcp.json`), so the 45 `hippo_*` tools are *available*. But
the model only calls them when its routing decides to. If the user
opens a fresh session and asks something memory-adjacent, latency to
"first hippo call" can be 1–2 turns.

This hook fires **before turn 0**: it reads counts + recent facts +
pinned episodes from local SQLite (~50ms, no embeddings, no MCP
round-trip) and prints them on stdout. Claude Code injects that
stdout as "additional context", so the model sees the memory
snapshot in its turn-0 system prompt.

## What it shows

- Episode count, fact count, skill count
- 8 most-recent facts (latest declarative knowledge)
- All pinned episodes (high-priority, never decay)
- 3 most-recent episodes
- A reminder: "memory = HippoAgent, not CLAUDE.md"

## Install

1. Copy `hippo_session_start.py` to `~/.claude/hooks/`.
2. Add to `~/.claude/settings.json`:
   ```json
   {
     "hooks": {
       "SessionStart": [
         {
           "matcher": "*",
           "hooks": [
             {
               "type": "command",
               "command": "python %USERPROFILE%\\.claude\\hooks\\hippo_session_start.py"
             }
           ]
         }
       ]
     }
   }
   ```
   (Adjust the path for Linux/macOS: `python ~/.claude/hooks/hippo_session_start.py`.)

3. Restart Claude Code. Every new session now boots with the memory
   context already loaded.

## Defensive guarantees

- **Silent on missing data**: if the data dir is unreachable, the
  hook prints nothing and exits 0 (the session starts as before).
- **No ML imports**: pure SQLite reads. Doesn't load
  sentence-transformers (would be a 16s cold start), doesn't import
  the `hippoagent` package.
- **Path autodetection**: tries `HIPPO_DATA_DIR` env, then default
  `~/.hippoagent/data`, then the worktree path. First hit wins.
- **Schema-tolerant**: handles legacy `data/semantic.db` and current
  `data/semantic/semantic.db` layouts. Tolerates older episode
  schemas without `pinned` column.
