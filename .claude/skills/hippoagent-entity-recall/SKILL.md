---
name: hippoagent-entity-recall
description: >-
  When the user asks "cosa ricordi di X?", "dammi tutto su Y", "chi è Z?",
  "cosa abbiamo detto di W?", "ricostruisci ciò che sai di
  [Capitalized name or known alias]", call hippo_entity_get(name) BEFORE
  answering. Triggers also on "what do you know about X", "tell me about Y",
  "facts about Z", "history of W". The tool returns entity+aliases+facts
  from a persistent SQLite KG (P2.a entity-centric KG, schema v4,
  Unicode-safe). Lookup is case-insensitive Unicode (Müller/MÜLLER/müller
  same match) and resolves aliases ("S. Tonegawa" → canonical "Tonegawa"),
  returning the list of fact_id linked to the entity. If entity is None,
  declare honestly "non ho memoria di X" — do NOT confabulate from training
  data. If entity exists but facts == [], declare "ho il nodo entity ma
  nessun fatto collegato" and suggest hippo_facts_search or hippo_recall.
  Zero LLM cost, sub-50ms on ~500 entity corpus, free in hosted mode.
  Backend SQLite WAL + UNIQUE INDEX on name_norm Python-normalized
  (NFC + str.lower, NOT SQLite ASCII-only LOWER). Entity-first recall —
  complements hippo_facts_search (topic-based) and hippo_recall (semantic
  episode) with a third modality, graph node lookup. ANTI-PATTERN: do NOT
  use for factual claim validation ("Tonegawa won Nobel in 2014") — that's
  hippo_validate_claim. Do NOT use for topic-based episode/dialog search —
  that's hippo_search or hippo_recall.
---

# HippoAgent — entity-first recall (hippo_entity_get)

Quando l'utente chiede "che sai di X?" / "ricordami chi è Y?" /
"dammi tutto su Z", chiama `hippo_entity_get(name=<X>)` PRIMA di
rispondere da memoria interna. Il tool ritorna l'entity canonica
(risolvendo eventuali alias) + la lista di fact collegati, da un
knowledge graph SQLite persistente.

## ⚠️ Quando ATTIVARE (trigger)

Pattern lessicali che attivano il skill:

- **Italiano**: "che sai di X", "cosa ricordi di Y", "dammi tutto
  su Z", "chi è W", "ricostruisci ciò che sappiamo di V",
  "abbiamo discusso di U", "informazioni su T", "storia di S".
- **English**: "what do you know about X", "tell me about Y",
  "facts about Z", "who is W", "history of V", "what have we said
  about U", "summarize what we know on T".
- **Implicito**: l'utente menziona un nome Capitalized (persona,
  paper, repo, progetto interno) e ti aspetti che ne sappia qualcosa.

**Risoluzione automatica alias**: lookup di "S. Tonegawa" trova
l'entity canonica "Tonegawa" se è stato registrato l'alias.

**Case + Unicode-safe**: "müller", "MÜLLER", "Müller" trovano
tutti la stessa entity. Anche NFC vs NFD (`unicodedata.normalize`
forma decomposta vs composta) sono trattati come uguali.

**NON serve** per:
- Claim factual da validare ("X is Y") → `hippo_validate_claim`
- Ricerca su episodi/dialoghi su un topic → `hippo_search`,
  `hippo_recall`
- Ricerca su fact per topic-namespace → `hippo_facts_search`,
  `hippo_facts_list`
- Saluti, chat casuale, opinioni

## Flow

```
1. Identifica il nome dell'entity nella domanda (Capitalized,
   eventualmente con prefisso "S." / "Dr." / titolo).
2. hippo_entity_get(name="<entity>")
3. Read payload:
   {
     "entity": { "id": "...", "canonical_name": "...", "type": "..." }
              | None,
     "aliases": ["...", "..."],
     "facts": ["fact_id_1", "fact_id_2", ...]
   }
4. Act:
   ┌─ entity is None     → "Non ho memoria di <name> nel KG. Vuoi
   │                       che cerchi episodi correlati?
   │                       (`hippo_search`)"
   ├─ entity, facts == [] → "Ho il nodo <canonical_name> (id=...,
   │                       type=...) ma nessun fatto direttamente
   │                       linkato. Posso cercare con
   │                       `hippo_facts_search` o `hippo_recall`."
   └─ entity, facts ≠ []  → Leggi i fact con `hippo_facts_list`
                           (passando i fact_id ottenuti) per
                           ricostruire la conoscenza completa,
                           poi rispondi citando i fact_id come
                           evidenza.
```

## Output semantics

