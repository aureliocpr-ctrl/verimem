# Spec P2.c — OpenIE LLM-based Entity & Triple Extraction

> Stato: paper-first, ≤300 parole core. Build on P2.a (commit 12fa4ff)
> + P2.b (commit 1453480). Pattern HippoRAG 2-step (NER → triple) ma
> SENZA parser eseguibile su output LLM — `json.loads` strict only.
> Riferimento: openie_openai.py HippoRAG usa un anti-pattern di parser
> code-execution; noi NON lo replichiamo.

## Obiettivo

P2.a + P2.b espongono il KG entity-centric (nodes + edges + PPR) ma la
popolazione è manuale (`hippo_entity_link`). P2.c automatizza con un
tool LLM-based che estrae da testo libero:
- entity names (Capitalized + alias + type guess)
- triple (subject, predicate, object) → diventa edge entity_edges

Hook integrabile in `hippo_record_episode`: se l'episode `task_text +
final_answer` supera 500 char di ricchezza testuale, opt-in chiama
`hippo_extract_entities` e auto-popola il KG con `source_fact_id`
tracking.

## API MCP (1 tool, LLM OPT-IN — costo+latenza)

`hippo_extract_entities(text: str, mode: "ner_only" | "ner+triple",
existing_entities: list[str] = []) → {entities: [{name, type,
aliases?}], triples: [{subject, predicate, object,
confidence}]}`.

`existing_entities` permette dedup pre-LLM-call: l'LLM riceve la lista
e usa canonical name esistente invece di crearne nuovi.

## Pipeline (2-step strict)

1. **Step 1 NER**: prompt JSON-only output (`{"entities": [...]}`),
   `temperature=0.0`, `response_format={"type": "json_object"}`. Output
   parsed via `json.loads` strict. Su ValueError → retry once con prompt
   "fix the JSON syntax", su secondo fail → return empty. **MAI parser
   code-execution sul testo LLM**.
2. **Step 2 Triple**: solo se `mode="ner+triple"`. Prompt secondario
   con entities dello step 1 + testo. Output `{"triples": [{subject,
   predicate, object, confidence}]}`. Stesso json.loads strict + retry.

## Test plan (5 RED minimi)

1. RED — `_parse_ner_response` strict json.loads: malformed → `[]`,
   valid → list.
2. RED — `_parse_triple_response` valida subject/object ∈ entities
   estratte (drop triples con entity sconosciuta).
3. RED — `hippo_extract_entities(text, mode="ner_only")` fake LLM
   ritorna 2 entity → tool ritorna 2 entity con type.
4. RED — `hippo_extract_entities(text, mode="ner+triple")` fake LLM
   ritorna 2 entity + 1 triple → tool ritorna entrambi.
5. RED — `existing_entities` deduplica: alias risolto a canonical
   esistente, nessuna nuova entity creata.

## Non-goals (P2.c)

- NON popolazione automatica retroactive (script seed separato P2.c-bis).
- NON multi-turn extraction (>1 LLM call per episodio).
- NON Italian-native NER (gazetteer P4 opzionale).
- NON skill .md (P2.d-bis per ergonomia post-merge).

## Critic gate

Round con critic-orchestrator v0.3.0 (commit 03ed212, debiased).
Particolare attenzione a: fake LLM faithful (no token-overlap shortcut
come cycle #70 round 1 P1), prompt injection (testo malizioso che
fa output non-JSON), idempotency (`extract` su testo identico due
volte → stessi risultati).
