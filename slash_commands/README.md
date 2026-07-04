# Optional Claude Code slash commands

If you prefer **explicit memory control** instead of the
[auto-protocol](../docs/MEMORY_PROTOCOL.md), drop these into
`~/.claude/commands/` and they become available as slash commands.

## Install

```bash
# Linux / macOS
cp slash_commands/*.md ~/.claude/commands/

# Windows
copy slash_commands\*.md %USERPROFILE%\.claude\commands\
```

Restart Claude Code. Verify with `/help` — you should see
`/recall`, `/remember`, `/memory`.

## Available commands

| Command | What it does |
|---|---|
| `/recall <query>` | Semantic search over episodes (calls `hippo_recall`) |
| `/remember <fact>` | Store a fact (calls `hippo_remember`) |
| `/memory` | Show stats + recent episodes/facts (calls `hippo_stats`, `hippo_episode_list`, `hippo_facts_recent`) |
| `/forget <id>` | Delete a fact by id (calls `hippo_fact_forget`) |
| `/skill-top` | Show top-fitness skills (calls `hippo_skill_top`) |

## Examples

```
/recall WordPress RCE chain
/remember Aurelio prefers TypeScript strict mode for new projects
/memory
/forget 6bb697dc506f
/skill-top
```

## Auto-protocol vs slash commands

You can use **both**. The auto-protocol in `CLAUDE.md` handles the
common case (write at end of task, read at start). The slash commands
give you a quick override:

- `/recall` when you want to force a memory lookup mid-conversation
- `/remember` when you want to flag a fact NOW, not at task end
- `/memory` as a status dashboard

If you don't want auto-protocol at all, simply don't add the
"HippoAgent Memory Protocol" block to your `CLAUDE.md` — the slash
commands will still work.
