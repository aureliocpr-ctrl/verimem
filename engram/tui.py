"""HippoAgent TUI — Textual-based terminal UI.

Tabs:
  Chat       — talk to the agent, see skills applied + outcome
  Skills     — browse consolidated skills (sortable by fitness)
  Episodes   — past task attempts
  Settings   — pick provider, set models, save

Run:  hippo tui
"""
from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from .agent import HippoAgent

_pool = ThreadPoolExecutor(max_workers=2)


def _sync_to_thread(fn, *args, **kwargs):
    """Run a blocking call in a worker thread (for awaitable usage in Textual)."""
    return asyncio.get_event_loop().run_in_executor(_pool, lambda: fn(*args, **kwargs))


class ChatPane(Vertical):
    """Chat pane: input box at the bottom, conversation log above."""

    DEFAULT_CSS = """
    ChatPane { height: 1fr; }
    #chat-log { height: 1fr; border: round $primary-lighten-1; padding: 1; }
    #chat-input { dock: bottom; height: 5; border: round $accent; }
    #chat-status { dock: bottom; height: 1; color: $text-muted; padding: 0 1; }
    """

    def compose(self) -> ComposeResult:
        self.log_widget = ScrollableContainer(id="chat-log")
        yield self.log_widget
        yield Static("ready · Ctrl+Enter to send · /sleep to consolidate", id="chat-status")
        yield TextArea(id="chat-input")

    def on_mount(self) -> None:
        self.input_box: TextArea = self.query_one("#chat-input", TextArea)
        self.status: Static = self.query_one("#chat-status", Static)

    def append_log(self, text: str, style: str = "") -> None:
        line = Static(text, classes=style)
        self.log_widget.mount(line)
        self.log_widget.scroll_end(animate=False)

    async def submit(self, agent: HippoAgent) -> None:
        task = self.input_box.text.strip()
        if not task:
            return
        if task in ("/sleep",):
            self.append_log("[bold magenta]🌙 Running sleep cycle…[/]")
            self.status.update("sleeping…")
            t0 = time.time()
            try:
                report = await _sync_to_thread(agent.consolidate)
            except Exception as exc:  # noqa: BLE001
                self.append_log(f"[red]sleep error: {exc}[/]")
                self.status.update("error")
                return
            self.append_log(
                f"[bold magenta]Sleep done[/] in {time.time()-t0:.1f}s: "
                f"NREM={report.n_nrem_skills} REM={report.n_rem_skills} "
                f"facts={report.n_facts} promoted={len(report.promoted)} "
                f"retired={len(report.retired)}"
            )
            self.status.update("ready")
            self.input_box.text = ""
            return
        self.append_log(f"[bold cyan]you ›[/] {task}")
        self.input_box.text = ""
        self.status.update("thinking…")
        t0 = time.time()
        try:
            result = await _sync_to_thread(
                agent.run_task,
                f"tui-{int(time.time())}", task,
                lambda ans: (bool(ans and ans.strip()), "non-empty"),
            )
        except Exception as exc:  # noqa: BLE001
            self.append_log(f"[red]error: {exc}[/]")
            self.status.update("error")
            return
        ms = int((time.time() - t0) * 1000)
        skills = ", ".join(s.name for s in result.skills_retrieved) or "none"
        outcome_color = "green" if result.success else "red"
        self.append_log(
            f"[bold {outcome_color}]agent ‹[/] {result.episode.final_answer or '(empty)'}"
        )
        self.append_log(
            f"[dim]   ↳ {result.episode.outcome} · {result.episode.num_steps} steps · "
            f"{result.episode.tokens_used} tokens · {ms}ms · skills: {skills}[/]"
        )
        self.status.update(f"done ({ms}ms)")