| campo | tipo | semantica |
|---|---|---|
| `entity` | dict \| None | None = entity sconosciuta. Dict = `{id, canonical_name, type}` |
| `entity.id` | str | UUID 12-char, primary key SQLite, usalo per `hippo_entity_link` (futuro P2.a addendum) |
| `entity.canonical_name` | str | Nome canonico (la forma "ufficiale", es. "Tonegawa") |
| `entity.type` | str | Tag libero, es. `"person"`, `"paper"`, `"repo"`, `"project"`, `"concept"` — può essere `""` |
| `aliases` | list[str] | Tutte le forme alternative registrate (es. `["S. Tonegawa", "Susumu Tonegawa"]`) |
| `facts` | list[str] | `fact_id` collegati all'entity tramite tabella `entity_facts`. Vuota se nessun link |

## Parametri

- `name: str` — il nome o alias da cercare. Trim + Unicode NFC +
  case-fold automatici dal backend.

## Esempi concreti

### Esempio 1 — entity trovata con facts

User: "cosa ricordi di Tonegawa?"

```
hippo_entity_get(name="Tonegawa")
→ {
    "entity": {
      "id": "a8f3c9d12e4b",
      "canonical_name": "Tonegawa",
      "type": "person"
    },
    "aliases": ["S. Tonegawa", "Susumu Tonegawa"],
    "facts": ["f_tonegawa_nobel_1987", "f_tonegawa_engram_2014"]
  }
```

Azione: chiama `hippo_facts_list(fact_ids=["f_tonegawa_nobel_1987",
"f_tonegawa_engram_2014"])` per leggere le proposizioni complete,
poi rispondi:

> Tonegawa (Susumu Tonegawa, person) — 2 fact in memoria:
> 1. Nobel Prize 1987 per immunology (V(D)J recombination)
>    [f_tonegawa_nobel_1987]
> 2. Lavori sull'engram a MIT 2014 [f_tonegawa_engram_2014]
> Alias noti: "S. Tonegawa", "Susumu Tonegawa".

### Esempio 2 — alias risolve a canonical

User: "dammi tutto su S. Tonegawa"

```
hippo_entity_get(name="S. Tonegawa")
→ {
    "entity": {"id": "a8f3c9d12e4b", "canonical_name": "Tonegawa", ...},
    "aliases": [...],
    "facts": [...]
  }
```

L'alias è risolto trasparentemente: stesso `id` dell'entity canonica.

### Esempio 3 — entity sconosciuta

User: "che sai di Marie Curie?"

```
hippo_entity_get(name="Marie Curie")
→ {"entity": None, "aliases": [], "facts": []}
```

Risposta corretta (onesta):

> Non ho memoria di Marie Curie nel knowledge graph entity-centric.
> Posso cercare episodi correlati con `hippo_search("Marie Curie")`
> o fatti con `hippo_facts_search`?

**NON CONFABULARE** una risposta basata su training data — l'utente
ha chiesto cosa c'è in *memoria persistente*, non cosa sa il modello.

### Esempio 4 — entity nota, zero fact linkati

User: "abbiamo discusso di NeuroFlask?"

```
hippo_entity_get(name="NeuroFlask")
→ {
    "entity": {"id": "...", "canonical_name": "NeuroFlask", "type": "repo"},
    "aliases": [],
    "facts": []
  }
```

Risposta:

> Il nodo entity "NeuroFlask" esiste nel KG (type=repo) ma non ha
> fatti direttamente linkati. Probabilmente è stato menzionato in
> episodi senza che facts/triple siano state estratte (l'auto-
> extraction OpenIE è P2.c, non ancora attiva). Vuoi che cerchi negli
> episodi con `hippo_search`?

### Esempio 5 — Unicode case-fold + NFC

User: "che sai di müller?" (lowercase, NFC)

User store-side: `hippo_entity_get(name="MÜLLER")` o
`name="Müller"` o anche forma NFD u+combining-diaeresis →
tutti risolvono allo stesso `id`. Backend usa `unicodedata.normalize`
`("NFC", s).strip().lower()` su una colonna `name_norm` indicizzata
UNIQUE (schema v4).

## Limitazioni note (P2.a)

- **No edges**: non c'è ancora `entity_edges` (predicate + weight),
  quindi nessuna navigazione multi-hop tipo "entity vicine di X" o
  "fact che connettono X a Y". P2.b lo aggiungerà con
  `hippo_entity_neighbors` + `hippo_ppr_retrieve` (HippoRAG-style
  Personalized PageRank).
- **No auto-extraction**: le entity e i link entity↔fact non vengono
  estratti automaticamente dagli episodi. Per ora vanno inseriti
  manualmente con script di seed. P2.c esporrà
  `hippo_extract_entities(text)` LLM-based con `json.loads` strict.
- **No type schema**: il campo `type` è una stringa libera
  (`"person"`, `"paper"`, ...). Non ci sono vincoli o gerarchie.
