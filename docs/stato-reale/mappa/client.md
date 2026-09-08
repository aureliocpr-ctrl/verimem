# Mappa — `verimem/client.py`

*ws3 Galileo. Parte assegnata: 20 file, 15.064 righe misurate sul mio albero
(l'indice dice 15.084: differenza di 20 righe, dichiarata, da riconciliare col
lead). Questo file: **4.339 righe, 80 fra funzioni e classi** (`ast`, escluse
le dunder). Ordine del mandato: prima ciò che sta dietro un claim del README.*

**Metodo, e cosa vale una riga di questa tabella.** La colonna «prova» porta il
comando eseguito e il suo esito; senza, il verdetto è `NON MISURATO` e si
scrive così. I chiamanti sono **letti**, non contati: `grep -w add` su
`verimem/` dà 200+ righe che sono `set.add`, `list.add`, `index.add` — la
regola del mandato («grep serve a trovare, non a contare») qui morde subito.

**Contatore**: 4 righe misurate su 80 · 3 claim del README collegati.

| # | funzione (file:riga) | cosa promette | chiamata da (letto) | test che la esercita | claim README (riga) | verdetto | prova (comando e esito) |
|---|---|---|---|---|---|---|---|
| 1 | `Memory.__init__` (client.py:556) | apre lo store: senza argomento «the library, the CLI and the MCP server all open the SAME store»; con un path, quello | `cli.py`, `mcp_server.py`, `gateway.py` (da leggere uno per uno: riga nella prossima passata) | `tests/test_moat_works_out_of_the_box.py` (8 passed) | README:428-429 | **FUNZIONA COME PROMESSO, con un avviso fuorviante** | `python prova_sdk.py` 08/09 20:31: `Memory(<tmp>/mappa.db)` scrive in `<tmp>/mappa.db` (106 KB creato) e **non** nello store di casa — verificato dopo: 0 righe con quei due id e 0 col topic `mappa/prova`, mtime del db di casa fermo alle 19:40. ⚠️ Ma il warning stampato dice «*using C:\Users\aurel\.engram (HIPPO_DATA_DIR wins)*» mentre il path esplicito vince davvero: il messaggio nomina un vincitore che non è quello dei fatti → **ticket T-MAP-1, owner Galileo** |
| 2 | `Memory.add` (client.py:613) | «Store `text` AFTER the anti-confab gate»; ritorna `{stored, id?, status, grounding_score, warnings, advice}` | `airgap.py:166`, `agent_guide.py:152` (esempi), + le tre porte (da leggere) | `tests/test_moat_works_out_of_the_box.py`, `tests/test_all_write_channels_judge_a_source.py`, `tests/test_adjudication_receipt.py` | README:441-442 (quickstart: entailed → admitted, confab → QUARANTINED) | **FUNZIONA COME PROMESSO** | `python prova_sdk.py` 08/09 20:31, store temporaneo: `add("Analytics runs on Postgres.", source=…)` → `status='model_claim'`, `grounding_score=99.916`, `layers=[]`, `stored=True`; `add("Analytics runs on MongoDB.", source=…)` → `status='quarantined'`, `grounding_score=0.613`, `quarantined_by='moat'`, `layers=['L4-grounding']`. E `pytest tests/test_moat_works_out_of_the_box.py` → **8 passed, EXIT=0** |
| 3 | `Memory.search` (client.py:1217) | «Recall the top-k facts for `query`, each with its provenance — `status` + write-time `grounding_score`» | `active_probe.py:59`, + porte (da leggere) | `tests/test_moat_works_out_of_the_box.py` | README:428-448 (l'SDK del quickstart) | **FUNZIONA COME PROMESSO (parziale: k=5 su un corpus di 2)** | stessa esecuzione: `search("Analytics", k=5)` → 1 hit, `flow.recall best=0.8424 n=1 tagliati=0`; il quarantinato **non** è servito, come promesso |
| 4 | `Memory.recall` (alias di `search`, client.py:1217) | i documenti e le porte la nominano accanto a `search`, come se fossero due letture | — (è lo stesso oggetto: chi chiama `recall` chiama `search`) | gli stessi di `search` | — | **FUNZIONA, ma è UN SOLO metodo con due nomi** | stessa esecuzione, riga finale: `Memory.recall is Memory.search` → **True**, e `[a for a in dir(Memory) if 'recall' in a]` → `['recall']`. ⚠️ **Prima avevo scritto in questa riga «NON ESISTE COME METODO SEPARATO»: sbagliato, e l'ho corretto prima di pubblicare** — l'output della prova diceva già «True» e l'ho letto male. Vale come reperto per chi legge la mappa: due nomi per una funzione fanno credere a due comportamenti |

## Le altre 76 voci — `NON MISURATO`, elencate per non perderle

Estratte con `ast` (banco `ws3-mappa-base.py`), con chiamanti e test **da
leggere**: `_json_default`, `_pretty`, `_fmt_score`, `AutoMemory` e i suoi
metodi, `search_documents` (1873), `index_document`, `ask`, `explain`,
`forget`, `restore_fact`, `supersede`, `stats`, `health`, `doctor_report`,
`export`, `import_facts`, `topics`, `by_topic`, `recent`, `pin`, `unpin`, e i
privati `_gate_and_store`, `_apply_gate_result`, `_entity_link`, `_provenance`,
`_receipt`, `_gate_mode`, `_should_ground`, … (elenco completo nel banco).

**Prossima passata, in quest'ordine**: ① i chiamanti veri delle tre porte per
`add`/`search` (letti, con la riga); ② `search_documents` e `ask` (stanno
dietro i claim README su documenti e domande); ③ il resto per righe
decrescenti.

## Ticket aperti da questa passata

- **T-MAP-1** (owner Galileo, 08/09 20:31) — `Memory(path)` con path esplicito
  scrive nel path, ma il warning di risoluzione dei DATA_DIR annuncia un altro
  vincitore («HIPPO_DATA_DIR wins»). Il messaggio è vero per gli accessori e
  falso per il fatto principale, e chi legge conclude di aver scritto altrove.
  Nessuna cura durante la mappa: qui si registra.