class SkillsPane(Vertical):
    DEFAULT_CSS = """
    SkillsPane { height: 1fr; padding: 1; }
    """

    def compose(self) -> ComposeResult:
        self.table = DataTable(zebra_stripes=True, cursor_type="row")
        self.table.add_columns("id", "name", "stage", "status", "trials", "fitness")
        yield self.table

    def refresh_skills(self, agent: HippoAgent) -> None:
        self.table.clear()
        skills = sorted(agent.skills.all(), key=lambda s: -s.fitness_mean)
        for s in skills:
            self.table.add_row(
                s.id[:8], s.name[:50], s.stage, s.status,
                f"{s.successes}/{s.trials}", f"{s.fitness_mean:.2f}",
            )


class EpisodesPane(Vertical):
    DEFAULT_CSS = """
    EpisodesPane { height: 1fr; padding: 1; }
    """

    def compose(self) -> ComposeResult:
        self.table = DataTable(zebra_stripes=True, cursor_type="row")
        self.table.add_columns("id", "task", "outcome", "steps", "tokens", "skills")
        yield self.table

    def refresh_episodes(self, agent: HippoAgent) -> None:
        self.table.clear()
        eps = agent.memory.all(limit=200)
        for e in eps:
            self.table.add_row(
                e.id[:8],
                (e.task_text[:60] + "…") if len(e.task_text) > 60 else e.task_text,
                e.outcome, str(e.num_steps), str(e.tokens_used),
                str(len(e.skills_used)),
            )


