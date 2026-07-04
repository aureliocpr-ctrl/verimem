"""/chat, /api/chat, /api/plan, /api/sleep, /api/feedback — chat-loop UI + actions."""
from __future__ import annotations

import time

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from ..observability import emit, get_log
from .auth import verify_session_token
from .layout import get_agent

log = get_log()


def _safe_error(exc: Exception, where: str) -> str:
    """FORGIA #189 — sanitize exception messages for HTTP responses.

    CodeQL `py/stack-trace-exposure` flags `str(exc)` returned in JSON
    bodies because exception text can leak filesystem paths, query
    contents, or stack frames. We log the full exception server-side
    and return only a stable error code to the client.
    """
    log.exception("api_error", where=where, exc_type=type(exc).__name__)
    return f"{where}: {type(exc).__name__}"

_PLAN_SYSTEM = """You are HippoAgent in PLAN mode. Do NOT execute the task.
Instead, output a numbered plan (3 to 7 steps) of what you would do, including
which tools you'd use and in what order. Be concrete and specific.
Format: just numbered steps, one per line, no preamble or trailing text."""


class ChatRequest(BaseModel):
    task: str


class FeedbackRequest(BaseModel):
    episode_id: str
    kind: str  # "up" | "down"


def register(app: FastAPI, templates: Jinja2Templates) -> None:
    @app.get("/chat", response_class=HTMLResponse)
    def chat_page(request: Request):
        return templates.TemplateResponse(
            request, "chat.html", {"page_title": "Chat"},
        )

    @app.post("/api/chat", dependencies=[Depends(verify_session_token)])
    def chat_api(req: ChatRequest) -> JSONResponse:
        if not req.task or not req.task.strip():
            return JSONResponse({"error": "empty task"}, status_code=400)
        a = get_agent()
        task_id = f"chat-{int(time.time())}"
        try:
            result = a.run_task(
                task_id=task_id,
                task_text=req.task.strip(),
                validator=lambda ans: (bool(ans and ans.strip()), "non-empty"),
            )
        except Exception as exc:
            return JSONResponse({"error": _safe_error(exc, "chat")},
                                 status_code=500)
        skills = [
            {"id": s.id, "name": s.name, "fitness": s.fitness_mean, "stage": s.stage}
            for s in result.skills_retrieved
        ]
        return JSONResponse({
            "episode_id": result.episode.id,
            "outcome": result.episode.outcome,
            "answer": result.episode.final_answer,
            "steps": result.episode.num_steps,
            "tokens": result.episode.tokens_used,
            "skills_used": skills,
            "message": result.message,
        })

    @app.post("/api/plan", dependencies=[Depends(verify_session_token)])
    def plan_api(req: ChatRequest) -> JSONResponse:
        if not req.task or not req.task.strip():
            return JSONResponse({"error": "empty task"}, status_code=400)
        try:
            from ..llm import get_llm, resolve_model
            llm = get_llm()
            resp = llm.complete(
                system=_PLAN_SYSTEM,
                messages=[{"role": "user", "content": "TASK: " + req.task.strip()}],
                temperature=0.2,
                max_tokens=600,
                model=resolve_model("executor"),
            )
            return JSONResponse({
                "plan": resp.text,
                "tokens": resp.input_tokens + resp.output_tokens,
                "model": resp.model,
            })
        except Exception as exc:
            return JSONResponse({"error": _safe_error(exc, "plan")},
                                 status_code=500)

    @app.post("/api/sleep", dependencies=[Depends(verify_session_token)])
    def sleep_api() -> JSONResponse:
        a = get_agent()
        try:
            report = a.consolidate()
        except Exception as exc:
            return JSONResponse({"error": _safe_error(exc, "sleep")},
                                 status_code=500)
        return JSONResponse({
            "n_episodes_replayed": report.n_episodes_replayed,
            "n_clusters": report.n_clusters,
            "n_nrem_skills": report.n_nrem_skills,
            "n_rem_skills": report.n_rem_skills,
            "n_facts": report.n_facts,
            "promoted": report.promoted,
            "retired": report.retired,
            "merged": [{"a": a_, "b": b_, "merged": m_} for a_, b_, m_ in report.merged],
            "duration_s": report.duration_s,
            "tokens_used": report.tokens_used,
        })

    @app.post("/api/feedback", dependencies=[Depends(verify_session_token)])
    def feedback_api(req: FeedbackRequest) -> JSONResponse:
        """Apply user feedback (up/down) on a chat turn to skill fitness."""
        if req.kind not in ("up", "down"):
            return JSONResponse({"error": "kind must be 'up' or 'down'"}, status_code=400)
        a = get_agent()
        ep = a.memory.get(req.episode_id)
        if ep is None:
            return JSONResponse({"error": "episode not found"}, status_code=404)
        success = req.kind == "up"
        tag = f"[user-feedback:{req.kind}]"
        if tag not in ep.notes:
            ep.notes = (ep.notes + " " + tag).strip()
        if not success and ep.outcome == "success":
            ep.outcome = "failure"
        a.memory.store(ep)
        # CYCLE #17 fix (analogo a #16 critic counterexample): dedup
        # skills_used PRIMA del loop. Se ep.skills_used contiene
        # duplicati (es. stessa skill citata in più step ReAct),
        # update_fitness verrebbe chiamato N volte sullo stesso skill
        # gonfiando trials/successes e corrompendo Hebbian lerp.
        unique_skills = list(dict.fromkeys(ep.skills_used))
        for sid in unique_skills:
            a.skills.update_fitness(
                sid, success=success, tokens=0, task_text=ep.task_text,
            )
        emit("user_feedback", episode_id=ep.id, kind=req.kind,
             n_skills=len(unique_skills))
        return JSONResponse({
            "ok": True,
            "episode_id": ep.id,
            "kind": req.kind,
            "skills_updated": len(unique_skills),
        })
