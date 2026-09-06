# Il disegno esploso — lo STORE: tabelle, migrazioni, campi, e chi li scrive

**05/09/2026, 23:10.** Tutto misurato con `sqlite3` in sola lettura sullo store
di casa (`C:\Users\aurel\.engram\semantic\semantic.db`), non a memoria. Dove non
ho misurato, c'è scritto **non misurato**.

> ⚠️ **Non ho potuto leggere `DISEGNO-ESPLOSO.md`**: il ramo indicato,
> `push-lead-0209`, **non esiste su origin** — `git ls-remote --heads origin`
> elenca 30 rami e nessuno è del lead. Questa pagina è quindi autonoma; se il
> documento esiste altrove, va riconciliata con quella e non sostituita a essa.

## 1. Le tabelle — 21, e cinque sono vuote per costruzione

```
_schema_version              2        facts                    17722
audit_mutations           1171        facts_fts                17722
contradictions           94181        facts_fts_config             1
entities                     0        facts_fts_content        17722
entity_aliases               0        facts_fts_data            2042
entity_attrs                 0        facts_fts_docsize        17722
entity_edges                 0        facts_fts_idx             1659
entity_facts                 0        facts_undo_log             141
narrative                  627        source_trust                 0
telemetry                 7952        trust_ledger             11306
trust_ledger_totals        116
```

**Le cinque tabelle del grafo sono a zero, e non è un difetto: il grafo vive in
un altro file.**

```
C:\Users\aurel\.engram\entity_kg\entity_kg.db   entities=10921  entity_facts=37047
C:\Users\aurel\.engram\semantic\semantic.db     entities=0      entity_facts=0
```

⚠️ Ma **`semantic.db` porta comunque quelle cinque tabelle e undici indici
costruiti sopra** (`idx_entities_name_lower`, `idx_edges_src`,
`idx_entity_facts_fact`, …), che nessuno popolerà mai in quel file. È uno schema
doppio: uno vivo, uno vuoto. Chi apre `semantic.db` e trova `entities` vuota
conclude che il grafo non esiste — ed è la trappola già scritta in memoria
(«ogni store ha due DB»), qui nella sua forma peggiore, perché il file sbagliato
**ha la tabella giusta**.

Altri due `entity_kg.db` esistono e sono quasi vuoti: `dev-journal` (7 entità) e
`gateway/tenants/acme` (1). **Non misurato** chi li scriva.

**`contradictions` ha 94.181 righe** contro 17.722 fatti. **Non misurato** quante
siano risolte: il numero sta qui perché è il più grande dello store e nessuna
pagina lo nomina.

## 2. Le migrazioni

```
semantic    v17    2026-08-08 12:03:52
entity_kg   v6     2026-05-16 20:00:49
```

Due lignaggi separati, coerente con i due file. L'ultima migrazione dello store
semantico è del **8 agosto**: da allora lo schema non cambia.

## 3. Le colonne di `facts` — 31, e sei sotto l'1%

```
colonna                popolate       %      colonna                popolate       %
id                        17722   100.0     lineage_to                15229    85.9
proposition               17722   100.0     lineage_parents              32     0.2  ←
topic                     17586    99.2     writer_role               17722   100.0
confidence                17722   100.0     meta_narrative            17722   100.0
source_episodes            5250    29.6     last_verified_at          17501    98.8
created_at                17722   100.0     embedding_model           17722   100.0
embedding                 17722   100.0     valid_until                   0     0.0  ←
superseded_by              2353    13.3     derives_from                  1     0.0  ←
superseded_at              2353    13.3     grounding_score           11099    62.6
superseded_reason          2390    13.5     asserted_at                   1     0.0  ←
verified_by               17722   100.0     epistemic                     0     0.0  ←
status                    17722   100.0     confidence_tier           11237    63.4
source_signature          10006    56.5     writer_principal          11382    64.2
trigger_keywords           1254     7.1     quarantined_by             1024     5.8
applicable_when            1246     7.0     grounding_span             8313    46.9
worked_example                1     0.0  ←
```

🔑 **Sei colonne su trentuno stanno sotto l'1%**: `valid_until`, `asserted_at`,
`epistemic`, `worked_example`, `derives_from`, `lineage_parents`. Non sono
«opzionali»: sono **capacità dichiarate nello schema che nessuna porta
alimenta**. La conseguenza misurata su una di esse: `hippo_justified_audit`
pubblicizza quattro trigger di ritrattazione, e due si reggono su `valid_until` —
sul corpus vivo davano `would_stale_ids 0`, «non perché il corpus è sano, ma
perché dai canali che lo riempiono quelle colonne non sono raggiungibili».

**`grounding_score` è popolato su 11.099 di 17.722**: 6.623 righe (37,4%) non
portano un giudizio. Il campo `status` non lo distingue — un fatto mai giudicato
e uno giudicato al 99,97 hanno lo stesso `model_claim`.

## 4. `status`, e chi ferma i fatti

```
model_claim        11754  (66.3%)      diary                 86  (0.5%)
quarantined         2779  (15.7%)      bootstrap_rule        24  (0.1%)
user_manual         2599  (14.7%)      bootstrap_lesson      14  (0.1%)
provisional          343  (1.9%)       lesson_manual          3  (0.0%)
legacy_unverified    115  (0.6%)       bench_manual           2  (0.0%)
                                       verified               2  (0.0%)
                                       pending                1  (0.0%)
```

