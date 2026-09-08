# `verimem/wake.py` — 1.725 righe, 58 funzioni

**L'esecutore.** *«Wake cycle — the executor.»* Il file più grande dopo il gate, e l'unico
della mia superficie che **si apre con la sicurezza invece che col mestiere**. Mappato su
`7b9e8ca1`.

---

## 1. Le prime OTTO funzioni del file sono difese contro la prompt injection

Prima di qualunque cosa riguardi l'esecuzione, righe 83-249, sotto un'intestazione esplicita
`--- Prompt-injection defense (CVE-008) ---`:

| funzione | cosa impedisce |
|---|---|
| `_wrap_untrusted` (105) | l'osservazione esterna entra **marcata** `untrusted_content` |
| `_is_external_source_in_recent_traces` (124) | sapere se le ultime tracce hanno toccato l'esterno |
| `_episode_is_contaminated` (145) | *«True iff any past trace fetched external content»* |
| `_injection_review_blocks_call` (162) | **rifiutare** la chiamata che sta per partire |
| `_macro_blocked_by_injection_guard` (174) | la **scorciatoia** — vedi §2 |
| `_extract_source_arg` (216) | da dove viene il testo di una tool call |
| `_submit_cutoff_index` (232) | dopo quale indice non si può più «consegnare» |

🔑 **Il contenuto esterno è marcato, non filtrato**: il prodotto non prova a ripulire un
testo ostile, lo **circonda** e poi decide se una chiamata può partire. È la stessa scelta di
`_hang_watchdog` (rendere visibile invece che prevenire), applicata alla sicurezza.

---

## 2. 🔴 CVE-008 — la difesa aveva una scorciatoia intorno

> riga 175: *«CVE-008 (rescan2 2026-06-02): **the procedural macro fast-path bypassed** [la
> guardia]»*
> riga 1142: *«…the LLM loop gates dangerous tools»*

⇒ La guardia c'era **sul percorso lento** (il loop dell'LLM) e **non su quello veloce** (il
macro compilato, `_try_compiled_macro` a 1103). Una difesa presente e aggirabile **per
costruzione**, trovata in un rescan.

📌 È la forma che sui nostri appunti si chiama *«il bug è la GIUNTURA»*: nessuno dei due
percorsi era sbagliato, mancava il controllo **dove si incontravano**. Vale la pena cercarla
altrove: **ogni fast-path è un candidato**.

✅ **E oggi è CHIUSA** — la guardia del macro è chiamata a `1146`, quella del loop a `1444`,
e il fast-path deterministico è **uno solo**: la verifica sta nel §7. Questo paragrafo
racconta il difetto **storico**, non uno aperto.

---

## 3. Il file ha UNA superficie sola per tutto — e il mio sospetto contrario era sbagliato

    _run_with_strategy (1387)   «The unified wake loop — SINGLE SOURCE OF TRUTH»
    _run_loop_tools    (1504)   «thin facade over _run_with_strategy»   17 righe
    _run_loop_react    (1630)   «thin facade over _run_with_strategy»   18 righe
    _call_tool         (1590)   «Single source of truth for BOTH»

⚠️ **Qui avevo scritto che il pruning invece era duplicato**, perché `ast` conta 22 e 21
righe per `_prune_working_memory` e `_prune_working_memory_react`, e il secondo docstring
dice *«same algorithm, different encoding»*. **Ho eseguito il confronto invece di
pubblicare il sospetto, e il sospetto è caduto:**

    istruzioni (senza docstring):  3  contro  3
    l'algoritmo vero:              working_memory.prune_messages (riga 59)
    le due strategie:              react_obs_is_candidate · react_obs_replace

⇒ **Non sono due implementazioni: sono due adattatori da tre istruzioni** su un algoritmo
unico, che vive in un altro modulo. Le 21 righe di differenza erano **quasi tutte
docstring**. Il pattern è quello giusto — strategy — e il file lo applica anche al pruning,
non solo al loop.

📌 **La lezione è sul metodo, non sul codice**: contare le righe di due funzioni **non**
dice se una logica è duplicata. `_dispatch_native` (5 righe) e `_dispatch` (18) sono
asimmetrici per la stessa ragione — uno riceve argomenti già strutturati, l'altro deve
parsare `ActionInput` — e **non li ho verificati allo stesso modo**, quindi su quelli non
affermo niente.

