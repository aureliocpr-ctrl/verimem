"""LLM client wrapper — multi-provider.

All providers expose the same `complete(system, messages, ...) → LLMResponse`
interface, so the rest of HippoAgent is provider-agnostic.

Supported providers (autodetected by env, or forced via HIPPO_LLM_PROVIDER):

  US / EU (OpenAI-compatible):
    openai      OPENAI_API_KEY         gpt-4o-mini
    openrouter  OPENROUTER_API_KEY     gateway to any model (defaults: claude-haiku)
    together    TOGETHER_API_KEY       Llama 3.1 8B
    groq        GROQ_API_KEY           Llama 3.3 70B
    fireworks   FIREWORKS_API_KEY      Llama 3.1 70B
    xai         XAI_API_KEY            Grok 2
    mistral     MISTRAL_API_KEY        Mistral Large
    cerebras    CEREBRAS_API_KEY       Llama 3.3 70B
    gemini      GEMINI_API_KEY         Gemini 1.5 Flash (OpenAI-compat endpoint)

  China (OpenAI-compatible):
    moonshot    MOONSHOT_API_KEY       Kimi (alias: "kimi") — moonshot-v1-auto
    deepseek    DEEPSEEK_API_KEY       deepseek-chat
    qwen        DASHSCOPE_API_KEY      Qwen Plus (alias: "dashscope")
    zhipu       ZHIPU_API_KEY          GLM-4-Plus (alias: "glm")
    baichuan    BAICHUAN_API_KEY       Baichuan4-Turbo
    yi          YI_API_KEY             Yi-Large (alias: "lingyi", "01ai")
    doubao      DOUBAO_API_KEY         ByteDance Ark (alias: "ark")

  Native:
    anthropic   ANTHROPIC_API_KEY      Claude (uses Anthropic SDK, not OpenAI-compat)
    ollama      OLLAMA_HOST            local Ollama (default: localhost:11434)

  Special:
    mock        — deterministic, scripted responses (no network)

Per-stage model overrides:
    HIPPO_MODEL                   = applies to all stages
    HIPPO_MODEL_EXECUTOR          = wake-loop ReAct
    HIPPO_MODEL_DREAMER           = sleep NREM/REM synthesis (smarter model recommended)
    HIPPO_MODEL_CRITIC            = self-critique + curator merge

Examples:
    HIPPO_LLM_PROVIDER=kimi MOONSHOT_API_KEY=sk-... hippo wake
    HIPPO_LLM_PROVIDER=ollama OLLAMA_MODEL=qwen2.5:7b hippo wake
    HIPPO_LLM_PROVIDER=deepseek HIPPO_MODEL=deepseek-reasoner hippo wake
"""
from __future__ import annotations

import ipaddress
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import CONFIG
from .observability import emit, get_log

log = get_log()


def _retry_sleep(attempt: int, wait: float) -> None:
    """Sleep `wait`s between retries, but NEVER after the final attempt.

    Scan low #7: every provider's retry loop slept on each failed attempt
    INCLUDING the last one, right before raising — pure wasted latency on a
    terminal error (e.g. groq 404 model_not_found, observed live 2026-06-10).
    `attempt` is the 0-based loop index over range(CONFIG.llm_max_retries)."""
    if attempt < CONFIG.llm_max_retries - 1:
        time.sleep(wait)



@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    latency_s: float

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ToolCall:
    """One tool invocation requested by the LLM (native tool-use)."""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMToolResponse:
    """Response when using native tool-use APIs.

    `text` is any prose the model emitted alongside (or instead of) tool calls.
    `tool_calls` is the list of structured tool requests — these come back as
    JSON objects, no string parsing required.
    `raw_content` is the assistant turn re-serialized for the next request
    (Anthropic needs the tool_use blocks echoed back to satisfy the protocol).
    """
    text: str
    tool_calls: list[ToolCall]
    input_tokens: int
    output_tokens: int
    model: str
    latency_s: float
    raw_content: Any  # provider-specific, opaque to wake loop

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMError(RuntimeError):
    pass


class LazyLLM:
    """Transparent proxy that defers ``get_llm()`` until the LLM is first used.

    Constructing a HippoAgent must NOT require a usable LLM: the memory layer —
    and the read-only dashboard views (episodes / skills / active-memory) — do
    zero inference, yet they previously 500'd because building the agent eagerly
    constructed an AnthropicLLM and raised "ANTHROPIC_API_KEY not set" when no
    key / no hosted mode was configured (2026-06-06).

    The real backend is built on first *attribute* access, so a missing key
    only raises when inference is actually attempted, not at construction time.
    No ``isinstance`` checks are done on the llm in the wake/sleep hot paths
    (verified), so a proxy is safe here.
    """

    __slots__ = ("_real",)

    def __init__(self) -> None:
        object.__setattr__(self, "_real", None)

    def _resolve(self):  # noqa: ANN202 - returns whatever get_llm() returns
        real = object.__getattribute__(self, "_real")
        if real is None:
            real = get_llm()
            object.__setattr__(self, "_real", real)
        return real

    def __getattr__(self, name: str):  # only called when normal lookup misses
        return getattr(self._resolve(), name)


# ---- Claude CLI subprocess (cycle #72 — subscription via OAuth) ----

