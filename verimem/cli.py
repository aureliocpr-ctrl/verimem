"""Command-line interface for HippoAgent."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agent import HippoAgent
from .config import CONFIG
from .observability import METRICS, get_log
from .tools import PythonExecutor

app = typer.Typer(no_args_is_help=True, add_completion=False,
                  help="Verimem CLI — verified memory for AI agents: gated writes, "
                       "provenance on every read, abstention instead of hallucination.")
skills_app = typer.Typer(help="Inspect / manage the skill library")
episodes_app = typer.Typer(help="Inspect episodic memory")
providers_app = typer.Typer(help="Inspect LLM providers and discover models")
# Cycle #138-bis (2026-05-18): semantic memory operator CLI cluster.
# Aurelio gap: there was no CLI surface for facts, only the 60+
# mcp__hippoagent__hippo_facts_* MCP tools. The facts cluster pairs
# the most useful tool subset with terminal-friendly output.
facts_app = typer.Typer(help="Inspect / manage semantic memory (facts)")
# Cycle #145 (2026-05-18 sera): auto-consolidation operator surface.
# Wrapper Typer attorno a verimem.consolidation.{auto_consolidate,
# detect_cluster_candidates}. Tre sub-comandi: dry-run / apply / status.
# Pairs the deterministic cycle 144 orchestrator with terminal-friendly
# output. NB: the legacy ``engram consolidate`` (FORGIA #186 sleep cycle
# wrapper) is preserved under the alias ``engram sleep-now`` so the
# Claude Code plugin slash-command ``hippo:consolidate`` (which routes
# through hippoagent.cli, a different module) keeps working.
consolidate_app = typer.Typer(
    help="Auto-consolidate fact clusters (detect + persist master nodes)",
    no_args_is_help=True,
)
# Cycle #146 (2026-05-18 sera): lab live dashboard. Rich Live polling
# over a chat topic on the semantic store — used to watch multi-agent
# coordination chat in real time (see lab/cycle145-agent-chat-2026-05-18
# for the inaugural experiment). Generic — works on any chat topic.
lab_app = typer.Typer(
    help="Lab live dashboards (multi-agent chat watcher etc.)",
    no_args_is_help=True,
)
app.add_typer(skills_app, name="skills")
app.add_typer(episodes_app, name="episodes")
app.add_typer(providers_app, name="providers")
app.add_typer(facts_app, name="facts")
app.add_typer(consolidate_app, name="consolidate")
app.add_typer(lab_app, name="lab")
# Cycle #148 (2026-05-18 sera): swarm orchestrator over claude --bg.
from .swarm.cli import swarm_app  # noqa: E402 — Typer add_typer needs the app object before commands  # isort:skip
app.add_typer(swarm_app, name="swarm")
# Cycle #150 (2026-05-19): teams Mailbox bridge — completamento cycle 145.
# ``engram teams watch <team>`` tail dei messaggi agent-teams; ``engram
# teams send`` permette ad un operatore umano di iniettare messaggi
# nell'inbox di un teammate dall'esterno della sessione Claude.
from .teams.cli import teams_app  # noqa: E402  # isort:skip
app.add_typer(teams_app, name="teams")
# Self-host gateway (roadmap #3, 2026-07-08): REST multi-tenant sopra l'SDK.
gateway_app = typer.Typer(
    help="Self-host REST gateway (multi-tenant, API-key auth)",
    no_args_is_help=True,
)
gateway_keys_app = typer.Typer(help="Manage gateway API keys", no_args_is_help=True)
gateway_app.add_typer(gateway_keys_app, name="keys")
app.add_typer(gateway_app, name="gateway")

# LIVE Engine Room in the terminal (2026-07-15): tail of the flow events
# every surface (sdk/mcp/gateway, any vendor's agent via VERIMEM_ACTOR)
# emits from the core. `verimem flow tail` = the /ui/engine feed as text.
flow_app = typer.Typer(help="Live flow events feed",
                       no_args_is_help=True)
app.add_typer(flow_app, name="flow")


@flow_app.command("tail")
def flow_tail_cmd(
    replay: int = typer.Option(20, "--replay", help="Events to replay on start"),
    once: bool = typer.Option(False, "--once", help="Print the replay and exit (no follow)"),
    no_color: bool = typer.Option(False, "--no-color", help="Plain output"),
):
    """Follow the engine live: one line per write admitted/quarantined and
    per recall answered/abstained — across every surface and agent."""
    from .flow_tail import tail_flow
    tail_flow(replay=replay, follow=not once, color=not no_color)


@lab_app.command("live")
def lab_live_cmd(
    topic: str = typer.Option(
        "lab/cycle145-agent-chat-2026-05-18", "--topic", "-t",
        help="Chat topic to follow (default: cycle145 experiment).",
    ),
    refresh_sec: float = typer.Option(
        2.0, "--refresh-sec", "-r",
        help="Polling interval in seconds (default 2).",
    ),
    max_sec: float = typer.Option(
        0.0, "--max-sec",
        help="Auto-exit after N seconds (0 = run until Ctrl-C).",
    ),
) -> None:
    """Live tail-style dashboard of chat facts on ``topic``.

    Rich Live table refreshes every ``--refresh-sec`` and colours each
    row by the ``[ROLE @T]`` prefix. Useful for watching multi-agent
    coordination experiments end-to-end without scraping SQLite by hand.
    """
    from .lab_live import run_live
    from .semantic import SemanticMemory
    sm = SemanticMemory()
    run_live(
        sm, topic,
        refresh_sec=refresh_sec,
        max_seconds=max_sec if max_sec > 0 else None,
    )

console = Console()
log = get_log()


@app.command()
def code(
    workspace: str = typer.Argument(None, help="Workspace path (default: cwd)"),
    plan: bool = typer.Option(False, "--plan", help="Start in plan mode (agent must propose before editing)"),
    model: str = typer.Option(None, "--model", help="Override executor model (e.g. claude-opus-4-7)"),
):
    """Verimem Code — interactive agentic coding session with persistent memory.

    Like Claude Code or Aider, but every turn feeds the active-memory loop:
    skills compile from your repeated workflow, forward replay shows the
    expected action chain, sleep cycles consolidate during /sleep.
    """
    from .code import EngramCode  # heavy import — only when needed
    ws = Path(workspace) if workspace else Path.cwd()
    session = EngramCode(workspace=ws, plan_mode=plan, model_override=model)
    raise typer.Exit(session.run())


@app.command()
def run(
    task: str = typer.Argument(..., help="Free-form task text"),
    task_id: str = typer.Option("adhoc", help="Task identifier"),
):
    """Run a single ad-hoc task (no validator — non-empty answer = success)."""
    agent = HippoAgent.build()
    def _val(ans: str): return (bool(ans.strip()), "non-empty" if ans.strip() else "empty")
    result = agent.run_task(task_id=task_id, task_text=task, validator=_val)
    console.print(Panel.fit(result.episode.final_answer or "(empty)",
                            title=f"Answer ({result.episode.outcome})"))
    console.print(
        f"[dim]steps={result.episode.num_steps} tokens={result.episode.tokens_used} "
        f"skills_used={len(result.skills_retrieved)}[/dim]"
    )


@app.command()
def status():
    """Quick health check: episodes, skills, semantic facts.

    Used by the Claude Code plugin's `hippo:status` slash command.
    """
    agent = HippoAgent.build()
    n_eps = agent.memory.count()
    n_sk = agent.skills.count()
    n_sk_promoted = agent.skills.count(status="promoted")
    n_facts = agent.semantic.count() if hasattr(agent, "semantic") and agent.semantic else 0
    console.print(Panel.fit(
        f"[bold]HippoAgent[/bold]\n"
        f"  episodes:        {n_eps}\n"
        f"  skills (total):  {n_sk}\n"
        f"  skills promoted: {n_sk_promoted}\n"
        f"  semantic facts:  {n_facts}\n"
        f"  data dir:        {CONFIG.data_dir}",
        title="status",
    ))


@app.command()
def health():
    """Quick health check — alias for `status` (episodes, skills, facts, data dir).

    Audit#2 C-3 (2026-06-08): `engram health` is the obvious name users and docs
    reach for, but it errored with 'no such command'. Delegates to `status`.
    """
    status()


@app.command("backup-all")
def backup_all(
    tier: str = typer.Option(
        "daily", "--tier", help="Backup tier: daily | weekly | monthly | manual.",
    ),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Skip the per-store integrity check.",
    ),
) -> None:
    """Back up ALL stores (semantic + episodes + skills), not just facts.

    Audit#2 A-9 (2026-06-08): `engram facts backup` only protected semantic.db,
    so a disaster-restore lost every episode and skill. This backs up the full
    trio, each verified against its primary table.
    """
    from .backup import create_all_backups
    res = create_all_backups(tier=tier, verify_integrity=not no_verify)  # type: ignore[arg-type]
    ok = 0
    for name, info in res.items():
        if isinstance(info, dict):  # error record
            console.print(f"[red]{name}: {info.get('error')}[/red]")
        else:
            ok += 1
            console.print(
                f"[green]{name} ok:[/green] {info.path.name}  "
                f"rows: {info.fact_count}  size: {info.size_bytes / 1024:.1f} KB"
            )
    if ok == 0:
        console.print("[red]backup-all: no store backed up[/red]")
        raise typer.Exit(1) from None


@app.command()
def warmup(
    daemon: bool = typer.Option(
        True, help="Also ensure the shared encode daemon is running and warm.",
    ),
) -> None:
    """Pre-load (and download on first run) the embedding model.

    Run this ONCE after install, before wiring Verimem into Claude Code, so the
    first real recall is instant instead of silently downloading ~440 MB of
    model weights in the background on the first query. Also the natural
    pre-bake step in CI / Docker build. Exit 1 if the model can't be loaded
    (e.g. running offline with the model not yet cached).
    """
    import time

    from . import embedding

    model_name = CONFIG.embedding_model
    console.print(
        f"Warming embedding model [cyan]{model_name}[/] (dim {CONFIG.embedding_dim}) "
        "— first run downloads ~440 MB, please wait…"
    )
    t0 = time.time()
    try:
        embedding._model()  # in-process load; downloads from HF Hub if not cached
        vec = embedding.encode("warmup probe")  # prove it actually encodes
    except Exception as exc:  # noqa: BLE001 — report cleanly, no traceback
        console.print(f"[red]✗ model warm failed:[/] {type(exc).__name__}: {exc}")
        console.print(
            "  Most common cause: running offline with the model not cached. "
            "Unset VERIMEM_OFFLINE / HIPPO_OFFLINE / HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE and retry "
            "online so the weights can download once."
        )
        raise typer.Exit(code=1) from None
    dt = time.time() - t0
    console.print(f"[green]✓ model ready[/] in {dt:.1f}s (vector dim {len(vec)})")

    # Also pre-load the stage-2 cross-encoder reranker (the R@1 lever, default-ON).
    # Its cold load is ~33s; without this, every fresh process serves rerank-cold
    # recalls (the per-query budget bails to bi-encoder order) until it warms in
    # the background — so the verified R@1 lift silently doesn't apply on the first
    # ~33s of traffic. Warming it here makes the moat live from query #1.
    # Best-effort: a missing/offline reranker model must NOT fail the embed warmup.
    from . import semantic
    if semantic._rerank_enabled():
        console.print("Warming cross-encoder reranker (R@1 lever) — first run downloads…")
        t1 = time.time()
        try:
            if semantic._load_reranker() is not None:
                console.print(f"[green]✓ reranker ready[/] in {time.time() - t1:.1f}s")
            else:
                console.print("[dim]· reranker unavailable — recall falls back to fusion order[/]")
        except Exception as exc:  # noqa: BLE001
            console.print(f"[dim]· reranker warm skipped ({type(exc).__name__}); "
                          "recall still works via fusion order[/]")

    if daemon:
        from . import encode_service
        if encode_service.ensure_running():
            console.print("[green]✓ shared encode daemon already running[/]")
        else:
            console.print(
                "[dim]· shared encode daemon spawning in the background "
                "(warms from cache in ~20s; all MCP servers then share it)[/]"
            )
    console.print("[bold green]Warmup complete — Verimem recall will be instant.[/]")


@app.command()
def airgap(
    json_out: bool = typer.Option(False, "--json", help="Emit the raw JSON verdict"),
    live: bool = typer.Option(
        False, "--live",
        help="PROVE it: run a real write+search while auditing every socket "
             "and report any non-loopback egress (not just the config)."),
):
    """Air-gap self-check: can this config run with ZERO network egress?

    For the sovereign / air-gapped segment. Reports whether the LLM is local
    (Ollama / OpenAI-compatible on localhost), embeddings are pinned offline,
    and hosted-mode is off — plus one line per egress risk. For a fully
    air-gapped deployment set HIPPO_LLM_PROVIDER=ollama + HF_HUB_OFFLINE=1 and
    unset HIPPO_HOSTED. Exit code: 0 if air-gapped, 1 otherwise (CI/ops gate).

    ``--live`` goes beyond the config check: it exercises a real write+search
    with a CPython audit hook on every ``socket.connect`` and reports any
    non-loopback destination actually attempted — runtime PROOF, not a promise.
    """
    if live:
        from .airgap import probe_live_egress
        rep = probe_live_egress()
        if json_out:
            import json as _json
            console.print_json(_json.dumps(rep))
            raise typer.Exit(0 if rep["air_gapped"] else 1)
        verdict = ("[green]ZERO EGRESS ✓[/green]" if rep["air_gapped"]
                   else "[red]EGRESS DETECTED ✗[/red]")
        lines = [
            f"[bold]Verimem live no-egress probe[/bold]   {verdict}",
            f"  socket.connect observed: {rep['connects_total']}",
            f"  non-loopback egress:     {len(rep['egress'])}",
        ]
        lines.extend(f"    → {h}" for h in rep["egress"])
        console.print(Panel.fit("\n".join(lines), title="airgap --live"))
        raise typer.Exit(0 if rep["air_gapped"] else 1)
    from .airgap import airgap_status
    st = airgap_status()
    if json_out:
        import json as _json
        console.print_json(_json.dumps(st))
        raise typer.Exit(0 if st["air_gapped"] else 1)
    verdict = (
        "[green]AIR-GAPPED ✓[/green]" if st["air_gapped"]
        else "[red]NOT air-gapped ✗[/red]"
    )
    lines = [
        f"[bold]Verimem air-gap self-check[/bold]   {verdict}",
        f"  LLM:         provider={st['llm']['provider']}  local={st['llm']['local']}",
        f"               {st['llm']['reason']}",
        f"  embeddings:  offline_pinned={st['embeddings']['offline_pinned']}",
        f"  hosted_mode: {st['hosted_mode']}",
    ]
    if st["leaks"]:
        lines.append("  [yellow]egress risks:[/yellow]")
        lines.extend(f"    • {leak}" for leak in st["leaks"])
    console.print(Panel.fit("\n".join(lines), title="airgap"))
    raise typer.Exit(0 if st["air_gapped"] else 1)


@app.command()
def index(
    path: str = typer.Argument(..., help="File to index (pdf/docx/html/txt/md)"),
    source_id: str = typer.Option(None, "--source-id", help="Logical id (default: the path)"),
):
    """Index a whole FILE for semantic search with exact citation (document RAG).

    Extracts text (pdf/docx/html/txt), splits it into provenance-anchored
    chunks and embeds them. Idempotent per content-hash: re-indexing an
    unchanged file does zero work; a changed file becomes a new version that
    supersedes the old one in search. Isolated store — NOT the recall corpus.
    """
    from .document_index import DocumentIndex
    try:
        res = DocumentIndex().index_file(path, source_id=source_id)
    except FileNotFoundError:
        console.print(f"[red]file not found:[/red] {path}")
        raise typer.Exit(1) from None
    except (ValueError, RuntimeError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    if not res["is_new"]:
        console.print(f"[yellow]unchanged[/yellow] — already indexed as "
                      f"v{res['version']} (0 new chunks)")
        raise typer.Exit(0)
    console.print(f"[green]indexed[/green] {path} -> v{res['version']}, "
                  f"{res['chunks_indexed']} chunks (source_id={res['source_id']})")


@app.command("search-docs")
def search_docs(
    query: str = typer.Argument(..., help="Natural-language query"),
    k: int = typer.Option(5, "-k", help="Top-k chunks"),
):
    """Semantic search over indexed documents, with the exact citation.

    Every hit shows source file, version and character offsets
    (original[start:end] == chunk text) — the provenance moat applied to
    documents. Only the LATEST version of each source is searched.
    """
    from .document_index import DocumentIndex
    hits = DocumentIndex().search(query, k=k)
    if not hits:
        console.print("no results (index empty or no match)")
        raise typer.Exit(0)
    terms = [t for t in query.lower().split() if t.strip()]
    for i, h in enumerate(hits, 1):
        cite = f"{h['source_id']} v{h['version']} [{h['start']}:{h['end']}]"
        text = h["text"]
        # Snippet centered on the first query term present — show WHY it matched,
        # not just how the chunk begins (same idea as the lexical tier's snippet).
        low = text.lower()
        pos = min((p for p in (low.find(t) for t in terms) if p >= 0), default=0)
        start = max(0, pos - 90)
        snippet = ("…" if start > 0 else "") + text[start:start + 180].strip() \
                  + ("…" if start + 180 < len(text) else "")
        console.print(f"[bold]{i}.[/bold] ({h['score']:.3f}) [cyan]{cite}[/cyan]\n   {snippet}")


def _gateway_data_dir(data_dir: str | None) -> Path:
    from verimem._compat import data_dir as _dd
    return Path(data_dir) if data_dir else _dd() / "gateway"


@gateway_app.command("serve")
def gateway_serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (loopback by default; expose remotely behind a TLS reverse-proxy)"),
    port: int = typer.Option(8377, "--port"),
    data_dir: str = typer.Option(None, "--data-dir", help="Gateway data dir (keys db + per-tenant stores); default <verimem data>/gateway"),
    rate_limit: int = typer.Option(0, "--rate-limit", help="Max requests per key per minute (0 = off); 429 + Retry-After beyond it"),
):
    """Serve the multi-tenant REST gateway (self-host scenario).

    Every tenant gets an ISOLATED SQLite store under <data-dir>/tenants/;
    the tenant is derived from the API key alone. Writes pass the
    anti-confabulation gate, reads carry provenance, /v1/explain returns the
    TrustReport. Create keys first: ``verimem gateway keys create --tenant t``.
    """
    try:
        import uvicorn

        from .gateway import create_app
    except ImportError:
        console.print("[red]the gateway needs fastapi+uvicorn[/red] — "
                      "pip install 'verimem[server]'")
        raise typer.Exit(1) from None
    dd = _gateway_data_dir(data_dir)
    # Profilo server multi-tenant: durabilità per-commit di default —
    # WAL+synchronous=NORMAL può perdere l'ultima transazione committata su
    # crash dell'OS (finestra tra checkpoint): accettabile sul laptop
    # personale (SDK/console restano NORMAL), non su uno store che serve
    # tenant. setdefault: un override esplicito dell'operatore vince.
    os.environ.setdefault("ENGRAM_SQLITE_SYNCHRONOUS", "FULL")
    # control plane: la admin key arriva SOLO da env (mai flag = mai nella
    # shell history). Senza, gli endpoint /admin/* non esistono.
    admin_key = os.environ.get("VERIMEM_ADMIN_KEY", "").strip() or None
    app_ = create_app(data_dir=dd, rate_limit_per_minute=rate_limit,
                      admin_key=admin_key)
    console.print(f"[green]verimem gateway[/green] on http://{host}:{port} "
                  f"(data: {dd})")
    console.print("[cyan]admin API:[/cyan] "
                  + ("ON (/admin/tenants, /admin/stats)" if admin_key
                     else "off — set VERIMEM_ADMIN_KEY to enable"))
    if host not in ("127.0.0.1", "localhost", "::1"):
        console.print("[yellow]non-loopback bind:[/yellow] put a TLS "
                      "reverse-proxy (nginx/caddy) in front for remote use")
    uvicorn.run(app_, host=host, port=port, log_level="info")


@app.command("console")
def console_cmd(
    port: int = typer.Option(8378, "--port"),
    db: str = typer.Option(None, "--db", help="Path to your memory store (default: the SDK default store)"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't auto-open the browser"),
):
    """Open the trust console on YOUR local memory — one command, no keys.

    The visual layer for the single user: odometer, knowledge graph with
    chain of custody, blocked-claims log — on the store you already have.
    Personal mode: binds 127.0.0.1 ONLY and requests without a key resolve
    to your own store (Host must be localhost — DNS-rebinding guarded).
    For teams/SaaS use ``verimem gateway serve`` (API-key multi-tenant).
    """
    try:
        import uvicorn

        from .gateway import create_app
    except ImportError:
        console.print("[red]the console needs fastapi+uvicorn[/red] — "
                      "pip install 'verimem[server]'")
        raise typer.Exit(1) from None
    from .client import Memory
    mem = Memory(db) if db else Memory()
    app_ = create_app(data_dir=_gateway_data_dir(None) / "console",
                      local_tenant="local", local_memory=mem)
    url = f"http://127.0.0.1:{port}/ui"
    console.print(f"[green]verimem console[/green] → {url}")
    console.print(f"[cyan]store:[/cyan] {mem.semantic.db_path} "
                  "(personal mode, loopback only)")
    if not no_browser:
        import threading
        import webbrowser
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    uvicorn.run(app_, host="127.0.0.1", port=port, log_level="warning")


@gateway_keys_app.command("create")
def gateway_keys_create(
    tenant: str = typer.Option(..., "--tenant", help="Tenant slug ([a-z0-9._-], max 64) — its facts live in an isolated store"),
    name: str = typer.Option("", "--name", help="Label for this key (e.g. 'laptop', 'ci')"),
    plan: str = typer.Option("free", "--plan", help="Subscription tier: free | pro | enterprise | self_host (unknown → free)"),
    data_dir: str = typer.Option(None, "--data-dir"),
):
    """Create an API key for a tenant. The key is shown ONCE — only its
    sha256 is stored at rest."""
    from .gateway import GatewayKeys
    from .gateway_plans import get_plan
    resolved = get_plan(plan).name
    try:
        key = GatewayKeys(_gateway_data_dir(data_dir) / "gateway_keys.db").create(
            tenant_id=tenant, name=name, plan=resolved)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    console.print(f"[green]key created[/green] for tenant [cyan]{tenant}[/cyan] "
                  f"on plan [magenta]{resolved}[/magenta] "
                  f"— save it now, it is NOT retrievable later:\n  {key}")


@gateway_keys_app.command("list")
def gateway_keys_list(data_dir: str = typer.Option(None, "--data-dir")):
    """List keys (id, tenant, name, status) — never the secret itself."""
    from .gateway import GatewayKeys
    rows = GatewayKeys(_gateway_data_dir(data_dir) / "gateway_keys.db").list()
    if not rows:
        console.print("no keys yet — verimem gateway keys create --tenant <t>")
        raise typer.Exit(0)
    t = Table("key_id", "tenant", "name", "plan", "status")
    for r in rows:
        t.add_row(r["key_id"], r["tenant_id"], r["name"] or "-",
                  r.get("plan", "free") or "free",
                  "[red]revoked[/red]" if r["revoked_at"] else "[green]active[/green]")
    console.print(t)


@gateway_app.command("backup")
def gateway_backup_cmd(
    dest: str = typer.Argument(..., help="Snapshot directory (one per backup, never overwritten)"),
    data_dir: str = typer.Option(None, "--data-dir"),
):
    """Consistent snapshot of the gateway (keys + every tenant store).

    Uses SQLite's online backup API — correct even while the gateway is
    serving traffic (WAL connections open). Writes a backup_manifest.json.
    """
    from .gateway_backup import backup_gateway
    try:
        m = backup_gateway(_gateway_data_dir(data_dir), dest)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    console.print(f"[green]backup ok[/green] → {dest}  "
                  f"({m['n_files']} db, {m['n_tenants']} tenants)")


@gateway_app.command("restore")
def gateway_restore_cmd(
    snapshot: str = typer.Argument(..., help="Snapshot directory (from `gateway backup`)"),
    target: str = typer.Argument(..., help="NEW/empty gateway data dir to restore into"),
):
    """Restore a snapshot into an empty directory (never overwrites state)."""
    from .gateway_backup import restore_gateway
    try:
        m = restore_gateway(snapshot, target)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None
    console.print(f"[green]restore ok[/green] → {target}  "
                  f"({m['n_files']} db, {m['n_tenants']} tenants). "
                  f"Serve with: verimem gateway serve --data-dir {target}")


@gateway_keys_app.command("revoke")
def gateway_keys_revoke(
    key_id: str = typer.Argument(..., help="key_id from `gateway keys list`"),
    data_dir: str = typer.Option(None, "--data-dir"),
):
    """Revoke a key (kept in the table for audit, no longer accepted)."""
    from .gateway import GatewayKeys
    ok = GatewayKeys(_gateway_data_dir(data_dir) / "gateway_keys.db").revoke(key_id)
    console.print("[green]revoked[/green]" if ok
                  else "[yellow]not found or already revoked[/yellow]")
    raise typer.Exit(0 if ok else 1)


def _import_llm(model: str | None = None):
    """LLM for the import ingest — separate factory so tests can stub it."""
    from benchmark.qa_runner import LeanClaudeCLILLM  # subscription claude -p
    return LeanClaudeCLILLM(timeout_s=120, model=model or "claude-sonnet-4-6")


@app.command("import")
def import_cmd(
    export_path: str = typer.Argument(..., help="Chat export file (ChatGPT/Claude conversations.json or generic JSON)"),
    ids: str = typer.Option(None, "--ids", help="Comma-separated conversation ids to import (explicit consent)"),
    import_all: bool = typer.Option(False, "--all", help="Import ALL listed conversations (explicit consent for everything)"),
    match: str = typer.Option(None, "--match", help="Filter: case-insensitive substring on the conversation title"),
    since: str = typer.Option(None, "--since", help="Filter: only conversations updated on/after this date (e.g. 2026-06-01)"),
    project: str = typer.Option(None, "--project", help="Filter: exact project name (claude.ai exports)"),
    all_matching: bool = typer.Option(False, "--all-matching", help="Import the whole FILTERED subset (the explicit filter is the consent)"),
    user_name: str = typer.Option(None, "--user-name", help="Your name — used as the subject of extracted facts (identity fix)"),
    model: str = typer.Option(None, "--model", help="LLM for extraction (default claude-sonnet-4-6)"),
):
    """Cold-start the memory from your past conversations — consent-first.

    Without a selection (--ids / --all / --all-matching) this LISTS the
    conversations and imports NOTHING (privacy by default). --match/--since/
    --project narrow both the listing and --all-matching; with hundreds of
    conversations "import my verimem project since June" becomes:
    verimem import export.json --project verimem --since 2026-06-01 --all-matching
    """
    from .import_conversations import filter_conversations, import_conversations, list_conversations
    try:
        convs = filter_conversations(
            list_conversations(export_path),
            match=match, since=since, project=project)
    except FileNotFoundError:
        console.print(f"[red]file not found:[/red] {export_path}")
        raise typer.Exit(1) from None
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1) from None

    filtered = any((match, since, project))
    if not ids and not import_all and not all_matching:
        console.print(f"[bold]{len(convs)} conversations[/bold]"
                      f"{' (filtered)' if filtered else ' found'} "
                      f"(format: {convs[0]['format'] if convs else '?'}) — nothing imported yet:")
        for c in convs:
            proj = f"  [magenta]{c['project']}[/magenta]" if c.get("project") else ""
            console.print(f"  [cyan]{c['id']}[/cyan]  {c['title']}{proj}  ({c['n_messages']} messages)")
        console.print("\nTo import: [bold]--ids id1,id2[/bold], [bold]--all[/bold], "
                      "or narrow with [bold]--match/--since/--project[/bold] then [bold]--all-matching[/bold]")
        raise typer.Exit(0)

    if all_matching and not filtered:
        console.print("[red]--all-matching requires at least one filter "
                      "(--match/--since/--project); for everything use --all[/red]")
        raise typer.Exit(1) from None

    if import_all or all_matching:
        selected = [c["id"] for c in convs] if all_matching else None
    else:
        selected = [s.strip() for s in (ids or "").split(",") if s.strip()]
    from .agent import wire_reconcile_judge
    from .semantic import SemanticMemory
    sm = SemanticMemory()
    wire_reconcile_judge(sm, None)
    rep = import_conversations(sm, export_path, llm=_import_llm(model),
                               ids=selected, user_name=user_name)
    console.print(f"[green]imported[/green] {rep['imported']}/{rep['listed']} conversations "
                  f"-> {rep['stored']} facts stored, {rep['rejected']} rejected by the gate")
    for e in rep["errors"]:
        console.print(f"  [yellow]warn:[/yellow] {e}")


@app.command("stats")
def trust_stats_cmd(
    db: str = typer.Option(
        None, "--db", help="Store file (default: the configured corpus)"),
    json_out: bool = typer.Option(False, "--json", help="Emit raw JSON"),
):
    """Trust odometer: what the admission gate DID on this store.

    Persistent counters of observable gate actions — writes admitted,
    quarantined (unsupported self-claims), rejected (contradicted /
    ungrounded), plus honest read-path abstentions — and the live facts
    broken down by status. The numbers competitors don't show.
    """
    from .client import Memory
    m = Memory(db) if db else Memory()
    s = m.trust_stats()
    if json_out:
        import json as _json
        console.print_json(_json.dumps(s))
        raise typer.Exit(0)
    led = s["ledger"]
    console.print("[bold]Gate actions (all time)[/bold]")
    console.print(f"  admitted:    {led['admitted']}")
    console.print(f"  quarantined: {led['quarantined']}  [dim]unsupported claims stored hidden[/dim]")
    console.print(f"  rejected:    {led['rejected']}  [dim]not stored at all[/dim]")
    console.print(f"  abstained:   {led['abstained']}  [dim]honest 'I don't know' on reads[/dim]")
    if s["by_layer"]:
        layers = ", ".join(f"{k}:{v}" for k, v in sorted(s["by_layer"].items()))
        console.print(f"  by layer:    {layers}")
    if s["store"]:
        live = ", ".join(f"{k}:{v}" for k, v in sorted(s["store"].items()))
        console.print(f"[bold]Live facts by status[/bold]  {live}")


@app.command()
def trust(
    claim: str = typer.Argument(..., help="The claim / proposition to evaluate"),
    verified_by: list[str] = typer.Option(  # noqa: B008 — typer idiom
        None, "--verified-by",
        help="Provenance ref (repeatable): commit:abc123, pr:#12:merged, "
             "ci:main:green, coverage:85, bash:test_PASS",
    ),
    topic: str = typer.Option("adhoc/trust-check", "--topic"),
    validate: str = typer.Option(
        "fast", "--validate", help="Gate tier: 'fast' (L1 keyword detectors) "
        "or 'full' (L1+L3 contradiction vs the live corpus)",
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit the raw JSON verdict"),
):
    """Anti-confab TRUST check: would Verimem trust this claim, and WHY?

    Verimem's moat is a memory that DOESN'T LIE. This runs the same governance
    gate that guards every write: it flags unsupported hype / production-ready /
    tested / quantitative claims and tells you what evidence is missing. Add a
    real provenance ref (--verified-by commit:... / ci:...:green / coverage:N)
    and watch the same claim pass. Exit 0 if trusted, 1 if flagged.
    """
    from .anti_confab_gate import run_validation_gate
    refs = list(verified_by or [])
    res = run_validation_gate(
        proposition=claim, verified_by=refs, topic=topic,
        agent=None, validate=validate,
    )
    d = res.to_dict()
    action = d.get("action", "persist")
    if json_out:
        import json as _json
        console.print_json(_json.dumps(d))
        raise typer.Exit(0 if action == "persist" else 1)
    verdict = {
        "persist": "[green]TRUSTED ✓[/green]",
        "downgrade": "[yellow]FLAGGED ↓ (would store as provisional)[/yellow]",
        "quarantine": "[red]QUARANTINED ✗ (excluded from recall)[/red]",
        "reject": "[red]REJECTED ✗[/red]",
    }.get(action, f"[white]{action}[/white]")
    lines = [
        f"[bold]Anti-confab trust check[/bold]   {verdict}",
        f"  claim:       {claim[:90]}",
        f"  provenance:  {', '.join(refs) or '(none)'}",
    ]
    warnings = d.get("warnings") or []
    if warnings:
        lines.append("  [yellow]flags (why it's not trusted):[/yellow]")
        for w in warnings:
            layer = w.get("layer", "?")
            msg = w.get("advice") or w.get("reason") or w.get("matched_text") or ""
            lines.append(f"    • [{layer}] {str(msg)[:130]}")
    else:
        lines.append("  [dim]no anti-confab flags — adequate evidence / not a risky assertion[/dim]")
    console.print(Panel.fit("\n".join(lines), title="trust"))
    raise typer.Exit(0 if action == "persist" else 1)


@app.command("sleep-now")
def sleep_now():
    """Force a sleep cycle now (no waiting for the trigger).

    Cycle #145 rename: legacy ``engram consolidate`` (sleep-cycle wrapper)
    moved here so that ``engram consolidate`` can host the cycle 144
    auto-consolidation sub-commands. The Claude Code plugin slash
    command ``hippo:consolidate`` routes through ``hippoagent.cli`` (a
    different module) and is unaffected.
    """
    agent = HippoAgent.build()
    report = agent.consolidate()
    console.print(Panel.fit(
        f"  episodes replayed: {report.n_episodes_replayed}\n"
        f"  NREM skills:       {report.n_nrem_skills}\n"
        f"  REM skills:        {report.n_rem_skills}\n"
        f"  macros compiled:   {report.n_macros_compiled}\n"
        f"  bundle skills:     {getattr(report, 'n_bundle_skills', 0)}\n"
        f"  antagonisms:       {getattr(report, 'n_antagonisms', 0)}\n"
        f"  synaptic tags:     {getattr(report, 'n_synaptic_tags', 0)}\n"
        f"  crossovers:        {getattr(report, 'n_crossovers', 0)}\n"
        f"  promoted: {len(report.promoted)} / retired: {len(report.retired)}\n"
        f"  duration: {report.duration_s:.2f}s · LLM calls: {report.n_llm_calls}",
        title="sleep cycle complete",
    ))


@app.command()
def wake(
    n_tasks: int = typer.Option(0, help="Limit number of wake tasks (0 = all of split)"),
    seed: int = typer.Option(CONFIG.seed),
    no_skills: bool = typer.Option(False, "--no-skills", help="Baseline: ignore skill library"),
):
    """Run agent on the wake-set of the benchmark, recording episodes."""
    try:
        from benchmark.evaluator import Evaluator
        from benchmark.tasks import wake_split
    except ImportError:
        console.print("[red]research command — the `benchmark` harness is not "
                      "shipped in the wheel; run from a source checkout "
                      "(git clone https://github.com/aureliocpr-ctrl/verimem)[/]")
        raise typer.Exit(1) from None

    from .wake import WakeConfig
    cfg = WakeConfig(use_skills=not no_skills, use_past_episodes=not no_skills)
    agent = HippoAgent.build(wake_config=cfg)
    tasks = wake_split(seed=seed)
    if n_tasks > 0:
        tasks = tasks[:n_tasks]
    evaluator = Evaluator(agent, executor=PythonExecutor())
    label = "wake-baseline" if no_skills else "wake"
    console.rule(f"[bold cyan]Wake cycle ({label}) — {len(tasks)} tasks[/]")
    report = evaluator.run(tasks, label=label, on_each=_progress_printer)
    _print_report(report)


@app.command()
def sleep():
    """Run a sleep consolidation cycle on stored episodes."""
    agent = HippoAgent.build()
    console.rule("[bold magenta]Sleep cycle[/]")
    report = agent.consolidate()
    console.print(Panel.fit(
        f"replayed={report.n_episodes_replayed} clusters={report.n_clusters}\n"
        f"NREM_skills={report.n_nrem_skills}  REM_skills={report.n_rem_skills}\n"
        f"facts={report.n_facts}  promoted={len(report.promoted)}  retired={len(report.retired)}\n"
        f"merged={len(report.merged)}  duration={report.duration_s:.1f}s  tokens={report.tokens_used}",
        title="Sleep Report", border_style="magenta",
    ))


@app.command()
def benchmark(
    seed: int = typer.Option(CONFIG.seed),
    no_skills: bool = typer.Option(False, "--no-skills"),
):
    """Run the held-out test set."""
    try:
        from benchmark.evaluator import Evaluator
        from benchmark.tasks import heldout_split
    except ImportError:
        console.print("[red]research command — the `benchmark` harness is not "
                      "shipped in the wheel; run from a source checkout "
                      "(git clone https://github.com/aureliocpr-ctrl/verimem)[/]")
        raise typer.Exit(1) from None

    from .wake import WakeConfig
    cfg = WakeConfig(use_skills=not no_skills, use_past_episodes=not no_skills)
    agent = HippoAgent.build(wake_config=cfg)
    tasks = heldout_split(seed=seed)
    evaluator = Evaluator(agent, executor=PythonExecutor())
    label = "heldout-baseline" if no_skills else "heldout-hippo"
    console.rule(f"[bold green]Held-out benchmark ({label}) — {len(tasks)} tasks[/]")
    report = evaluator.run(tasks, label=label, on_each=_progress_printer)
    _print_report(report)
    out = CONFIG.reports_dir / f"{label}.json"
    out.write_text(json.dumps(report.summary_dict(), indent=2), encoding="utf-8")
    console.print(f"[dim]saved → {out}[/dim]")


@app.command()
def tui():
    """Launch the full-screen terminal UI (Textual)."""
    from .tui import main as tui_main
    tui_main()


@app.command()
def mcp():
    """Run as an MCP server over stdio.

    Use this to plug HippoAgent into Claude Code, Cursor, Cline, opencode,
    Continue, Zed, or any other MCP-aware client. Example mcp.json entry:

      {
        "mcpServers": {
          "hippoagent": {
            "command": "hippo",
            "args": ["mcp"]
          }
        }
      }
    """
    # stdout belongs to JSON-RPC from here on. cli.py already imported
    # observability (stdout logger) at module top, so the env-var default
    # inside mcp_server would come too late — re-route explicitly first.
    from .observability import route_logs_to_stderr
    route_logs_to_stderr()
    from .mcp_server import main as mcp_main
    mcp_main()


@app.command()
def chat():
    """Interactive REPL: type tasks, see the agent answer, run sleep on demand.

    Same backend as the /chat web page. Useful when you live in the terminal.
    Commands inside the REPL: /sleep, /skills, /skills <id>, /quit
    """
    agent = HippoAgent.build()
    console.print(Panel.fit(
        "[bold cyan]HippoAgent chat[/]\n"
        "Type a task and press Enter. Special commands:\n"
        "  [bold]/sleep[/]        run a consolidation cycle\n"
        "  [bold]/skills[/]       list current skills\n"
        "  [bold]/skills <id>[/]  show one skill\n"
        "  [bold]/episodes[/]     last 10 episodes\n"
        "  [bold]/quit[/]         exit",
        border_style="cyan",
    ))
    import time
    while True:
        try:
            task = console.input("[bold cyan]you ›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/]")
            return
        if not task:
            continue
        if task in ("/quit", "/exit", "/q"):
            return
        if task == "/sleep":
            console.print("[magenta]running sleep cycle…[/]")
            r = agent.consolidate()
            console.print(Panel.fit(
                f"replayed={r.n_episodes_replayed}  clusters={r.n_clusters}\n"
                f"NREM={r.n_nrem_skills}  REM={r.n_rem_skills}  facts={r.n_facts}\n"
                f"promoted={len(r.promoted)}  retired={len(r.retired)}  merged={len(r.merged)}\n"
                f"duration={r.duration_s:.1f}s  tokens={r.tokens_used}",
                title="🌙 Sleep", border_style="magenta",
            ))
            continue
        if task == "/skills":
            skills_list()
            continue
        if task.startswith("/skills "):
            skills_show(task.split(" ", 1)[1].strip())
            continue
        if task == "/episodes":
            episodes_list(limit=10)
            continue

        task_id = f"chat-{int(time.time())}"
        result = agent.run_task(
            task_id=task_id, task_text=task,
            validator=lambda ans: (bool(ans and ans.strip()), "non-empty"),
        )
        skills_used = ", ".join(f"{s.name} (f={s.fitness_mean:.2f})"
                                for s in result.skills_retrieved) or "none"
        oc_color = "green" if result.success else "red"
        console.print(Panel(
            result.episode.final_answer or "(empty)",
            title=f"[{oc_color}]{result.episode.outcome}[/] · "
                  f"{result.episode.num_steps} steps · "
                  f"{result.episode.tokens_used} tokens · skills: {skills_used}",
            border_style=oc_color,
        ))


@app.command()
def reset(yes: bool = typer.Option(False, "--yes")):
    """Wipe all episodes, skills, semantic facts."""
    if not yes:
        confirm = typer.confirm("Wipe ALL memory and skills?", default=False)
        if not confirm:
            raise typer.Abort()
    HippoAgent.build().reset()
    console.print("[red]agent reset[/red]")


@app.command()
def metrics():
    """Print current metrics snapshot."""
    snap = METRICS.snapshot()
    console.print_json(json.dumps(snap, indent=2, default=str))


@app.command()
def dashboard(
    host: str = typer.Option(CONFIG.dashboard_host),
    port: int = typer.Option(CONFIG.dashboard_port),
    insecure_bind: bool = typer.Option(
        False, "--insecure-bind",
        help="Allow binding to non-loopback hosts (REQUIRED for 0.0.0.0). "
             "When set, you must also export HIPPO_TRUSTED_NETWORK=1 to acknowledge "
             "the threat model documented in docs/SECURITY.md.",
    ),
):
    """Launch the web dashboard.

    Hardened (CVE-008 / SEC V8): refuses non-loopback bind unless
    `--insecure-bind` AND `HIPPO_TRUSTED_NETWORK=1` are both set.

    A per-process auth token is auto-generated at startup if not set
    (`HIPPO_AUTH_TOKEN`); IDE shell endpoints require it.
    """
    import os as _os
    import secrets as _secrets

    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]The web dashboard needs the server extra:[/] "
            "pip install verimem[server]")
        raise typer.Exit(1) from None

    # ---- Bind safety ------------------------------------------------------
    loopback_hosts = {"127.0.0.1", "localhost", "::1"}
    if host not in loopback_hosts:
        trusted = _os.environ.get("HIPPO_TRUSTED_NETWORK", "").strip().lower() in (
            "1", "true", "yes", "on",
        )
        if not (insecure_bind and trusted):
            console.print(
                f"[red]REFUSED:[/] non-loopback bind to {host!r} requires "
                "BOTH `--insecure-bind` AND `HIPPO_TRUSTED_NETWORK=1`.\n"
                "Loopback bind is the default. See docs/SECURITY.md for the "
                "production-deployment threat model.",
            )
            raise typer.Exit(code=2)
        console.print(
            f"[yellow]WARNING:[/] dashboard exposed on {host}:{port} — make sure "
            "the network is trusted; auth token is enforced for shell endpoints.",
        )

    # ---- Token bootstrap --------------------------------------------------
    if not _os.environ.get("HIPPO_AUTH_TOKEN", "").strip():
        token = _secrets.token_urlsafe(32)
        _os.environ["HIPPO_AUTH_TOKEN"] = token
        console.print(
            f"[dim]auth token (in-memory only): X-Hippo-Token={token}[/]",
        )

    # ---- Origin allowlist sync ------------------------------------------
    if not _os.environ.get("HIPPO_IDE_ORIGIN_ALLOWLIST", "").strip():
        _os.environ["HIPPO_IDE_ORIGIN_ALLOWLIST"] = (
            f"http://{host}:{port},http://localhost:{port}"
        )

    from .dashboard import app as fastapi_app  # noqa: F401
    console.print(f"[bold cyan]→ http://{host}:{port}[/]")
    uvicorn.run("verimem.dashboard:app", host=host, port=port, log_level="warning")


# ---- Providers sub-commands ---------------------------------------------

@providers_app.command("list")
def providers_list():
    """List all known providers with env-var status."""
    from .llm import ALIASES, PROVIDERS, is_configured, list_providers
    table = Table(title=f"LLM providers ({len(list_providers())} known)")
    table.add_column("provider"); table.add_column("env"); table.add_column("status")
    table.add_column("default_model"); table.add_column("aliases")
    aliases_by_canonical: dict[str, list[str]] = {}
    for alias, canon in ALIASES.items():
        aliases_by_canonical.setdefault(canon, []).append(alias)
    for p in list_providers():
        if p == "mock":
            continue
        if p == "anthropic":
            env, default = "ANTHROPIC_API_KEY", "claude-haiku-4-5-..."
        elif p == "ollama":
            env, default = "OLLAMA_HOST", "(any local model)"
        else:
            spec = PROVIDERS.get(p, {})
            env, default = spec.get("env", "?"), spec.get("default_model", "")
        status = "[green]configured[/]" if is_configured(p) else "[dim]not set[/]"
        table.add_row(p, env, status, default,
                      ", ".join(aliases_by_canonical.get(p, [])) or "—")
    console.print(table)


@providers_app.command("scan")
def providers_scan(
    timeout: float = typer.Option(10.0, help="HTTP timeout per provider"),
    json_out: bool = typer.Option(False, "--json", help="emit JSON only"),
):
    """Scan every configured provider and list real available models via /v1/models."""
    from .llm import scan_all_providers
    if not json_out:
        console.print("[dim]Querying configured providers (this may take a moment)…[/]")
    report = scan_all_providers(timeout=timeout)
    if json_out:
        console.print_json(json.dumps(report, indent=2, default=str))
        return
    for name, info in report.items():
        if not info.get("configured"):
            console.print(f"  [dim]{name:14s}  not configured[/]")
            continue
        if "error" in info:
            console.print(f"  [yellow]{name:14s}  configured but failed:[/] {info['error']}")
            continue
        n = info.get("n", 0)
        models = info.get("models", [])
        console.print(f"  [green]{name:14s}[/]  [bold]{n}[/] models")
        # Show a sample
        for m in models[:8]:
            console.print(f"      • {m}")
        if n > 8:
            console.print(f"      [dim]… ({n - 8} more)[/]")
    out = CONFIG.reports_dir / "providers_scan.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    console.print(f"\n[dim]→ full report saved at {out}[/dim]")


@providers_app.command("models")
def providers_models(
    provider: str = typer.Argument(..., help="Provider name or alias (e.g. kimi, deepseek, qwen)"),
):
    """List models for ONE provider via its /v1/models endpoint."""
    from .llm import _canonical, list_models_for_provider
    p = _canonical(provider)
    try:
        models = list_models_for_provider(p)
    except Exception as exc:
        console.print(f"[red]error:[/] {exc}")
        raise typer.Exit(1) from exc
    table = Table(title=f"{p}: {len(models)} models")
    cols = list({k for m in models for k in m.keys()})
    cols = ["id"] + [c for c in cols if c != "id"]
    for c in cols:
        table.add_column(c)
    for m in models:
        table.add_row(*[str(m.get(c, ""))[:60] for c in cols])
    console.print(table)


@providers_app.command("active")
def providers_active():
    """Show which provider is selected right now."""
    from .llm import _autodetect_provider, _canonical, is_configured, resolve_model
    forced = os.environ.get("HIPPO_LLM_PROVIDER", "").strip()
    provider = _canonical(forced) if forced else _autodetect_provider()
    console.print(Panel.fit(
        f"provider:        [bold]{provider}[/]\n"
        f"forced via env:  {forced or '(autodetect)'}\n"
        f"configured:      {is_configured(provider)}\n"
        f"executor model:  {resolve_model('executor') or '(provider default)'}\n"
        f"dreamer model:   {resolve_model('dreamer') or '(provider default)'}\n"
        f"critic model:    {resolve_model('critic') or '(provider default)'}",
        title="Active LLM", border_style="cyan",
    ))


@providers_app.command("check")
def providers_check(
    name: str = typer.Argument(..., help="Provider name or alias (e.g. kimi, deepseek, anthropic, ollama)"),
    timeout: float = typer.Option(10.0, help="HTTP / DNS timeout in seconds"),
):
    """Real round-trip diagnostic for one provider.

    Walks four stages and reports the precise failure mode at each:
      1. registry lookup     (is the name even known?)
      2. configuration       (is the env var set?)
      3. DNS resolution      (does the base_url hostname resolve?)
      4. /v1/models GET      (does the endpoint answer with a parseable list?)

    Exits with code 0 on full success, 1 otherwise. Designed for CI / install
    smoke tests — operator gets a clear error per failure mode rather than a
    generic 404.
    """
    import socket
    from urllib.parse import urlparse

    from .provider_registry import ALIASES_DICT, get_provider

    # Stage 1 — registry lookup
    canonical = ALIASES_DICT.get(name.lower().strip(), name.lower().strip())
    spec = get_provider(canonical)
    if spec is None:
        console.print(f"[red]✗ unknown provider:[/] {name!r}")
        console.print("  [dim]hint:[/] run `hippo providers list` for the full list")
        raise typer.Exit(1) from None

    console.print(f"[bold]Provider:[/] {spec.name}  ([dim]family={spec.family}[/])")
    if name.lower() != spec.name:
        console.print(f"  [dim]resolved alias[/] {name!r} → {spec.name!r}")

    # Stage 2 — configuration
    if spec.env:
        if not os.environ.get(spec.env):
            console.print(f"[red]✗ env var {spec.env} is not set[/]")
            console.print(f"  [dim]hint:[/] export {spec.env}=<your-key>")
            raise typer.Exit(1) from None
        console.print(f"[green]✓[/] env {spec.env} is set")
    else:
        console.print(f"[dim]⊘ no env var required (family={spec.family})[/]")

    # Stage 3 — base url + DNS resolution
    base_url = spec.base_url
    if spec.base_url_env and os.environ.get(spec.base_url_env):
        base_url = os.environ[spec.base_url_env]
        console.print(f"[dim]base_url overridden by {spec.base_url_env}[/]")

    if base_url:
        host = urlparse(base_url).hostname
        if not host:
            console.print(f"[red]✗ malformed base_url: {base_url!r}[/]")
            raise typer.Exit(1) from None
        try:
            socket.gethostbyname(host)
        except OSError as exc:
            console.print(f"[red]✗ DNS resolution failed:[/] {host}: {exc}")
            raise typer.Exit(1) from exc
        console.print(f"[green]✓[/] DNS resolved {host}")
    else:
        console.print("[dim]⊘ no base_url to probe (native SDK)[/]")

    # Stage 4 — real /v1/models call
    try:
        from .llm import list_models_for_provider
        models = list_models_for_provider(spec.name, timeout=timeout)
    except Exception as exc:
        msg = str(exc)
        kind = "connection"
        low = msg.lower()
        if "401" in msg or "auth" in low or "invalid" in low:
            kind = "401 (bad / missing API key)"
        elif "403" in msg or "forbidden" in low:
            kind = "403 (forbidden — region or plan)"
        elif "404" in msg:
            kind = "404 (endpoint not found — check base_url)"
        elif "429" in msg or "rate" in low or "quota" in low:
            kind = "429 (rate-limited)"
        elif "timeout" in low or "timed out" in low:
            kind = "timeout"
        console.print(f"[red]✗ /v1/models failed ({kind}):[/] {msg[:200]}")
        raise typer.Exit(1) from exc

    console.print(f"[green]✓[/] /v1/models returned {len(models)} entries")
    if models:
        sample = models[0].get("id", "?")
        console.print(f"  [dim]e.g.[/] {sample}")
    console.print("[bold green]All checks passed.[/]")


# ---- Skills sub-commands -------------------------------------------------

@skills_app.command("list")
def skills_list(status: str | None = typer.Option(None)):
    agent = HippoAgent.build()
    skills = agent.skills.all(status=status)  # type: ignore[arg-type]
    if not skills:
        console.print("[dim]no skills[/dim]")
        return
    table = Table(title=f"Skills ({len(skills)})")
    table.add_column("id"); table.add_column("name"); table.add_column("stage")
    table.add_column("status"); table.add_column("trials"); table.add_column("fitness")
    for s in sorted(skills, key=lambda x: -x.fitness_mean):
        table.add_row(
            s.id, s.name[:40], s.stage, s.status,
            str(s.trials), f"{s.fitness_mean:.2f}",
        )
    console.print(table)


@app.command("introspect")
def introspect(
    topic: str = typer.Argument(..., help="What you want the agent to surface knowledge about."),
    skills_top: int = typer.Option(5, help="How many skills to show"),
    episodes_top: int = typer.Option(5, help="How many episodes to show"),
):
    """Surface what the agent has learned about `topic`.

    Pure retrieval — no LLM call. Embeds the topic, returns the top-N
    cosine-similar skills (across all statuses) and the top-N similar
    episodes. Useful for "what does the system actually remember about
    fix-arithmetic-bug?" without paying for an LLM round-trip.
    """
    import numpy as _np

    from verimem import embedding as _emb

    agent = HippoAgent.build()
    q = _emb.encode(topic)

    # Skills: rank all by cosine to (learned_embedding or canonical).
    sk_scored = []
    for s in agent.skills.all():
        if s.learned_embedding is not None:
            v = _np.asarray(s.learned_embedding, dtype=_np.float32)
        else:
            v = _emb.encode(f"{s.name}\n{s.trigger}")
        sk_scored.append((float(_emb.cosine(q, v / max(_np.linalg.norm(v), 1e-9))), s))
    sk_scored.sort(key=lambda p: -p[0])
    sk_scored = sk_scored[:skills_top]

    skills_table = Table(title=f"Top {len(sk_scored)} skills for {topic!r}")
    skills_table.add_column("sim"); skills_table.add_column("name")
    skills_table.add_column("status"); skills_table.add_column("fitness")
    skills_table.add_column("trials")
    for sim, s in sk_scored:
        skills_table.add_row(
            f"{sim:+.2f}", s.name[:40], s.status,
            f"{s.fitness_mean:.2f}", str(s.trials),
        )
    console.print(skills_table)

    # Episodes: same idea but uses the existing recall path.
    ep_scored = agent.memory.recall(topic, k=episodes_top)
    eps_table = Table(title=f"Top {len(ep_scored)} episodes for {topic!r}")
    eps_table.add_column("sim"); eps_table.add_column("outcome")
    eps_table.add_column("task")
    for ep, sim in ep_scored:
        eps_table.add_row(
            f"{sim:+.2f}", ep.outcome, ep.task_text[:60],
        )
    console.print(eps_table)


@skills_app.command("show")
def skills_show(skill_id: str):
    agent = HippoAgent.build()
    s = agent.skills.get(skill_id)
    if not s:
        console.print(f"[red]not found: {skill_id}[/red]")
        raise typer.Exit(1) from None
    console.print(Panel.fit(
        f"[bold]{s.name}[/]\n"
        f"stage={s.stage} status={s.status} trials={s.trials}/{s.successes} "
        f"fitness={s.fitness_mean:.2f}\n\n"
        f"[bold]Trigger:[/] {s.trigger}\n\n"
        f"[bold]Body:[/]\n{s.body}\n\n"
        f"[bold]Rationale:[/] {s.rationale}\n"
        f"[bold]Provenance:[/] {len(s.provenance_episodes)} episodes, "
        f"{len(s.parent_skills)} parent skills",
        title=f"Skill {s.id}", border_style="cyan",
    ))


# ---- Episodes sub-commands -----------------------------------------------

@episodes_app.command("list")
def episodes_list(limit: int = 20):
    agent = HippoAgent.build()
    eps = agent.memory.all(limit=limit)
    table = Table(title=f"Episodes ({len(eps)})")
    table.add_column("id"); table.add_column("task"); table.add_column("outcome")
    table.add_column("steps"); table.add_column("tokens")
    for e in eps:
        table.add_row(
            e.id[:8], e.task_text[:40] + ("…" if len(e.task_text) > 40 else ""),
            e.outcome, str(e.num_steps), str(e.tokens_used),
        )
    console.print(table)


@episodes_app.command("show")
def episodes_show(episode_id: str):
    agent = HippoAgent.build()
    e = agent.memory.get(episode_id)
    if not e:
        # try prefix match
        for cand in agent.memory.all():
            if cand.id.startswith(episode_id):
                e = cand
                break
    if not e:
        console.print("[red]not found[/red]")
        raise typer.Exit(1) from None
    console.print(Panel.fit(e.trajectory_text(), title=f"Episode {e.id}", border_style="green"))


# ---- helpers --------------------------------------------------------------

def _progress_printer(i: int, er):
    mark = "[green]✓[/]" if er.success else "[red]✗[/]"
    console.print(f"  {mark} [{i:02d}] {er.task_id:24s}  "
                  f"steps={er.steps:2d} tokens={er.tokens:5d}  "
                  f"skills={len(er.skills_used)}  ({er.message[:40]})")


def _print_report(report) -> None:
    summary = report.summary_dict()
    console.print(Panel.fit(
        f"pass_rate=[bold]{summary['pass_rate']:.1%}[/] "
        f"({sum(1 for r in report.results if r.success)}/{len(report.results)})\n"
        f"avg_steps={summary['avg_steps']:.1f}  "
        f"avg_tokens={summary['avg_tokens']:.0f}\n"
        f"skill_reuse_rate={summary['skill_reuse_rate']:.1%}",
        title=summary["label"], border_style="cyan",
    ))
    if summary["by_family"]:
        table = Table(title="By family")
        table.add_column("family"); table.add_column("n"); table.add_column("pass_rate")
        table.add_column("avg_steps"); table.add_column("avg_tokens")
        for fam, m in summary["by_family"].items():
            table.add_row(fam, str(m["n"]), f"{m['pass_rate']:.1%}",
                          f"{m['avg_steps']:.1f}", f"{m['avg_tokens']:.0f}")
        console.print(table)


# ---- Facts sub-commands (cycle 138-bis) -----------------------------------
# Operator-facing CLI surface for semantic memory. Pairs the most useful
# subset of the hippo_facts_* MCP tools with terminal-friendly output. The
# helper ``_facts_sm`` reads HIPPO_DATA_DIR / ENGRAM_DATA_DIR dynamically so
# test isolation via monkeypatch.setenv works at call time (CONFIG is frozen
# at import).


def _facts_data_dir() -> Path:
    """Resolve the engram data directory honouring env-time overrides.

    CONFIG.data_dir is frozen at import time. The CLI must honour
    HIPPO_DATA_DIR / ENGRAM_DATA_DIR set AFTER import (eg in tests or
    when launching from a wrapper script) — otherwise pytest cannot
    isolate the live corpus.
    """
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR"):
        v = os.environ.get(k, "").strip()
        if v:
            return Path(v).expanduser().resolve()
    return CONFIG.data_dir


def _facts_sm():
    """Build a SemanticMemory pointed at the env-resolved corpus."""
    from .semantic import SemanticMemory
    data = _facts_data_dir()
    # Prefer subdir layout (data/semantic/semantic.db); fall back to
    # legacy flat (data/semantic.db) for older installations.
    sub = data / "semantic" / "semantic.db"
    flat = data / "semantic.db"
    db = sub if sub.exists() else (flat if flat.exists() else sub)
    db.parent.mkdir(parents=True, exist_ok=True)
    return SemanticMemory(db_path=db)


def _fact_id_resolve(sm, partial: str):
    """Resolve ``partial`` to a full Fact, accepting id prefix match.

    Returns the resolved Fact or None when no match (or ambiguous).
    """
    f = sm.get(partial)
    if f is not None:
        return f
    # Prefix scan (operator convenience: 8-char ids are common in output).
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT id FROM facts WHERE id LIKE ? LIMIT 2",
            (partial + "%",),
        ).fetchall()
    if len(rows) == 1:
        return sm.get(rows[0]["id"])
    return None


@facts_app.command("list")
def facts_list(
    topic: str = typer.Option(None, "--topic", help="Filter by topic"),
    limit: int = typer.Option(20, "--limit", help="Cap returned rows"),
    include_hidden: bool = typer.Option(
        False, "--include-hidden",
        help="Surface orphaned + quarantined + user_belief rows "
             "(hidden by default).",
    ),
    user_id: str = typer.Option(None, "--user-id", help="B-1: scope to user."),
    agent_id: str = typer.Option(None, "--agent-id", help="B-1: scope to agent."),
    run_id: str = typer.Option(None, "--run-id", help="B-1: scope to run."),
    include_shared: bool = typer.Option(
        False, "--include-shared",
        help="Also surface UNSCOPED/global facts (never other tenants').",
    ),
) -> None:
    """List recent facts (verified + model_claim + provisional).

    Default view hides orphaned and quarantined to mirror recall.
    Use --include-hidden for audit / undo flows.
    """
    from .scope import lead_prefix as _lead_prefix
    from .scope import matches_scope as _matches_scope
    from .scope import scoped_topic as _scoped_topic
    sm = _facts_sm()
    _scoped = user_id is not None or agent_id is not None or run_id is not None
    if _scoped:
        try:  # fail fast on a malformed scope id
            _scoped_topic(
                "probe", user_id=user_id, agent_id=agent_id, run_id=run_id,
            )
        except ValueError as exc:
            console.print(f"[red]invalid scope id:[/red] {exc}")
            raise typer.Exit(1) from exc
    _lead = _lead_prefix(user_id=user_id, agent_id=agent_id, run_id=run_id)
    with sm._connect() as conn:  # noqa: SLF001
        clauses = ["superseded_by IS NULL"]
        params: list = []
        if not include_hidden:
            # Giro 2: user_belief joins the hidden set on the CLI listing too
            # (parity with recall's default view — sweep twin).
            clauses.append(
                "status NOT IN ('orphaned', 'quarantined', 'user_belief')")
        if topic:
            _t = topic
            if _scoped:
                _t = _scoped_topic(
                    topic, user_id=user_id, agent_id=agent_id, run_id=run_id,
                )
            clauses.append("topic = ?")
            params.append(_t)
        elif _lead and not include_shared:
            # Leading canonical prefix -> DB-level narrow to the tenant's rows.
            esc = _lead.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
            clauses.append("topic LIKE ? ESCAPE '\\'")
            params.append(esc + "%")
        # Over-fetch when a Python post-filter is still needed (non-leading dim
        # or include_shared), so the LIMIT truncation doesn't drop matches.
        _sql_limit = int(max(1, limit))
        if _scoped and (topic or not _lead or include_shared):
            _sql_limit = min(_sql_limit * 8, 2000)
        sql = (
            "SELECT id, proposition, topic, status, confidence "
            "FROM facts WHERE " + " AND ".join(clauses)
            + " ORDER BY created_at DESC LIMIT ?"
        )
        params.append(_sql_limit)
        rows = conn.execute(sql, tuple(params)).fetchall()
    if _scoped:
        rows = [
            r for r in rows
            if _matches_scope(
                r["topic"] or "", user_id=user_id, agent_id=agent_id,
                run_id=run_id, include_shared=include_shared,
            )
        ][: int(max(1, limit))]
    table = Table(title=f"Facts ({len(rows)})")
    table.add_column("id"); table.add_column("topic")
    table.add_column("status"); table.add_column("conf")
    table.add_column("proposition")
    for r in rows:
        table.add_row(
            r["id"][:8], (r["topic"] or "")[:24],
            r["status"] or "",
            f"{r['confidence']:.2f}",
            (r["proposition"] or "")[:80],
        )
    console.print(table)


@facts_app.command("recall")
def facts_recall(
    query: str,
    k: int = typer.Option(5, "--k", help="Top-K results"),
    topic: str = typer.Option(None, "--topic", help="Filter by topic"),
    include_hidden: bool = typer.Option(
        False, "--include-hidden",
        help="Include orphaned rows (quarantined stays hidden via default).",
    ),
    user_id: str = typer.Option(None, "--user-id", help="B-1: scope to user."),
    agent_id: str = typer.Option(None, "--agent-id", help="B-1: scope to agent."),
    run_id: str = typer.Option(None, "--run-id", help="B-1: scope to run."),
    include_shared: bool = typer.Option(
        False, "--include-shared",
        help="Also surface UNSCOPED/global facts (never other tenants').",
    ),
) -> None:
    """Semantic recall on the cosine of fact embeddings."""
    from .scope import lead_prefix as _lead_prefix
    from .scope import matches_scope as _matches_scope
    from .scope import scoped_topic as _scoped_topic
    sm = _facts_sm()
    _scoped = user_id is not None or agent_id is not None or run_id is not None
    _rtopic = topic
    if _scoped and topic:
        try:
            _rtopic = _scoped_topic(
                topic, user_id=user_id, agent_id=agent_id, run_id=run_id,
            )
        except ValueError as exc:
            console.print(f"[red]invalid scope id:[/red] {exc}")
            raise typer.Exit(1) from exc
    _lead = _lead_prefix(user_id=user_id, agent_id=agent_id, run_id=run_id)
    _pref = _lead if (_lead and not _rtopic and not include_shared) else None
    _rk = k if _pref else (min(k * 8, 200) if _scoped else k)
    _pf = {"topic_prefix": _pref} if _pref else {}
    hits = sm.recall(
        query, k=_rk, topic=_rtopic, include_orphaned=include_hidden, **_pf,
    )
    if _scoped:
        hits = [
            (f, s) for (f, s) in hits
            if _matches_scope(
                getattr(f, "topic", ""), user_id=user_id,
                agent_id=agent_id, run_id=run_id, include_shared=include_shared,
            )
        ][:k]
    table = Table(title=f"Recall '{query[:40]}'")
    table.add_column("id"); table.add_column("sim")
    table.add_column("status"); table.add_column("topic")
    table.add_column("proposition")
    for f, sim in hits:
        table.add_row(
            f.id[:8], f"{sim:.3f}", getattr(f, "status", "?"),
            (f.topic or "")[:24], (f.proposition or "")[:80],
        )
    console.print(table)


@facts_app.command("search")
def facts_search(
    query: str,
    topic: str = typer.Option(None, "--topic", help="Filter by topic"),
    limit: int = typer.Option(20, "--limit", help="Cap returned rows"),
    user_id: str = typer.Option(None, "--user-id", help="B-1: scope to user."),
    agent_id: str = typer.Option(None, "--agent-id", help="B-1: scope to agent."),
    run_id: str = typer.Option(None, "--run-id", help="B-1: scope to run."),
    include_shared: bool = typer.Option(
        False, "--include-shared",
        help="Also surface UNSCOPED/global facts (never other tenants').",
    ),
) -> None:
    """Keyword/substring search over fact propositions (SQL LIKE)."""
    from .scope import lead_prefix as _lead_prefix
    from .scope import matches_scope as _matches_scope
    from .scope import scoped_topic as _scoped_topic
    sm = _facts_sm()
    _scoped = user_id is not None or agent_id is not None or run_id is not None
    _stopic = topic
    if _scoped and topic:
        try:
            _stopic = _scoped_topic(
                topic, user_id=user_id, agent_id=agent_id, run_id=run_id,
            )
        except ValueError as exc:
            console.print(f"[red]invalid scope id:[/red] {exc}")
            raise typer.Exit(1) from exc
    _lead = _lead_prefix(user_id=user_id, agent_id=agent_id, run_id=run_id)
    _pref = _lead if (_lead and not _stopic and not include_shared) else None
    _lim = limit if _pref else (min(limit * 8, 500) if _scoped else limit)
    _pf = {"topic_prefix": _pref} if _pref else {}
    hits = sm.search_facts(query, limit=_lim, topic=_stopic, **_pf)
    if _scoped:
        hits = [
            f for f in hits
            if _matches_scope(
                getattr(f, "topic", ""), user_id=user_id,
                agent_id=agent_id, run_id=run_id, include_shared=include_shared,
            )
        ][:limit]
    table = Table(title=f"Search '{query[:40]}'")
    table.add_column("id"); table.add_column("status")
    table.add_column("topic"); table.add_column("proposition")
    for f in hits:
        table.add_row(
            f.id[:8], getattr(f, "status", "?"),
            (f.topic or "")[:24], (f.proposition or "")[:80],
        )
    console.print(table)


@facts_app.command("get")
def facts_get(fact_id: str) -> None:
    """Show one fact's details (proposition + provenance + status).

    Accepts a full id or an unambiguous prefix.
    """
    sm = _facts_sm()
    f = _fact_id_resolve(sm, fact_id)
    if f is None:
        console.print(f"[red]not found:[/red] {fact_id}")
        raise typer.Exit(1) from None
    panel_body = (
        f"[bold]id[/bold] {f.id}\n"
        f"[bold]topic[/bold] {f.topic or ''}\n"
        f"[bold]status[/bold] {getattr(f, 'status', '?')}\n"
        f"[bold]confidence[/bold] {f.confidence:.2f}\n"
        f"[bold]verified_by[/bold] {list(getattr(f, 'verified_by', []))}\n"
        f"\n{f.proposition}"
    )
    console.print(Panel.fit(panel_body, title=f"Fact {f.id[:12]}",
                             border_style="cyan"))


@facts_app.command("forget")
def facts_forget(
    fact_id: str,
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip the confirmation prompt.",
    ),
    undoable: bool = typer.Option(
        True, "--undoable/--no-undoable",
        help=(
            "Cycle 2026-05-27 round 13 P0c — snapshot the row to "
            "facts_undo_log before deletion (7-day TTL). Default ON. "
            "Pass --no-undoable for hard delete (privacy/GDPR)."
        ),
    ),
) -> None:
    """Delete one fact (privacy / GDPR / cleanup).

    Resolution accepts an id prefix. Without --yes the command prompts
    for confirmation; running unattended without --yes is a no-op.

    Default mode (--undoable) snapshots the pre-delete row to
    facts_undo_log so `engram facts undo <op_id>` can restore it within
    7 days. Use --no-undoable for true privacy-compliant hard delete.
    """
    sm = _facts_sm()
    f = _fact_id_resolve(sm, fact_id)
    if f is None:
        console.print(f"[red]not found:[/red] {fact_id}")
        raise typer.Exit(1) from None
    if not yes:
        try:
            ok = typer.confirm(
                f"Delete fact {f.id} ({(f.proposition or '')[:60]})?",
                default=False,
            )
        except typer.Abort:
            ok = False
        if not ok:
            console.print("[yellow]aborted[/yellow]")
            return
    if undoable:
        result = sm.delete_with_undo(f.id)
        if result["removed"]:
            console.print(
                f"[green]forgotten:[/green] {f.id} "
                f"[dim](op_id={result['op_id']} — undoable for 7 days)[/dim]"
            )
        else:
            console.print(f"[yellow]nothing to forget:[/yellow] {f.id}")
    else:
        sm.delete(f.id)
        console.print(f"[green]hard-deleted:[/green] {f.id}")


@facts_app.command("undo")
def facts_undo(
    op_id: str = typer.Argument(
        ..., help="op_id from a previous undoable delete/supersede",
    ),
) -> None:
    """Restore a fact deleted via `engram facts forget` (undoable mode).

    Cycle 2026-05-27 round 13 P0c. Reads facts_undo_log to recover the
    pre-deletion row state. Returns:
        restored      — fact is back in the DB
        already_undone — this op_id was already undone
        expired       — older than 7 days
        not_found     — unknown op_id
    """
    sm = _facts_sm()
    result = sm.undo_destructive_op(op_id)
    action = result.get("action", "unknown")
    if action == "restored":
        console.print(
            f"[green]restored:[/green] fact_id={result['fact_id']} "
            f"op_type={result['op_type']}"
        )
    elif action == "already_undone":
        console.print(
            f"[yellow]already undone:[/yellow] op_id={op_id} "
            f"fact_id={result.get('fact_id')}"
        )
    elif action == "expired":
        console.print(
            f"[red]expired:[/red] op_id={op_id} past 7-day TTL"
        )
    elif action == "not_found":
        console.print(f"[red]not found:[/red] op_id={op_id}")
        raise typer.Exit(1) from None
    else:
        console.print(f"[red]unknown action:[/red] {result}")
        raise typer.Exit(2)


@facts_app.command("undo-list")
def facts_undo_list(
    limit: int = typer.Option(20, "--limit", "-n", help="Max rows"),
) -> None:
    """List the N most recent undoable ops (newest first)."""
    sm = _facts_sm()
    ops = sm.list_undoable_ops(limit=limit)
    if not ops:
        console.print("[dim]no undoable ops[/dim]")
        return
    from datetime import datetime as _dt
    table = Table(title=f"Undoable ops (newest first, max {limit})")
    table.add_column("op_id")
    table.add_column("type")
    table.add_column("fact_id")
    table.add_column("created")
    table.add_column("expires")
    for op in ops:
        table.add_row(
            op["op_id"],
            op["op_type"],
            op["fact_id"],
            _dt.fromtimestamp(op["created_at"]).strftime("%Y-%m-%d %H:%M"),
            _dt.fromtimestamp(op["ttl_expires_at"]).strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@facts_app.command("backup")
def facts_backup(
    tier: str = typer.Option(
        "manual", "--tier",
        help="Backup tier: daily / weekly / monthly / manual (default).",
    ),
    no_verify: bool = typer.Option(
        False, "--no-verify",
        help="Skip integrity hash check (faster but unsafe).",
    ),
    rotate: bool = typer.Option(
        True, "--rotate/--no-rotate",
        help="Apply retention policy after backup (default ON).",
    ),
) -> None:
    """Atomic DB backup via SQLite VACUUM INTO.

    Cycle 2026-05-27 round 13 P0b. Writes to
    ``~/.engram/backups/<tier>/<dbname>-<ts>.db`` with rotation policy
    (7 daily / 4 weekly / 12 monthly). Integrity hash verifies the
    backup matches the live DB before reporting success.
    """
    from .backup import create_backup, rotate_backups
    sm = _facts_sm()
    db_path = Path(sm.db_path)
    try:
        info = create_backup(
            db_path, tier=tier, verify_integrity=not no_verify,
        )
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]backup failed:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(
        f"[green]backup ok:[/green] {info.path}\n"
        f"  size: {info.size_bytes/1024:.1f} KB  "
        f"facts: {info.fact_count}  tier: {info.tier}"
    )
    if rotate:
        deleted = rotate_backups()
        if deleted:
            console.print(
                f"[dim]rotated: removed {len(deleted)} older backup(s)[/dim]"
            )


@facts_app.command("restore")
def facts_restore(
    backup_path: str = typer.Argument(..., help="Path to backup file"),
    yes: bool = typer.Option(False, "--yes", "-y"),
) -> None:
    """Restore the DB from a backup. Keeps a pre-restore safety copy."""
    from .backup import restore_from_backup
    sm = _facts_sm()
    target = Path(sm.db_path)
    bp = Path(backup_path)
    if not bp.exists():
        console.print(f"[red]backup not found:[/red] {bp}")
        raise typer.Exit(1) from None
    if not yes:
        try:
            ok = typer.confirm(
                f"Restore {target.name} from {bp.name}? "
                f"A pre-restore copy will be kept.",
                default=False,
            )
        except typer.Abort:
            ok = False
        if not ok:
            console.print("[yellow]aborted[/yellow]")
            return
    try:
        result = restore_from_backup(bp, target)
    except ValueError as exc:
        # audit#3-r3 R5: backup failed pre-flight validation (wrong store /
        # not a SQLite DB). The target was NOT touched — report cleanly.
        console.print(f"[red]refused:[/red] {exc}")
        raise typer.Exit(1) from exc
    console.print(
        f"[green]restored:[/green] {target}\n"
        f"  facts: {result.get('fact_count')}  "
        f"pre-restore copy: {result.get('pre_restore_copy')}"
    )


@facts_app.command("safety")
def facts_safety() -> None:
    """Cycle 2026-05-27 round 13 — foundation safety status snapshot.

    Reports:
      - schema_version of the live semantic.db
      - latest backup per tier + age
      - undoable ops count
      - capability matrix coverage
      - last 5 sandbox audit events (if any)
    """
    import sqlite3
    from datetime import datetime as _dt

    from .backup import list_backups
    from .sandbox import DEFAULT_AUDIT_ROOT
    from .tool_registry import REGISTRY

    sm = _facts_sm()
    db = Path(sm.db_path)

    # Schema version.
    conn = sqlite3.connect(str(db), timeout=5)
    try:
        from .migrations import schema_version
        ver = schema_version(conn, "semantic")
    except Exception:
        ver = "?"
    # Undoable ops count.
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM facts_undo_log "
            "WHERE undone_at IS NULL AND ttl_expires_at > strftime('%s','now')"
        )
        undoable_n = int(cur.fetchone()[0])
    except sqlite3.OperationalError:
        undoable_n = -1  # table missing
    conn.close()

    # Backups.
    backups = list_backups()
    by_tier: dict[str, str] = {}
    for tier in ("daily", "weekly", "monthly", "manual"):
        tier_backups = [b for b in backups if b.tier == tier]
        if tier_backups:
            latest = tier_backups[0]
            age_h = (_dt.now().timestamp() - latest.created_at) / 3600
            by_tier[tier] = (
                f"{_dt.fromtimestamp(latest.created_at):%Y-%m-%d %H:%M} "
                f"(age {age_h:.1f}h, {latest.size_bytes/1024:.0f}KB)"
            )
        else:
            by_tier[tier] = "[red]none[/red]"

    # Capability matrix.
    n_classified = len(REGISTRY.all())
    n_destructive = len(REGISTRY.by_capability("DESTRUCTIVE"))
    n_writes_mem = len(REGISTRY.writes_memory())
    n_executes = len(REGISTRY.executes_command())

    # Sandbox audit (last 5).
    audit_dir = Path(DEFAULT_AUDIT_ROOT)
    sandbox_events: list[str] = []
    if audit_dir.exists():
        log_today = audit_dir / f"sandbox-{_dt.now():%Y%m%d}.jsonl"
        if log_today.exists():
            lines = log_today.read_text(encoding="utf-8").strip().splitlines()
            for line in lines[-5:]:
                try:
                    evt = json.loads(line)
                    sandbox_events.append(
                        f"  [{_dt.fromtimestamp(evt['ts']):%H:%M:%S}] "
                        f"{evt.get('event','?')}: {evt.get('cmd','?')[:60]}"
                    )
                except Exception:
                    continue

    body = (
        f"[bold]Foundation safety status[/bold]\n\n"
        f"  schema_version:        v{ver}\n"
        f"  undoable ops (live):   {undoable_n}\n"
        f"  capability matrix:     {n_classified} tools "
        f"({n_destructive} destructive, {n_writes_mem} mem-writers, "
        f"{n_executes} executors)\n\n"
        f"  [bold]backups[/bold]\n"
        f"    daily:    {by_tier['daily']}\n"
        f"    weekly:   {by_tier['weekly']}\n"
        f"    monthly:  {by_tier['monthly']}\n"
        f"    manual:   {by_tier['manual']}\n"
    )
    if sandbox_events:
        body += "\n  [bold]sandbox events (today, last 5)[/bold]\n"
        body += "\n".join(sandbox_events)
    console.print(Panel.fit(body, title="safety"))


@facts_app.command("capability")
def facts_capability(
    name: str = typer.Argument(
        None,
        help="Tool name to inspect; omit to list all classified tools.",
    ),
    risk: str = typer.Option(
        None, "--risk",
        help="Filter by risk: low / medium / high / critical.",
    ),
    capability: str = typer.Option(
        None, "--cap",
        help="Filter by capability: READ / WRITE / EXECUTE / NETWORK / DESTRUCTIVE.",
    ),
) -> None:
    """Cycle 2026-05-27 round 13 P0.5 — inspect the tool capability matrix.

    Examples:
        engram facts capability hippo_fact_forget
        engram facts capability --risk high
        engram facts capability --cap DESTRUCTIVE
    """
    from .tool_registry import REGISTRY
    if name:
        cap = REGISTRY.get(name)
        console.print(Panel.fit(
            f"[bold]{cap.name}[/bold]\n"
            f"  capability:        {cap.capability}\n"
            f"  risk_level:        {cap.risk_level}\n"
            f"  reversibility:     {cap.reversibility}\n"
            f"  requires_confirm:  {cap.requires_confirm}\n"
            f"  requires_sandbox:  {cap.requires_sandbox}\n"
            f"  mandatory_log:     {cap.mandatory_log}\n"
            f"  writes_memory:     {cap.writes_memory}\n"
            f"  executes_command:  {cap.executes_command}\n"
            f"  notes:             {cap.notes or '-'}",
            title="capability",
        ))
        return
    caps = REGISTRY.all()
    if risk:
        caps = [c for c in caps if c.risk_level == risk]
    if capability:
        caps = [c for c in caps if c.capability == capability]
    if not caps:
        console.print("[dim]no tools matched filter[/dim]")
        return
    table = Table(title=f"Capability matrix ({len(caps)} tools)")
    table.add_column("name", style="cyan")
    table.add_column("capability")
    table.add_column("risk")
    table.add_column("reversibility")
    table.add_column("confirm", justify="center")
    table.add_column("sandbox", justify="center")
    for cap in caps:
        table.add_row(
            cap.name,
            cap.capability,
            cap.risk_level,
            cap.reversibility,
            "yes" if cap.requires_confirm else "-",
            "yes" if cap.requires_sandbox else "-",
        )
    console.print(table)


@facts_app.command("stats")
def facts_stats() -> None:
    """Counts per status enum + a total row."""
    sm = _facts_sm()
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM facts "
            "WHERE superseded_by IS NULL GROUP BY status"
        ).fetchall()
    table = Table(title="Facts by status")
    table.add_column("status"); table.add_column("count")
    total = 0
    # Stable presentation order — always list the canonical enum so
    # callers can grep for a status that happens to be empty.
    seen: dict[str, int] = {r["status"] or "(null)": int(r["n"]) for r in rows}
    canonical = [
        "verified", "model_claim", "provisional",
        "legacy_unverified", "quarantined", "orphaned",
    ]
    for s in canonical:
        n = seen.get(s, 0)
        total += n
        table.add_row(s, str(n))
    # Anything outside the canonical set (shouldn't happen post-cycle-138)
    for s, n in seen.items():
        if s not in canonical:
            total += n
            table.add_row(s + " (unknown)", str(n))
    table.add_row("[bold]total[/bold]", f"[bold]{total}[/bold]")
    console.print(table)


@facts_app.command("anti-confab-scan")
def facts_anti_confab_scan(
    limit_per_category: int = typer.Option(
        20, "--limit-per-category",
        help="Cap sample fact_ids per category.",
    ),
) -> None:
    """L2 reconciler scan: which corpus rows would the L1 detectors
    flag today? Read-only — no mutation."""
    from .anti_confabulation import scan_orphaned_facts, summarize_scan
    sm = _facts_sm()
    with sm._connect() as conn:  # noqa: SLF001
        corpus_rows = conn.execute("SELECT * FROM facts").fetchall()
    corpus_facts = [sm._row(r) for r in corpus_rows]  # noqa: SLF001
    report = scan_orphaned_facts(corpus_facts)
    console.print(f"[bold]{summarize_scan(report)}[/bold]")
    for cat in ("shipped", "diagnosis", "task_state"):
        items = report.get(cat) or []
        if not items:
            continue
        table = Table(title=f"{cat} ({len(items)})")
        table.add_column("id"); table.add_column("warning")
        for fid, w in items[:limit_per_category]:
            table.add_row(fid[:12], (w or "")[:80])
        console.print(table)


@facts_app.command("anti-confab-apply")
def facts_anti_confab_apply(
    dry_run: bool = typer.Option(
        True, "--dry-run/--no-dry-run",
        help="Default safe: list what WOULD flip. --no-dry-run mutates.",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip confirmation when --no-dry-run.",
    ),
) -> None:
    """Apply L2 reconciler: mark detected confabulations as orphaned.

    Safe by default (dry-run). --no-dry-run mutates the corpus — prompts
    for confirmation unless --yes is set.
    """
    from .anti_confabulation import scan_orphaned_facts
    sm = _facts_sm()
    with sm._connect() as conn:  # noqa: SLF001
        corpus_rows = conn.execute("SELECT * FROM facts").fetchall()
    corpus_facts = [sm._row(r) for r in corpus_rows]  # noqa: SLF001
    report = scan_orphaned_facts(corpus_facts)
    to_flip: set[str] = set()
    for cat in ("shipped", "diagnosis", "task_state"):
        for fid, _ in (report.get(cat) or []):
            to_flip.add(fid)
    if dry_run:
        console.print(
            f"[yellow]DRY-RUN[/yellow] would mark {len(to_flip)} "
            f"facts as orphaned (use --no-dry-run to apply)."
        )
        return
    if not yes:
        try:
            ok = typer.confirm(
                f"Flip {len(to_flip)} facts to status='orphaned'?",
                default=False,
            )
        except typer.Abort:
            ok = False
        if not ok:
            console.print("[yellow]aborted[/yellow]")
            return
    applied = 0
    for fid in to_flip:
        if sm.mark_orphaned(fid, reason="cli facts anti-confab-apply"):
            applied += 1
    console.print(f"[green]applied:[/green] {applied}/{len(to_flip)} flipped.")


# ---- Cycle #140 (2026-05-18 sera) — engram facts add ---------------------
# Aurelio direttiva 2026-05-18: in una sessione CLI di pentest sul proprio
# asset (nexuscyber.com, CVP Anthropic approved), il classifier upstream del
# client che instrada il `hippo_remember` MCP tool ha BLOCCATO un fact con
# contenuto 'reconnaissance data on live host'. Il blocco non è nel codice
# HippoAgent — è la safety policy del wire (Claude Code).
#
# Cycle 140 aggiunge un sub-comando ``engram facts add`` che chiama
# DIRETTAMENTE ``SemanticMemory.store`` senza passare per il wire MCP / LLM
# safety. La discipline anti-confab cycle 138 (L1+L1.5+L1.7 + L3) viene
# RICALCATA in locale, così il gate vale anche per le scritture CLI — ma
# nessun classifier upstream tocca i bytes.
#
# Use case canonico: pentest su asset propri, ricerca su finding tecnici
# sensibili, import bulk da report Burp/nmap/CSV. Local SQLite owner = GDPR
# self-data. Nessuna chiamata API esterna. Nessun LLM coinvolto nel write.


@facts_app.command("add")
def facts_add(
    proposition: str = typer.Option(
        None, "--proposition", "-p",
        help="Fact proposition text (required unless --jsonl-stdin).",
    ),
    topic: str = typer.Option(
        None, "--topic", "-t",
        help="Topic namespace (e.g. project/nexus/pentest-2026-05-18).",
    ),
    confidence: float = typer.Option(
        0.9, "--confidence", "-c",
        help="Confidence 0.0-1.0 (default 0.9, parity with hippo_remember).",
    ),
    verified_by: list[str] = typer.Option(  # noqa: B008 — typer convention
        None, "--verified-by",
        help=(
            "Provenance ref (repeatable). Examples: "
            "'commit:abc1234', 'pr:#80:merged', 'bash:nmap_exit_0', "
            "'file:report.md:42'."
        ),
    ),
    status: str = typer.Option(
        "model_claim", "--status",
        help="Initial status enum (model_claim default).",
    ),
    validate: str = typer.Option(
        "fast", "--validate",
        help=(
            "Cycle 138 gate tier: 'off' bypass / 'fast' (default) L1 "
            "keyword detectors / 'full' L1+L3 validate_claim."
        ),
    ),
    gate_mode: str = typer.Option(
        "downgrade", "--gate-mode",
        help="On L3 contradiction: 'downgrade' (default) or 'reject'.",
    ),
    force_persist: bool = typer.Option(
        False, "--force-persist",
        help="Bypass gate rejection (warnings still surface).",
    ),
    jsonl_stdin: bool = typer.Option(
        False, "--jsonl-stdin",
        help=(
            "Read newline-delimited JSON objects from stdin instead of "
            "flags. Each object accepts the same fields as the flags. "
            "Useful for bulk import from a pentest tool, nmap parser, etc."
        ),
    ),
    from_file: str = typer.Option(
        None, "--from-file",
        help=(
            "Read the proposition body from a file path (useful for long "
            "or multi-line content with shell-quoting hazards)."
        ),
    ),
    user_id: str = typer.Option(
        None, "--user-id",
        help="B-1 multi-tenancy: scope this fact to a user (topic prefix).",
    ),
    agent_id: str = typer.Option(
        None, "--agent-id",
        help="B-1 multi-tenancy: scope this fact to an agent.",
    ),
    run_id: str = typer.Option(
        None, "--run-id",
        help="B-1 multi-tenancy: scope this fact to a run/session.",
    ),
) -> None:
    """Persist one or more facts DIRECTLY to local semantic memory.

    Bypasses the MCP wire entirely — no LLM, no upstream classifier ever
    sees the bytes. The cycle 138 anti-confab gate still runs LOCALLY for
    consistency, so SHIPPED-no-ref claims still get downgraded to
    quarantined just like the MCP path. Use ``--validate off`` to bypass
    the local gate as well.

    Examples::

        engram facts add -p "nexuscyber.com runs nginx 1.24" \\
                         -t project/nexus/pentest-2026-05-18 \\
                         --verified-by "bash:curl_HEAD:server_header"

        cat findings.jsonl | engram facts add --jsonl-stdin
    """
    from .anti_confab_gate import run_validation_gate
    from .scope import scoped_topic as _scoped_topic
    from .semantic import Fact

    # B-1: validate flag-supplied scope ids eagerly so a malformed id fails
    # fast (exit non-zero) rather than silently skipping every payload.
    if any(v is not None for v in (user_id, agent_id, run_id)):
        try:
            _scoped_topic(
                "probe", user_id=user_id, agent_id=agent_id, run_id=run_id,
            )
        except ValueError as exc:
            console.print(f"[red]invalid scope id:[/red] {exc}")
            raise typer.Exit(1) from exc

    # Build the list of payloads (either one from flags or many from stdin).
    payloads: list[dict] = []
    parse_errors = 0  # audit#3-r3 R6: count dropped jsonl lines for the exit code
    if jsonl_stdin:
        import json as _json
        import sys as _sys
        raw = _sys.stdin.read()
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = _json.loads(line)
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]jsonl parse error:[/red] {exc} :: {line[:80]}")
                parse_errors += 1
                continue
            if isinstance(obj, dict):
                payloads.append(obj)
            else:
                console.print(
                    f"[red]jsonl skip (not an object):[/red] {str(obj)[:80]}"
                )
                parse_errors += 1
    else:
        body = proposition
        if from_file:
            try:
                body = Path(from_file).read_text(encoding="utf-8").strip()
            except OSError as exc:
                console.print(f"[red]cannot read --from-file:[/red] {exc}")
                raise typer.Exit(1) from exc
        if not body:
            console.print(
                "[red]--proposition or --jsonl-stdin or --from-file required[/red]"
            )
            raise typer.Exit(1) from None
        if not topic:
            console.print("[red]--topic required[/red]")
            raise typer.Exit(1) from None
        payloads.append({
            "proposition": body,
            "topic": topic,
            "confidence": confidence,
            "verified_by": list(verified_by or []),
            "status": status,
            "validate": validate,
            "gate_mode": gate_mode,
            "force_persist": force_persist,
        })

    sm = _facts_sm()

    class _AgentShim:
        def __init__(self, sm) -> None:
            self.semantic = sm
    agent = _AgentShim(sm)

    # buco #2 LIVE (2026-06-03): repo_root per la verifica di ESISTENZA dei ref
    # nel gate (commit:/file: fabbricati -> downgrade). _facts_sm() non setta
    # repo_root sullo store, quindi risolviamo CONFIG.project_root come fa
    # agent.build per il verified_by hard-gate.
    try:
        from .config import CONFIG as _CFG
        _gate_repo_root = getattr(sm, "repo_root", None) or _CFG.project_root
    except Exception:  # noqa: BLE001 — never break the write path
        _gate_repo_root = getattr(sm, "repo_root", None)

    inserted: list[str] = []
    quarantined: list[str] = []
    rejected: list[str] = []
    for p in payloads:
        prop = str(p.get("proposition") or "").strip()
        tpc = str(p.get("topic") or topic or "").strip()
        if not prop or not tpc:
            console.print(
                f"[yellow]skipped:[/yellow] missing proposition or topic — "
                f"prop={prop[:40]!r} topic={tpc!r}"
            )
            continue
        # B-1 multi-tenancy: prefix topic with the scope (per-payload override
        # from jsonl, else the command flags). Idempotent + merging.
        _u = p.get("user_id") if p.get("user_id") is not None else user_id
        _a = p.get("agent_id") if p.get("agent_id") is not None else agent_id
        _r = p.get("run_id") if p.get("run_id") is not None else run_id
        # Write-side isolation guard (audit 2026-06-09): a free-text topic must
        # not embed a scope segment not authorized by the matching flag, else it
        # would land in another tenant's scope (read path trusts the prefix).
        from .scope import parse_scope as _parse_scope
        _emb = _parse_scope(tpc)
        _bad = next(
            (d for d, sup in (("user_id", _u), ("agent_id", _a), ("run_id", _r))
             if _emb.get(d) is not None and (sup is None or str(sup) != _emb[d])),
            None,
        )
        if _bad is not None:
            console.print(
                f"[red]skipped (topic embeds unauthorized {_bad} scope):[/red] "
                f"{prop[:40]!r} — pass scope via --{_bad.replace('_id','-id')}"
            )
            rejected.append(prop[:60])
            continue
        if _u is not None or _a is not None or _r is not None:
            try:
                tpc = _scoped_topic(tpc, user_id=_u, agent_id=_a, run_id=_r)
            except ValueError as exc:
                console.print(
                    f"[yellow]skipped (bad scope):[/yellow] "
                    f"{prop[:40]!r} — {exc}"
                )
                continue
        # Scan low #28: a PRESENT ``"confidence": null`` makes get() return
        # None (default only kicks in for a MISSING key), so float(None) raised
        # TypeError OUTSIDE the per-record guard and aborted the whole batch.
        # None/missing -> the command default; a non-numeric value skips THIS
        # record only (a malformed line must never drop the valid ones).
        _conf_raw = p.get("confidence")
        try:
            conf = float(confidence if _conf_raw is None else _conf_raw)
        except (TypeError, ValueError):
            console.print(
                f"[yellow]skipped (bad confidence {_conf_raw!r}):[/yellow] "
                f"{prop[:40]!r}"
            )
            continue
        conf = max(0.0, min(conf, 1.0))
        vb = [str(x) for x in (p.get("verified_by") or [])]
        st = str(p.get("status") or status)
        v_lvl = str(p.get("validate") or validate)
        g_mode = str(p.get("gate_mode") or gate_mode)
        force = bool(p.get("force_persist", force_persist))
        # Cycle 2026-05-27 round 12 F-fix: forward provenance kwargs
        # (writer_role + meta_narrative) so the trusted-hook bypass works
        # also via this CLI path. Closes the gap caught by the
        # critic-orchestrator caller_verification worker (job
        # 27e9595481d4e216 — "engram facts add does not forward the new
        # kwargs"). Defaults preserve legacy behaviour.
        wr = str(p.get("writer_role") or "agent_inference")
        mn = bool(p.get("meta_narrative", False))
        # Security fix 2026-06-02: the legitimate local CLI path (clp save,
        # invoked by the pre-compact hook) supplies the server-side secret
        # from the env so the trusted-hook bypass is honored. The MCP path
        # deliberately passes nothing (fail-closed → no client-side spoof).
        hook_token = os.environ.get("ENGRAM_HOOK_TOKEN")

        # Apply cycle 138 anti-confab gate locally.
        gate = run_validation_gate(
            proposition=prop,
            verified_by=vb,
            topic=tpc,
            agent=agent,
            validate=v_lvl,
            gate_mode=g_mode,
            force_persist=force,
            writer_role=wr,
            meta_narrative=mn,
            hook_token=hook_token,
            repo_root=_gate_repo_root,
        )
        if gate.action == "reject":
            console.print(
                f"[red]rejected:[/red] {prop[:60]!r} — {gate.advice}"
            )
            rejected.append(prop[:60])
            continue
        final_status = "quarantined" if gate.action == "downgrade" else st
        if final_status not in {
            "verified", "model_claim", "provisional",
            "legacy_unverified", "orphaned", "quarantined",
        }:
            final_status = "model_claim"
        f = Fact(
            proposition=prop,
            topic=tpc,
            confidence=conf,
            verified_by=vb,
            status=final_status,
            writer_role=wr,
            meta_narrative=mn,
        )
        # 2026-06-05: embed="auto" so `engram facts add` never cold-blocks
        # ~22s when the encode daemon is down (defers; heal via
        # `engram facts backfill` / next warm op). Daemon warm -> embeds now.
        sm.store(f, hook_token=hook_token, embed="auto")
        inserted.append(f.id)
        if final_status == "quarantined":
            quarantined.append(f.id)

    # Summary
    if inserted:
        console.print(
            f"[green]inserted:[/green] {len(inserted)} fact(s). "
            f"quarantined={len(quarantined)} rejected={len(rejected)} "
            f"parse_errors={parse_errors}"
        )
        for fid in inserted:
            console.print(f"  id={fid[:12]}  status="
                          + ("quarantined" if fid in quarantined else "ok"))
    else:
        # audit#3-r3 R6: an `add` that persisted NOTHING is a failure — exit
        # non-zero so a bulk pipeline (cat findings.jsonl | engram facts add
        # --jsonl-stdin) cannot mistake an all-dropped/rejected import for
        # success. Pre-fix this returned normally (exit 0).
        console.print(
            f"[red]no facts inserted[/red] "
            f"(rejected={len(rejected)} parse_errors={parse_errors})"
        )
        raise typer.Exit(1) from None


@facts_app.command("backfill")
def facts_backfill(
    limit: int = typer.Option(
        0, "--limit", help="Max rows to embed this run (0 = all pending).",
    ),
) -> None:
    """Embed facts saved with a deferred (empty) embedding.

    A non-blocking save (`engram facts add` / hippo_remember while the encode
    daemon is cold) persists the row instantly with an empty-blob embedding so
    it never cold-blocks ~22s; the row is keyword-findable but not yet in
    semantic recall. This command computes those embeddings (fast on a warm
    daemon) and makes the rows recallable. Idempotent.
    """
    sm = _facts_sm()
    n = sm.backfill_pending_embeddings(limit=(limit or None))
    if n:
        console.print(f"[green]backfilled:[/green] {n} pending embedding(s).")
    else:
        console.print(
            "[yellow]nothing pending[/yellow] — all facts already embedded."
        )


@facts_app.command("archive-narration")
def facts_archive_narration(
    apply: bool = typer.Option(
        False, "--apply",
        help="Actually move the rows. Default = DRY RUN (reports only, mutates nothing).",
    ),
    use_llm: bool = typer.Option(
        False, "--use-llm",
        help="Use the LLM extractor (verimem.llm.get_llm, hosted) for higher-recall "
             "atomic claims instead of the deterministic rule-based pass.",
    ),
) -> None:
    """Move dated session-NARRATION out of the curated ``facts`` table.

    ~5% of curated facts are dated first-person session summaries ("ENGRAM
    2026-06-13 sera: …", "HippoAgent roadmap 2026-05-11 P0 …") — time-bound
    stories that recall surfaces as CURRENT TRUTH, so a later instance acts on
    stale state (the confabulation Aurelio flagged). This reports the atomic
    verifiable claims they yield, then — with ``--apply`` — moves the prose into
    a separate, non-lossy ``narrative`` table. Reversible; run with the MCP
    server STOPPED and a fresh backup. Default is a DRY RUN.
    """
    from verimem.narration import archive_and_extract_narration
    sm = _facts_sm()
    llm = None
    if use_llm:
        from verimem.llm import get_llm
        llm = get_llm()
    res = archive_and_extract_narration(sm.db_path, dry_run=not apply, llm=llm)
    mode = "APPLIED" if apply else "DRY-RUN (use --apply to move)"
    console.print(
        f"[bold]{mode}[/bold]  scanned={res['scanned']}  "
        f"narration={res['narration_found']}  "
        f"atomic_candidates={res['atomic_candidates']}  archived={res['archived']}"
    )


@facts_app.command("cleanup-episode-telemetry")
def facts_cleanup_episode_telemetry(
    apply: bool = typer.Option(
        False, "--apply",
        help="Actually move the rows. Default = DRY RUN (reports only, mutates nothing).",
    ),
) -> None:
    """Move auto-saved cross-LLM call records out of the curated ``episodes``.

    ~22% of the live episode store are ``[agy-call …]`` / ``[gemini-call …]``
    telemetry records the bridge auto-saves — not real tasks. The episode gate
    (#222) routes NEW ones; this clears the BACKLOG into a separate, non-lossy
    ``episode_telemetry`` table (full row + linked traces preserved). Reversible;
    run with the MCP server STOPPED and a fresh backup. Default is a DRY RUN.
    """
    from verimem.admission_cleanup import cleanup_episode_telemetry
    data = _facts_data_dir()
    sub = data / "episodes" / "episodes.db"
    flat = data / "episodes.db"
    ep_path = sub if sub.exists() else (flat if flat.exists() else sub)
    res = cleanup_episode_telemetry(ep_path, dry_run=not apply)
    mode = "APPLIED" if apply else "DRY-RUN (use --apply to move)"
    console.print(
        f"[bold]{mode}[/bold]  scanned={res['scanned']}  "
        f"episode_telemetry={res['telemetry_found']}  moved={res['moved']}"
    )


@facts_app.command("requalify-quarantined")
def facts_requalify_quarantined(
    apply: bool = typer.Option(
        False, "--apply",
        help="Actually promote. Default = DRY RUN (reports only, mutates nothing).",
    ),
) -> None:
    """Recover real knowledge a SINCE-FIXED false positive had quarantined.

    The recall path hard-excludes ``quarantined`` rows. This re-evaluates each
    quarantined fact with the CURRENT gate and promotes to ``model_claim`` only
    the ones that now pass ALL three quarantine sources (no L1.x warning, not
    prompt-injection, admission gate admits) — genuine positives stay hidden.
    Reversible; run with a fresh backup. Default is a DRY RUN.
    """
    from verimem.admission_cleanup import requalify_quarantined
    sm = _facts_sm()
    res = requalify_quarantined(sm.db_path, dry_run=not apply)
    mode = "APPLIED" if apply else "DRY-RUN (use --apply to promote)"
    console.print(
        f"[bold]{mode}[/bold]  scanned={res['scanned']}  "
        f"recoverable={res['recoverable']}  promoted={res['promoted']}"
    )


# ---- Consolidate sub-commands (cycle 145) --------------------------------
# Operator-facing CLI surface for the cycle 144 auto-consolidation
# orchestrator (verimem.consolidation). Three sub-commands:
#
#   engram consolidate dry-run   detect clusters + propose masters (no write)
#   verimem consolidate apply     persist master Episode+Fact+causal edges
#   engram consolidate status    count existing AUTO-CLUSTER-MASTER facts
#
# All three honour HIPPO_DATA_DIR / ENGRAM_DATA_DIR via ``_facts_data_dir``
# for test isolation (same pattern as the facts cluster).


def _consolidate_em():
    """Build an EpisodicMemory pointed at the env-resolved corpus.

    audit#3-r3 R4: the canonical layout (``CONFIG.episodes_db``, used by the
    MCP server and every plain ``EpisodicMemory()``) is the SUBDIR
    ``<data>/episodes/episodes.db``. This helper previously hardcoded the flat
    ``<data>/episodes.db``, so on a standard install ``consolidate apply``
    wrote the master Episode to an orphan file nobody reads (the master Fact's
    ``source_episodes`` then dangled). Mirror ``_facts_sm()``: prefer the
    subdir, fall back to a pre-existing legacy flat DB only.
    """
    from .memory import EpisodicMemory
    data = _facts_data_dir()
    sub = data / "episodes" / "episodes.db"
    flat = data / "episodes.db"
    ep_path = sub if sub.exists() else (flat if flat.exists() else sub)
    ep_path.parent.mkdir(parents=True, exist_ok=True)
    return EpisodicMemory(db_path=ep_path)


@consolidate_app.command("dry-run")
def consolidate_dry_run(
    min_size: int = typer.Option(
        5, "--min-size",
        help="Minimum cluster size (sub-fact count) to surface.",
    ),
    prefix_depth: int = typer.Option(
        2, "--prefix-depth",
        help="How many slash-separated segments define a cluster prefix.",
    ),
) -> None:
    """Detect cluster candidates and propose master nodes WITHOUT writing.

    Reports each cluster's topic_prefix + fact_count, plus the proposed
    master proposition (truncated). Use to preview an ``apply`` run.
    """
    from .consolidation import detect_cluster_candidates, propose_master_node
    sm = _facts_sm()
    clusters = detect_cluster_candidates(
        sm, min_size=min_size, prefix_depth=prefix_depth,
    )
    if not clusters:
        console.print(
            f"[yellow]0 clusters detected[/yellow] "
            f"(min_size={min_size}, prefix_depth={prefix_depth})."
        )
        return
    table = Table(
        title=(
            f"Clusters detected: {len(clusters)} "
            f"(min_size={min_size}, prefix_depth={prefix_depth})"
        ),
    )
    table.add_column("topic_prefix")
    table.add_column("fact_count")
    table.add_column("master proposition (preview)")
    for cluster in clusters:
        master = propose_master_node(sm, cluster)
        table.add_row(
            cluster["topic_prefix"],
            str(cluster["fact_count"]),
            (master["proposition"] or "")[:80],
        )
    console.print(table)
    console.print(
        f"[dim]dry-run: {len(clusters)} master(s) WOULD be persisted "
        f"on `verimem consolidate apply`. No write performed.[/dim]"
    )


@consolidate_app.command("apply")
def consolidate_apply(
    min_size: int = typer.Option(
        5, "--min-size",
        help="Minimum cluster size (sub-fact count) to consolidate.",
    ),
    prefix_depth: int = typer.Option(
        2, "--prefix-depth",
        help="How many slash-separated segments define a cluster prefix.",
    ),
) -> None:
    """Run auto_consolidate end-to-end: persist master Episode+Fact+edges.

    Idempotent: re-running on the same corpus skips clusters already
    consolidated (proposition LIKE 'AUTO-CLUSTER-MASTER %').
    """
    from .consolidation import auto_consolidate
    sm = _facts_sm()
    mem = _consolidate_em()
    out = auto_consolidate(
        sm, mem, min_size=min_size, prefix_depth=prefix_depth,
        dry_run=False,
    )
    console.print(Panel.fit(
        f"  clusters detected:   {out['clusters_detected']}\n"
        f"  masters proposed:    {out['masters_proposed']}\n"
        f"  masters persisted:   {out['masters_persisted']}\n"
        f"  causal edges:        {out['edges_created']}\n"
        f"  duration:            {out['duration_ms']:.1f} ms",
        title="auto-consolidate apply",
        border_style="cyan",
    ))


@consolidate_app.command("status")
def consolidate_status() -> None:
    """Count master facts already created by previous ``apply`` runs.

    Master = a Fact whose proposition starts with the
    ``AUTO-CLUSTER-MASTER `` tag (see verimem.consolidation).
    """
    sm = _facts_sm()
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM facts "
            "WHERE superseded_by IS NULL "
            "AND proposition LIKE 'AUTO-CLUSTER-MASTER %'",
        ).fetchone()
        n_masters = int(row["n"]) if row else 0
        recent = conn.execute(
            "SELECT id, topic, proposition FROM facts "
            "WHERE superseded_by IS NULL "
            "AND proposition LIKE 'AUTO-CLUSTER-MASTER %' "
            "ORDER BY created_at DESC LIMIT 10",
        ).fetchall()
    console.print(Panel.fit(
        f"  master facts (AUTO-CLUSTER-MASTER):  {n_masters}",
        title="auto-consolidate status",
        border_style="cyan",
    ))
    if recent:
        table = Table(title=f"Recent masters ({len(recent)})")
        table.add_column("id"); table.add_column("topic")
        table.add_column("proposition (head)")
        for r in recent:
            table.add_row(
                r["id"][:8],
                (r["topic"] or "")[:40],
                (r["proposition"] or "")[:60],
            )
        console.print(table)


def _force_utf8_stdio() -> None:
    """Best-effort UTF-8 stdout/stderr so the CLI's status glyphs (✓ ✗ → ⚠)
    never crash on a legacy Windows console or a redirected pipe (cp1252) with
    UnicodeEncodeError. Modern terminals render the glyphs; legacy ones show a
    replacement char — but a command never aborts over output encoding. No-op
    where the stream can't be reconfigured (older Python, captured streams)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — never break the CLI over encoding
            pass


@app.command("agent-guide")
def agent_guide_cmd() -> None:
    """How ANY agent should use Verimem — the same onboarding guide the MCP
    server hands every client on connect, plus wiring (MCP config, SDK, CLI).
    Paste it into a system prompt / CLAUDE.md, or pipe it wherever you need."""
    from .agent_guide import AGENT_GUIDE_FULL
    print(AGENT_GUIDE_FULL)


# --- `verimem agent` namespace (VERIMEM-MAP.md 1b, 2026-07-18) -----------------
# The product CLI is verified MEMORY; the agent runtime (chat/code/run/benchmark,
# sleep cycles, swarm/teams/lab) moves under `verimem agent <cmd>`. Done by
# post-registration re-wiring so the 11 definitions stay untouched. The original
# top-level spellings still WORK for 0.5.x users — just hidden from --help.
_AGENT_RUNTIME_COMMANDS = {"benchmark", "chat", "code", "run", "wake",
                           "sleep", "sleep-now", "tui"}
_AGENT_RUNTIME_GROUPS = {"swarm", "teams", "lab"}

agent_app = typer.Typer(
    no_args_is_help=True,
    help="Agent runtime — chat/code/run, benchmark, sleep cycles, swarm/teams "
         "(advanced; the memory product itself lives in the top-level commands)")


def _regroup_agent_runtime() -> None:
    import copy as _copy
    for _ci in app.registered_commands:
        _name = _ci.name or _ci.callback.__name__.replace("_", "-")
        if _name in _AGENT_RUNTIME_COMMANDS:
            _pub = _copy.copy(_ci)
            _pub.name = _name
            _pub.hidden = False
            agent_app.registered_commands.append(_pub)
            _ci.hidden = True          # old spelling keeps working, out of --help
    for _gi in app.registered_groups:
        if _gi.name in _AGENT_RUNTIME_GROUPS:
            _pub = _copy.copy(_gi)
            _pub.hidden = False
            agent_app.registered_groups.append(_pub)
            _gi.hidden = True
    app.add_typer(agent_app, name="agent")


_regroup_agent_runtime()


def main() -> None:
    """Console-script entry (`engram` / `hippo`): force UTF-8 stdio, then run
    the Typer app. Wrapping the app (vs pointing the entry directly at it) is
    what lets the encoding fix run before any command writes output."""
    _force_utf8_stdio()
    app()


if __name__ == "__main__":
    main()
