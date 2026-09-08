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

*Mappato da ws5 (Tara) su `7b9e8ca1`.*
