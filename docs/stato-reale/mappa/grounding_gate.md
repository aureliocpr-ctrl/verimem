# `verimem/grounding_gate.py` — 671 righe, 22 funzioni

**Il modulo che decide se una fonte sostiene un fatto, e con quale soglia.** È il livello
sotto `anti_confab_gate`: qui non ci sono layer, c'è il punteggio e il taglio. Mappato su
`7b9e8ca1`. 11 funzioni pubbliche, 11 private.

---

## 1. 🔴 IL REPERTO: **lo span viene troncato DUE VOLTE, e solo il secondo costa**

Questo è il pezzo che spiega T40 e ne rende la cura precisa.

| dove | funzione | unità | costo |
|---|---|---|---|
| `grounding_gate.py:364` | `select_relevant_span` | **caratteri** (`up to budget chars`) | **zero** — *«Pure + deterministic — no embeddings»* |
| `local_grounding.py:389` | `_entro_la_finestra` | **token** | **35,4 s** — serve il tokenizer (misurato stasera) |

Il primo taglio è già fatto, è gratis, ed è quello che porta il beneficio dichiarato nel
docstring:

> *clean-admission ~0.70 → 0.80 a budget di caratteri FISSO, noise-rejection invariata
> ~100%* (`benchmark/halumem_gate_source_ab.py`)

Il secondo taglio ri-riduce lo **stesso** span contando token, e per contarli carica un
tokenizer da 35 secondi **sul thread della richiesta**.

⇒ **La cura di T40 diventa piccola e a basso rischio**: in delegate-only lo span è già
dentro un budget di caratteri e va **mandato al daemon così com'è** — il conteggio dei token
lo fa chi il modello ce l'ha già in memoria. Non serve inventare un troncamento nuovo:
serve **non fare il secondo**.

---

## 2. Le soglie: tre risolutori, non uno

    _resolve_threshold          (161)  generico
    _resolve_write_threshold    (173)  «Calibrated LOWER» per il percorso di SCRITTURA
    resolve_write_threshold_for (510)  la soglia CONSISTENTE col giudice che ha prodotto il punteggio

🔑 Il terzo esiste perché **il taglio dipende da chi ha giudicato**: un punteggio del CE
locale e uno di un llm non stanno sulla stessa scala, e applicare la soglia sbagliata è il
modo silenzioso di ammettere o rifiutare per errore. `_resolve_write_threshold` dichiara che
il taglio in scrittura è **più basso** di quello in lettura — una scelta, non un caso.

📌 Su questo albero c'è anche il presidio della banda di mezzo: `_ce_band_enforced` (570),
**acceso di default dal 2026-07-19**, con `_ce_band_tau_hi` (565).

---

## 3. Il giudice: `_e_un_giudice_vero` (194)

> *«C'è un llm che sa davvero giudicare, o solo il segnaposto?»*

È il predicato che impedisce di chiamare `llm.complete()` su un oggetto finto. `_resolve_backend`
(245) sceglie fra `claude` (default, llm iniettato) e `local`; `fact_grounding_score_ex`
(439) torna **anche QUALE giudice ha prodotto il punteggio** — ed è la funzione che rende
possibile la soglia coerente del §2.

---

## 4. `confidence_tier` (586) — il campo che dice di non essere una verità

> *«The judge's CONFIDENCE level for a gate score — **NOT a truth claim**»*

📌 È il tipo di onestà che manca altrove nel prodotto: il nome del campo potrebbe far
credere a una probabilità di verità, e il docstring lo nega esplicitamente. **Chi scrive
ricevute copi questa riga.**

---

## 5. L'astensione, e perché ha un classificatore

    _is_abstention   (113)
    _abstention_kind (127)  «Classify a reply for the short-circuit decision (F4, kimi audit…)»

Una risposta che si astiene non va giudicata come una risposta sbagliata: `gate_answer`
(290) la fa uscire prima. ⇒ **l'astensione è un esito, non un fallimento** — coerente con
la riga del README sulle *«honest read-path abstentions»*.

---

## 6. Le 22 funzioni

**Pubbliche (11)**: `grounding_score` · `is_grounded` · `gate_answer` · `optimal_threshold`
· `select_relevant_span` · `fact_grounding_score` · `fact_grounding_score_ex` ·
`resolve_write_threshold_for` · `confidence_tier` · `should_store_fact` ·
`fact_grounding_span`.

**Private (11)**: `_is_abstention` · `_abstention_kind` · `_resolve_threshold` ·
`_resolve_write_threshold` · `_resolve_judge` · `_e_un_giudice_vero` · `_resolve_backend` ·
`_span_tokens` · `_overlap` · `_ce_band_tau_hi` · `_ce_band_enforced`.