class SettingsPane(Vertical):
    DEFAULT_CSS = """
    SettingsPane { padding: 1; overflow: auto; }
    Label { padding: 1 0 0 0; color: $text-muted; }
    Input, Select { margin-bottom: 1; }
    .section-title { background: $accent 30%; color: $accent;
                     padding: 0 1; margin: 1 0; }
    """

    def compose(self) -> ComposeResult:
        from . import settings as us
        from .llm import list_providers
        cur = us.load()

        # --- Quick presets ---
        yield Static("⚡ Quick presets", classes="section-title")
        from .dashboard import PRESETS
        preset_options = [(p["label"] + " — " + p["tier"], p["id"]) for p in PRESETS]
        preset_options.insert(0, ("(custom)", ""))
        yield Label("Pick a preset for one-click switch")
        yield Select(preset_options, value="", id="preset")

        # --- Provider ---
        yield Static("🔧 Provider", classes="section-title")
        provs = [(name, name) for name in list_providers() if name != "mock"]
        provs.insert(0, ("(autodetect)", ""))
        yield Label("Provider")
        yield Select(provs, value=cur.provider or "", id="provider")
        yield Label("API key (leave empty to keep current)")
        yield Input(placeholder="sk-...", password=True, id="api_key")
        yield Label("Model (HIPPO_MODEL, applies to all stages)")
        yield Input(value=cur.model, placeholder="e.g. llama-3.3-70b-versatile", id="model")
        yield Label("Ollama model (optional)")
        yield Input(value=cur.ollama_model, placeholder="qwen2.5:7b-instruct", id="ollama_model")

        # --- Permissions ---
        yield Static("🔐 Permissions", classes="section-title")
        yield Label(f"Sandbox: {'ON' if cur.sandbox_enabled else 'OFF (UNRESTRICTED)'}")
        from textual.widgets import Switch
        yield Switch(value=cur.sandbox_enabled, id="sandbox_enabled")
        yield Label("Filesystem scope")
        yield Select(
            [("strict (data/ only)", "strict"), ("home (user dir)", "home"),
             ("full (anywhere)", "full")],
            value=cur.perm_filesystem, id="perm_filesystem",
        )
        yield Label(f"Computer use ({'ON' if cur.perm_computer_use else 'off'})")
        yield Switch(value=cur.perm_computer_use, id="perm_computer_use")
        yield Label(f"Webcam ({'ON' if cur.perm_webcam else 'off'})")
        yield Switch(value=cur.perm_webcam, id="perm_webcam")
        yield Label(f"Shell ({'ON' if cur.perm_shell else 'off'})")
        yield Switch(value=cur.perm_shell, id="perm_shell")
        yield Label(f"Web ({'ON' if cur.perm_web else 'off'})")
        yield Switch(value=cur.perm_web, id="perm_web")
        yield Label(f"Vision ({'ON' if cur.perm_vision else 'off'})")
        yield Switch(value=cur.perm_vision, id="perm_vision")

        with Horizontal():
            yield Button("💾 Save", variant="primary", id="save")
            yield Button("🧪 Test", id="test")
            yield Button("🔓 Unleash", variant="error", id="unleash")
            yield Button("🔒 Lockdown", variant="success", id="lockdown")
        yield Static("", id="set-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self._save()
        elif event.button.id == "test":
            self._test()
        elif event.button.id == "unleash":
            self._unleash()
        elif event.button.id == "lockdown":
            self._lockdown()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "preset" and event.value:
            self._apply_preset(str(event.value))

    def _apply_preset(self, preset_id: str) -> None:
        from . import settings as us
        from .dashboard import PRESETS
        p = next((x for x in PRESETS if x["id"] == preset_id), None)
        if not p:
            return
        cur = us.load()
        cur.provider = p["provider"]
        cur.model = p["model"]
        if p["provider"] == "ollama":
            cur.ollama_model = p["model"]
        us.save(cur)
        try:
            self.query_one("#provider").value = cur.provider
            self.query_one("#model").value = cur.model
            self.query_one("#ollama_model").value = cur.ollama_model
            self.query_one("#set-status", Static).update(
                f"✓ preset applied: {p['label']}"
            )
        except Exception:
            pass

    def _unleash(self) -> None:
        from . import settings as us
        cur = us.load()
        cur.sandbox_enabled = False
        cur.perm_filesystem = "full"
        cur.perm_computer_use = True
        cur.perm_webcam = True
        cur.perm_shell = True
        cur.perm_web = True
        cur.perm_vision = True
        us.save(cur)
        try:
            self.query_one("#sandbox_enabled").value = False
            self.query_one("#perm_filesystem").value = "full"
            for k in ("perm_computer_use","perm_webcam","perm_shell","perm_web","perm_vision"):
                self.query_one(f"#{k}").value = True
            self.query_one("#set-status", Static).update(
                "🔓 unleashed — agent has full PC access (sandbox OFF)"
            )
        except Exception:
            pass

    def _lockdown(self) -> None:
        from . import settings as us
        cur = us.load()
        cur.sandbox_enabled = True
        cur.perm_filesystem = "strict"
        cur.perm_computer_use = False
        cur.perm_webcam = False
        cur.perm_shell = False
        cur.perm_web = True
        cur.perm_vision = True
        us.save(cur)
        try:
            self.query_one("#sandbox_enabled").value = True
            self.query_one("#perm_filesystem").value = "strict"
            self.query_one("#perm_computer_use").value = False
            self.query_one("#perm_webcam").value = False
            self.query_one("#perm_shell").value = False
            self.query_one("#perm_web").value = True
            self.query_one("#perm_vision").value = True
            self.query_one("#set-status", Static).update(
                "🔒 lockdown — strict sandbox, only web + vision allowed"
            )
        except Exception:
            pass

    def _collect(self) -> dict:
        def v(wid):
            try:
                w = self.query_one(f"#{wid}")
                return getattr(w, "value", "") or ""
            except Exception:
                return ""
        return {
            "provider": v("provider"),
            "api_key": v("api_key"),
            "model": v("model"),
            "ollama_model": v("ollama_model"),
        }

    def _save(self) -> None:
        from . import settings as us
        from .llm import _canonical
        d = self._collect()
        cur = us.load()
        cur.provider = _canonical(d["provider"]) if d["provider"] else ""
        cur.model = d["model"]
        cur.ollama_model = d.get("ollama_model", cur.ollama_model)
        # Permissions
        for k in ("sandbox_enabled","perm_computer_use","perm_webcam",
                  "perm_shell","perm_web","perm_vision"):
            try:
                w = self.query_one(f"#{k}")
                setattr(cur, k, bool(w.value))
            except Exception:
                pass
        try:
            w = self.query_one("#perm_filesystem")
            cur.perm_filesystem = str(w.value or "home")
        except Exception:
            pass
        if d["api_key"] and d["provider"]:
            from .llm import PROVIDERS
            spec = PROVIDERS.get(d["provider"])
            if spec:
                cur.api_keys[spec["env"]] = d["api_key"]
            elif d["provider"] == "anthropic":
                cur.api_keys["ANTHROPIC_API_KEY"] = d["api_key"]
        cur.onboarded = True
        us.save(cur)
        self.query_one("#set-status", Static).update(
            f"✓ saved · provider={cur.provider or 'autodetect'} · "
            f"sandbox={'ON' if cur.sandbox_enabled else 'OFF'}"
        )

    def _test(self) -> None:
        from .llm import get_llm
        self._collect()
        # Save first so apply_to_env propagates the changes
        self._save()
        try:
            llm = get_llm(use_mock=False)
            t0 = time.time()
            resp = llm.complete(
                system="Reply only the single word: pong",
                messages=[{"role": "user", "content": "ping"}],
                temperature=0.0, max_tokens=8,
            )
            ms = int((time.time() - t0) * 1000)
            self.query_one("#set-status", Static).update(
                f"✓ {resp.text.strip()[:30]!r} · {resp.model} · {ms}ms"
            )
        except Exception as exc:
            self.query_one("#set-status", Static).update(f"✗ {exc}"[:120])


class HippoTUI(App):
    CSS = """
    Screen { layout: vertical; }
    TabbedContent { height: 1fr; }
    """
    BINDINGS = [
        Binding("ctrl+enter", "send", "Send"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("ctrl+s", "sleep", "Sleep cycle"),
        Binding("ctrl+q", "quit", "Quit"),
    ]
    TITLE = "Engram"
    SUB_TITLE = "LLM agent · memory · skills · sleep"

    def __init__(self) -> None:
        super().__init__()
        self.agent = HippoAgent.build()
        self.chat_pane: ChatPane | None = None
        self.skills_pane: SkillsPane | None = None
        self.episodes_pane: EpisodesPane | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="chat"):
            with TabPane("Chat", id="chat"):
                self.chat_pane = ChatPane()
                yield self.chat_pane
            with TabPane("Skills", id="skills"):
                self.skills_pane = SkillsPane()
                yield self.skills_pane
            with TabPane("Episodes", id="episodes"):
                self.episodes_pane = EpisodesPane()
                yield self.episodes_pane
            with TabPane("Settings", id="settings"):
                yield SettingsPane()
        yield Footer()

    def on_mount(self) -> None:
        if self.skills_pane:
            self.skills_pane.refresh_skills(self.agent)
        if self.episodes_pane:
            self.episodes_pane.refresh_episodes(self.agent)

    async def action_send(self) -> None:
        if self.chat_pane:
            await self.chat_pane.submit(self.agent)
            if self.skills_pane:
                self.skills_pane.refresh_skills(self.agent)
            if self.episodes_pane:
                self.episodes_pane.refresh_episodes(self.agent)

    def action_refresh(self) -> None:
        if self.skills_pane:
            self.skills_pane.refresh_skills(self.agent)
        if self.episodes_pane:
            self.episodes_pane.refresh_episodes(self.agent)

    async def action_sleep(self) -> None:
        if self.chat_pane:
            self.chat_pane.input_box.text = "/sleep"
            await self.chat_pane.submit(self.agent)


def main() -> None:
    HippoTUI().run()


if __name__ == "__main__":
    main()
