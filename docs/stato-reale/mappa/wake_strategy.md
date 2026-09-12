# `verimem/wake_strategy.py` — 439 righe, 22 funzioni

*«Encoding strategies for the wake loop.»* **È qui che vivono davvero le due encoding**, e
la sua esistenza spiega perché `wake.py` non è duplicato. Mappato su `7b9e8ca1`.

---

## 1. Il pattern strategy, esplicito: una base con OTTO metodi e due implementazioni

| metodo (base, 109-157) | cosa varia fra native-tools e ReAct |
|---|---|
| `system_prompt` (109) | il prompt di sistema per quell'encoding |
| `initial_messages` (112) | *«Both encodings start with one user message»* — **questo NON varia**, ed è dichiarato |
| `call` (118) | invocare l'LLM e **parsare** la risposta in un `ParsedTurn` |
| `on_no_tool_calls` (124) | cosa fare quando il turno non produce chiamate |
| `append_assistant` (142) | come si accoda il turno dell'assistente |
| `append_observations` (148) | come si accodano le osservazioni |
| `prune` (157) | *«Working-memory pruning specific to this encoding»* |

Due implementazioni complete: righe **180-283** e **346-428**.

🔑 **Questo chiude il sospetto che avevo scritto su `wake.py` e poi ritirato**: i due
`_prune_working_memory*` là non sono copie perché **`prune` è un metodo della strategia**, e
l'algoritmo generico sta in `working_memory.prune_messages`. Tre livelli, ognuno col suo
mestiere: l'algoritmo, la strategia, il wiring. **Il design è coerente, e l'avevo quasi
accusato al contrario.**

---

## 2. `parse_react_step` (311) — il parser che si aspetta un LLM disordinato

> *«Tolerant ReAct parser: handles markdown fences, asterisks, …»*

⇒ Il testo di un LLM arriva **sporco** (fence markdown, asterischi, maiuscole variabili), e
il parser lo mette in conto invece di pretendere una forma esatta. È il complemento
dell'encoding native-tools, dove la struttura la garantisce l'API.

📌 **Chi sceglie fra i due encoding sceglie anche fra due modi di sbagliare**: il ReAct può
parsare male una risposta valida; il native-tools dipende da un'API che deve supportare i
tool. Il file non nasconde la differenza — la incapsula.

---

## 3. Le 22 funzioni

8 nella base + 7+7 nelle due implementazioni concrete + `parse_react_step` (modulo).
Tutte pubbliche tranne i due `__init__`.

---

## 4. Quello che questa mappa NON dice — dichiarato

- ~~Non ho verificato che le due implementazioni coprano gli stessi metodi~~ →
  **VERIFICATO, e chiude in positivo.** Avevo scritto che non lo eseguivo «perché il turno è
  agli sgoccioli»: costava cinque secondi, quindi l'ho fatto.

      WakeStrategy (base)   7 metodi
      NativeToolsStrategy   6   →  manca solo: initial_messages
      ReActStrategy         6   →  manca solo: initial_messages

  **Simmetria perfetta**, e l'unico metodo non sovrascritto è proprio quello che la base
  dichiara di tenere per sé: *«Both encodings start with one user message — kept on the
  [base]»*. Non è una lacuna, è la parte che per progetto non varia.
- **`parse_react_step` non l'ho esercitata** su un input sporco vero.

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


