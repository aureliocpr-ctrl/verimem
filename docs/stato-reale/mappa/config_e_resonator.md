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

*Mappato da ws5 (Tara) su `7b9e8ca1`.*
