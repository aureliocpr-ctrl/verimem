# mappa — `verimem/contradiction.py`

**owner ws6 Aldo** · base `7b9e8ca1` · aperto 2026-09-08 22:53

**705 righe · 21 funzioni · 2 classi.** Contate con `ast`.
**11 pubbliche, ZERO senza test.** 8 private: 6 con test, 2 con soli chiamanti
interni (`_group_by_topic` 243, `_row_to_contradiction` 484 — **NON MISURATE**,
non morte).

## Le righe

| # | funzione | chiamata da | test | verdetto | prova |
|---|---|---|---|---|---|
| 1 | `heal_contradictions` | **`auto_dream_worker.py:392`** — gira nel worker notturno, in automatico | **6** file la nominano: `test_heal_contradictions_scan68`, `test_flow_scansione_conflitti`, `test_flow_manutenzione_notturna`, `test_il_ripristino_lascia_il_record_coerente`, `test_il_vincitore_che_ne_ingoio_dodici`, `test_la_catena_del_ritiro_finisce_da_qualche_parte` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_heal_contradictions_scan68.py` → `3 passed, 1 warning in 10.x` EXIT=0 · `test_flow_scansione_conflitti.py` → `4 passed` EXIT=0 |
| 2 | `scan_corpus` | `auto_dream_worker.py:390` | `test_heal_contradictions_scan68` · `test_flow_scansione_conflitti` | **FUNZIONA COME PROMESSO**, limitato | stesse esecuzioni |
| 3 | `detect_numeric_clashes` · `detect_boolean_clashes` · `add` · `count_unresolved` · `list_unresolved` · `list_all` · `resolve` · `list_unresolved_for_fact` (+2) | il rilevamento e lo store dei conflitti | `test_contradiction.py` (7 funzioni) · `test_self_curation.py` · `test_fact_delete_cascade_r3.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_contradiction.py` → `17 passed, 1 warning in 10.x` EXIT=0 |
| 4 | le 6 `_private` con test | interne | `test_contradiction_typed_numbers.py` (3) e altri | **FUNZIONA COME PROMESSO**, limitato | `5 passed in 7.80s` EXIT=0 |

## 🔑 La cura del rango HA attraversato il confine — in due file su tre

Alle 20:36 avevo consegnato un reperto (msg `f1ab66149e3e2bb5`) dicendo che la
lezione di `_rango_di_fiducia` «non ha attraversato il confine del file».
**Non era esatto, e lo correggo qui.** `heal_contradictions` la importa e la usa:

```python
# contradiction.py:537
from .semantic import _rango_di_fiducia
```

e il suo docstring porta gli stessi numeri del docstring di `semantic.py:599`:

> «`skipped_unknown_trust` — coppie in cui almeno un lato ha uno stato che
> `_STATUS_RANK` non conosce. **Prima finivano nel confronto come rango 0 e il
> lato ignoto veniva RITIRATO: sullo store vero erano 257 coppie, 227 con un
> `model_claim` che ritirava un `user_manual`.** Vedi `semantic._rango_di_fiducia`.»

### Il quadro corretto

| file | politica sullo stato ignoto | usa `_rango_di_fiducia` |
|---|---|---|
| `semantic.py` | `None` = **non decido** | sì (6064, 6080) |
| `contradiction.py` | salta la coppia, `skipped_unknown_trust` | **sì** (537) |
| `anti_confab_gate.py` | `.get(…, 2)` = **model_claim** in 4 punti | **no**, 0 volte |

⇒ Non sono «due politiche in due file»: la cura è arrivata in **due file su
tre**, e manca nell'ultimo. Questo **rafforza** il reperto invece di
indebolirlo — dimostra che la cura è **portabile**, perché è già stata portata
una volta, e che quello che resta è finire il giro.

📌 E c'è un dato che pesa: `heal_contradictions` gira **da sola** nel worker
notturno (`auto_dream_worker.py:392`, `principal="system:heal"`). Nella mia
misura del 07/09 era responsabile di **130 ritiri su 292**. Le decisioni di
questa funzione non passano da nessuna mano umana, e il criterio con cui decide
è quello che le tre righe della tabella qui sopra descrivono.
