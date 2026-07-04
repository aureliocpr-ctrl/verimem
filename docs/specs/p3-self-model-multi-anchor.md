# Spec P3 — Self-Model Multi-Anchor with Temporal-Weighted PPR

> Stato: paper-first exploration, ≤300 parole core. Build on
> cycle #67 (self_model continuity layer commit `a7e92d4`) + cycle #70
> P2.a/b (entity-centric KG + PPR retrieval).
>
> **Origine**: pattern PPR di P2.b è generalizzabile al concetto di
> "anchor identity" — riusare lo stesso algoritmo deterministico
> per recall conversazionale entity-first ANCHE sul self-model.
> Lesson cycle #67: "continuity layer != agency. La differenza
> qualitativa tra fact/episode (cosine-retrieved, may not appear)
> e self_model (always-injected) è agency continua."

## Obiettivo

P0 (cycle #67) ha implementato `self_model` come single-row JSON.
Limitazione attuale: 4KB hard cap → context-frugal ma rigido,
nessuna struttura granulare per "cosa è importante ora vs era
importante 1 settimana fa". Non c'è decay temporale né recall
modulato per anchor (focus, goal, project, identity-trait).

P3 estende `self_model` a **multi-anchor**: ogni anchor è
una `entity` (riusa P2.a `entities` table) con `type="anchor"` +
attrs JSON (label, payload, half-life). PPR su query_entities =
anchor_ids correnti → ranked entities + facts che importano ORA.

## Schema delta (additivo, migration v6 entity_kg)

```
entity_attrs (entity_id FK, key TEXT, value_json TEXT,
              created_at REAL, PK (entity_id, key))
  -- generico key-value store per arricchire entity senza alterare
  -- la tabella entities (forward-compat con P4 metadata).

-- Implicito: anchor entity = row in entities con type='anchor' +
-- entity_attrs row con key='half_life_days' value_json=float.
```

`engram/self_model.py` aggiunge `current_anchors() -> list[str]`
(ritorna anchor_ids con weight > threshold dopo decay temporale
`exp(-Δt/τ)`).

## API MCP proposte (2 tool, no LLM happy path)

- `hippo_anchor_set(name, type, half_life_days=7.0, payload={}) →
  {entity_id}`: crea o aggiorna anchor entity con decay metadata.
- `hippo_anchor_recall(damping=0.5, k=20) → {anchors[],
  ranked_entities[], facts[]}`: PPR su anchor correnti decay-pesati.

## Test plan (4 RED minimi)

1. RED — `anchor_set` crea entity type='anchor' + entity_attrs.
2. RED — `anchor_recall` ritorna ranked dove peso anchor entra in
   PPR personalization.
3. RED — decay temporale: anchor con `created_at` 30 giorni fa +
   `half_life=7` ha peso < 0.05.
4. RED — sessions start hook chiama `current_anchors()` e include
   nel context (replace heuristic single-row).

## Non-goals (P3)

- NON migrazione automatica dal self_model single-row v0 al
  multi-anchor (script seed separato).
- NON LLM-based anchor extraction (P3-bis opt-in).
- NON multi-user / multi-agent shared anchors (out of scope cycle #70).
- NON breaking `self_model_current` / `self_model_audit` table
  (rimangono come legacy / append-only audit).

## Critic gate plan

Round adversariale con critic v0.3.0 prima del commit. Particolare
attenzione: (a) interazione decay function vs PPR personalization
weight (entrambi modificano "importanza" — rischio doppio conteggio);
(b) idempotency `anchor_set` su update; (c) backward-compat con
SessionStart hook esistente (cycle #67).
