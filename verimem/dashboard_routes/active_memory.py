"""/active-memory + /api/active-memory/stats — KPIs for the 5 active-memory mechanisms."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .layout import get_agent, html_escape, page


def _kpi(label: str, value: int | str, hint: str, color: str) -> str:
    return (
        f"<div class='am-kpi-card' style='--am-color:{color};'>"
        f"<div class='am-kpi-label'>{label}</div>"
        f"<div class='am-kpi-value'>{value}</div>"
        f"<div class='am-kpi-hint'>{hint}</div>"
        f"</div>"
    )


def register(app: FastAPI, templates: Jinja2Templates) -> None:  # noqa: ARG001
    @app.get("/active-memory", response_class=HTMLResponse)
    def active_memory_page() -> HTMLResponse:
        a = get_agent()
        skills = a.skills.all()
        n_total = len(skills)
        promoted = [s for s in skills if s.status == "promoted"]
        compiled = [s for s in skills if s.compiled_macro]
        counterfactuals = [s for s in skills if s.is_counterfactual]
        hebbian = [s for s in skills if s.learned_embedding is not None]
        schemas = [s for s in skills if s.stage == "schema"]

        coverage = (
            f"{int(100 * len(compiled) / max(1, len(promoted)))}%"
            if promoted else "—"
        )
        avg_conf = (
            sum(s.compiled_macro.get("confidence", 0.0) for s in compiled)
            / max(1, len(compiled))
        ) if compiled else 0.0

        kpis = (
            _kpi("🔧 Compiled macros",
                  len(compiled),
                  f"avg conf {avg_conf:.2f} · coverage {coverage} of promoted",
                  "#1f6feb")
            + _kpi("⚡ Hebbian-tuned",
                    len(hebbian),
                    "trigger embeddings drifted toward solved tasks",
                    "#3fb950")
            + _kpi("🌀 Counterfactuals",
                    len(counterfactuals),
                    "alternatives generated from failing skills",
                    "#a371f7")
            + _kpi("🌳 Schemas",
                    len(schemas),
                    "meta-skills above clusters of specifics",
                    "#d29922")
        )

        rows_macros: list[str] = []
        for s in sorted(compiled, key=lambda x: -x.fitness_mean)[:15]:
            cm = s.compiled_macro or {}
            steps = cm.get("steps") or []
            conf = cm.get("confidence", 0.0)
            rows_macros.append(
                f"<tr>"
                f"<td><a href='/skills/{s.id}'>{s.id[:8]}</a></td>"
                f"<td>{html_escape(s.name)}</td>"
                f"<td>{len(steps)}</td>"
                f"<td>{conf:.2f}</td>"
                f"<td>{s.fitness_mean:.2f}</td>"
                f"<td>{s.successes}/{s.trials}</td>"
                f"</tr>"
            )
        macros_table = (
            "<table><tr><th>id</th><th>name</th><th>steps</th>"
            "<th>macro conf</th><th>fitness</th><th>s/t</th></tr>"
            + ("".join(rows_macros) or
                "<tr><td colspan='6' style='color:var(--dim);'>"
                "No compiled macros yet — let the library accumulate "
                "≥5 successes per skill, then run sleep.</td></tr>")
            + "</table>"
        )

        cf_rows: list[str] = []
        for s in counterfactuals[:10]:
            parent = s.parent_skills[0] if s.parent_skills else "—"
            parent_link = (f"<a href='/skills/{parent}'>{parent[:8]}</a>"
                            if parent != "—" else parent)
            cf_rows.append(
                f"<tr>"
                f"<td><a href='/skills/{s.id}'>{s.id[:8]}</a></td>"
                f"<td>{html_escape(s.name)}</td>"
                f"<td>{parent_link}</td>"
                f"<td>{s.fitness_mean:.2f} ({s.successes}/{s.trials})</td>"
                f"</tr>"
            )
        cf_table = (
            "<table><tr><th>cf skill</th><th>name</th>"
            "<th>parent</th><th>fitness</th></tr>"
            + ("".join(cf_rows) or
                "<tr><td colspan='4' style='color:var(--dim);'>"
                "No counterfactuals yet — they only appear when a skill has "
                "≥3 trials and fitness ≤ 0.5.</td></tr>")
            + "</table>"
        )

        g = a.skills.lineage_graph()
        schema_blocks: list[str] = []
        for sch in schemas[:5]:
            children = []
            for _u, v in g.out_edges(sch.id):
                rel = g.edges[sch.id, v].get("relation")
                if rel == "specialises":
                    child = a.skills.get(v)
                    if child:
                        children.append(child)
            children_html = "".join(
                f"<li><a href='/skills/{c.id}'>{html_escape(c.name)}</a> "
                f"<span style='color:var(--dim);'>"
                f"(fitness {c.fitness_mean:.2f})</span></li>"
                for c in children[:8]
            ) or "<li style='color:var(--dim);'>(no children resolved)</li>"
            schema_blocks.append(
                f"<div style='border-left:3px solid #d29922;padding:8px 14px;"
                f"margin:8px 0;background:#0a0d12;border-radius:4px;'>"
                f"<a href='/skills/{sch.id}' "
                f"style='font-weight:600;'>{html_escape(sch.name)}</a>"
                f"<div style='color:var(--dim);font-size:12px;margin:2px 0;'>"
                f"{html_escape(sch.trigger)}</div>"
                f"<ul style='margin:4px 0 0 16px;font-size:13px;'>{children_html}</ul>"
                f"</div>"
            )
        schemas_html = ("".join(schema_blocks) or
                         "<p style='color:var(--dim);'>No schemas yet — "
                         "they emerge when ≥3 skills share a domain.</p>")

        body = f"""
        <h1>Active memory <span style='font-size:14px;color:var(--dim);
            font-weight:400;'>— five mechanisms that make the library grow</span></h1>
        <div style='display:flex;gap:12px;margin:16px 0;'>{kpis}</div>

        <div class="card">
          <h3>🔧 Compiled macros</h3>
          <p style="color:var(--dim);font-size:13px;margin:0 0 12px 0;">
            These skills bypass the LLM at wake time when the task strongly
            matches their trigger. Distilled by the dreamer during sleep from
            accumulated successful trajectories.</p>
          {macros_table}
        </div>

        <div class="card">
          <h3>🌀 Counterfactual lineage</h3>
          <p style="color:var(--dim);font-size:13px;margin:0 0 12px 0;">
            Alternative strategies the dreamer proposed for skills that kept
            failing. They compete against their parent for retrieval; if the
            alternative wins, the parent gets retired by the usual fitness path.</p>
          {cf_table}
        </div>

        <div class="card">
          <h3>🌳 Schema hierarchy</h3>
          <p style="color:var(--dim);font-size:13px;margin:0 0 12px 0;">
            Skills sharing a domain are clustered into a SCHEMA — a meta-skill
            that picks among its children. The lineage graph shows
            <code>specialises</code> edges from each schema to its members.</p>
          {schemas_html}
        </div>

        <div class="card">
          <h3>⚡ Hebbian tuning &nbsp; <span style='color:var(--dim);font-size:12px;'>
            (drift on success)</span></h3>
          <p style="color:var(--dim);font-size:13px;margin:0;">
            Each successful application drifts the skill's trigger embedding
            toward the task that just succeeded. Skills become magnets for the
            kind of work they keep solving — without retraining anything.<br>
            <b>Total tuned skills:</b> {len(hebbian)} of {n_total}.
          </p>
        </div>

        <div class="card">
          <h3>📡 Forward replay</h3>
          <p style="color:var(--dim);font-size:13px;margin:0;">
            Pure-retrieval mechanism: before the wake loop runs, the agent
            projects the action sequence from past successful episodes that used
            the top-retrieved skill, and injects it as a <code>## PREDICTED PATH</code>
            block in the user prompt. Watch the live event stream
            (<a href='/events'>/events</a>) for <code>forward_replay</code> events.
          </p>
        </div>
        """
        return page("Active memory", body)

    @app.get("/api/active-memory/stats")
    def active_memory_stats() -> JSONResponse:
        a = get_agent()
        skills = a.skills.all()
        n_total = len(skills)
        n_compiled = sum(1 for s in skills if s.compiled_macro)
        n_counterfactual = sum(1 for s in skills if s.is_counterfactual)
        n_hebbian = sum(1 for s in skills if s.learned_embedding is not None)
        n_promoted = sum(1 for s in skills if s.status == "promoted")
        n_retired = sum(1 for s in skills if s.status == "retired")

        confs: list[float] = []
        step_counts: list[int] = []
        for s in skills:
            if s.compiled_macro:
                confs.append(float(s.compiled_macro.get("confidence", 0.0)))
                step_counts.append(len(s.compiled_macro.get("steps") or []))
        avg_macro_conf = sum(confs) / len(confs) if confs else 0.0
        avg_macro_steps = sum(step_counts) / len(step_counts) if step_counts else 0.0

        return JSONResponse({
            "skills_total": n_total,
            "promoted": n_promoted,
            "retired": n_retired,
            "compiled_macros": n_compiled,
            "counterfactuals": n_counterfactual,
            "hebbian_tuned": n_hebbian,
            "macro_avg_confidence": round(avg_macro_conf, 3),
            "macro_avg_steps": round(avg_macro_steps, 2),
            "compilation_coverage": (
                round(n_compiled / n_promoted, 3) if n_promoted else 0.0
            ),
        })
