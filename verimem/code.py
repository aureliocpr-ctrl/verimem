"""Engram Code — agentic CLI with persistent active memory.

Like Claude Code / Aider / opencode, but the differentiator is the memory
loop: every turn feeds the same Bayesian fitness machinery + Hebbian
trigger embedding + procedural compilation + counterfactual REM that the
rest of Engram uses. Skills compile from your repeated workflow; the
forward-replay block in the prompt anchors the agent on past successful
trajectories from this very repo.

Layout (terminal, single-pane Rich):

    ╭─ ⚡ ENGRAM CODE  C:\\path  · model · skills · forward replay ─╮
    │                                                                 │
    │ chat history with tool calls + diff previews inlined             │
    │                                                                 │
    ╰─────────────────────────────────────────────────────────────────╯
    » prompt (Ctrl-D to quit, /help for commands)

Design notes:
  • The session reuses the same VerimemAgent build that powers the dashboard
    — same memory, same skills, same sleep cycle. Switching between the
    web UI and `engram code` shares state automatically.
  • Edits are applied via search/replace blocks (editfmt module) with a
    diff preview shown before the file is written.
  • The repo map is regenerated lazily, scoped to the workspace.
  • Vision drop: write `[image: /path]` in the prompt and the contents
    are described inline before the task is sent to the model.
  • Slash commands handle non-LLM operations (sleep, model switch, etc.).

Slash command registry — every command is one method on VerimemCode named
`_cmd_<name>`. No giant dispatch table; new commands are auto-discovered.
"""
from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .agent import VerimemAgent
from .editfmt import (
    SEARCH_REPLACE_INSTRUCTIONS,
    EditBlock,
    apply_blocks,
    parse_edits,
)
from .episode import Episode
from .llm import resolve_model
from .observability import get_log
from .repomap import build_repomap
from .skill import Skill
from .tools_extra import all_tools

log = get_log()


# --- Vision prompt drop ----------------------------------------------------


def _resolve_vision_drops(text: str, console: Console) -> str:
    """Replace `[image: /path]` markers in the prompt with vision_describe output.

    Lets the user paste a screenshot path and have the agent see it before
    the task is composed. Uses the existing vision_describe tool, so any
    provider with vision support works (Anthropic, Groq, OpenRouter, …).
    """
    import re
    pattern = re.compile(r"\[image:\s*([^\]]+)\]")
    matches = list(pattern.finditer(text))
    if not matches:
        return text
    try:
        from .tools_extra import vision_describe  # lazy — heavy import
    except Exception as exc:  # noqa: BLE001
        console.print(f"[yellow]vision unavailable: {exc}[/yellow]")
        return text
    out = text
    for m in matches:
        path = m.group(1).strip()
        console.print(f"[dim]· vision_describe({path})[/dim]")
        try:
            # BUG #4 fix: tools_extra.vision_describe signature is
            # `vision_describe(image: str, prompt: str = ...)`. Previous
            # code passed `image_path=` and `question=` which raised
            # TypeError silently masked by the broad except below.
            result = vision_describe(image=path,
                                       prompt="Describe this image briefly.")
            desc = getattr(result, "output", str(result))
            out = out.replace(m.group(0), f"[image at {path}: {desc}]")
        except Exception as exc:  # noqa: BLE001
            log.warning("vision_describe failed", path=path, error=str(exc))
            out = out.replace(m.group(0),
                                f"[image at {path}: vision failed — {exc}]")
    return out


# --- Verimem Code session ---------------------------------------------------


