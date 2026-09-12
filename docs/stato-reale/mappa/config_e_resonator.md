# `verimem/config.py` (561 righe, 5 funzioni) e `verimem/resonator_text_bridge.py` (150 righe, 5 funzioni)

Gli ultimi due della mia superficie, mappati insieme perché piccoli e senza legami fra loro.
Su `7b9e8ca1`.

---

# `config.py` — 561 righe e SOLO 5 funzioni

*«Configuration: paths, models, hyper-parameters.»*

    _project_root (19) · _data_root (23) · _load_env (98) · __post_init__ (506) · ensure_dirs (547)

⇒ **Il rapporto righe/funzioni più alto della superficie (112:1)**: quasi tutto il file è
*dichiarativo* — costanti, dataclass, default. Non c'è logica da mappare, ci sono **scelte**.

## 🔑 `_data_root` (23) è la funzione più pericolosa del file

> *«Resolve the data root from env, else the shared `_compat`…»*

È il punto che decide **quale memoria** il processo aprirà. Sui nostri appunti è la trappola
più costosa in assoluto: *«ogni store ha due DB e quello alla radice è VUOTO ⇒ chiedi a
`CONFIG`»*, e *«`ENGRAM_DATA_DIR` non isola»*. ⇒ **Chi lancia un banco e non chiede a
`CONFIG` dove sta scrivendo, misura un'altra memoria** — è successo, e la cura pratica è
sempre la stessa: chiedere al prodotto, non dedurre dal path.

📌 `ensure_dirs` (547) è l'**unica** funzione pubblica: il file si usa leggendo `CONFIG`, non
chiamandolo.

## Quello che questa mappa NON dice

- **Non ho elencato le costanti**: sono la parte che conta e sono centinaia. Una mappa utile
  di `config.py` sarebbe *«quali default cambiano il comportamento e da che versione»* — è
  un lavoro a sé, e non l'ho fatto.
- **`_load_env` (98)**: *«candidate .env files»* al plurale — **non so quali, né in che
  ordine**, e l'ordine decide chi vince. È una domanda con una risposta breve e non l'ho
  cercata.

---

# `resonator_text_bridge.py` — il ponte con un fallback che non carica nulla

*«Cycle 397 (2026-05-23) — Bridge text → ResonatorMemory tuple indices.»*

| funzione | come mappa il testo |
|---|---|
| `text_to_atoms_via_embed` (73) | col sentence-transformer |
| `text_to_atoms_via_hash` (116) | *«Hash-only fallback… **Deterministic, no m[odel]**»* |
| `text_to_atoms_cached` (133) | punto d'ingresso, `method="embed"` o `"hash"` |
| `_get_embed_model` (51) · `_random_projection` (60) | il modello pigro e la proiezione cacheata |

🔑 **Il fallback è deterministico e senza modello**: una via che funziona anche a modello
assente, e che dà **sempre lo stesso risultato**. È lo stesso principio di
`select_relevant_span` in `grounding_gate` (*«Pure + deterministic — no embeddings»*): dove
si può, il prodotto tiene una strada che non dipende da un modello.

📌 `_get_embed_model` (51) è uno dei punti che ho curato oggi: importava
`sentence_transformers` **fuori** da `lock_import` (`cd644eff`).

## Quello che questa mappa NON dice

- **Non so se `via_hash` sia mai usata a runtime** o se resti un ramo teorico: un fallback
  mai esercitato è indistinguibile da un fallback rotto.
- **Non ho verificato la qualità del fallback**: «deterministico» non vuol dire «altrettanto
  buono», e il docstring non promette che lo sia.

---

*Mappato da ws5 (Piattaforma) su `7b9e8ca1`.*

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


### `verimem/config.py` — 6 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/config.py:19` `_project_root` | funzione | `verimem/config.py` | `tests/test_config_data_dir.py`; `tests/test_config_env.py` | NON MISURATO |
| 2 | `verimem/config.py:23` `_data_root` | funzione: Resolve the data root from env, else the shared ``_compat`` resolver. | `verimem/config.py` | `tests/test_config_data_dir.py`; `tests/test_config_env.py` (+1) | NON MISURATO |
| 3 | `verimem/config.py:98` `_load_env` | funzione: Load env vars from candidate .env files. | `verimem/config.py` | `tests/test_real_provider_smoke.py` | NON MISURATO |
| 4 | `verimem/config.py:120` `Config` | classe | `verimem/config.py` | `tests/test_embedding_dim_autodetect.py`; `tests/test_embedding_dim_guard.py` (+3) | NON MISURATO |
| 5 | `verimem/config.py:506` `Config.__post_init__` | funzione | **nessuno** | **nessuno** | NON MISURATO |
| 6 | `verimem/config.py:547` `Config.ensure_dirs` | funzione | `verimem/config.py` | **nessuno** | NON MISURATO |

### `verimem/resonator_text_bridge.py` — 5 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/resonator_text_bridge.py:51` `_get_embed_model` | funzione: Lazy load sentence-transformer (cycle 387 reuse pattern). | `verimem/resonator_text_bridge.py` | **nessuno** | NON MISURATO |
| 2 | `verimem/resonator_text_bridge.py:60` `_random_projection` | funzione: Cached random projection matrix (src_dim, dst_dim). | `verimem/resonator_text_bridge.py` | **nessuno** | NON MISURATO |
| 3 | `verimem/resonator_text_bridge.py:73` `text_to_atoms_via_embed` | funzione: Map text → tuple of atom indices via sentence-transformer + projection. | `verimem/resonator_text_bridge.py` | `tests/test_resonator_text_bridge.py` | NON MISURATO |
| 4 | `verimem/resonator_text_bridge.py:116` `text_to_atoms_via_hash` | funzione: Hash-only fallback (cycle 389 mirror). Deterministic, no model load. | `verimem/resonator_cli.py`; `verimem/resonator_text_bridge.py` | `tests/test_resonator_e2e_freetext.py`; `tests/test_resonator_text_bridge.py` | NON MISURATO |
| 5 | `verimem/resonator_text_bridge.py:133` `text_to_atoms_cached` | funzione: Cached entry point. method="embed" or "hash". | **nessuno** | `tests/test_resonator_text_bridge.py` | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