### `verimem/wake_strategy.py` — 27 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/wake_strategy.py:68` `ParsedTurn` | classe: The strategy-uniform view of one LLM turn. | `verimem/wake.py`; `verimem/wake_strategy.py` | **nessuno** | NON MISURATO |
| 2 | `verimem/wake_strategy.py:85` `ToolObservation` | classe: Result of executing one tool call, ready for the next turn. | `verimem/wake.py`; `verimem/wake_strategy.py` | **nessuno** | NON MISURATO |
| 3 | `verimem/wake_strategy.py:95` `WakeStrategy` | classe: Per-encoding behaviour for the wake loop. | `verimem/wake.py`; `verimem/wake_strategy.py` | **nessuno** | NON MISURATO |
| 4 | `verimem/wake_strategy.py:109` `WakeStrategy.system_prompt` | funzione: Return the system prompt for this encoding. | `verimem/wake.py` | `tests/test_mcp_sampling_llm.py` | NON MISURATO |
| 5 | `verimem/wake_strategy.py:112` `WakeStrategy.initial_messages` | funzione: Both encodings start with one user message — kept on the | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 6 | `verimem/wake_strategy.py:118` `WakeStrategy.call` | funzione: Invoke the LLM and parse its response into a `ParsedTurn`. | `verimem/wake.py` | `tests/test_embedding_preload.py`; `tests/test_governo_stesse_chiavi_su_ogni_porta.py` (+4) | NON MISURATO |
| 7 | `verimem/wake_strategy.py:124` `WakeStrategy.on_no_tool_calls` | funzione: Handle a turn that produced zero tool calls. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 8 | `verimem/wake_strategy.py:142` `WakeStrategy.append_assistant` | funzione: Append the assistant's turn to `messages` for the next iteration. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 9 | `verimem/wake_strategy.py:148` `WakeStrategy.append_observations` | funzione: Append the tool observations to `messages` for the next turn. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 10 | `verimem/wake_strategy.py:157` `WakeStrategy.prune` | funzione: Working-memory pruning specific to this encoding. | `verimem/smart_pruning.py`; `verimem/wake.py` | `tests/test_transcript_prune.py` | NON MISURATO |
| 11 | `verimem/wake_strategy.py:170` `NativeToolsStrategy` | classe: Driver for providers that support native tool-use. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 12 | `verimem/wake_strategy.py:180` `NativeToolsStrategy.__init__` | funzione | `verimem/client.py`; `verimem/document_index.py` (+2) | `tests/test_i_default_che_il_readme_dichiara.py`; `tests/test_windows_no_console_popup.py` | NON MISURATO |
| 13 | `verimem/wake_strategy.py:183` `NativeToolsStrategy.system_prompt` | funzione | `verimem/wake.py` | `tests/test_mcp_sampling_llm.py` | NON MISURATO |
| 14 | `verimem/wake_strategy.py:207` `NativeToolsStrategy.call` | funzione | `verimem/wake.py` | `tests/test_embedding_preload.py`; `tests/test_governo_stesse_chiavi_su_ogni_porta.py` (+4) | NON MISURATO |
| 15 | `verimem/wake_strategy.py:222` `NativeToolsStrategy.on_no_tool_calls` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 16 | `verimem/wake_strategy.py:242` `NativeToolsStrategy.append_assistant` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 17 | `verimem/wake_strategy.py:258` `NativeToolsStrategy.append_observations` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 18 | `verimem/wake_strategy.py:283` `NativeToolsStrategy.prune` | funzione | `verimem/smart_pruning.py`; `verimem/wake.py` | `tests/test_transcript_prune.py` | NON MISURATO |
| 19 | `verimem/wake_strategy.py:311` `parse_react_step` | funzione: Tolerant ReAct parser: handles markdown fences, asterisks, | `verimem/wake_strategy.py` | `tests/test_wake.py`; `tests/test_wake_extra.py` | NON MISURATO |
| 20 | `verimem/wake_strategy.py:336` `ReActStrategy` | classe: Driver for providers without native tool-use. | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 21 | `verimem/wake_strategy.py:346` `ReActStrategy.__init__` | funzione | `verimem/client.py`; `verimem/document_index.py` (+2) | `tests/test_i_default_che_il_readme_dichiara.py`; `tests/test_windows_no_console_popup.py` | NON MISURATO |
| 22 | `verimem/wake_strategy.py:352` `ReActStrategy.system_prompt` | funzione | `verimem/wake.py` | `tests/test_mcp_sampling_llm.py` | NON MISURATO |
| 23 | `verimem/wake_strategy.py:357` `ReActStrategy.call` | funzione | `verimem/wake.py` | `tests/test_embedding_preload.py`; `tests/test_governo_stesse_chiavi_su_ogni_porta.py` (+4) | NON MISURATO |
| 24 | `verimem/wake_strategy.py:393` `ReActStrategy.on_no_tool_calls` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 25 | `verimem/wake_strategy.py:408` `ReActStrategy.append_assistant` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 26 | `verimem/wake_strategy.py:414` `ReActStrategy.append_observations` | funzione | `verimem/wake.py` | **nessuno** | NON MISURATO |
| 27 | `verimem/wake_strategy.py:428` `ReActStrategy.prune` | funzione | `verimem/smart_pruning.py`; `verimem/wake.py` | `tests/test_transcript_prune.py` | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





