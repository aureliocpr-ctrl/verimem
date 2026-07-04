# Spec P1 — `hippo_validate_claim` (anti-confabulazione)

> Stato: paper-first, ≤300 parole core spec. NO codice ancora.
> Cycle target: il prossimo (post-compact).
> Origine: pattern di confabulazione pescato live in sessione 2026-05-14
> sera (Tonegawa Nobel 1987→2014, Anthropic Skills 2025→2026,
> LightRAG HKUDS→HKUST, attribuzione Sonnet 4.6→me).

## Obiettivo

Dare a Engram un tool MCP che, data una **claim verificabile** (es. "X è
nato nel 1987", "Y ha detto Z"), risponda con verdict + evidenza
cercata in memoria. Pensato per essere chiamato **prima** che Claude
risponda con un fatto, riducendo confabulazione.

## API proposta

```
hippo_validate_claim(claim: str, topic_hint: str | None = None,
                    threshold: float = 0.6)
  → { verdict, confidence, evidence_facts, evidence_episodes, advice }
```

- `verdict` ∈ {`"supported"`, `"contradicted"`, `"unknown"`}.
- `evidence_facts`: lista di fact_id che supportano/contraddicono.
- `evidence_episodes`: episode_id correlati.
- `advice`: stringa breve in italiano per Claude (es. "in memoria
  Tonegawa Nobel 1987 immunologia, NON 2014 engram — controlla prima
  di affermare").

## Meccanica (3 step, no LLM call propria)

1. **Semantic search** su `facts` via embedding daemon (già esistente).
2. **Keyword search** sui top-k risultati per match esatto sui termini
   salienti della claim (NER super-light: estrai nomi capitalized + anni).
3. **Contradiction detection**: se due fact con stesso soggetto+predicato
   ma oggetto diverso ⇒ `contradicted`. Se match positivo robust ⇒
   `supported`. Altrimenti `unknown`.

Costo: zero LLM call. Sub-100ms su corpus attuale (473 facts).

## Integrazione

- Tool MCP standalone (`hippo_validate_claim`).
- Skill `.md` che insegna a Claude quando invocarlo
  (claim factual con anno/numero/attribuzione).
- Eventuale hook UserPromptSubmit per validare claim Aurelio (P1.b
  opzionale, low priority).

## Test plan TDD

- RED: test su corpus fixture con claim contraddetta → atteso
  `contradicted` + evidence non vuota.
- RED: test claim supportata → `supported`.
- RED: test claim unknown (corpus vuoto su quel topic) → `unknown`.
- RED: test threshold (claim borderline) → respect parametro.

## Non-goals (P1)

- NON estrae nuovi fatti dalla claim.
- NON modifica memoria.
- NON LLM call (deterministic, leggero).
- NON multi-hop reasoning (P2 farà quello via PPR).

## Successivi

P1 sblocca pattern hook + tool MCP che riuserò in P2 (entity-centric KG)
e P3 (self_model multi-anchor). È il primo gradino concreto, non
isolato.