**`verified` esiste su due fatti su 17.722.** Lo status che il nome del prodotto
promette è, nei numeri, un caso limite: la separazione vera la porta
`grounding_score`, non `status`.

```
quarantined_by su 2779 quarantinati
  None               1909      L4-review          54
  moat                549      L3-coexistence     19
  L4.1                189      L1                  2
  gate                 55      store-screen        1 · moat:L4-grounding 1
```

**Di 2.779 fatti fermati, 1.909 non dicono chi li ha fermati** (68,7%). È debito
storico noto — il campo è stato aggiunto dopo — ma finché quelle righe restano,
due terzi delle quarantene non sono spiegabili a chi legge.

## 5. Chi scrive i campi chiave

Conteggio delle assegnazioni per file (lettura statica, `verimem/*.py`):

| campo | dove si scrive, in ordine |
|---|---|
| `status` | `mcp_server` 72 · `semantic` 44 · `provenance_validator` 18 · `client` 13 |
| `superseded_by` | `semantic` 5 · `anti_confab_gate` 2 · `trust_signal` 1 |
| `valid_until` | `semantic` 5 · `mcp_server` 3 · `justified_memory` 1 · `client` 1 |
| `asserted_at` | `semantic` 3 · `mcp_server` 3 · `client` 3 · `anti_confab_gate` 2 |
| `grounding_score` | `anti_confab_gate` 10 · `client` 7 · `mcp_server` 4 · `transcript_promote` 3 |
| `epistemic` | **`semantic` 3, e nessun altro** |
| `quarantined_by` | `mcp_server` 2 · `client` 2 · `semantic` 1 |

⚠️ **`epistemic` è nominato in un solo modulo e popolato su zero righe.** Le due
misure si confermano da direzioni diverse — il codice e il corpus — ed è la
lettura più forte di questa pagina: un campo che nessuna porta scrive.

⚠️ **`status` si scrive da 147 punti in quattro file.** Non ho misurato quanti
siano scritture vere e quanti confronti mal filtrati dal mio grep: **il numero è
un limite superiore**, e serve solo a dire che non esiste un punto unico che
decide lo stato di un fatto.

## 6. Il tier EPISODI — 493 righe, 21 colonne, e tre che non esistono nel codice

Il mandato del livello 3 dice «tier episodi/documenti», e le sezioni sopra
guardano solo `semantic.db`. Questa è la parte che mancava
(`episodes/episodes.db`, 17,6 MB — non quello alla radice, che è a 0 byte).

```
id · task_id · task_text · outcome · tokens_used · skills_used ·
created_at · summary_embedding · last_accessed_at · access_count ·
salience_score · pinned                        100,0%
final_answer                                    98,8%
dg_embedding · embedding_model                  96,8%
critique                     6 righe             1,2%
notes                        2 righe             0,4%
context_embedding            2 righe             0,4%
invalidated_at               0                   0,0%   ←
invalidated_by               0                   0,0%   ←
invalidation_reason          0                   0,0%   ←
```

**Le tre a zero sono di una categoria diversa dalle altre**, e la differenza si
vede solo guardando anche il codice:

```
grep -rc "<colonna>" verimem/*.py
  salience_score       33      ← [controllo positivo] il grep sa trovare
  access_count         21
  notes                79
  critique             41
  context_embedding    21
  invalidated_at        0      ← nessuna riga di codice la nomina
  invalidated_by        0
  invalidation_reason   0
```

- **NON CABLATE**: le tre dell'invalidazione. Zero nel codice *e* zero nei dati:
  il tier episodi ha un meccanismo di ritiro **che esiste solo nello schema**.
  (Le funzioni `invalidate_*` che si trovano riguardano la cache delle skill e
  gli handle dell'undo-log: altra cosa.)
- **CABLATE E QUASI MAI ALIMENTATE**: `notes`, `critique`, `context_embedding` —
  il codice le nomina decine di volte e il campo resta vuoto. È la forma di
  `valid_until` sui fatti, che era 0 su 17.575 finché una porta di scrittura non
  ha potuto popolarlo.

⚠️ Il grep è **lessicale**, e `notes` è una parola comune: per le colonne non-zero
quel numero è un limite superiore. Per gli zeri non cambia nulla — uno zero non
ha falsi positivi.

⛔ Non è una proposta di togliere le colonne: non è misurato se siano previste
per una funzione in arrivo, e in questa casa il limite si prova prima di buttare.

## 7. Il difetto del misuratore, dichiarato

Il primo giro di questa pagina ha stampato **una tabella sola** invece di 21:
iteravo su `cur.execute(...)` e dentro il ciclo rifacevo `cur.execute(...)` sullo
stesso cursore, distruggendo l'iterazione. Il verdetto sarebbe stato «lo store ha
una tabella», cioè un titolo. Corretto con `fetchall()` prima del ciclo.
È il terzo misuratore rotto in una serata — dopo il filtro che escludeva
`tests/test_<modulo>.py` e i due `endswith` sui path di Windows: **quando il
numero sorprende, il primo sospetto è il righello.**