class VerimemCode:
    """Interactive coding session with persistent active memory."""

    def __init__(
        self,
        workspace: Path,
        agent: VerimemAgent | None = None,
        plan_mode: bool = False,
        model_override: str | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        os.chdir(self.workspace)
        self.console = Console()
        self.agent = agent or VerimemAgent.build(tools=all_tools())
        self.plan_mode = plan_mode
        self.model_override = model_override
        self.history: list[dict[str, Any]] = []  # for in-session display
        # Cache the repomap; rebuild only when files actually change.
        self._repomap_text: str = ""
        self._repomap_built_at: float = 0.0

    # --- banner / status -------------------------------------------------

    def _status_line(self) -> Text:
        n_skills = self.agent.skills.count()
        n_promoted = self.agent.skills.count(status="promoted")
        n_eps = self.agent.memory.count()
        compiled = sum(1 for s in self.agent.skills.all() if s.compiled_macro)
        model = self.model_override or resolve_model("executor") or "(provider default)"
        plan = " · plan mode" if self.plan_mode else ""
        t = Text()
        t.append("ENGRAM CODE  ", style="bold green")
        t.append(str(self.workspace), style="cyan")
        t.append(f"  · {model}", style="dim")
        t.append(f"  · skills {n_skills} ({n_promoted}↑, {compiled} compiled)",
                  style="dim")
        t.append(f"  · episodes {n_eps}", style="dim")
        t.append(plan, style="yellow")
        return t

    def _episodes_since_sleep(self) -> int:
        """Rough count of episodes recorded after the most recent sleep cycle.

        Skills carry no per-episode `created_at` we can rely on, but episodes
        do — we count those whose timestamp is newer than the last skill
        update. Returns total episode count if no skills exist yet.
        """
        eps = self.agent.memory.all(limit=200)
        skills = self.agent.skills.all()
        if not skills:
            return len(eps)
        last_skill_ts = max(
            (getattr(s, "updated_at", 0) or getattr(s, "created_at", 0) or 0)
            for s in skills
        )
        if not last_skill_ts:
            return len(eps)
        return sum(1 for e in eps
                    if (getattr(e, "ts", None) or getattr(e, "created_at", 0) or 0)
                    > last_skill_ts)

    def _contextual_tip(self) -> str | None:
        """Return one short suggestion based on current memory state, or None."""
        n_eps = self.agent.memory.count()
        n_skills = self.agent.skills.count()
        candidates = self.agent.skills.count(status="candidate")
        if n_eps == 0:
            return ("first run — type any task and press Enter; "
                     "after 3+ episodes try /sleep to consolidate")
        try:
            since = self._episodes_since_sleep()
        except Exception:  # noqa: BLE001
            since = 0
        if since >= 8:
            return (f"{since} new episodes since last consolidation — "
                     "consider running /sleep")
        if candidates >= 5:
            return (f"{candidates} candidate skills awaiting evidence — "
                     "/skills shows them, /promote <id> if proven")
        if n_skills >= 1 and n_eps >= 5:
            return "/skills to browse what the agent has learned"
        return None

    def _banner(self) -> None:
        self.console.print()
        self.console.print(Panel(
            self._status_line(),
            border_style="green",
            padding=(0, 1),
        ))
        # Compact help line
        self.console.print(
            "[dim]/help for commands · Ctrl-D or /quit to exit · "
            "[image: /path] inlines a screenshot[/dim]"
        )
        # One contextual tip — keeps the banner short but actionable
        tip = self._contextual_tip()
        if tip:
            self.console.print(f"[yellow]tip:[/yellow] [dim]{tip}[/dim]")
        self.console.print()

    # --- repo map (lazy) -------------------------------------------------

    def _ensure_repomap(self, max_age_s: float = 60.0) -> str:
        if (time.time() - self._repomap_built_at) > max_age_s:
            recent_paths: set[str] = set()
            # Skills carry provenance episode ids, not paths — leave empty for v1
            self._repomap_text = build_repomap(self.workspace,
                                                recent_skill_paths=recent_paths)
            self._repomap_built_at = time.time()
        return self._repomap_text

    # --- system prompt extension -----------------------------------------

    def _system_addendum(self) -> str:
        repomap = self._ensure_repomap()
        plan = ""
        if self.plan_mode:
            plan = (
                "\n\n## PLAN MODE\nYou MUST present a plan first (numbered "
                "steps, file list, expected diffs) and wait for user approval "
                "before applying any edit. Do not call destructive tools "
                "until the user types 'go'.\n"
            )
        edits = "\n\n" + SEARCH_REPLACE_INSTRUCTIONS
        return repomap + plan + edits

    # --- one turn --------------------------------------------------------

    def _show_turn_meta(self, episode: Episode, ms: int,
                        skills: list[Skill]) -> None:
        bits = [f"[{episode.outcome}]"]
        bits.append(f"{episode.num_steps} step")
        bits.append(f"{episode.tokens_used} tok")
        bits.append(f"{ms}ms")
        if skills:
            bits.append("skills: " + ", ".join(
                f"{s.name}(f={s.fitness_mean:.2f})" for s in skills[:3]
            ))
        self.console.print("[dim]" + " · ".join(bits) + "[/dim]")

    def _show_diff(self, diff: str, path: str) -> None:
        if not diff:
            return
        self.console.print(Syntax(
            diff, "diff", theme="monokai", line_numbers=False,
            background_color="default",
        ))

    def _apply_edits_with_preview(
        self, answer: str
    ) -> tuple[int, list]:
        """Detect SEARCH/REPLACE blocks in `answer`, preview, optionally apply.

        Returns (applied_count, results) where results is the list of
        ApplyResult objects (one per block). The caller can use the failure
        list to retry with feedback to the agent.
        """
        blocks = parse_edits(answer)
        if not blocks:
            return 0, []
        self.console.print(
            f"\n[bold cyan]→ {len(blocks)} edit block(s) detected[/bold cyan]"
        )
        previews = []
        for b in blocks:
            previews.append(_preview_block(b, self.workspace))
            self.console.print(f"[bold]· {b.path}[/bold]")
            if previews[-1]:
                self._show_diff(previews[-1], b.path)
            else:
                self.console.print("[yellow]  (no preview — search mismatch or new file)[/yellow]")
        ok = Confirm.ask(
            "[bold yellow]Apply these edits?[/bold yellow]",
            default=True,
        )
        if not ok:
            self.console.print("[dim]edits skipped[/dim]")
            return 0, []
        results = apply_blocks(blocks, self.workspace)
        applied = 0
        for r in results:
            if r.ok:
                applied += 1
                self.console.print(
                    f"[green]  ✓ {r.block.path}[/green] "
                    f"({r.diff.count(chr(10))} diff lines)"
                )
            else:
                self.console.print(
                    f"[red]  ✗ {r.block.path}[/red]  {r.reason}"
                )
        self._repomap_built_at = 0.0
        return applied, results

    def _retry_failed_edits(self, results: list, original_task: str,
                              max_retries: int = 1) -> int:
        """When edits failed (mismatched SEARCH), feed the failures back to
        the agent with the current file content and ask for a corrected set.

        Returns the additional number of blocks successfully applied.
        """
        failed = [r for r in results if not r.ok]
        if not failed:
            return 0
        # Build context: each failure + the current file content (so the model
        # can copy SEARCH text byte-for-byte).
        ctx_parts: list[str] = [
            "Your previous edit attempt did not apply. The system reports:",
            "",
        ]
        for r in failed:
            ctx_parts.append(f"  • {r.block.path}: {r.reason}")
        ctx_parts.append("")
        ctx_parts.append("Here is the CURRENT content of the files you tried to edit. "
                          "Use these EXACT bytes for SEARCH:")
        seen_paths: set[str] = set()
        for r in failed:
            if r.block.path in seen_paths:
                continue
            seen_paths.add(r.block.path)
            target = self.workspace / r.block.path.replace("\\", "/").lstrip("/")
            if target.exists():
                try:
                    content = target.read_text(encoding="utf-8")[:4000]
                except OSError:
                    content = "(unreadable)"
                ctx_parts.append(f"\n--- {r.block.path} ---\n{content}\n")
        ctx_parts.append("\nRe-emit the SEARCH/REPLACE blocks with byte-correct SEARCH text. "
                          "Original task was:\n" + original_task[:500])
        retry_prompt = "\n".join(ctx_parts)

        self.console.print("\n[yellow]→ retrying with file content as context…[/yellow]")
        try:
            result = self.agent.run_task(
                task_id=f"code-retry-{int(time.time())}",
                task_text=retry_prompt,
                validator=lambda ans: (bool(ans and ans.strip()), "non-empty"),
            )
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]retry agent error:[/red] {exc}")
            return 0
        ans = result.episode.final_answer or ""
        applied, _ = self._apply_edits_with_preview(ans)
        return applied

    def submit(self, task: str) -> None:
        """Send one task to the agent, render the answer + apply edits."""
        task = _resolve_vision_drops(task, self.console)
        # Inject the workspace context (repo map, plan-mode rules, edit format)
        # by appending to task — keeps the rest of Engram unchanged.
        task_with_ctx = self._system_addendum() + "\n\n## TASK\n" + task

        if self.model_override:
            os.environ["HIPPO_MODEL_EXECUTOR"] = self.model_override

        self.console.print()
        with self.console.status("[bold green]thinking…[/bold green]",
                                   spinner="dots"):
            t0 = time.perf_counter()
            try:
                result = self.agent.run_task(
                    task_id=f"code-{int(time.time())}",
                    task_text=task_with_ctx,
                    validator=lambda ans: (bool(ans and ans.strip()), "non-empty"),
                )
            except Exception as exc:  # noqa: BLE001
                self.console.print(f"[red]agent error:[/red] {exc}")
                return
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        ans = result.episode.final_answer or "(no answer)"
        # Render markdown if it's parseable, else raw
        try:
            self.console.print(Markdown(ans))
        except Exception:  # noqa: BLE001
            self.console.print(ans)
        self._show_turn_meta(result.episode, elapsed_ms, result.skills_retrieved)
        # Apply edits if any are present in the answer
        try:
            applied, results = self._apply_edits_with_preview(ans)
            # Retry only when ZERO edits applied — partial successes are kept
            # as-is to avoid overwriting good edits with retry fallout.
            if results and applied == 0:
                self._retry_failed_edits(results, original_task=task)
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]edit-apply error:[/red] {exc}")

    # --- slash commands --------------------------------------------------

    def _slash(self, line: str) -> bool:
        """Dispatch /commands. Returns True if recognised."""
        parts = line.strip().split(maxsplit=1)
        name = parts[0][1:]  # drop leading '/'
        arg = parts[1] if len(parts) > 1 else ""
        handler: Callable[[str], None] | None = getattr(
            self, f"_cmd_{name}", None
        )
        if handler is None:
            self.console.print(f"[red]unknown command:[/red] /{name}  "
                                f"[dim](try /help)[/dim]")
            return True
        try:
            handler(arg)
        except SystemExit:
            raise
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]/{name} error:[/red] {exc}")
        return True

    # Category for each slash command — drives the grouped /help output.
    # Commands not listed here fall under "Other".
    _HELP_GROUPS: dict[str, list[str]] = {
        "Memory": ["sleep", "skills", "promote", "retire", "forget"],
        "Workspace": ["repomap", "diff", "review"],
        "Model": ["model", "provider", "plan"],
        "Session": ["status", "clear", "help", "quit", "exit"],
    }

    def _cmd_help(self, arg: str) -> None:
        """Show available slash commands. Usage: /help [command] for detail."""
        # Detail view: /help sleep -> full docstring
        target = arg.strip().lstrip("/").lower()
        if target:
            handler = getattr(self, f"_cmd_{target}", None)
            if handler is None or not callable(handler):
                self.console.print(f"[red]unknown command:[/red] /{target}")
                return
            doc = (handler.__doc__ or "(no description)").strip()
            self.console.print(Panel(
                doc, title=f"/{target}", border_style="cyan", padding=(0, 1),
            ))
            return

        # List view, grouped
        all_cmds = {
            name[5:]: (getattr(self, name).__doc__ or "").strip().split("\n")[0]
            for name in dir(self)
            if name.startswith("_cmd_") and callable(getattr(self, name))
        }
        seen: set[str] = set()
        for group, names in self._HELP_GROUPS.items():
            present = [n for n in names if n in all_cmds]
            if not present:
                continue
            t = Table(show_header=False, box=None, padding=(0, 1),
                       title=f"[bold]{group}[/bold]", title_justify="left")
            for n in present:
                t.add_row(f"[cyan]/{n}[/cyan]", all_cmds[n] or "")
                seen.add(n)
            self.console.print(t)
        # Anything not categorised
        leftover = sorted(n for n in all_cmds if n not in seen)
        if leftover:
            t = Table(show_header=False, box=None, padding=(0, 1),
                       title="[bold]Other[/bold]", title_justify="left")
            for n in leftover:
                t.add_row(f"[cyan]/{n}[/cyan]", all_cmds[n] or "")
            self.console.print(t)
        self.console.print(
            "[dim]/help <command>  shows the full description for one command[/dim]"
        )

    def _cmd_quit(self, _: str) -> None:
        """Exit the session."""
        raise SystemExit(0)

    def _cmd_exit(self, _: str) -> None:
        """Alias of /quit."""
        raise SystemExit(0)

    def _cmd_sleep(self, _: str) -> None:
        """Run a sleep consolidation cycle right now."""
        with self.console.status("[bold purple]🌙 sleep cycle running…[/bold purple]"):
            report = self.agent.consolidate()
        t = Table(show_header=False, box=None, padding=(0, 1))
        t.add_row("NREM skills", str(report.n_nrem_skills))
        t.add_row("REM hybrids", str(report.n_rem_skills))
        t.add_row("🔧 macros", str(report.n_macros_compiled))
        t.add_row("🌀 counterfactuals", str(report.n_counterfactuals))
        t.add_row("🌳 schemas", str(report.n_schemas))
        t.add_row("📚 practice prompts", str(report.n_practice_prompts))
        t.add_row("promoted", str(len(report.promoted)))
        t.add_row("retired", str(len(report.retired)))
        t.add_row("duration", f"{report.duration_s:.2f}s · {report.tokens_used} tok")
        self.console.print(Panel(t, title="🌙 sleep done",
                                   border_style="purple"))

    def _cmd_skills(self, arg: str) -> None:
        """List active skills, sorted by fitness. Usage: /skills [limit]"""
        limit = int(arg) if arg.strip().isdigit() else 20
        skills = sorted(
            (s for s in self.agent.skills.all() if s.status != "retired"),
            key=lambda s: -s.fitness_mean,
        )[:limit]
        if not skills:
            self.console.print("[dim]no skills yet — run a few tasks first[/dim]")
            return
        t = Table(show_header=True, header_style="bold")
        t.add_column("id", style="dim")
        t.add_column("name")
        t.add_column("stage")
        t.add_column("status")
        t.add_column("trials", justify="right")
        t.add_column("fitness", justify="right")
        t.add_column("active", style="cyan")
        for s in skills:
            badges: list[str] = []
            if s.compiled_macro:
                badges.append("🔧")
            if s.is_counterfactual:
                badges.append("🌀")
            if s.learned_embedding is not None:
                badges.append("⚡")
            t.add_row(
                s.id[:8], s.name[:42], s.stage, s.status,
                f"{s.successes}/{s.trials}",
                f"{s.fitness_mean:.2f}",
                " ".join(badges) or "·",
            )
        self.console.print(t)

    def _cmd_model(self, arg: str) -> None:
        """Switch model for the executor. Usage: /model claude-opus-4-7  (no arg = show)"""
        if not arg.strip():
            cur = self.model_override or resolve_model("executor") or "(provider default)"
            self.console.print(f"[dim]current model:[/dim] {cur}")
            return
        self.model_override = arg.strip()
        os.environ["HIPPO_MODEL_EXECUTOR"] = self.model_override
        self.console.print(f"[green]model →[/green] {self.model_override}")

    def _cmd_provider(self, arg: str) -> None:
        """Switch LLM provider. Usage: /provider anthropic|openai|groq|ollama|…"""
        if not arg.strip():
            self.console.print(f"[dim]current:[/dim] {os.environ.get('HIPPO_LLM_PROVIDER', '(auto)')}")
            return
        os.environ["HIPPO_LLM_PROVIDER"] = arg.strip().lower()
        # Force a rebuild on next turn by re-resolving the LLM
        from .llm import get_llm
        try:
            self.agent.wake.llm = get_llm()
            self.agent.sleep.llm = self.agent.wake.llm
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]provider switch failed:[/red] {exc}")
            return
        self.console.print(f"[green]provider →[/green] {arg.strip().lower()}")

    def _cmd_plan(self, _: str) -> None:
        """Toggle plan mode: agent must propose a plan before any edit."""
        self.plan_mode = not self.plan_mode
        s = "ON" if self.plan_mode else "OFF"
        self.console.print(f"[yellow]plan mode {s}[/yellow]")

    def _cmd_repomap(self, _: str) -> None:
        """Print the current repo map."""
        self._repomap_built_at = 0.0
        self.console.print(self._ensure_repomap())

    def _cmd_status(self, _: str) -> None:
        """Show workspace + memory status."""
        self.console.print(self._status_line())

    def _cmd_diff(self, arg: str) -> None:
        """Show git diff for current workspace. Usage: /diff [path]"""
        import subprocess
        cmd = ["git", "diff"]
        if arg.strip():
            cmd.extend(["--", arg.strip()])
        from ._proc_quiet import quiet_popen_kwargs
        try:
            r = subprocess.run(cmd, cwd=str(self.workspace),
                                capture_output=True, timeout=10,
                                **quiet_popen_kwargs())  # cycle #136: no win pop-up
            out = r.stdout.decode("utf-8", errors="replace")
            if not out.strip():
                self.console.print("[dim](no changes)[/dim]")
                return
            self._show_diff(out, "diff")
        except FileNotFoundError:
            self.console.print("[red]git not available[/red]")

    def _cmd_review(self, arg: str) -> None:
        """Ask the agent to review a file. Usage: /review path/to/file.py"""
        if not arg.strip():
            self.console.print("[red]usage:[/red] /review path/to/file.py")
            return
        target = (self.workspace / arg.strip().lstrip("/").lstrip("\\"))
        if not target.exists():
            self.console.print(f"[red]not found:[/red] {arg}")
            return
        try:
            content = target.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self.console.print(f"[red]read failed:[/red] {exc}")
            return
        prompt = (
            f"Review the following file: {arg.strip()} ({len(content)} chars).\n"
            f"Look for bugs, security issues, dead code, or design problems. "
            f"Be specific and cite line numbers. Don't propose edits "
            f"unless I ask.\n\n"
            f"```\n{content[:8000]}\n```"
        )
        self.submit(prompt)

    def _cmd_clear(self, _: str) -> None:
        """Clear the screen."""
        self.console.clear()
        self._banner()

    def _cmd_forget(self, _: str) -> None:
        """Wipe ALL persistent memory (episodes, skills, semantic facts). Asks confirmation."""
        if not Confirm.ask(
            "[red]Wipe ALL persistent memory? This is permanent.[/red]",
            default=False,
        ):
            return
        self.agent.reset()
        self.console.print("[yellow]memory wiped[/yellow]")

    def _resolve_skill_id(self, prefix: str):
        """Find a skill by full id or by 8-char prefix."""
        prefix = prefix.strip()
        if not prefix:
            return None
        s = self.agent.skills.get(prefix)
        if s:
            return s
        for cand in self.agent.skills.all():
            if cand.id.startswith(prefix):
                return cand
        return None

    def _cmd_promote(self, arg: str) -> None:
        """Promote a candidate skill so it becomes retrievable. Usage: /promote <id-prefix>"""
        if not arg.strip():
            self.console.print("[red]usage:[/red] /promote <id-prefix>  (find ids with /skills)")
            return
        s = self._resolve_skill_id(arg)
        if not s:
            self.console.print(f"[red]no skill matches:[/red] {arg}")
            return
        s.status = "promoted"
        self.agent.skills.store(s)
        self.console.print(f"[green]promoted[/green] {s.id[:8]}  {s.name}")

    def _cmd_retire(self, arg: str) -> None:
        """Retire (archive) a skill so it stops being retrieved. Usage: /retire <id-prefix>"""
        if not arg.strip():
            self.console.print("[red]usage:[/red] /retire <id-prefix>")
            return
        s = self._resolve_skill_id(arg)
        if not s:
            self.console.print(f"[red]no skill matches:[/red] {arg}")
            return
        if not Confirm.ask(
            f"Retire skill [cyan]{s.id[:8]}[/cyan] ({s.name})?", default=True,
        ):
            return
        s.status = "retired"
        self.agent.skills.store(s)
        self.console.print(f"[yellow]retired[/yellow] {s.id[:8]}  {s.name}")

    # --- main loop -------------------------------------------------------

    def run(self) -> int:
        self.console.clear()
        self._banner()
        while True:
            try:
                line = Prompt.ask("[bold green]»[/bold green]")
            except (EOFError, KeyboardInterrupt):
                self.console.print()
                return 0
            if not line.strip():
                continue
            if line.lstrip().startswith("/"):
                try:
                    self._slash(line)
                except SystemExit:
                    return 0
                continue
            try:
                self.submit(line)
            except KeyboardInterrupt:
                self.console.print("[yellow](interrupted)[/yellow]")


# --- helpers (private) -----------------------------------------------------


def _preview_block(block: EditBlock, root: Path) -> str:
    """Render a unified diff *without* writing to disk — for confirm prompts."""
    rel = block.path.replace("\\", "/").lstrip("/")
    target = root / rel
    if block.search.strip() == "":
        # Creating new file
        from .editfmt import make_diff
        return make_diff(rel, "", block.replace)
    if not target.exists():
        return ""
    try:
        before = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    if before.count(block.search) != 1:
        return ""
    after = before.replace(block.search, block.replace, 1)
    from .editfmt import make_diff
    return make_diff(rel, before, after)


# --- Entry point used by cli.py --------------------------------------------


# Backward-compat alias: the pre-0.7.0 name of this REPL session class.
EngramCode = VerimemCode


def main(workspace: str | None = None,
          plan: bool = False,
          model: str | None = None) -> int:
    """Launch a Verimem Code session in `workspace` (default: cwd)."""
    ws = Path(workspace) if workspace else Path.cwd()
    session = VerimemCode(workspace=ws, plan_mode=plan, model_override=model)
    return session.run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
