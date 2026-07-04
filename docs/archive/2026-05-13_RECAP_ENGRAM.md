# Engram — Recap Sincero (2026-05-13)

> Snapshot onesto del progetto subito dopo il rebrand (cycle #40 + sonnet
> cleanup). Risponde a 4 domande: cosa funziona davvero, cosa è ancora
> prototype, è davvero innovativo, cosa migliorare per primo.

---

## 1. Cosa funziona davvero (testato, non assertito)

| Capability | Evidenza | Cifre |
|---|---|---|
| **Hippo Dreams pipeline** (subscription-first consolidation) | 51 test TDD verdi (cycles #34-#40) + bench reale su corpus prod | propose 522ms / submit 1.8s per task / adopt 784ms / **20.8s E2E su 10 task** |
| **Compositional generalization** vs LLM raw | Bench 4-provider 96 chiamate reali | LLM raw collassa a 0% accuracy a Lv3-5; con Engram → 100% Lv5 su 3/4 provider |
| **Macro fast-path** (skill compilata bypassa LLM) | Anthropic Opus 4.7, 5 iter × 8 task | Iter 0: 4225 tok / 4.5s — Iter 3+: **0 tok / 0.22s** (-95%) |
| **Held-out generalization** | 5 task TRAIN → 5 task held-out fresh | **100%** held-out success |
| **MCP server** | 175 tool registrati, dispatch via stdio JSON-RPC | `hippo_health` verde + suite `test_mcp_server.py` |
| **Test coverage** | pytest full run + ruff + bandit | **2253 test passing** / coverage 59% / 0 errori lint |
| **Atomic rollback** | Critic-found 2 bug reali + fix TDD counterexample-driven | `_restore_live_skills` wipe-orphan + restore-from-backup |
| **Zero API extra spend** | Monkeypatch sentinel su `get_llm` in tutti i 7 tool della pipeline | `calls == 0` invariant validato |

## 2. Cosa è ancora prototype / da migliorare

| Area | Stato attuale | Gap |
|---|---|---|
| **Brand / distribution** | Rebrand README + GitHub desc fatto | PyPI distribution name resta `hippoagent`; `engram-memory` non ancora registrato |
| **Package fisico** | `hippoagent/` come dir | Rename a `engram/` non fatto: 180 file, 334 import, 297 test — PR dedicato |
| **MCP tool name** | `hippo_*` (175 tool) | Alias `engram_*` con backward-compat 3 mesi — PR dedicato |
| **Dashboard live** | Polling-based | Push sub-second su scrittura memoria (EventBus in-process) → design doc, no code |
| **Hosted cloud** | Solo local SQLite | Variante hosted (S3/Postgres backend) non esiste |
| **ReasoningBank integration** | Solo design doc citato in README | Codice non scritto |
| **Test coverage** | 59% | Target healthy 70%+; gap su `dashboard_routes/`, `tools_extra.py` paths |
| **Documentation drift** | STATE_OF_HIPPOAGENT_*, FINAL_REVIEW.md, etc. | 8 audit/recap doc scritti in date diverse — vanno consolidati o archived |
| **Sonnet eliminato** | Default opus-4-7 ovunque (post commit oggi) | OK ✓ |

## 3. È davvero innovativo? Comparison vs alternatives

| Componente | Engram | Anthropic Dreams | Google ReasoningBank (Sep 2025) | MemSkill (arXiv 2605.06614) |
|---|---|---|---|---|
| Skill consolidation loop | ✓ (NREM + REM + fitness selection) | – (no skill, è migration tool) | ✓ (extract from success+failure) | ✓ (skill = meta-procedura) |
| Immutable shadow + review + adopt | ✓ | ✓ (DB schema migrations) | – | – |
| Subscription-first (host LLM) | ✓ (cycle #34-#40, originale) | – (è infrastructure tool) | – (usa API direttamente) | – (paper, no impl) |
| Compiled-macro deterministic bypass | ✓ (skill → AST → exec, 95% lat ↓) | – | – | – |
| Lateral inhibition + engram crossover | ✓ (11 mecc. neuro-ispirati) | – | – (1 mecc.) | – |
| Open source + production hardening | ✓ (MIT, 2253 test, CI 3OS×4py) | proprietary | proprietary | paper only |
| MCP integration (Claude Code, Cursor) | ✓ (175 tool) | N/A | N/A | N/A |

**Conclusione onesta**:
- **Genuinamente originale**: subscription-first pipeline + compiled-macro bypass + 11 meccanismi neuro-ispirati opt-in. Non vedo precedenti open-source.
- **Derivato (e onesto sul fatto)**: shadow+adopt pattern mutuato da Anthropic Dreams; sleep cycle pattern condiviso con MemSkill; vector recall + SQLite storage standard.
- **Posizionamento**: Engram non compete con Anthropic Dreams (è infra tool). Compete con ReasoningBank e MemSkill su skill consolidation — ma è l'unico **open-source production-ready** del trio, con MCP integration nativa.

## 4. Cosa migliorare per primo (priorità onesta)

1. **PyPI distribution `engram-memory`** — registra il nome, pubblica wheel. Lascia `hippoagent` come alias deprecated. _Effort: 1h._
2. **MCP tool aliasing `engram_*`** — registra entrambi i nomi per 3 mesi. Riduce confusione brand → import. _Effort: 4h con test._
3. **Dashboard live push** — sub-second update via EventBus in-process quando un tool MCP scrive. Effetto wow visivo. _Effort: 1-2 cicli (skill design, FastAPI SSE)._
4. **Package fisico rename** `hippoagent/` → `engram/` — 334 import via sed + test full. Breaking per chi importa Python direttamente, ma con shim alias gestibile. _Effort: 1 ciclo dedicato._
5. **Doc consolidation** — fondere 8 audit/recap doc in 1 unico `STATE.md` aggiornato. Eliminare drift. _Effort: 1h._
6. **Test coverage 59% → 70%** — focus su `dashboard_routes/` e `tools_extra.py`. _Effort: 2-3 cicli TDD._
7. **Hosted variant** (long-term) — backend pluggable Postgres + S3 per skill bodies. Permette deploy cloud-first per team. _Effort: progetto a sé._

## 5. Verdict

Engram è un **prototype maturo con asset reali**: pipeline funzionante,
benchmark reali ripetibili, test discipline TDD+critic, 175 tool MCP
production-ready. La parte di consolidation subscription-first è il
contributo originale più chiaro. Il debito tecnico principale è la
**coerenza brand-vs-codebase** (Engram nel README, `hippoagent` nel
package) e la **distribution PyPI** non ancora effettuata.

**Non è ancora un prodotto pubblicato** — è un repo pubblico
production-grade, in attesa di un release event coordinato (PyPI + tag +
annuncio). I prossimi 2-3 cicli dovrebbero chiudere il rebrand fisico e
arrivare a `pip install engram-memory` funzionante.

---

_Doc autogenerato dopo cycle #40 + sonnet cleanup + rebrand brand-first.
Sostituisce le note "innovativo?" sparse nei vari audit. Da tenere
aggiornato a fine di ogni macro-cycle._
