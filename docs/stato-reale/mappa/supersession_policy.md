# mappa — `verimem/supersession_policy.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:37

**318 righe · 8 funzioni · 0 classi** (`ast`). **6 pubbliche, 2 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| `classify_write_relation` | `test_supersession_policy.py` · `test_il_fatto_di_bruno_archiviava_quello_di_anna.py` (4 file) | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_supersession_policy.py` → `7 passed in 6.97s` EXIT=0 |
| `is_same_source` (3 file) · `references_fact` (2) · `canonical_source_of` (1) · `declared_identity` (1) | i loro | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_il_fatto_di_bruno_archiviava_quello_di_anna.py` → `12 passed, 22 warnings` EXIT=0 |
| **`source_signature_of`** (62) | 🔴 **nessuno la nomina** | **NON MISURATA** direttamente — vedi sotto | `pytest -q tests/test_all_write_channels_judge_a_source.py` → `6 passed, 23 warnings` EXIT=0 (la esercita dal canale) |
| le 2 `_private` | via i chiamanti | **NON MISURATE** | — |

## 🪞 `source_signature_of` — e l'ho scritta io

Il conteggio per nome dice: cinque pubbliche su sei hanno almeno un test che le
nomina, **una no**.

```
canonical_source_of        1 file
classify_write_relation    4 file
declared_identity          1 file
is_same_source             3 file
references_fact            2 file
source_signature_of        0
```

I cinque controlli:

```
grep -rnw source_signature_of .   (tutto il repo, ogni tipo di file)
  → supersession_policy.py:25   dentro __all__
  → supersession_policy.py:62   la definizione
  → cli.py:4688                 from .supersession_policy import source_signature_of
  → cli.py:4739                 source_signature=source_signature_of(src) if src else None
```

⇒ **Viva, esportata in `__all__`, e usata dalla CLI.** Non è morta e non è senza
porta. Ma nessun test la nomina: la esercita `test_all_write_channels_judge_a_source.py`
(`6 passed`) **attraverso il canale**, non direttamente.

📌 **Questa funzione l'ho scritta io il 06/09** (la cura dei 345 fatti con
punteggio e senza firma), e il presidio che ho aggiunto lo stesso giorno chiede
«il canale conserva la fonte?» — non «questa funzione calcola la firma?». È
esattamente la forma che ho trovato negli altri file oggi, e me l'ero fatta
addosso senza vederla: **il test presidia il comportamento, la funzione resta
non misurata**. Nel caso specifico è la scelta giusta (il presidio dal canale è
più forte), ma il conteggio va detto com'è, e vale per me come per gli altri.

## Inventario completo — ogni funzione per nome

**8 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 35 | `references_fact` | **pub** | True when the new write NAMES the stored fact's id. | 2 — `test_due_guardie_si_coprono_e_nessuno_lo_sa.py` |
| 62 | `source_signature_of` | **pub** | L'impronta di un TESTO di fonte, o ``None`` se testo non c | 🔴 **nessuno** |
| 89 | `canonical_source_of` | **pub** | The reputation key of a fact's writer: the ``canonical_sou | 1 — `test_due_cartelle_diverse_non_sono_la_stessa_fonte.py` |
| 162 | `declared_identity` | **pub** | L'identita' DICHIARATA in un ``writer_principal``, o ``Non | 1 — `test_il_fatto_di_bruno_archiviava_quello_di_anna.py` |
| 196 | `is_same_source` | **pub** | Due fatti vengono dalla stessa penna? (la `canonical_sourc | 3 — `test_due_cartelle_diverse_non_sono_la_stessa_fonte.py` |
| 232 | `_coerce_ts` | priv |  | 🔴 **nessuno** |
| 243 | `_when_true` | priv | WHEN the fact is asserted TRUE — ``asserted_at`` (bi-tempo | 🔴 **nessuno** |
| 256 | `classify_write_relation` | **pub** | ``"evolution"`` iff ``new_fact`` is the SAME canonical sou | 4 — `test_il_fatto_di_bruno_archiviava_quello_di_anna.py` |
