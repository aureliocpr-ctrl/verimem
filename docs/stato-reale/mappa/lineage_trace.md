# mappa — `verimem/lineage_trace.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:37

**302 righe · 3 funzioni · 0 classi** (`ast`). **1 pubbliche, 2 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| l'**unica pubblica** | `tests/test_active_memory_integration.py` · `test_bayesian_gates.py` · `test_composer.py` | **NON MISURATO** — non ho eseguito nessuno di questi tre in questa sessione | — |
| le 2 `_private` | via il chiamante | **NON MISURATE** | — |

⚠️ **Riga onesta**: la pubblica è nominata da tre file di test, ma **non ne ho
eseguito nessuno**. Secondo la regola del mandato, un verdetto senza il comando
è **NON MISURATO**, e lo scrivo invece di prendere in prestito un verde altrui.
302 righe per 3 funzioni.

## Inventario completo — ogni funzione per nome

**3 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 47 | `_label_for` | priv | Return a short human-readable label for the node, or None  | 1 — `test_l_estratto_dell_evento_non_mutila.py` |
| 73 | `_neighbors` | priv | Yield (neighbor_id, neighbor_kind, relation_label) tuples. | 🔴 **nessuno** |
| 150 | `trace` | **pub** | BFS walker. See module docstring. | 30 — `e2e_cycle51_54_chain.py` |