📌 `should_store_fact` (614) e `fact_grounding_span` (648) sono le due porte che il resto
del prodotto chiama: la prima decide, la seconda **conserva la prova** (`{"score", "span"}`).
⚠️ E il team ha misurato **2.786 fatti giudicati senza span conservato** — cioè la seconda
non è sempre stata chiamata dove la prima decideva. Reperto mio del 07/09, **non curato da
nessuno**.

---

## 7. Quello che questa mappa NON dice — dichiarato

- **`optimal_threshold` (Youden's J) non è esercitata qui**: non so se sia usata a runtime
  o solo negli esperimenti.
- **Non ho misurato** se `select_relevant_span` e `_entro_la_finestra` producano lo stesso
  span su input reali: l'ipotesi che il secondo sia ridondante in delegate-only **va provata
  con un A/B** prima della cura di T40, non dopo.
- `_span_tokens` e `_overlap` sono lette solo di nome.

---

*Mappato da ws5 (Tara) su `7b9e8ca1`. §1 usa i tre bracci misurati da me stasera; il numero
del §2 e il beneficio dello span vengono dal docstring e sono attribuiti lì.*

---

<!-- TABELLA-FUNZIONI ws5 -->

## Dove sta ogni funzione, e con che verdetto

*Rubrica generata dall'AST. Cosa e' misurato e cosa no, per colonna:*

- **dove e chi** — `file:riga` dall'AST: misurato.
- **cos'e'** — tipo e prima riga del docstring: e' cio' che la funzione
  PROMETTE, non cio' che fa.
- **nominata da** — file che NOMINANO il nome corto: chiamate, ma anche
  riferimenti nudi, property e annotazioni. Gli alias di import sono
  risolti (senza, `emit_write` risultava a zero). Contando solo le
  chiamate, 17 funzioni su 27 risultavano morte e non lo erano: Protocol,
  property e callback non passano da una `ast.Call`. Include il file
  stesso. ⚠️ Un nome che vive in piu' classi (`call`, `to_dict`) somma
  usi non suoi: e' un TETTO, non una misura.
- **test** — file sotto `tests/` che lo nominano: dice che e' TOCCATA,
  non che sia coperta.
- **verdetto** — `MAI CHIAMATA` = zero riferimenti nel prodotto E zero nei
  test (i dunder esclusi: li chiama il linguaggio). `NON MISURATO` =
  tutto il resto, ed e' lo stato onesto: sapere chi la nomina non e'
  sapere che funziona.


### `verimem/grounding_gate.py` — 24 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/grounding_gate.py:59` `NoGroundingJudge` | classe: Raised when NO grounding judge could score a write — no llm injected AND | `verimem/anti_confab_gate.py`; `verimem/grounding_gate.py` | `tests/test_grounding_gate.py`; `tests/test_la_porta_mcp_dice_perche_il_moat_non_e_girato.py` (+4) | NON MISURATO |
| 2 | `verimem/grounding_gate.py:113` `_is_abstention` | funzione — **un commento del 2026-07-21 (grounding_gate.py:129) ne descrive il comportamento come attivo, ma il nome non compare nel codice** | **nessuno** | **nessuno** | MAI CHIAMATA |
| 3 | `verimem/grounding_gate.py:127` `_abstention_kind` | funzione: Classify a reply for the short-circuit decision (F4, kimi audit | `verimem/client.py`; `verimem/grounding_gate.py` | `tests/test_abstention_hybrid.py` | NON MISURATO |
| 4 | `verimem/grounding_gate.py:161` `_resolve_threshold` | funzione | `verimem/client.py`; `verimem/grounding_gate.py` (+1) | `tests/test_verimem_env_thresholds.py`; `tests/test_write_threshold.py` | NON MISURATO |
| 5 | `verimem/grounding_gate.py:173` `_resolve_write_threshold` | funzione: Admission threshold for the WRITE path (source ⊢ fact). Calibrated lower than | `verimem/grounding_gate.py` | `tests/test_write_threshold.py` | NON MISURATO |
| 6 | `verimem/grounding_gate.py:189` `_resolve_judge` | funzione | `verimem/grounding_gate.py` | **nessuno** | NON MISURATO |
| 7 | `verimem/grounding_gate.py:194` `_e_un_giudice_vero` | funzione: C'e' un llm che sa davvero giudicare, o solo il segnaposto? | `verimem/grounding_gate.py` | `tests/test_un_llm_finto_non_e_un_giudice.py` | NON MISURATO |
| 8 | `verimem/grounding_gate.py:245` `_resolve_backend` | funzione: Write-gate judge backend: 'claude' (default, injected llm — unchanged), | `verimem/anti_confab_gate.py`; `verimem/grounding_gate.py` | `tests/test_gate_source_provenance.py` | NON MISURATO |
| 9 | `verimem/grounding_gate.py:254` `grounding_score` | funzione: External grounding score in [0, 100]: how strongly ``evidence`` supports that | `verimem/anti_confab_gate.py`; `verimem/client.py` (+9) | `tests/test_chi_ha_quarantinato_si_sa_anche_domani.py`; `tests/test_freschezza_non_nasce_da_un_tocco.py` (+17) | NON MISURATO |
| 10 | `verimem/grounding_gate.py:275` `is_grounded` | funzione | **nessuno** | `tests/test_grounding_gate.py` | NON MISURATO |
| 11 | `verimem/grounding_gate.py:280` `GateResult` | classe: Outcome of gating one answer. ``answer`` is the answer to USE (the original if | `verimem/anti_confab_gate.py`; `verimem/grounding_gate.py` | `tests/test_abstention_hybrid.py`; `tests/test_grounding_gate.py` (+3) | NON MISURATO |
| 12 | `verimem/grounding_gate.py:290` `gate_answer` | funzione: Verify ``answer`` against ``evidence``; abstain if below threshold. An answer that | **nessuno** | `tests/test_abstention_hybrid.py`; `tests/test_grounding_gate.py` | NON MISURATO |
| 13 | `verimem/grounding_gate.py:307` `optimal_threshold` | funzione: Youden's J optimal cut on labeled scores (label 1 = sound). Returns the score | **nessuno** | `tests/test_grounding_gate.py` | NON MISURATO |
| 14 | `verimem/grounding_gate.py:357` `_span_tokens` | funzione | `verimem/grounding_gate.py` | **nessuno** | NON MISURATO |
| 15 | `verimem/grounding_gate.py:364` `select_relevant_span` | funzione: Return the most fact-relevant portion of ``source``, up to ``budget`` chars, in the | `verimem/anti_confab_gate.py`; `verimem/grounding_gate.py` (+2) | `tests/test_grounding_gate.py`; `tests/test_la_prova_della_verifica_non_veniva_conservata.py` (+2) | NON MISURATO |
| 16 | `verimem/grounding_gate.py:383` `select_relevant_span._overlap` | funzione | `verimem/grounding_gate.py` | **nessuno** | NON MISURATO |
| 17 | `verimem/grounding_gate.py:422` `fact_grounding_score` | funzione: Entailment of a standalone candidate FACT by its SOURCE, in [0, 100] — the | **nessuno** | `tests/test_grounding_gate.py`; `tests/test_interactive_judge.py` (+2) | NON MISURATO |
| 18 | `verimem/grounding_gate.py:439` `fact_grounding_score_ex` | funzione: Like ``fact_grounding_score`` but also returns WHICH judge actually scored | `verimem/anti_confab_gate.py`; `verimem/grounding_gate.py` | `tests/test_un_llm_finto_non_e_un_giudice.py`; `tests/test_verimem_judge_reasoning_models.py` | NON MISURATO |
| 19 | `verimem/grounding_gate.py:510` `resolve_write_threshold_for` | funzione: The admission cut CONSISTENT with the judge that produced the score. Env | `verimem/anti_confab_gate.py`; `verimem/doctor.py` (+1) | `tests/test_i_parametri_in_vigore_si_possono_vedere.py`; `tests/test_property_gate_admission_g5.py` | NON MISURATO |
| 20 | `verimem/grounding_gate.py:565` `_ce_band_tau_hi` | funzione | `verimem/anti_confab_gate.py`; `verimem/doctor.py` (+1) | `tests/test_il_doctor_dichiara_ENTRAMBE_le_soglie.py` | NON MISURATO |
| 21 | `verimem/grounding_gate.py:570` `_ce_band_enforced` | funzione: ON by default (2026-07-19): a local-CE score in the middle band | `verimem/anti_confab_gate.py`; `verimem/doctor.py` | `tests/test_il_doctor_dichiara_ENTRAMBE_le_soglie.py` | NON MISURATO |
| 22 | `verimem/grounding_gate.py:586` `confidence_tier` | funzione: The judge's CONFIDENCE level for a gate score - NOT a truth claim. It names | `verimem/client.py`; `verimem/mcp_server.py` (+1) | `tests/test_adjudication_receipt.py` | NON MISURATO |
| 23 | `verimem/grounding_gate.py:614` `should_store_fact` | funzione: Write-path gate: store the fact only if the source grounds it above threshold. | **nessuno** | `tests/test_grounding_gate.py`; `tests/test_interactive_judge.py` (+2) | NON MISURATO |
| 24 | `verimem/grounding_gate.py:648` `fact_grounding_span` | funzione: Provenance verification: returns ``{"score": float, "span": str-None}`` — the score | **nessuno** | `tests/test_grounding_gate.py` | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





