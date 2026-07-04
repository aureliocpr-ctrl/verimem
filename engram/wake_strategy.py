"""Encoding strategies for the wake loop.

The wake loop has ONE shape:

  prompt → LLM call → parse turn → execute tool calls
  → append assistant + observations → repeat until submit_solution
  or max_steps.

What varies between Anthropic native tool-use, OpenAI native tool-use,
and ReAct text-mode is exclusively *how* each step is encoded:

  - the system prompt template,
  - how the LLM is called (`complete_with_tools` vs `complete`),
  - how the response is parsed into (text, tool_calls),
  - how the assistant turn re-enters the message list (raw blocks
    vs string content),
  - how tool observations re-enter (tool_result blocks vs tool role
    messages vs ReAct "Observation:" lines),
  - which working-memory pruner applies.

Before this module the wake class held two near-duplicate ~120-LOC
loops and an `if hasattr(supports_tools): tools_loop else react_loop`
fork to choose between them. Each cross-cutting change (a new event
emit, a new CVE-008 gate, a new working-memory rule) had to be made
in two places, which is exactly the kind of accumulation the FORGIA
documents as Panda-DNA.

This module isolates the variation in a Strategy object so the loop
itself becomes single-source.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .config import CONFIG
from .llm import LLMToolResponse, ToolCall, resolve_model
from .observability import emit
from .working_memory import (
    native_tool_is_candidate,
    native_tool_replace,
    prune_messages,
    react_obs_is_candidate,
    react_obs_replace,
)

if TYPE_CHECKING:
    from .episode import Episode


# Re-export so wake.py can import everything from one place.
__all__ = [
    "ParsedTurn",
    "ToolObservation",
    "WakeStrategy",
    "NativeToolsStrategy",
    "ReActStrategy",
]


# ----- Uniform view of one LLM turn ---------------------------------------


@dataclass
class ParsedTurn:
    """The strategy-uniform view of one LLM turn.

    Both ReAct text and native tool-use produce one of these. The wake
    loop touches only this — never the raw `LLMResponse` /
    `LLMToolResponse`. `text` holds prose / Thought, `tool_calls` is the
    structured list of decisions (zero, one, or many), `total_tokens` is
    used by the agent to bookkeep, `raw` is opaque payload returned to
    the strategy on `append_assistant` for provider-specific re-echo.
    """
    text: str
    tool_calls: list[ToolCall]
    total_tokens: int
    raw: Any = None  # provider-specific; only the strategy reads it


@dataclass
class ToolObservation:
    """Result of executing one tool call, ready for the next turn."""
    tool_call_id: str
    tool_name: str
    observation: str


# ----- Strategy base ------------------------------------------------------


class WakeStrategy(ABC):
    """Per-encoding behaviour for the wake loop.

    The methods are deliberately fine-grained: each isolates one step of
    the loop's interaction with the message list or the LLM. Pulling a
    method out of an existing strategy is a sign that the abstraction is
    leaking — that should be a red flag, not a quick fix.
    """

    #: shows up as the `mode=` field in `emit("react_step")`. Useful
    #: for grepping logs to filter by encoding without renaming events.
    mode_name: str

    @abstractmethod
    def system_prompt(self, tools_catalog: str) -> str:
        """Return the system prompt for this encoding."""

    def initial_messages(self, user_prompt: str) -> list[dict[str, Any]]:
        """Both encodings start with one user message — kept on the
        base class so concrete strategies don't repeat trivia."""
        return [{"role": "user", "content": user_prompt}]

    @abstractmethod
    def call(
        self, llm: Any, system: str, messages: list[dict[str, Any]],
    ) -> ParsedTurn:
        """Invoke the LLM and parse its response into a `ParsedTurn`."""

    @abstractmethod
    def on_no_tool_calls(
        self,
        turn: ParsedTurn,
        episode: Episode,
        step: int,
        trace_step: int,
        validator: Any,
    ) -> tuple[int, tuple[bool, str]]:
        """Handle a turn that produced zero tool calls.

        For native tools that's a text-only "I'm done" response. For
        ReAct it's an unparseable model output (the parser couldn't
        extract Action/ActionInput).

        Returns `(new_trace_step, (success, message))`.
        """

    @abstractmethod
    def append_assistant(
        self, messages: list[dict[str, Any]], turn: ParsedTurn,
    ) -> None:
        """Append the assistant's turn to `messages` for the next iteration."""

    @abstractmethod
    def append_observations(
        self,
        messages: list[dict[str, Any]],
        turn: ParsedTurn,
        observations: list[ToolObservation],
    ) -> None:
        """Append the tool observations to `messages` for the next turn."""

    @abstractmethod
    def prune(
        self, messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        """Working-memory pruning specific to this encoding.

        Returns `(messages, n_pruned)` so the agent can emit a metric
        when something was actually compacted.
        """


# ----- Native tool-use strategy (Anthropic + OpenAI compat) ---------------


class NativeToolsStrategy(WakeStrategy):
    """Driver for providers that support native tool-use.

    The LLM returns structured `ToolCall` objects directly — no string
    parsing, no JSON-in-text fragility. That's what makes this path
    preferred when available.
    """

    mode_name = "tools"

    def __init__(self, tool_schemas: list[dict[str, Any]]):
        self._tool_schemas = tool_schemas

    def system_prompt(self, tools_catalog: str) -> str:
        # tools_catalog is unused in native mode — schemas go through
        # `tools=` parameter, not the system prompt. Kept on the
        # interface for ReAct symmetry.
        return (
            "You are HippoAgent — an autonomous agent with persistent memory.\n\n"
            "You are given a TASK. Use the available TOOLS to investigate, "
            "experiment, write code, fetch data, and finally submit your answer "
            "via the `submit_solution` tool.\n\n"
            "IMPORTANT — terminate explicitly:\n"
            "  • The TASK is only complete when you call `submit_solution` with "
            "a final summary in `answer`. Do NOT stop early — even after a "
            "successful side effect (like saving a file), you must still call "
            "`submit_solution` summarising what you did.\n\n"
            "Tool tips:\n"
            "  • `fs_write_file` is sandboxed under the project's data/ folder. "
            "To write elsewhere (Desktop, home dir, anywhere), use `run_python` "
            "with `pathlib.Path` or `open()` — full filesystem access via Python.\n"
            "  • `run_python` runs in a fresh subprocess with a 5s timeout, so "
            "make scripts self-contained.\n\n"
            "Past consolidated SKILLS may be injected into the task — apply them "
            "when relevant. Be concise. Stop on success by calling submit_solution."
        )

    def call(
        self, llm: Any, system: str, messages: list[dict[str, Any]],
    ) -> ParsedTurn:
        resp: LLMToolResponse = llm.complete_with_tools(
            system=system, messages=messages, tools=self._tool_schemas,
            temperature=CONFIG.llm_temperature_executor,
            model=resolve_model("executor"),
        )
        return ParsedTurn(
            text=resp.text,
            tool_calls=resp.tool_calls,
            total_tokens=resp.total_tokens,
            raw=resp.raw_content,
        )

    def on_no_tool_calls(
        self, turn: ParsedTurn, episode: Episode,
        step: int, trace_step: int, validator: Any,
    ) -> tuple[int, tuple[bool, str]]:
        # Pure text response — the agent gave up or just answered.
        from .episode import Trace
        trace_step += 1
        episode.traces.append(Trace(
            step=trace_step, thought=turn.text[:500],
            action="(text-only)", action_input="",
            observation="(no tool call)",
        ))
        emit("react_step", episode_id=episode.id, step=step,
             action="(text-only)", ok=True, mode=self.mode_name)
        if turn.text.strip():
            ok, msg = validator(turn.text)
            episode.final_answer = turn.text
            return trace_step, (ok, msg)
        return trace_step, (False, "empty response")

    def append_assistant(
        self, messages: list[dict[str, Any]], turn: ParsedTurn,
    ) -> None:
        # Anthropic returns a list of content blocks; OpenAI/Ollama
        # return a complete message dict already. Echo whichever shape
        # the provider produced — the next request needs the
        # `tool_use` blocks to validate the protocol on Anthropic and
        # the message to align tool_call_ids on OpenAI.
        raw = turn.raw
        if isinstance(raw, list):
            messages.append({"role": "assistant", "content": raw})
        elif isinstance(raw, dict):
            messages.append(raw)
        else:
            messages.append({"role": "assistant", "content": str(raw)})

    def append_observations(
        self, messages: list[dict[str, Any]], turn: ParsedTurn,
        observations: list[ToolObservation],
    ) -> None:
        # Anthropic style — single user message with tool_result blocks
        if isinstance(turn.raw, list):
            messages.append({
                "role": "user",
                "content": [
                    {"type": "tool_result",
                     "tool_use_id": o.tool_call_id,
                     "content": o.observation}
                    for o in observations
                ],
            })
            return
        # OpenAI / Ollama style — one tool role message per call
        for o in observations:
            messages.append({
                "role": "tool",
                "tool_call_id": o.tool_call_id,
                "name": o.tool_name,
                "content": o.observation,
            })

    def prune(
        self, messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        return prune_messages(
            messages,
            budget=CONFIG.working_memory_max_chars,
            keep_tail=CONFIG.working_memory_keep_tail,
            placeholder=CONFIG.working_memory_pruned_placeholder,
            is_candidate=native_tool_is_candidate,
            replace_in_place=native_tool_replace,
        )


# ----- ReAct text-mode strategy (legacy fallback) -------------------------


_THOUGHT_RE = re.compile(
    r"Thought:\s*(.*?)(?=\n\s*Action:|\Z)", re.DOTALL | re.IGNORECASE,
)
_ACTION_RE = re.compile(
    r"Action:\s*[`*_]*([A-Za-z_][A-Za-z0-9_]*)[`*_]*", re.IGNORECASE,
)
_ACTIONINPUT_RE = re.compile(
    r"Action[\s_]*Input:?\s*(.*?)(?=\n\s*Thought:|\n\s*Action:|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def parse_react_step(text: str) -> tuple[str, str, str] | None:
    """Tolerant ReAct parser: handles markdown fences, asterisks,
    snake-case variants. Returns (thought, action, action_input) or
    None if the input doesn't contain a valid step."""
    s = text.strip()
    s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
    s = re.sub(r"\s*```\s*$", "", s)

    a_match = _ACTION_RE.search(s)
    i_match = _ACTIONINPUT_RE.search(s)
    if not (a_match and i_match):
        return None

    thought = ""
    t_match = _THOUGHT_RE.search(s)
    if t_match:
        thought = t_match.group(1).strip()

    action = a_match.group(1).strip()
    action_input = i_match.group(1).strip()
    action_input = re.sub(r"^```[a-zA-Z]*\s*", "", action_input)
    action_input = re.sub(r"\s*```\s*$", "", action_input)
    return thought, action, action_input


class ReActStrategy(WakeStrategy):
    """Driver for providers without native tool-use.

    The LLM emits Thought/Action/ActionInput as plain text; we parse it.
    Fragile (newline escaping, JSON quoting), preserved as fallback when
    `complete_with_tools` raises — see `WakeAgent._run_loop`.
    """

    mode_name = "react"

    def __init__(self, base_system: str, tools_catalog: str):
        # The system prompt embeds the full tool catalog as plain text
        # because there's no native tools= parameter. Composed once at
        # construction so the loop doesn't pay for it on every step.
        self._system = base_system + "\n\nAVAILABLE TOOLS:\n" + tools_catalog

    def system_prompt(self, tools_catalog: str) -> str:
        # Already built at __init__; the `tools_catalog` arg is part of
        # the abstract contract but redundant here.
        return self._system

    def call(
        self, llm: Any, system: str, messages: list[dict[str, Any]],
    ) -> ParsedTurn:
        resp = llm.complete(
            system=system, messages=messages,
            temperature=CONFIG.llm_temperature_executor,
            model=resolve_model("executor"),
        )
        parsed = parse_react_step(resp.text)
        tool_calls: list[ToolCall] = []
        thought = ""
        if parsed is not None:
            thought, action, action_input = parsed
            # Lazy JSON parse — invalid JSON is reported by `_call_tool`
            # downstream, so we keep it in args even if it doesn't parse.
            try:
                args = (
                    json.loads(action_input)
                    if action_input.strip().startswith("{") else {}
                )
            except json.JSONDecodeError:
                args = {"_raw_action_input": action_input}
            tool_calls.append(ToolCall(
                # ReAct doesn't have tool_call_ids — synthesise one
                # from the step counter at the agent layer.
                id=f"react_{action}",
                name=action,
                input=args,
            ))
        return ParsedTurn(
            text=thought or resp.text[:500],
            tool_calls=tool_calls,
            total_tokens=resp.total_tokens,
            raw=resp.text,
        )

    def on_no_tool_calls(
        self, turn: ParsedTurn, episode: Episode,
        step: int, trace_step: int, validator: Any,
    ) -> tuple[int, tuple[bool, str]]:
        # Parser failed — episode is dead.
        from .episode import Trace
        trace_step += 1
        episode.traces.append(Trace(
            step=trace_step, thought="(unparseable)",
            action="(none)", action_input="",
            observation="LLM output was not valid ReAct format",
        ))
        emit("react_parse_failed", episode_id=episode.id, step=step)
        return trace_step, (False, "unparseable")

    def append_assistant(
        self, messages: list[dict[str, Any]], turn: ParsedTurn,
    ) -> None:
        # The raw text is what the LLM produced — re-attach for context.
        messages.append({"role": "assistant", "content": str(turn.raw)})

    def append_observations(
        self, messages: list[dict[str, Any]], turn: ParsedTurn,
        observations: list[ToolObservation],
    ) -> None:
        # ReAct convention: each observation is a single user message
        # ending with "Continue." to anchor the next Thought. With at
        # most ONE tool call per turn (the parser only extracts one),
        # we expect len(observations) == 1; if zero we no-op.
        for o in observations:
            messages.append({
                "role": "user",
                "content": f"Observation:\n{o.observation}\n\nContinue.",
            })

    def prune(
        self, messages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], int]:
        return prune_messages(
            messages,
            budget=CONFIG.working_memory_max_chars,
            keep_tail=CONFIG.working_memory_keep_tail,
            placeholder=CONFIG.working_memory_pruned_placeholder,
            is_candidate=react_obs_is_candidate,
            replace_in_place=react_obs_replace,
        )