---

## 4. Cosa fa davvero l'esecutore: memoria che entra nel prompt

Metà delle 58 funzioni serve a **costruire il contesto da episodi passati**:

- `_retrieve_skills` (614) — *«Bayesian-weighted retrieval: cosine-pool then Thompson…»*, con
  `_retrieve_skills_legacy` (681) accanto: *«il percorso pre-bayesiano, ignora la fitness»*
- `_forward_replay_block` (829) — un **«predicted path»** deterministico dalla memoria
- `_avoid_path_block` (969) — il prefisso di azioni degli episodi **falliti** simili
- `_divergence_block` (1034) + `_historical_divergence_counts` (916) — dove questa
  esecuzione si discosta da un «gemello riuscito»
- `_build_episode_context` (762) — la deriva TCM del contesto
- `_apply_lateral_inhibition` (415) — filtro greedy sui link antagonisti

🔑 **Il prodotto non ricorda per rispondere: ricorda per DECIDERE il prossimo passo.** Queste
sei funzioni sono la differenza fra una memoria e un esecutore che impara.

---

## 5. La riga che ho curato oggi

`wake.py:301` — `np.random.default_rng()`. Era **dentro** `with lock_import()` insieme
all'assegnazione (lavoro sotto il lock, violazione della regola di `_import_lock` scritta da
me il 06/09); ora l'import è esplicito dentro il blocco e la costruzione fuori (`cd644eff`).
Ed è il punto in cui la richiesta si fermava nel dump di T1b.

---

## 6. Le 58 funzioni

**8 top-level** (7 private di difesa + `trivial_validator` pubblica) · **3 classi**
(`WakeConfig`, `WakeResult`, `WakeAgent`) · **50 metodi** di `WakeAgent`, di cui **20
pubblici** (le statistiche `FORGIA`: istogrammi, breakdown, co-occorrenze, finestre
temporali, `predict_next_skill`, i tre di contesto `reset`/`checkpoint`/`restore`) e **30
privati** (recupero, costruzione del prompt, i due loop, i due pruner, i due dispatch).

---

## 7. Quello che questa mappa NON dice — dichiarato

- ~~Non ho misurato se i due pruner divergano~~ → **MISURATO, e ha smentito me** (§3):
  tre istruzioni ciascuno, algoritmo unico in `working_memory.prune_messages`. *Il limite era
  scritto e l'ho chiuso con un comando — se non l'avessi fatto, avrei pubblicato un ticket
  che non esiste.*
- **`_dispatch_native` (5 righe) contro `_dispatch` (18)**: NON verificati allo stesso modo.
  L'asimmetria ha una spiegazione plausibile nei docstring (uno riceve argomenti già
  strutturati, l'altro parsa `ActionInput`), ma **plausibile non è misurato** e su questo
  non affermo niente.
- ~~Non ho verificato che la guardia di CVE-008 copra OGNI fast-path~~ → **VERIFICATO, e
  chiude in positivo.** La domanda era *«quanti percorsi saltano il loop dell'LLM?»*:

      _macro_blocked_by_injection_guard   definita 174   CHIAMATA a 1146  (dentro _try_compiled_macro)
      _injection_review_blocks_call       definita 162   CHIAMATA a 1444  (dentro il loop LLM)
      riga 1101   «--- Procedural compilation fast-path ---»   ← l'unico
      riga  846   «informational, not a deterministic fast-path» ← dichiara di NON esserlo

  ⇒ **C'è UN solo fast-path deterministico, e ha la sua guardia**, con lo stesso criterio
  del percorso lento (il docstring a 181: *«hatch as `_injection_review_blocks_call`»*). La
  cura di CVE-008 non ha lasciato scorciatoie aperte, e un secondo punto che poteva
  sembrarne una **dichiara di non esserlo**.
- **Le funzioni `FORGIA` sono lette solo di nome**: sono venti superfici pubbliche di
  statistica, e non so quante siano usate da un chiamante vero.
- `_critique`, `_tool_catalog`, `_system_prompt`, `_estimate_messages_size`: solo nomi.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. Le misure di riga del §3 sono mie, con `ast`.*