- **Solo lookup esatto**: cerca per `canonical_name` o alias
  con match Unicode case-insensitive. Nessun fuzzy match,
  nessuna espansione semantica. "Schroedinger" NON matcha
  "Schrödinger" (Ö vs OE è translitterazione, fuori scope).
- **Population seed-only**: il KG è popolato manualmente fino a P2.c.

## Cost

- Zero LLM call.
- Sub-50ms su corpus ~500 entity (SQLite WAL + UNIQUE INDEX su
  `name_norm`).
- Free in hosted mode (read on local SQLite + Python str ops).

## Quando NON chiamarlo

- Claim factual da validare ("X did Y in YEAR") → `hippo_validate_claim`
- Ricerca topic-based su fact ("fatti su engram") →
  `hippo_facts_search(query="engram")`
- Ricerca episodica su dialoghi/sessioni ("quando abbiamo parlato di
  Beacon") → `hippo_search` o `hippo_recall`
- Domanda generica senza nome Capitalized ("che lavoro ho fatto ieri")
  → `hippo_episode_list` + `hippo_session_recap`
- Chat casuale, saluti, opinioni, output codice

## Combinazioni utili

- **Entity + tutti i suoi fact**: `hippo_entity_get(name)` →
  prendi `facts[]` → `hippo_facts_list(fact_ids=facts)` per le
  proposizioni complete.
- **Entity + episodi correlati** (workaround per assenza di edges):
  `hippo_entity_get(name)` → leggi i fact_id → per ogni fact_id
  chiama `hippo_lineage_trace(start_id=fact_id, kind="fact",
  direction="backward")` per arrivare agli episodi sorgente.
- **Disambigua un nome**: `hippo_entity_get` ritorna gli `aliases` —
  utile per capire come l'utente potrebbe averlo chiamato in altre
  sessioni.

## Storia

P2.a della roadmap Engram-amplifies-Claude (cycle #70).
- Commit `54a0c35` (2026-05-15): MVP iniziale, `engram/entity_kg.py`,
  3 tabelle SQLite (`entities` + `entity_aliases` + `entity_facts`),
  10 RED→GREEN test, tool MCP `hippo_entity_get`.
- Commit `12fa4ff` (2026-05-15 notte tarda): **hardening
  multi-round critic-driven**. 5 round adversariali consecutivi con
  critic-orchestrator hanno scoperto 6 bug reali e li hanno
  forzati a essere fixati:
  1. Race condition check-then-insert non atomico (8 thread paralleli
     → 2-8 duplicate). Fix: `BEGIN IMMEDIATE` + `UNIQUE INDEX` su
     `name_norm` + IntegrityError fallback re-SELECT.
  2. Cross-alias dedupe contract violation. Fix: SELECT
     canonical-only (no JOIN su alias durante `store`).
  3. Empty `canonical_name` bypass. Fix: strip + `ValueError`.
  4. Unicode case-folding bug (SQLite `LOWER()` ASCII-only:
     MÜLLER/Müller diventavano 2 entity). Fix: colonne
     `name_norm`/`alias_norm` Python-side via `str.lower()`
     full-Unicode + migration v3 backfill + dedup duplicate
     pre-existenti.
  5. NFC vs NFD form-folding bypass. Fix:
     `unicodedata.normalize("NFC", ...)` in `_norm()` + migration
     v4 re-backfill.
  6. Migration v4 IntegrityError su DB v3 con duplicate NFC+NFD.
     Fix: DROP UNIQUE INDEX a inizio v4, UPDATE+dedup, ricreare
     UNIQUE alla fine.

  Schema finale v4: `entities(id, canonical_name, name_norm,
  type, created_at)` con UNIQUE su `name_norm` + `entity_aliases`
  con `alias_norm` + `entity_facts` (PRIMARY KEY composito,
  idempotente via INSERT OR IGNORE).

  Test coverage: 17/17 PASS (10 base + 7 critic-driven). Full
  pytest 2451 PASS 0 fail.

- Spec: `docs/specs/p2-entity-centric-kg.md` (commit `48678a2`).
- Test: `tests/test_entity_kg.py`.

## Cosa arriva dopo (NON ANCORA disponibile)

- **P2.b** (next): `hippo_entity_neighbors(entity_id, k, hops)` +
  `hippo_ppr_retrieve(query_entities, damping=0.5, k=20)` per
  recall multi-hop tipo HippoRAG. Dipendenza: `networkx` (prpack).
- **P2.c**: `hippo_extract_entities(text, mode="ner+triple")`
  LLM-based 2-step (NER → triple) con `json.loads` strict, NO
  parser eseguibile su LLM output. Hook automatico in
  `hippo_record_episode` quando l'episodio è abbastanza ricco.
- **P2.b/c addendum**: `hippo_entity_link(fact_id, entities[])`
  per manual override e seed pipeline.
