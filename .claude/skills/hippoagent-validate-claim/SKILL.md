---
name: hippoagent-validate-claim
description: Before asserting any verifiable factual claim (year/number/attribution/citation/date), call `hippo_validate_claim(claim)` to check it against persistent memory. Triggers when about to say things like "X was born in YEAR", "Y won the Nobel in YEAR", "Z released VERSION in MONTH", "W said EXACT_QUOTE", "this library/paper/repo is from ORG", or any other claim containing a Capitalized name + a specific year/number/version/org. The tool returns verdict ∈ {supported, contradicted, unknown} + an advice string in Italian (e.g. "in memoria 1987 (fact f_id), NON 2014 — controlla prima di affermare"). If verdict=contradicted, STOP and re-read the evidence_facts; do NOT assert the claim verbatim. If verdict=unknown, hedge ("non ricordo con certezza", "credo ma verifica"). If verdict=supported, proceed. Zero LLM cost (deterministic, sub-100ms). Anti-confabulation gate — born from live confabulations 2026-05-14 (Tonegawa Nobel 1987→2014, Anthropic Skills Oct 2025→Oct 2026, LightRAG HKUDS→HKUST).
---

# HippoAgent — anti-confabulation gate (hippo_validate_claim)

Prima di asserire un fatto verificabile, chiama `hippo_validate_claim`.
È un gate **deterministico, zero LLM call, sub-100ms** che intercetta
i pattern di confabulazione più frequenti: cambio di anno, numero,
versione, attribuzione, organizzazione.

## ⚠️ Quando ATTIVARE (trigger)

Il tool va chiamato **prima** di pronunciare una frase factual che
contiene almeno **2 token salienti** (nome Capitalized + anno/numero,
o due nomi Capitalized). Esempi tipici:

- "Tonegawa won the Nobel Prize in **1987**"
- "Anthropic released Skills in **October 2025**"
- "LightRAG is from **HKUDS** (HK Data Science group)"
- "Newton wrote **Principia** in **1687**"
- "HippoRAG paper appeared at **NeurIPS 2024**"
- "GPT-4 was released in **March 2023**"
- "Sonnet 4.6 said X"  ← attribuzione di citazione
- "Cycle #51 introduced narrative episodes" ← versione/release interna

**NON serve** per claim generiche ("Tonegawa is a researcher",
"Python is a language"): meno di 2 token salienti = il tool risponde
`unknown` di default.

## Flow

```
1. Pre-flight:    hippo_validate_claim(claim="<la frase factual completa>")
2. Read verdict:  payload.verdict ∈ {supported, contradicted, unknown}
3. Act:
   ┌─ supported    → procedi, asserisci la frase
   ├─ contradicted → STOP. Leggi payload.advice + payload.evidence_facts.
   │                 Re-leggi i fact con hippo_facts_list o hippo_facts_search.
   │                 Riformula con il valore CORRETTO della memoria.
   └─ unknown      → hedge: "non ricordo con certezza", "credo ma verifica".
                     Se importante, chiedi conferma all'utente.
```

## Verdict semantics

| verdict | significato | azione |
|---|---|---|
| `supported` | trovato fact in memoria con stessi nomi e anno/numero match | asserisci |
| `contradicted` | trovato fact con stessi nomi MA anno/numero diverso | **NON asserire** — usa il valore in memoria |
| `unknown` | nessun fact correlato O claim troppo generica (< 2 token salienti) | hedge esplicito |

`confidence` ∈ [0, 1]: tipicamente eredita dal confidence del fact più
forte in memoria. Cap a 0.95 (nessuna asserzione è 1.0).

`evidence_facts`: lista di `fact_id` da approfondire con
`hippo_facts_list` o `hippo_facts_search` per leggere la proposition
completa.