class ClaudeCLILLM:
    """LLM client that delegates to `claude -p` CLI subprocess.

    Cycle #72 (2026-05-15). Unblocks `hippo_consolidate` in HOSTED MODE
    when MCP sampling is unavailable (Claude Code as of 2026-05-15
    returns McpError "Method not found"). The CLI authenticates via
    OAuth/keychain locally — same subscription, ZERO external API key.

    Drop-in replacement for `AnthropicLLM` from `SleepEngine`'s
    perspective. SYNC `subprocess.run` (not async — fits SleepEngine's
    pattern of calling self.llm.complete from asyncio.to_thread).

    Limitations (P0):
    - `supports_tools()` returns False (text-only; tool-use via CLI
      requires --bare + permission setup, out of scope).
    - Spawn overhead ~3-4s per call (TTFT). Acceptable for sleep cycle
      operations (~14 calls × 8s = ~2 min for full consolidate).
    - Token counts char-proxy estimate (CLI returns usage dict but
      we keep parity with MCPSamplingLLM proxy).
    """

    def __init__(
        self, *,
        claude_bin: str = "claude",
        timeout_s: float = 180.0,
        extra_args: list[str] | None = None,
    ) -> None:
        self.claude_bin = claude_bin
        self.timeout_s = float(timeout_s)
        self.extra_args = list(extra_args or [])

    def complete(
        self, system: str, messages: list[dict[str, str]],
        *, model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """Concatenate system+messages → claude -p --output-format json
        subprocess → parse stdout → LLMResponse."""
        import subprocess as _sp
        # Build full prompt: system header then user/assistant turns.
        # We pass via stdin to avoid Windows argv quoting issues.
        # Cycle 159.7 bug fix (eve+frank sonnet duo + Arm A consensus):
        # the previous loop did ``parts.insert(0, content)`` for any
        # role=='system' message, which pushed the primary ``system`` arg
        # to index 1 (or further), reversing the order of multiple
        # system messages. Now we collect ALL system content (primary
        # arg + role=system messages) in their natural sequence, then
        # append non-system turns. Docstring (line 154) intent preserved:
        # "system header then user/assistant turns".
        system_parts: list[str] = []
        if system:
            system_parts.append(system.strip())
        turn_parts: list[str] = []
        for m in messages:
            role = m.get("role", "user")
            content = str(m.get("content", ""))
            if role == "system":
                system_parts.append(content)
            else:
                turn_parts.append(content)
        parts = system_parts + turn_parts
        full_prompt = "\n\n".join(parts)

        cmd = [
            self.claude_bin, "-p",
            "--output-format", "json",
        ] + self.extra_args

        t0 = time.time()
        try:
            result = _sp.run(
                cmd,
                input=full_prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                encoding="utf-8",
            )
        except _sp.TimeoutExpired as exc:
            raise LLMError(
                f"claude CLI timed out after {self.timeout_s}s",
            ) from exc
        except FileNotFoundError as exc:
            raise LLMError(
                f"claude CLI not found: {self.claude_bin}",
            ) from exc

        latency = time.time() - t0
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()

        if result.returncode != 0:
            raise LLMError(
                f"claude CLI exited with code {result.returncode}: "
                f"{stderr[:300]}",
            )

        try:
            data = json.loads(stdout)
        except (json.JSONDecodeError, ValueError) as exc:
            raise LLMError(
                f"claude CLI returned non-JSON output: "
                f"{stdout[:300]}",
            ) from exc

        is_error = data.get("is_error", False)
        if is_error:
            raise LLMError(
                f"claude CLI error: "
                f"{str(data.get('result', ''))[:300]}",
            )

        text = str(data.get("result", ""))
        usage = data.get("usage", {}) or {}
        in_tokens = int(usage.get("input_tokens", 0) or 0)
        out_tokens = int(usage.get("output_tokens", 0) or 0)
        # Resolve model from modelUsage keys (first key) or fallback
        model_usage = data.get("modelUsage", {}) or {}
        model_name = (next(iter(model_usage.keys()), None)
                      or "claude-cli")

        emit(
            "llm_call", provider="claude_cli", model=model_name,
            input_tokens=in_tokens, output_tokens=out_tokens,
            latency_s=round(latency, 3),
        )
        return LLMResponse(
            text=text,
            input_tokens=in_tokens, output_tokens=out_tokens,
            model=model_name, latency_s=latency,
        )

    def supports_tools(self) -> bool:
        # P0 cycle #72: text-only via CLI. Tool-use via --bare requires
        # explicit permission setup — out of scope.
        return False


# ---- MCP Sampling (cycle #71 — subscription via host) --------------------

class MCPSamplingLLM:
    """LLM client that delegates to the MCP host via sampling/createMessage.

    Cycle #71 (2026-05-15). Unblocks `hippo_consolidate` in HOSTED MODE
    without external API keys: instead of calling Anthropic/OpenAI HTTP
    directly, asks the host MCP client (Claude Code) to generate a
    completion using ITS subscription. Cost to HippoAgent = ZERO.

    Drop-in replacement for `AnthropicLLM` from SleepEngine's
    perspective: same `complete(system, messages, ...)` signature
    returning `LLMResponse`. SYNC façade over async
    `ServerSession.create_message(...)` via `run_coroutine_threadsafe`,
    so it works from `asyncio.to_thread` (used by hippo_consolidate
    handler to avoid blocking the event loop).

    Limitations (P0):
    - `supports_tools()` returns False (text-only sampling for now).
    - No retry/backoff (host handles its own retries).
    - Token counts are character-proxy estimates (MCP sampling result
      does not expose usage stats).
    """

    def __init__(
        self, *, loop: Any, session: Any,
        default_max_tokens: int = 1024,
        timeout_s: float = 120.0,
    ) -> None:
        self._loop = loop
        self._session = session
        self._default_max_tokens = int(default_max_tokens)
        self._timeout_s = float(timeout_s)

    def complete(
        self, system: str, messages: list[dict[str, str]],
        *, model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """Sync façade. SAFE to call from `asyncio.to_thread` —
        bridges to the event loop's create_message via
        run_coroutine_threadsafe."""
        import asyncio as _asyncio
        coro = self._async_complete(
            system, messages,
            temperature=temperature,
            max_tokens=max_tokens or self._default_max_tokens,
            stop_sequences=stop_sequences,
        )
        future = _asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=self._timeout_s)
        except TimeoutError as exc:
            raise LLMError(
                f"MCP sampling timed out after {self._timeout_s}s",
            ) from exc

    async def _async_complete(
        self, system: str, messages: list[dict[str, str]],
        *, temperature: float, max_tokens: int,
        stop_sequences: list[str] | None,
    ) -> LLMResponse:
        from mcp.types import SamplingMessage, TextContent
        t0 = time.time()
        sampling_msgs = []
        for m in messages:
            role = m.get("role", "user")
            if role not in ("user", "assistant"):
                role = "user"
            content = m.get("content", "")
            sampling_msgs.append(SamplingMessage(
                role=role,
                content=TextContent(type="text", text=str(content)),
            ))
        kwargs: dict[str, Any] = {
            "messages": sampling_msgs,
            "max_tokens": max_tokens,
            "system_prompt": system,
        }
        if temperature is not None:
            kwargs["temperature"] = float(temperature)
        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences
        try:
            result = await self._session.create_message(**kwargs)
        except Exception as exc:
            # CYCLE #71 BIS — log the failure BEFORE re-raising as LLMError
            # so we can see what the host actually replied (or refused).
            try:
                from pathlib import Path
                dbg = Path.home() / ".engram" / "mcp_sampling_debug.log"
                dbg.parent.mkdir(parents=True, exist_ok=True)
                with dbg.open("a", encoding="utf-8") as f:
                    f.write(f"\n--- {time.time():.0f} FAILED "
                            f"exc_type={type(exc).__name__} ---\n")
                    f.write(f"SYSTEM: {(system or '')[:200]}\n")
                    f.write(f"USER[0]: "
                            f"{(str(messages[0].get('content', '')) if messages else '')[:300]}\n")
                    f.write(f"EXC: {str(exc)[:600]}\n")
            except Exception:  # noqa: BLE001
                pass
            raise LLMError(f"MCP sampling failed: {exc}") from exc
        latency = time.time() - t0
        # Extract text from result.content (TextContent | Image | Audio).
        content = getattr(result, "content", None)
        text = getattr(content, "text", "") if content else ""
        model = getattr(result, "model", "mcp_sampling")
        # Token counts not exposed by MCP — char-proxy estimate (~4 chars/token).
        # Cycle 159.7 bug fix (frank sonnet duo, independent read): the
        # earlier `in_chars` summed only message contents and ignored
        # `system`, which is passed to `create_message(system_prompt=...)`
        # and is part of the input the model bills. For large system
        # prompts (8K chars) this caused ~2K tokens undercount on every
        # llm_call emit — observability drift, not correctness, but
        # billed metrics were wrong.
        out_tokens = len(text) // 4
        in_chars = (
            len(system or "")
            + sum(len(str(m.get("content", ""))) for m in messages)
        )
        in_tokens = in_chars // 4

        # CYCLE #71 BIS debug — dump raw sampling response to file for
        # forensics when consolidate produces 0 skills despite routing OK.
        # Tag with timestamp to keep separate samples per run.
        try:
            from pathlib import Path
            dbg = Path.home() / ".engram" / "mcp_sampling_debug.log"
            dbg.parent.mkdir(parents=True, exist_ok=True)
            with dbg.open("a", encoding="utf-8") as f:
                f.write(f"\n--- {time.time():.0f} model={model} "
                        f"latency={latency:.2f}s len={len(text)} ---\n")
                f.write(f"SYSTEM: {(system or '')[:200]}\n")
                f.write(f"USER[0]: "
                        f"{(messages[0].get('content', '') if messages else '')[:300]}\n")
                f.write(f"RESP: {text[:600]}\n")
        except Exception:  # noqa: BLE001
            pass

        emit(
            "llm_call", provider="mcp_sampling", model=model,
            input_tokens=in_tokens, output_tokens=out_tokens,
            latency_s=round(latency, 3),
        )
        return LLMResponse(
            text=text,
            input_tokens=in_tokens, output_tokens=out_tokens,
            model=model, latency_s=latency,
        )

    def supports_tools(self) -> bool:
        # P0 cycle #71: text-only sampling. Tool-use via MCP sampling
        # requires SamplingToolsCapability — out of scope per spec.
        return False


# ---- Anthropic (native) --------------------------------------------------

class AnthropicLLM:
    def __init__(self, api_key: str | None = None) -> None:
        from anthropic import Anthropic

        key = api_key or CONFIG.anthropic_api_key
        if not key:
            raise LLMError("ANTHROPIC_API_KEY not set")
        self.client = Anthropic(api_key=key)
        self.default_model = CONFIG.model_executor

    @staticmethod
    def _supports_temperature(model: str) -> bool:
        """Some Claude models (extended-thinking, opus-4-7) deprecate the
        `temperature` parameter — passing it returns 400. Detect by name."""
        if not model:
            return True
        m = model.lower()
        # Opus 4.7+ deprecates temperature; Sonnet/Haiku still accept it.
        # Pattern matches both 'claude-opus-4-7' and 'claude-opus-4-7[1m]'.
        if "claude-opus-4-7" in m or "claude-opus-4-8" in m:
            return False
        return True

    def complete(
        self, system: str, messages: list[dict[str, str]], model: str | None = None,
        temperature: float = 0.0, max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        max_tokens = max_tokens or CONFIG.llm_max_tokens
        last_exc: Exception | None = None
        for attempt in range(CONFIG.llm_max_retries):
            t0 = time.time()
            try:
                kwargs: dict[str, Any] = dict(
                    model=model, system=system, messages=messages,
                    max_tokens=max_tokens,
                    stop_sequences=stop_sequences or [],
                )
                if self._supports_temperature(model):
                    kwargs["temperature"] = temperature
                resp = self.client.messages.create(**kwargs)
                latency = time.time() - t0
                text = "".join(b.text for b in resp.content
                               if getattr(b, "type", None) == "text")
                emit("llm_call", provider="anthropic", model=model,
                     input_tokens=resp.usage.input_tokens,
                     output_tokens=resp.usage.output_tokens,
                     latency_s=round(latency, 3))
                return LLMResponse(
                    text=text, input_tokens=resp.usage.input_tokens,
                    output_tokens=resp.usage.output_tokens,
                    model=model, latency_s=latency,
                )
            except Exception as exc:
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_retry", provider="anthropic",
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
        raise LLMError(f"Anthropic call failed after retries: {last_exc}")

    def supports_tools(self) -> bool:
        return True

    def complete_with_tools(
        self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
        model: str | None = None, temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMToolResponse:
        """Native Anthropic tool-use. `tools` = list of {name, description, input_schema}.

        The returned `raw_content` is the assistant message blocks; pass it back
        as a {"role":"assistant", "content": raw_content} entry next turn,
        followed by tool_result blocks for each tool_call.id.
        """
        model = model or self.default_model
        max_tokens = max_tokens or CONFIG.llm_max_tokens
        last_exc: Exception | None = None
        for attempt in range(CONFIG.llm_max_retries):
            t0 = time.time()
            try:
                kwargs: dict[str, Any] = dict(
                    model=model, system=system, messages=messages,
                    tools=tools, max_tokens=max_tokens,
                )
                if self._supports_temperature(model):
                    kwargs["temperature"] = temperature
                resp = self.client.messages.create(**kwargs)
                latency = time.time() - t0
                text = ""
                tool_calls: list[ToolCall] = []
                raw_blocks: list[dict[str, Any]] = []
                for block in resp.content:
                    btype = getattr(block, "type", None)
                    if btype == "text":
                        text += block.text
                        raw_blocks.append({"type": "text", "text": block.text})
                    elif btype == "tool_use":
                        tool_calls.append(ToolCall(
                            id=block.id, name=block.name,
                            input=dict(block.input) if isinstance(block.input, dict) else {},
                        ))
                        raw_blocks.append({
                            "type": "tool_use", "id": block.id,
                            "name": block.name, "input": block.input,
                        })
                emit("llm_call", provider="anthropic", model=model,
                     input_tokens=resp.usage.input_tokens,
                     output_tokens=resp.usage.output_tokens,
                     latency_s=round(latency, 3), n_tool_calls=len(tool_calls))
                return LLMToolResponse(
                    text=text, tool_calls=tool_calls,
                    input_tokens=resp.usage.input_tokens,
                    output_tokens=resp.usage.output_tokens,
                    model=model, latency_s=latency, raw_content=raw_blocks,
                )
            except Exception as exc:
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_tools_retry", provider="anthropic",
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
        raise LLMError(f"Anthropic tool call failed after retries: {last_exc}")


# ---- OpenAI-compatible (everything below) -------------------------------

# ---------------------------------------------------------------------------
# audit#3-r3 R7 — SSRF guard for the operator-overridable provider base_url.
# ---------------------------------------------------------------------------
_SSRF_BLOCKED_HOSTNAMES = frozenset({
    "metadata.google.internal",
    "metadata.goog",
})
# Metadata IPs that are NOT link-local (so ``is_link_local`` won't catch them):
# Alibaba Cloud (100.100.100.200) and AWS IMDS over IPv6 (fd00:ec2::254).
_SSRF_BLOCKED_IPS = frozenset({
    ipaddress.ip_address("100.100.100.200"),
    ipaddress.ip_address("fd00:ec2::254"),
})


def _is_blocked_host(base_url: str) -> bool:
    """True if ``base_url`` targets a cloud-metadata / link-local endpoint that
    is never a legitimate LLM provider (the classic SSRF credential-theft
    target). NOT a full egress filter: localhost, private LAN and public hosts
    stay allowed (legit self-hosted / Ollama / Azure), and hostnames are not
    DNS-resolved (no rebind defense). audit#3-r3 R7.
    """
    try:
        host = (urlparse(base_url).hostname or "").strip().lower()
    except (ValueError, TypeError):
        return False
    if not host:
        return False
    if host in _SSRF_BLOCKED_HOSTNAMES:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a regular hostname we don't resolve -> allow
    return ip.is_link_local or ip in _SSRF_BLOCKED_IPS


class OpenAICompatLLM:
    """Works for any OpenAI-compatible chat completions endpoint."""

    def __init__(self, api_key: str, base_url: str, default_model: str,
                 provider_label: str = "openai-compat") -> None:
        if not api_key:
            raise LLMError(f"{provider_label} api_key not set")
        # audit#3-r3 R7: refuse a base_url that targets a cloud-metadata /
        # link-local endpoint (SSRF credential-theft vector) BEFORE building the
        # client. localhost / private-LAN / public hosts stay allowed (legit
        # self-hosted / Ollama / Azure). Enforced here so every entry path
        # (settings save+test, env var, CLI) is covered.
        if _is_blocked_host(base_url):
            raise LLMError(
                f"{provider_label} base_url targets a blocked cloud-metadata / "
                f"link-local host (SSRF guard): {base_url!r}"
            )
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.default_model = default_model
        self.provider_label = provider_label

    def complete(
        self, system: str, messages: list[dict[str, str]], model: str | None = None,
        temperature: float = 0.0, max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        max_tokens = max_tokens or CONFIG.llm_max_tokens
        msgs = [{"role": "system", "content": system}] + list(messages)
        last_exc: Exception | None = None
        for attempt in range(CONFIG.llm_max_retries):
            t0 = time.time()
            try:
                resp = self.client.chat.completions.create(
                    model=model, messages=msgs, temperature=temperature,
                    max_tokens=max_tokens, stop=stop_sequences or None,
                )
                latency = time.time() - t0
                text = resp.choices[0].message.content or ""
                usage = resp.usage
                in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
                out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
                emit("llm_call", provider=self.provider_label, model=model,
                     input_tokens=in_tok, output_tokens=out_tok,
                     latency_s=round(latency, 3))
                return LLMResponse(text=text, input_tokens=in_tok,
                                   output_tokens=out_tok, model=model,
                                   latency_s=latency)
            except Exception as exc:
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_retry", provider=self.provider_label,
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
        raise LLMError(f"{self.provider_label} call failed after retries: {last_exc}")

    def supports_tools(self) -> bool:
        # Most OpenAI-compat endpoints support tools, but some (e.g. very small
        # local models) don't. We optimistically claim support; failures fall
        # back to ReAct text in the wake loop.
        return self.provider_label not in {"perplexity"}  # known to not support tools

    def complete_with_tools(
        self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
        model: str | None = None, temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMToolResponse:
        """Native OpenAI tool-calls."""
        model = model or self.default_model
        max_tokens = max_tokens or CONFIG.llm_max_tokens
        # Convert {name, description, input_schema} -> OpenAI {type:'function', function:{...}}
        oai_tools = [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", t.get("parameters", {"type": "object"})),
            },
        } for t in tools]
        msgs = [{"role": "system", "content": system}] + list(messages)
        last_exc: Exception | None = None
        for attempt in range(CONFIG.llm_max_retries):
            t0 = time.time()
            try:
                resp = self.client.chat.completions.create(
                    model=model, messages=msgs, tools=oai_tools,
                    max_tokens=max_tokens, temperature=temperature,
                )
                latency = time.time() - t0
                msg = resp.choices[0].message
                text = msg.content or ""
                tool_calls: list[ToolCall] = []
                if msg.tool_calls:
                    import json as _j
                    for tc in msg.tool_calls:
                        # CQ #12 fix: OpenAI may return ChatCompletionMessage
                        # CustomToolCall objects which don't have a `.function`
                        # attribute. Skip those — we don't support custom
                        # tool-call shapes today.
                        fn = getattr(tc, "function", None)
                        if fn is None:
                            log.debug("skipping non-function tool call",
                                      tc_type=type(tc).__name__)
                            continue
                        raw_args = getattr(fn, "arguments", "") or ""
                        try:
                            args = _j.loads(raw_args) if raw_args else {}
                        except (_j.JSONDecodeError, TypeError, ValueError):
                            args = {"_raw": raw_args}
                        tc_id = getattr(tc, "id", "") or ""
                        tc_name = getattr(fn, "name", "") or ""
                        tool_calls.append(ToolCall(
                            id=tc_id, name=tc_name, input=args,
                        ))
                usage = resp.usage
                in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
                out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
                emit("llm_call", provider=self.provider_label, model=model,
                     input_tokens=in_tok, output_tokens=out_tok,
                     latency_s=round(latency, 3), n_tool_calls=len(tool_calls))
                # Re-serialize for next-turn echo. Mirrors the parsing
                # guard above: non-function tool-call shapes (e.g. OpenAI
                # ChatCompletionMessageCustomToolCall) lack `.function`
                # entirely. Skipping them keeps the loop alive on
                # provider drift instead of bombing the whole call.
                serialised_tool_calls: list[dict[str, Any]] = []
                for tc in (msg.tool_calls or []):
                    fn = getattr(tc, "function", None)
                    if fn is None:
                        continue
                    serialised_tool_calls.append({
                        "id": getattr(tc, "id", "") or "",
                        "type": "function",
                        "function": {
                            "name": getattr(fn, "name", "") or "",
                            "arguments": getattr(fn, "arguments", "") or "",
                        },
                    })
                raw_assistant = {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": serialised_tool_calls or None,
                }
                return LLMToolResponse(
                    text=text, tool_calls=tool_calls,
                    input_tokens=in_tok, output_tokens=out_tok,
                    model=model, latency_s=latency, raw_content=raw_assistant,
                )
            except Exception as exc:
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_tools_retry", provider=self.provider_label,
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
        raise LLMError(f"{self.provider_label} tool call failed after retries: {last_exc}")


# ---- Ollama (native HTTP) ------------------------------------------------

def _ollama_keep_alive() -> str:
    """How long Ollama keeps the model resident between calls.

    Ollama's default is 5 minutes; after that the model unloads and the NEXT
    call pays the full cold-load (MEASURED 2026-06-06: ~97s for qwen2.5:1.5b on
    CPU vs 0.5-2.8s warm). A memory system calls the LLM intermittently
    (gate-judge per write, periodic consolidate), so the 5-min default hits the
    cold cliff constantly in local/air-gap mode. Keep the model warm. Override
    via HIPPO_OLLAMA_KEEP_ALIVE: "-1" = resident until Ollama restarts (best for
    a dedicated air-gap server), "10m", or "0" = unload immediately.
    """
    return (os.environ.get("HIPPO_OLLAMA_KEEP_ALIVE") or "30m").strip()


class OllamaLLM:
    """Direct Ollama HTTP API. More reliable than its openai-compat shim."""

    def __init__(self, base_url: str = "http://localhost:11434",
                 default_model: str = "llama3.1") -> None:
        self.base = base_url.rstrip("/")
        self.default_model = default_model
        self._client = httpx.Client(timeout=600.0)
        self._models_cache: list[str] | None = None

    def _available_models(self) -> list[str]:
        """Names of models installed on this Ollama server (cached). [] on error."""
        if self._models_cache is not None:
            return self._models_cache
        try:
            r = self._client.get(f"{self.base}/api/tags", timeout=5.0)
            r.raise_for_status()
            self._models_cache = [
                m.get("name", "") for m in r.json().get("models", [])
            ]
        except Exception:  # noqa: BLE001
            self._models_cache = []
        return self._models_cache

    def _fallback_model(self, requested: str) -> str | None:
        """Pick an INSTALLED chat model when `requested` 404s. Prefers the
        configured default, else the first non-embedding model actually present
        on the server (so air-gap "just works" with whatever the operator
        pulled). Returns None if nothing better exists (let the 404 stand)."""
        avail = self._available_models()
        if not avail:
            return self.default_model if self.default_model != requested else None
        if self.default_model in avail and self.default_model != requested:
            return self.default_model
        for m in avail:
            if m and "embed" not in m.lower() and m != requested:
                return m
        return None

    def complete(
        self, system: str, messages: list[dict[str, str]], model: str | None = None,
        temperature: float = 0.0, max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        model = model or self.default_model
        msgs = [{"role": "system", "content": system}] + [
            {"role": m["role"], "content": m["content"]} for m in messages
        ]
        options: dict[str, Any] = {
            "temperature": temperature,
            "num_predict": max_tokens or CONFIG.llm_max_tokens,
        }
        if stop_sequences:
            options["stop"] = stop_sequences
        body = {"model": model, "messages": msgs, "options": options,
                "stream": False, "keep_alive": _ollama_keep_alive()}
        last_exc: Exception | None = None
        for attempt in range(CONFIG.llm_max_retries):
            t0 = time.time()
            try:
                r = self._client.post(f"{self.base}/api/chat", json=body)
                r.raise_for_status()
                data = r.json()
                text = data.get("message", {}).get("content", "")
                latency = time.time() - t0
                in_tok = int(data.get("prompt_eval_count", 0))
                out_tok = int(data.get("eval_count", 0))
                emit("llm_call", provider="ollama", model=model,
                     input_tokens=in_tok, output_tokens=out_tok,
                     latency_s=round(latency, 3))
                return LLMResponse(text=text, input_tokens=in_tok,
                                   output_tokens=out_tok, model=model,
                                   latency_s=latency)
            except httpx.HTTPStatusError as exc:
                # 404 = model not found on this Ollama server. Callers can pass
                # a provider-incoherent name (e.g. a cloud `model_executor`
                # projected from settings while HIPPO_LLM_PROVIDER=ollama). Fall
                # back to a model actually INSTALLED on the server instead of
                # crashing the run — critical for local/air-gap usability.
                if exc.response.status_code == 404:
                    alt = self._fallback_model(body["model"])
                    if alt and alt != body["model"]:
                        log.warning("ollama_model_fallback", requested=body["model"],
                                    fallback=alt, reason="404 not found")
                        body["model"] = alt
                        model = alt
                        continue
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_retry", provider="ollama",
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
            except Exception as exc:
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_retry", provider="ollama",
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
        raise LLMError(f"Ollama call failed after retries: {last_exc}")

    def supports_tools(self) -> bool:
        # Ollama 0.4+ supports native tool calling via /api/chat for many
        # modern instruct models (qwen2.5*, llama3.1+, mistral-nemo, command-r,
        # hermes-3, etc). Disable explicitly via HIPPO_OLLAMA_TOOLS=0 if your
        # specific model misbehaves.
        flag = os.environ.get("HIPPO_OLLAMA_TOOLS", "").strip().lower()
        if flag in ("0", "false", "no", "off"):
            return False
        return True

    def complete_with_tools(
        self, system: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
        model: str | None = None, temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> LLMToolResponse:
        """Native Ollama tool calling via /api/chat with `tools` parameter.

        Ollama mirrors the OpenAI tool schema, so we send the same shape and
        receive back `message.tool_calls` with `function.name` + parsed args.
        """
        model = model or self.default_model
        max_tokens = max_tokens or CONFIG.llm_max_tokens
        oai_tools = [{
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", t.get("parameters", {"type": "object"})),
            },
        } for t in tools]

        # Ollama accepts the same role-based messages as OpenAI. We need the
        # system prompt at the front; intermediate "user" wrappers we sent
        # for the React loop also work.
        ollama_messages = [{"role": "system", "content": system}]
        for m in messages:
            content = m.get("content")
            # Ollama doesn't natively understand list-of-blocks (Anthropic style)
            # — flatten to text so we don't lose information.
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        bt = block.get("type")
                        if bt == "text":
                            parts.append(block.get("text", ""))
                        elif bt == "tool_use":
                            parts.append(f"[tool_use {block.get('name','')}({block.get('input','')})]")
                        elif bt == "tool_result":
                            parts.append(f"[tool_result {block.get('tool_use_id','')}: "
                                         f"{block.get('content','')}]")
                    else:
                        parts.append(str(block))
                content = "\n".join(parts)
            ollama_messages.append({"role": m.get("role", "user"), "content": content or ""})

        body = {
            "model": model,
            "messages": ollama_messages,
            "tools": oai_tools,
            "stream": False,
            "keep_alive": _ollama_keep_alive(),
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        last_exc: Exception | None = None
        for attempt in range(CONFIG.llm_max_retries):
            t0 = time.time()
            try:
                r = self._client.post(f"{self.base}/api/chat", json=body)
                r.raise_for_status()
                data = r.json()
                latency = time.time() - t0
                msg = data.get("message", {})
                text = msg.get("content", "")
                tool_calls: list[ToolCall] = []
                for i, tc in enumerate(msg.get("tool_calls", []) or []):
                    fn = tc.get("function", {}) if isinstance(tc, dict) else {}
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        import json as _j
                        try:
                            args = _j.loads(args)
                        except Exception:
                            args = {"_raw": args}
                    tool_calls.append(ToolCall(
                        id=tc.get("id") or f"call_{i}",
                        name=fn.get("name", ""),
                        input=args if isinstance(args, dict) else {},
                    ))
                in_tok = int(data.get("prompt_eval_count", 0))
                out_tok = int(data.get("eval_count", 0))
                emit("llm_call", provider="ollama", model=model,
                     input_tokens=in_tok, output_tokens=out_tok,
                     latency_s=round(latency, 3), n_tool_calls=len(tool_calls))
                return LLMToolResponse(
                    text=text, tool_calls=tool_calls,
                    input_tokens=in_tok, output_tokens=out_tok,
                    model=model, latency_s=latency,
                    raw_content={"role": "assistant", "content": text,
                                 "tool_calls": msg.get("tool_calls", [])},
                )
            except httpx.HTTPStatusError as exc:
                # 404 = model not found — fall back to an INSTALLED model
                # (see OllamaLLM.complete / _fallback_model).
                if exc.response.status_code == 404:
                    alt = self._fallback_model(body["model"])
                    if alt and alt != body["model"]:
                        log.warning("ollama_model_fallback", requested=body["model"],
                                    fallback=alt, reason="404 not found")
                        body["model"] = alt
                        model = alt
                        continue
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_tools_retry", provider="ollama",
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
            except Exception as exc:
                last_exc = exc
                wait = CONFIG.llm_retry_backoff ** attempt
                log.warning("llm_tools_retry", provider="ollama",
                            attempt=attempt + 1, error=str(exc), wait_s=wait)
                _retry_sleep(attempt, wait)
        raise LLMError(f"Ollama tool call failed after retries: {last_exc}")

    @staticmethod
    def alive(base_url: str | None = None, timeout: float = 1.0) -> bool:
        url = (base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        try:
            with httpx.Client(timeout=timeout) as c:
                return c.get(f"{url}/api/tags").status_code == 200
        except Exception:
            return False


# ---- Mock ----------------------------------------------------------------

class MockLLM:
    def __init__(self, scripted: list[str] | None = None) -> None:
        self._scripted = list(scripted or [])
        self._calls: list[dict[str, Any]] = []

    def complete(
        self, system: str, messages: list[dict[str, str]], model: str | None = None,
        temperature: float = 0.0, max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        self._calls.append({"system": system, "messages": messages, "model": model})
        text = self._scripted.pop(0) if self._scripted else "OK"
        return LLMResponse(
            text=text,
            input_tokens=len(system) // 4 + sum(len(m["content"]) for m in messages) // 4,
            output_tokens=len(text) // 4,
            model=model or "mock",
            latency_s=0.0,
        )

    @property
    def calls(self) -> list[dict[str, Any]]:
        return self._calls

    def supports_tools(self) -> bool:
        return False


# ---- Provider registry ---------------------------------------------------

# Each entry: (env_var, base_url_default, default_model, base_url_env_override?)
PROVIDERS: dict[str, dict[str, Any]] = {
    # US / EU
    "openai": {
        "env": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "base_url_env": "OPENAI_BASE_URL",
        "default_model": "gpt-4o-mini",
    },
    "openrouter": {
        "env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "anthropic/claude-haiku-4.5",
    },
    "together": {
        "env": "TOGETHER_API_KEY",
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    },
    "groq": {
        "env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
    },
    "fireworks": {
        "env": "FIREWORKS_API_KEY",
        "base_url": "https://api.fireworks.ai/inference/v1",
        "default_model": "accounts/fireworks/models/llama-v3p1-70b-instruct",
    },
    "xai": {
        "env": "XAI_API_KEY",
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-4",  # FORGIA #36: grok-2-latest deprecated
    },
    "mistral": {
        "env": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-large-latest",
    },
    "cerebras": {
        "env": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama3.3-70b",
    },
    "gemini": {
        "env": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-1.5-flash",
    },
    # China
    "moonshot": {
        "env": "MOONSHOT_API_KEY",
        "base_url": "https://api.moonshot.cn/v1",
        "base_url_env": "MOONSHOT_BASE_URL",   # use https://api.moonshot.ai/v1 for intl
        "default_model": "moonshot-v1-auto",
    },
    "deepseek": {
        "env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "qwen": {
        "env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "base_url_env": "DASHSCOPE_BASE_URL",  # use https://dashscope-intl.aliyuncs.com/... outside China
        "default_model": "qwen-plus",
    },
    "zhipu": {
        "env": "ZHIPU_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-plus",
    },
    "baichuan": {
        "env": "BAICHUAN_API_KEY",
        "base_url": "https://api.baichuan-ai.com/v1",
        "default_model": "Baichuan4-Turbo",
    },
    "yi": {
        "env": "YI_API_KEY",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "default_model": "yi-large",
    },
    "doubao": {
        "env": "DOUBAO_API_KEY",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "base_url_env": "ARK_BASE_URL",
        "default_model": "doubao-pro-32k",
    },
    "hunyuan": {  # Tencent
        "env": "HUNYUAN_API_KEY",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "default_model": "hunyuan-pro",
    },
    "stepfun": {  # 阶跃星辰
        "env": "STEP_API_KEY",
        "base_url": "https://api.stepfun.com/v1",
        "default_model": "step-1-8k",
    },
    "minimax": {
        "env": "MINIMAX_API_KEY",
        "base_url": "https://api.minimax.chat/v1",
        "default_model": "MiniMax-Text-01",
    },
    "spark": {  # iFlytek 讯飞星火
        "env": "SPARK_API_KEY",
        "base_url": "https://spark-api-open.xf-yun.com/v1",
        "default_model": "general",
    },
    # --- More US/EU providers ---
    "perplexity": {
        "env": "PERPLEXITY_API_KEY",
        "base_url": "https://api.perplexity.ai",
        "default_model": "sonar",
    },
    "nvidia": {
        "env": "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "meta/llama-3.3-70b-instruct",
    },
    "huggingface": {
        "env": "HF_TOKEN",
        "base_url": "https://router.huggingface.co/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
    },
    "deepinfra": {
        "env": "DEEPINFRA_API_KEY",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
    },
    "hyperbolic": {
        "env": "HYPERBOLIC_API_KEY",
        "base_url": "https://api.hyperbolic.xyz/v1",
        "default_model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
    },
    "novita": {
        "env": "NOVITA_API_KEY",
        "base_url": "https://api.novita.ai/v3/openai",
        "default_model": "meta-llama/llama-3.1-70b-instruct",
    },
    "lepton": {
        "env": "LEPTON_API_KEY",
        "base_url": "https://llama3-1-70b.lepton.run/api/v1",
        "default_model": "llama3-1-70b",
    },
    "anyscale": {
        "env": "ANYSCALE_API_KEY",
        "base_url": "https://api.endpoints.anyscale.com/v1",
        "default_model": "meta-llama/Meta-Llama-3-70B-Instruct",
    },
    "azure": {  # Azure OpenAI — set OPENAI_BASE_URL to your deployment endpoint
        "env": "AZURE_OPENAI_API_KEY",
        "base_url": "https://your-resource.openai.azure.com/openai/v1",
        "base_url_env": "AZURE_OPENAI_ENDPOINT",
        "default_model": "gpt-4o-mini",
    },
    # --- Local OpenAI-compatible servers ---
    "lmstudio": {
        "env": "LMSTUDIO_API_KEY",  # any non-empty string works locally
        "base_url": "http://localhost:1234/v1",
        "base_url_env": "LMSTUDIO_BASE_URL",
        "default_model": "local-model",
    },
    "vllm": {
        "env": "VLLM_API_KEY",  # any non-empty string
        "base_url": "http://localhost:8000/v1",
        "base_url_env": "VLLM_BASE_URL",
        "default_model": "local-model",
    },
    "localai": {
        "env": "LOCALAI_API_KEY",
        "base_url": "http://localhost:8080/v1",
        "base_url_env": "LOCALAI_BASE_URL",
        "default_model": "local-model",
    },
    "tabby": {  # TabbyAPI / text-generation-webui openai-compat
        "env": "TABBY_API_KEY",
        "base_url": "http://localhost:5000/v1",
        "base_url_env": "TABBY_BASE_URL",
        "default_model": "local-model",
    },
}

# User-friendly aliases → canonical name
ALIASES: dict[str, str] = {
    "kimi": "moonshot",
    "glm": "zhipu",
    "chatglm": "zhipu",
    "ark": "doubao",
    "bytedance": "doubao",
    "tencent": "hunyuan",
    "step": "stepfun",
    "iflytek": "spark",
    "google": "gemini",
    "lingyi": "yi",
    "01ai": "yi",
    "01": "yi",
    "dashscope": "qwen",
    "alibaba": "qwen",
    "tongyi": "qwen",
    "claude": "anthropic",
    "grok": "xai",
    "hf": "huggingface",
    "lm-studio": "lmstudio",
    "lm_studio": "lmstudio",
}


# rescan2 2026-06-02 (NONNA): allinea i default_model del registry inline ai
# valori di providers.yaml (single source per gli id dei modelli). Senza questo
# il motore girava su id obsoleti (gpt-4o-mini, gemini-1.5-flash, glm-4-plus...)
# mentre cli/dashboard usano gli id 2026 dello yaml. Override NON distruttivo:
# tocca SOLO default_model dei provider gia presenti in ENTRAMBI; non aggiunge
# ne rimuove provider, non cambia la shape (i 17 provider only-inline restano
# coi loro valori). Il refactor completo (un solo registry) resta A1+A3 nel piano.
try:
    from .provider_registry import PROVIDERS_BY_NAME as _REGISTRY_SPECS
    for _pname, _pspec in _REGISTRY_SPECS.items():
        _dm = getattr(_pspec, "default_model", "")
        if _pname in PROVIDERS and _dm:
            PROVIDERS[_pname]["default_model"] = _dm
except Exception:  # noqa: BLE001 — registry opzionale; mai rompere l'import di llm
    pass


# Autodetection priority order (first one with a configured env wins).
# Anthropic first because the baseline experiment was tuned for it.
AUTODETECT_ORDER: list[str] = [
    "anthropic",
    "openai", "azure", "openrouter", "mistral", "groq", "xai", "perplexity",
    "fireworks", "together", "cerebras", "gemini", "nvidia",
    "huggingface", "deepinfra", "hyperbolic", "novita", "anyscale", "lepton",
    "moonshot", "deepseek", "qwen", "zhipu", "baichuan", "yi", "doubao",
    "hunyuan", "stepfun", "minimax", "spark",
    "lmstudio", "vllm", "localai", "tabby",
    "ollama",
]


def _canonical(name: str) -> str:
    return ALIASES.get(name.lower().strip(), name.lower().strip())


def _autodetect_provider() -> str:
    for p in AUTODETECT_ORDER:
        if p == "anthropic" and CONFIG.anthropic_api_key:
            return "anthropic"
        if p == "ollama" and OllamaLLM.alive():
            return "ollama"
        spec = PROVIDERS.get(p)
        if spec and os.environ.get(spec["env"]):
            return p
    return "mock"


def _build(provider: str):
    p = _canonical(provider)
    if p == "anthropic":
        return AnthropicLLM()
    if p == "ollama":
        return OllamaLLM(
            base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            default_model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        )
    if p == "mock":
        return MockLLM()
    spec = PROVIDERS.get(p)
    if not spec:
        raise LLMError(f"Unknown provider: {provider} (canonical: {p}). "
                       f"Known: {list(PROVIDERS.keys()) + ['anthropic','ollama','mock']}.")
    api_key = os.environ.get(spec["env"], "")
    base_url = spec["base_url"]
    if "base_url_env" in spec and os.environ.get(spec["base_url_env"]):
        base_url = os.environ[spec["base_url_env"]]
    default_model = os.environ.get("HIPPO_MODEL", spec["default_model"])
    return OpenAICompatLLM(api_key=api_key, base_url=base_url,
                           default_model=default_model, provider_label=p)


def list_providers() -> list[str]:
    """All known provider names (canonical, no aliases)."""
    return ["anthropic"] + list(PROVIDERS.keys()) + ["ollama", "mock"]


def is_configured(provider: str) -> bool:
    """Does the named provider have credentials / be reachable?"""
    p = _canonical(provider)
    if p == "anthropic":
        return bool(CONFIG.anthropic_api_key)
    if p == "ollama":
        return OllamaLLM.alive()
    if p == "mock":
        return True
    spec = PROVIDERS.get(p)
    return bool(spec) and bool(os.environ.get(spec["env"]))


def list_models_for_provider(provider: str, timeout: float = 15.0) -> list[dict[str, Any]]:
    """Query the provider's discovery endpoint and return a list of model entries.

    Returns raw entries normalised to at least {"id": <str>}; extra fields preserved.
    Raises LLMError if the provider isn't configured or the call fails.
    """
    p = _canonical(provider)
    if p == "anthropic":
        from anthropic import Anthropic
        if not CONFIG.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY not set")
        client = Anthropic(api_key=CONFIG.anthropic_api_key, timeout=timeout)
        out: list[dict[str, Any]] = []
        for m in client.models.list().data:
            out.append({
                "id": m.id,
                "type": getattr(m, "type", ""),
                "display_name": getattr(m, "display_name", ""),
                "created_at": str(getattr(m, "created_at", "")),
            })
        return out

    if p == "ollama":
        url = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        with httpx.Client(timeout=timeout) as c:
            r = c.get(f"{url}/api/tags")
            r.raise_for_status()
            return [
                {
                    "id": m["name"],
                    "size_bytes": m.get("size", 0),
                    "modified_at": m.get("modified_at", ""),
                    "family": (m.get("details") or {}).get("family", ""),
                    "param_size": (m.get("details") or {}).get("parameter_size", ""),
                    "quant": (m.get("details") or {}).get("quantization_level", ""),
                }
                for m in r.json().get("models", [])
            ]

    if p == "mock":
        return [{"id": "mock-model"}]

    spec = PROVIDERS.get(p)
    if not spec:
        raise LLMError(f"Unknown provider: {provider} (canonical: {p})")
    api_key = os.environ.get(spec["env"], "")
    if not api_key:
        raise LLMError(f"{spec['env']} not set for provider {p}")
    base_url = spec["base_url"]
    if "base_url_env" in spec and os.environ.get(spec["base_url_env"]):
        base_url = os.environ[spec["base_url_env"]]
    base_url = base_url.rstrip("/")
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=timeout) as c:
        r = c.get(f"{base_url}/models", headers=headers)
        r.raise_for_status()
        data = r.json()
    items = data.get("data", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        items = [items]
    out = []
    for m in items:
        if isinstance(m, str):
            out.append({"id": m})
        elif isinstance(m, dict):
            entry = {"id": m.get("id") or m.get("model") or m.get("name") or str(m)}
            # Preserve common metadata if present
            for k in ("created", "owned_by", "object", "context_length", "name"):
                if k in m:
                    entry[k] = m[k]
            out.append(entry)
    return out


def scan_all_providers(timeout: float = 10.0) -> dict[str, dict[str, Any]]:
    """Discovery scan: for each provider, report configured-state and models.

    {
      "anthropic": {"configured": True, "n": 8, "models": ["claude-...", ...]},
      "groq":      {"configured": False},
      "ollama":    {"configured": True, "n": 12, "models": [...]},
      ...
    }
    """
    report: dict[str, dict[str, Any]] = {}
    for name in list_providers():
        if name == "mock":
            continue
        if not is_configured(name):
            report[name] = {"configured": False}
            continue
        try:
            models = list_models_for_provider(name, timeout=timeout)
            report[name] = {
                "configured": True,
                "n": len(models),
                "models": [m.get("id", str(m)) for m in models],
                "raw": models,
            }
        except Exception as exc:  # noqa: BLE001
            report[name] = {"configured": True, "error": str(exc)[:200]}
    return report


def resolve_model(stage: str = "executor") -> str | None:
    """Pick the model id appropriate for the active provider + stage.

    Stage ∈ {"executor","dreamer","critic"}. Resolution order:
      1. HIPPO_MODEL_<STAGE> env (e.g. HIPPO_MODEL_DREAMER=mistral-large)
      2. HIPPO_MODEL env (applies to all stages)
      3. Provider-specific default (Anthropic-stage defaults from CONFIG; others
         fall through to the provider's own default by returning None).
    """
    env_specific = os.environ.get(f"HIPPO_MODEL_{stage.upper()}")
    if env_specific:
        return env_specific
    if os.environ.get("HIPPO_MODEL"):
        return os.environ["HIPPO_MODEL"]
    forced = os.environ.get("HIPPO_LLM_PROVIDER", "").strip().lower()
    provider = _canonical(forced) if forced else _autodetect_provider()
    if provider == "anthropic":
        return getattr(CONFIG, f"model_{stage}", CONFIG.model_executor)
    return None  # let provider client use its own default


class FallbackLLM:
    """Chain multiple LLM clients — try the first, fall back on quota/5xx errors.

    Wraps `complete()` and `complete_with_tools()` calls. Each call tries the
    primary; if it raises, walks the fallback list. The chain is reset per call,
    so a primary that recovers is used again next time.
    """

    def __init__(self, primary, fallbacks: list) -> None:
        self.primary = primary
        self.fallbacks = list(fallbacks)
        self._all = [primary] + list(fallbacks)

    def supports_tools(self) -> bool:
        # We support tools if ANY in the chain does — the dispatcher walks
        # the chain looking for one that supports.
        return any(getattr(c, "supports_tools", lambda: False)() for c in self._all)

    @staticmethod
    def _is_recoverable(exc: Exception) -> bool:
        msg = str(exc).lower()
        # rescan2 2026-06-02: context/token-length errors contain the substring
        # "limit" but fail IDENTICALLY on every provider (the prompt is too
        # long), so retrying the fallback chain is pointless and burns the
        # remaining providers. Exclude them BEFORE the recoverable match (which
        # keeps "limit" for rate / concurrency limits that DO benefit from a
        # provider switch).
        nonrecoverable = (
            "context length", "context_length", "context window",
            "maximum context", "token limit", "tokens limit",
            "max_tokens", "too long", "reduce the length",
            "string too long",
        )
        if any(s in msg for s in nonrecoverable):
            return False
        # Rate limit, quota, billing, 5xx, timeout, connection — try next provider.
        return any(s in msg for s in (
            "429", "rate", "quota", "billing", "credit", "limit",
            "503", "504", "timeout", "connection", "overload",
        ))

    def complete(self, system, messages, model=None, temperature=0.0,
                 max_tokens=None, stop_sequences=None) -> LLMResponse:
        last_exc = None
        for client in self._all:
            try:
                return client.complete(
                    system=system, messages=messages, model=model,
                    temperature=temperature, max_tokens=max_tokens,
                    stop_sequences=stop_sequences,
                )
            except Exception as exc:
                last_exc = exc
                if not self._is_recoverable(exc):
                    raise
                emit("llm_fallback", from_provider=type(client).__name__,
                     reason=str(exc)[:160])
                continue
        raise last_exc or LLMError("all fallback providers failed")

    def complete_with_tools(self, system, messages, tools,
                             model=None, temperature=0.0,
                             max_tokens=None) -> LLMToolResponse:
        last_exc = None
        for client in self._all:
            if not getattr(client, "supports_tools", lambda: False)():
                continue
            try:
                return client.complete_with_tools(
                    system=system, messages=messages, tools=tools, model=model,
                    temperature=temperature, max_tokens=max_tokens,
                )
            except Exception as exc:
                last_exc = exc
                if not self._is_recoverable(exc):
                    raise
                emit("llm_fallback_tools", from_provider=type(client).__name__,
                     reason=str(exc)[:160])
                continue
        raise last_exc or LLMError("all fallback providers failed (tools)")


def get_llm(use_mock: bool | None = None):
    """Return an LLM client. Selection order:
    1. HIPPO_OFFLINE=1 or use_mock=True → MockLLM
    2. HIPPO_LLM_PROVIDER env → forced provider (with alias support)
    3. autodetect by available API keys / Ollama
    """
    if use_mock is True:
        return MockLLM()
    if use_mock is False:
        forced = os.environ.get("HIPPO_LLM_PROVIDER", "").strip()
        provider = _canonical(forced) if forced else _autodetect_provider()
        if provider == "mock":
            raise LLMError(
                "No LLM provider available. Set one of: "
                "ANTHROPIC_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, "
                "MOONSHOT_API_KEY, DEEPSEEK_API_KEY, DASHSCOPE_API_KEY, "
                "ZHIPU_API_KEY, BAICHUAN_API_KEY, YI_API_KEY, DOUBAO_API_KEY, "
                "GEMINI_API_KEY, MISTRAL_API_KEY, GROQ_API_KEY, XAI_API_KEY, "
                "FIREWORKS_API_KEY, TOGETHER_API_KEY, CEREBRAS_API_KEY — or "
                "run Ollama on localhost:11434."
            )
        return _build(provider)
    if os.environ.get("HIPPO_OFFLINE") == "1":
        log.warning("llm_using_mock", reason="HIPPO_OFFLINE=1")
        return MockLLM()
    forced = os.environ.get("HIPPO_LLM_PROVIDER", "").strip()
    provider = _canonical(forced) if forced else _autodetect_provider()
    if provider == "mock":
        log.warning("llm_using_mock", reason="no provider available")
    log.info("llm_provider_selected", provider=provider, forced=bool(forced))
    primary = _build(provider)

    # Wrap with fallback chain. Priority:
    #   1. user-configured `settings.fallback_providers` (explicit opt-in)
    #   2. auto-fallback to OTHER configured providers (FORGIA #45)
    #
    # Auto-fallback fires only when `HIPPO_AUTO_FALLBACK=1` is set OR the
    # user has explicitly listed providers. The defensive default OFF
    # preserves the legacy single-provider behaviour for tests / CI that
    # pin a specific provider.
    try:
        from . import settings as _us
        cur = _us.load()
        chain = []
        # Explicit user list first.
        for fp in cur.fallback_providers or []:
            cn = _canonical(fp)
            if cn == provider:
                continue
            if not is_configured(cn):
                continue
            try:
                chain.append(_build(cn))
            except Exception:
                continue
        # FORGIA #45 — auto-fallback opt-in: every other configured
        # provider gets appended in registry order (skipping primary +
        # already-listed + ollama which has its own resilience). This
        # is what saves a long-running session (e.g. sleep cycle on
        # groq free tier) from getting wedged on a 429.
        if os.environ.get("HIPPO_AUTO_FALLBACK", "").strip() == "1":
            already = {provider} | {
                _canonical(fp) for fp in (cur.fallback_providers or [])
            }
            for cand in list(PROVIDERS.keys()) + ["anthropic"]:
                if cand in already:
                    continue
                if not is_configured(cand):
                    continue
                if cand == "mock":
                    continue
                try:
                    chain.append(_build(cand))
                    already.add(cand)
                except Exception:
                    continue
        if chain:
            log.info("llm_fallback_chain", primary=provider,
                     fallbacks=[type(c).__name__ for c in chain],
                     auto=os.environ.get("HIPPO_AUTO_FALLBACK") == "1")
            return FallbackLLM(primary, chain)
    except Exception:
        pass
    return primary
