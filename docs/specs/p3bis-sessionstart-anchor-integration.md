# Spec P3-bis — SessionStart Integration via Anchor Recall

> Stato: paper-first, ≤300 parole. Build on P3 minimal (commit
> `b127687`) + cycle #67 self_model continuity layer.
>
> **Obiettivo**: il SessionStart hook attuale (cycle #67) inietta un
> blob JSON statico `self_model_current.content_json` (≤4 KB). P3-bis
> sostituisce il blob con un **anchor recall live**, costruito al volo
> da `hippo_anchor_recall` decay-pesato. Vantaggi: (a) granularità —
> ogni anchor è un nodo distinto; (b) recency adattiva — decay
> esponenziale fa scendere automaticamente focus vecchi; (c) recall
> cross-anchor via PPR (un anchor "pulla" entity correlate via edges).

## Modifiche proposte

1. **`engram/self_model.py`**: aggiungi `render_anchor_block(store,
   max_bytes=4096) -> str` che chiama `anchor_recall` + format Markdown
   ≤4 KB (`name`, `weight`, `payload.label`, top-3 facts per anchor).
2. **`engram/hooks/session_start.py`** (cycle #67): sostituisce
   `content_json` con `render_anchor_block(agent.entity_kg)` se il KG
   contiene almeno N anchor (default N=1). Backward-compat: fallback al
   blob legacy se KG vuoto.
3. **No schema changes**: tutto è already in `entity_attrs` + `entity_edges`.

## API addendum

- `hippo_self_model_render(max_bytes=4096) → {markdown, n_anchors,
  truncated}`: tool MCP che ritorna il blocco SessionStart-ready.

## Test plan (4 RED minimi)

1. RED — `render_anchor_block` su KG con 3 anchor decay-pesati →
   markdown contiene 3 sezioni in ordine weight desc, top-3 fact per
   anchor.
2. RED — `max_bytes=512` con 10 anchor → output troncato a ≤512 byte,
   campo `truncated=True`.
3. RED — KG vuoto (0 anchor) → markdown vuoto, fallback legacy
   triggerato (no exception).
4. RED — tool MCP `hippo_self_model_render` listed + dispatchato.

## Non-goals (P3-bis)

- NON modifica `self_model_current` / `self_model_audit` legacy table
  (rimangono per audit history pre-P3-bis).
- NON migration automatica del `content_json` blob esistente alle
  anchor entity (script seed separato P3-bis-migr).
- NON real-time decay refresh (cache 5 min, refresh on demand).

## Critic gate plan

Round critic v0.3.0. Attenzione a: (a) byte counting Unicode-correct
(`len(markdown.encode('utf-8'))` non `len(markdown)`); (b) determinismo
ordering anchor (tie-break su weight + entity_id asc, riusa pattern
P2.b); (c) backward-compat hook in assenza di `entity_kg` field
sull'agent (gestione `getattr(a, "entity_kg", None) is None`).

## Performance baseline (bench turno 5)

`anchor_recall` su 5 anchor + 55 entity + 100 edge:
p50=60ms, p95=86ms, p99=512ms (cold-start). Bocciato uso al boot
ogni session se p99 troppo alto → mitigazione: cache LRU 5-min su
`render_anchor_block`, invalidata da `anchor_set`/`anchor_recall`
con write. Future optimization, NON in P3-bis core.