`advice`: stringa breve in italiano già pronta da inserire nel
ragionamento interno (es. "in memoria: 1987 (fact f_tonegawa_1987),
NON 2014 — controlla prima di affermare").

## Parametri opzionali

- `topic_hint: str` — restringi la ricerca a un topic specifico
  (es. `"science/biology/nobel"`, `"project/engram/cycle-70"`).
  Riduce falsi positivi quando il corpus è grosso.
- `threshold: float` (default 0.6) — frazione minima di nomi della
  claim che devono apparire in un fact per considerarlo "soggettivamente
  rilevante". Aumenta a 0.8-0.9 se vuoi essere più selettivo, abbassa
  a 0.4 per essere più sensibile.

## Esempi concreti (canary cases reali)

### Esempio 1 — contradicted (Tonegawa)

Pre-claim: "Tonegawa won the Nobel Prize in 2014 for engram research."

```
hippo_validate_claim(claim="Tonegawa won the Nobel Prize in 2014.")
→ {
    "verdict": "contradicted",
    "confidence": 0.95,
    "evidence_facts": ["f_tonegawa_nobel_1987"],
    "advice": "in memoria: 1987 (fact f_tonegawa_nobel_1987), NON 2014 — controlla prima di affermare."
  }
```

Azione corretta: re-leggere il fact → scoprire che Nobel 1987 era per
**immunology** (V(D)J recombination), NON per engram. Affermare la
versione corretta.

### Esempio 2 — contradicted (Anthropic Skills date)

Pre-claim: "Anthropic released Skills in October 2026."

```
hippo_validate_claim(claim="Anthropic released Skills in October 2026.")
→ {"verdict": "contradicted",
   "evidence_facts": ["f_skills_release_2025"],
   "advice": "in memoria: 2025 ..., NON 2026 — ..."}
```

### Esempio 3 — unknown (claim generica)

Pre-claim: "Newton è uno scienziato."

```
hippo_validate_claim(claim="Newton è uno scienziato.")
→ {"verdict": "unknown",
   "advice": "Claim troppo generica per validazione lessicale (servono ≥ 2 token salienti)."}
```

Azione: asserisci pure, il tool non può/deve validarla.

### Esempio 4 — supported

Pre-claim: "Newton published Principia in 1687."

```
hippo_validate_claim(claim="Newton published Principia in 1687.")
→ {"verdict": "supported", "confidence": 0.95,
   "evidence_facts": ["f_newton_principia"],
   "advice": "Claim coerente con la memoria."}
```

## Limitazioni note

- **Solo lessicale**, non semantica/multi-hop. "Tonegawa Nobel" trova
  Tonegawa, ma non sa che Nobel Prize ⊂ premi scientifici.
- **NER super-light**: regex Capitalized + anni. Niente WikiNER, niente
  LLM. Funziona bene su nomi propri + date, meno bene su entità con
  nomi non-Capitalized (organismi, malattie, geni a lowercase).
- **No claim modifier**: il tool NON modifica la claim né suggerisce
  un fix preciso — solo segnala discrepanza. L'agent decide come
  riformulare.
- **Backend SQL LIKE strict**: cerca per ogni nome Capitalized
  separatamente, dedup per id. Anni non sono mai chiave di ricerca
  (troppo rumorosi: "1987" da solo matcha cross-topic).

## Cost

- Zero LLM call.
- Sub-100ms sul corpus attuale (~500 facts).
- Free in hosted mode (read on local SQLite + regex Python).

## Quando NON chiamarlo

- Chat casuale, saluti, domande personali ("come stai?")
- Output codice (Python/JSON/SQL non è claim factual)
- Opinioni ("credo che X sia meglio di Y")
- Domande aperte all'utente ("vuoi che procediamo?")
- Riassunti narrativi senza nuove asserzioni factual

## Storia

P1 della roadmap Engram-amplifies-Claude (cycle #70, commit a07debf).
Origine: pattern di confabulazione pescati live in sessione
2026-05-14 (Tonegawa Nobel 1987→2014, Anthropic Skills Oct 2025→Oct
2026, LightRAG HKUDS→HKUST, attribuzione Sonnet 4.6→me).
Spec: `docs/specs/p1-hippo-validate-claim.md` (ce67839).
Test: `tests/test_validate_claim.py` (8 casi, canary Tonegawa).
Critic-orchestrator gate: 2 round adversariali (counterexample worker
ha pescato bug fake-vs-production, fix in place, falsification worker
verificato 0.95).
