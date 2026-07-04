# HippoAgent — Claude Code Plugin Quickstart

Give Claude Code a hippocampus in 3 commands.

## What this gives you

After installation, every Claude Code session has:
- **Persistent memory** across sessions (episodes + skills + semantic facts on local SQLite).
- **Auto-recall** at the start of each conversation (the `hippoagent-memory` skill triggers `hippo_recall` and `hippo_skills_for` automatically).
- **3 slash commands**: `/hippo:status`, `/hippo:consolidate`, `/hippo:bench`.
- **10 MCP tools** the agent can call: `hippo_run_task`, `hippo_recall`, `hippo_consolidate`, `hippo_skills_for`, `hippo_status`, `hippo_skill_retire/promote/edit`, `hippo_episode_get`, `hippo_skill_bundles`, `hippo_compound_skills`.

## Install

```bash
# 1. Install HippoAgent from source (not published to PyPI yet)
pip install "git+https://github.com/aureliocpr-ctrl/hippoagent.git"

# 2. Register the MCP server with Claude Code via .mcp.json
#    (command: "engram", args: ["mcp"] — see README "Install in 2 minutes")

# 3. (Optional) opt in to the new neuroscientific mechanisms
export HIPPO_BUNDLE_DISCOVERY_ENABLED=1
export HIPPO_NEGATIVE_BUNDLE_ENABLED=1
export HIPPO_SYNAPTIC_TAGGING_ENABLED=1
export HIPPO_CROSSOVER_ENABLED=1
```

That's it. Restart Claude Code and the `hippoagent-memory` skill activates automatically.

## Manual install (without `claude plugin install`)

If your Claude Code version doesn't have a plugin manifest installer yet, copy the MCP entry into `claude_desktop_config.json` directly:

```json
{
  "mcpServers": {
    "hippoagent": {
      "command": "python",
      "args": ["-m", "hippoagent.mcp_server"],
      "env": {
        "HIPPO_LOG_STDERR": "1"
      }
    }
  }
}
```

And copy the `SKILL.md` from `.claude/skills/hippoagent-memory/` into your global Claude Code skills directory.

## Verify

In Claude Code, run:

```
/hippo:status
```

You should see something like:

```
HippoAgent
  episodes:        0
  skills (total):  0
  skills promoted: 0
  semantic facts:  0
  data dir:        ~/.hippoagent/data
```

Now do a few tasks. Each one is recorded as an episode. After ~10-20 tasks, run:

```
/hippo:consolidate
```

To force a sleep cycle: skill compilation, bundle abstraction, synaptic tagging, lateral inhibition, engram crossover. The next session will have skills ready to reuse.

## Verify the agent actually scales

Run the compositional generalization bench (real LLM call):

```
/hippo:bench
```

Expected output (Anthropic Claude Haiku, 8 tasks):

| Level | raw LLM | HippoAgent |
|---|---|---|
| Lv1 (1 skill) | 100% | 100% |
| Lv2 (2 skills chained) | **0%** | **100%** |
| Lv3 (3 skills chained) | **0%** | **100%** |

The gap **grows with composition depth** — which is the empirical proof that HippoAgent scales where raw LLMs collapse.

## Privacy & data

- All memory is stored locally on disk under `HIPPO_DATA_DIR` (default `~/.hippoagent/data`).
- The skill library is plain Markdown — `.hippoagent/skills/*.md` — open in your editor any time.
- HippoAgent never sends data to a remote server other than the LLM provider's standard API.
- Delete everything: `rm -rf ~/.hippoagent/data`.

## Disable / pause

- Disable the auto-recall skill: edit `.claude/skills/hippoagent-memory/SKILL.md` and remove the file (or rename to `_SKILL.md.disabled`).
- Disable the MCP server: comment out the entry in `claude_desktop_config.json`.
- Disable just the new neuroscientific mechanisms while keeping core memory: unset the `HIPPO_*_ENABLED` env vars.

## Troubleshooting

**"Tool hippo_recall not found"**: the MCP server isn't running. Check `claude_desktop_config.json` syntax and restart Claude Code.

**"No episodes after 10 tasks"**: the auto-recall skill might not be firing. Confirm by running `/hippo:status`. If counts stay at 0, check that the `hippoagent-memory` skill is in your global skills directory.

**"Sleep cycle takes forever"**: the consolidate stage runs LLM calls for NREM/REM/schema. Limit with `HIPPO_OFFLINE=1` for pure-mechanical-only consolidation, or adjust `CONFIG.sleep_min_episodes` to fire less often.

**"CodeQL alerts"**: see `tests/test_ide_path_injection.py` (FORGIA #183) — the path-injection vector is closed via defense-in-depth pre-resolve checks.

## Going deeper

- **Architecture**: `docs/PLATFORM.md`
- **MCP integration details**: `docs/MCP_QUICKSTART.md`
- **The 183-piece engineering diary**: `FORGIA.md`
- **Bench reference data**: `data/bench_compositional_anthropic.{results,summary}.json`
