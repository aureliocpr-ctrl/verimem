"""/skills (Jinja2 design-system page) + /skills/{id} detail + promote/retire actions."""
from __future__ import annotations

import json

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .auth import verify_session_token
from .layout import get_agent, html_escape, page


def register(app: FastAPI, templates: Jinja2Templates) -> None:
    @app.get("/skills", response_class=HTMLResponse)
    def skills_page(request: Request):
        """New design-system skills page (Jinja2 template + dashboard.css)."""
        a = get_agent()
        all_skills = sorted(a.skills.all(), key=lambda s: -s.fitness_mean)
        kpi = {
            "total": len(all_skills),
            "promoted": sum(1 for s in all_skills if s.status == "promoted"),
            "candidate": sum(1 for s in all_skills if s.status == "candidate"),
            "compiled": sum(1 for s in all_skills if s.compiled_macro),
            "counterfactual": sum(1 for s in all_skills if s.is_counterfactual),
        }
        return templates.TemplateResponse(
            request,
            "skills.html",
            {
                "page_title": "Skills",
                "skills": all_skills,
                "kpi": kpi,
            },
        )

    @app.get("/skills/{skill_id}", response_class=HTMLResponse)
    def skill_detail(skill_id: str) -> HTMLResponse:
        a = get_agent()
        s = a.skills.get(skill_id)
        if not s:
            for cand in a.skills.all():
                if cand.id.startswith(skill_id):
                    s = cand
                    break
        if not s:
            return page("Not found", "<h1>Not found</h1>")
        parents = " ".join(
            f"<a class='tag' href='/skills/{p}'>{p[:8]}</a>" for p in s.parent_skills
        )
        eps = " ".join(
            f"<a class='tag' href='/episodes/{e}'>{e[:8]}</a>"
            for e in s.provenance_episodes[:20]
        )

        detail_badges = []
        if s.compiled_macro:
            detail_badges.append(
                "<span class='tag' style='background:#1f6feb;color:#fff;'>🔧 compiled</span>"
            )
        if s.is_counterfactual:
            detail_badges.append(
                "<span class='tag' style='background:#a371f7;color:#fff;'>🌀 counterfactual</span>"
            )
        if s.learned_embedding is not None:
            detail_badges.append(
                "<span class='tag' style='background:#3fb950;color:#0e1116;'>⚡ Hebbian-tuned</span>"
            )
        badges_html = " ".join(detail_badges)

        macro_block = ""
        if s.compiled_macro:
            steps = s.compiled_macro.get("steps") or []
            conf = s.compiled_macro.get("confidence", 0.0)
            from_eps = s.compiled_macro.get("derived_from_episodes") or []
            steps_rendered = []
            for st in steps:
                args_json = html_escape(json.dumps(st.get("args") or {}, indent=2))
                steps_rendered.append(
                    f"<li><code>{html_escape(str(st.get('tool', '')))}</code>"
                    f"<pre style='margin:4px 0 8px 0;font-size:12px;'>{args_json}</pre></li>"
                )
            macro_block = f"""
            <div class="card" style="border-left:3px solid #1f6feb;">
              <h3>🔧 Compiled macro</h3>
              <p style="color:var(--dim);">When this skill matches a task strongly,
                 the macro below is executed deterministically — <b>zero LLM
                 tokens</b>, no model latency between steps. On any error the
                 agent falls back to the regular ReAct loop.</p>
              <p><b>Confidence:</b> {conf:.2f} &nbsp;
                 <b>Steps:</b> {len(steps)} &nbsp;
                 <b>Distilled from:</b> {len(from_eps)} successful episodes</p>
              <ol>{''.join(steps_rendered)}</ol>
            </div>
            """

        cf_block = ""
        if s.is_counterfactual and s.parent_skills:
            parent_id = s.parent_skills[0]
            cf_block = f"""
            <div class="card" style="border-left:3px solid #a371f7;">
              <h3>🌀 Counterfactual lineage</h3>
              <p>Generated as an alternative to a failing skill:
                 <a class='tag' href='/skills/{parent_id}'>{parent_id[:8]}</a>.
                 This skill competes with the parent for retrieval; if it
                 outperforms, the parent will eventually be retired.</p>
            </div>
            """

        practice_block = ""
        if s.practice_prompts:
            prompt_items = []
            for p in s.practice_prompts:
                esc = html_escape(p)
                prompt_items.append(
                    f"<li style='margin:6px 0;'>"
                    f"<span style='display:inline-block;max-width:80%;"
                    f"vertical-align:middle;'>{esc}</span> "
                    f"<button onclick=\"location.href='/chat?prefill=' + "
                    f"encodeURIComponent({json.dumps(p)})\" "
                    f"style='margin-left:8px;background:#1f6feb;color:#fff;"
                    f"border:0;padding:4px 10px;border-radius:4px;cursor:pointer;'>"
                    f"▶ run in chat</button></li>"
                )
            practice_block = f"""
            <div class="card" style="border-left:3px solid #58a6ff;">
              <h3>📚 Practice prompts <span style='color:var(--dim);font-size:12px;
                  font-weight:400;'>(dreamer-suggested)</span></h3>
              <p style='color:var(--dim);font-size:13px;margin:0 0 8px 0;'>
                This skill's fitness is in the uncertain zone (≈
                {s.fitness_mean:.2f}). The dreamer wrote concrete tasks the agent
                could try — running them feeds real evidence into the Bayesian
                fitness so the skill is either promoted or retired.</p>
              <ul style='list-style:none;padding-left:0;margin:0;'>{''.join(prompt_items)}</ul>
            </div>
            """

        body = f"""
        <h1>Skill: {html_escape(s.name)} {badges_html}</h1>
        <div class="card">
          <p><b>Stage:</b> {s.stage} &nbsp; <b>Status:</b>
             <span class='{s.status}'>{s.status}</span> &nbsp;
             <b>Fitness:</b> {s.fitness_mean:.2f} ({s.successes}/{s.trials})</p>
          <p><b>Trigger:</b> {html_escape(s.trigger)}</p>
          <p><b>Body:</b></p><pre>{html_escape(s.body)}</pre>
          <p><b>Rationale:</b> {html_escape(s.rationale)}</p>
          <p><b>Parent skills:</b> {parents or '<span class=tag>none (root)</span>'}</p>
          <p><b>Provenance episodes:</b> {eps or '<span class=tag>none</span>'}</p>
          <div style="margin-top:16px;display:flex;gap:8px;align-items:center;">
            <button onclick="if(confirm('Promote this skill?')) fetch('/api/skills/{s.id}/promote',
              {{method:'POST'}}).then(()=>location.reload());" style="background:var(--ok);
              color:#0e1116;border:0;padding:8px 14px;border-radius:4px;cursor:pointer;">
              ✓ Promote</button>
            <button onclick="if(confirm('Retire (archive) this skill?')) fetch('/api/skills/{s.id}/retire',
              {{method:'POST'}}).then(()=>location.reload());" style="background:var(--bad);
              color:white;border:0;padding:8px 14px;border-radius:4px;cursor:pointer;">
              ✗ Retire</button>
            <a href="/skills" style="margin-left:auto;color:var(--dim);">← back to skills</a>
          </div>
        </div>
        {macro_block}
        {cf_block}
        {practice_block}
        """
        return page(f"Skill {s.id[:8]}", body)

    @app.post("/api/skills/{skill_id}/retire",
              dependencies=[Depends(verify_session_token)])
    def skill_retire(skill_id: str) -> JSONResponse:
        a = get_agent()
        s = a.skills.get(skill_id)
        if not s:
            for cand in a.skills.all():
                if cand.id.startswith(skill_id):
                    s = cand
                    break
        if not s:
            return JSONResponse({"error": "skill not found"}, status_code=404)
        s.status = "retired"
        a.skills.store(s)
        return JSONResponse({"ok": True, "id": s.id, "status": "retired"})

    @app.post("/api/skills/{skill_id}/promote",
              dependencies=[Depends(verify_session_token)])
    def skill_promote(skill_id: str) -> JSONResponse:
        a = get_agent()
        s = a.skills.get(skill_id)
        if not s:
            for cand in a.skills.all():
                if cand.id.startswith(skill_id):
                    s = cand
                    break
        if not s:
            return JSONResponse({"error": "skill not found"}, status_code=404)
        s.status = "promoted"
        a.skills.store(s)
        return JSONResponse({"ok": True, "id": s.id, "status": "promoted"})
