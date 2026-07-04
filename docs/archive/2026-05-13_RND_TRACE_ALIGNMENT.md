# Trace Alignment — il pezzo mancante della memoria attiva

**Data**: 2026-05-08
**Autore**: team-lead
**Tipo**: nota di laboratorio, non specifica

## Cosa ho trovato leggendo il codice

Stavo guardando `wake.py::_avoid_path_block`. Il sistema, quando trova un episodio fallito che ha usato la stessa skill della task corrente, mostra al modello:

> `Avoid path: action_1 → action_2 → action_3 → action_4. Diverge from this prefix as soon as it diverged then.`

Funziona. Ma è vago. "Diverge as soon as it diverged then" non dice **dove**. Il modello sa che qualcosa è andato storto ma deve indovinare a quale step.

E la cosa che mi ha bloccato: nei Sprint 6a, i 6 (poi 7) meccanismi di memoria attiva sono ispirati a NREM/REM consolidation. Ma il **prediction error encoding** — il segnale specifico che le place cells dell'ippocampo emettono nel reverse replay durante sharp-wave ripples — non è implementato. Il sistema ha forward replay ma non backward replay. Sa cosa fare ma non sa esattamente dove ha sbagliato l'ultima volta.

In neuroscienza c'è una linea di lavoro precisa:

- Foster & Wilson (2006) — *reverse replay during waking*
- Karlsson & Frank (2009) — *replays in CA1 are biased towards salient or recently aversive trajectories*
- Buzsáki (2015) — *sharp-wave ripples replay sequences in compressed time*

Tutto questo dice la stessa cosa: **il cervello allinea la traiettoria fallita a quella canonica e marca il punto di divergenza**. Quel marker è il segnale di credit assignment.

## Cosa ho costruito

`hippoagent/trace_alignment.py` (~250 LOC, zero LLM call).

L'idea in una frase: **Needleman-Wunsch sulle observation embeddings, divergence detection sulle action**. È *sequence alignment classico* (1970) applicato alle traiettorie ReAct.

### Perché allineare sulle observation, non sulle action

Le observation sono cosa il **mondo** ha detto. Le action sono cosa il **modello** ha scelto.

Se allineo sulle action, due trajectory che hanno preso azioni diverse a parità di situazione vengono trattate come se "fossero a step diversi" — esattamente il caso che voglio rilevare. Allineare sulle observation mi dà una timeline stabile e il mismatch sull'action è il segnale puro.

### Cosa è la "divergenza"

Il primo step dove:
1. La cosine similarity delle observation è sopra soglia (stessa situazione)
2. Le action delle due trajectory differiscono

Se non c'è nessuno step così, il fallimento non è attribuibile a un'azione sbagliata sotto una situazione confrontabile. Restituisco `None` invece di inventare un punto. Questo conta — ho un test (`test_no_divergence_when_observations_are_unrelated`) che lo verifica con osservazioni proprio ortogonali.

### Cosa appare nel prompt

Quando wake.py trova un fail e un success-twin, al posto del bare avoid-path il modello vede:

```
## DIVERGENCE FROM SUCCESS PATH
step 2: same situation (obs sim 0.64) but action diverged ('fs_write_file' vs 'apply_edit')
At that point the canonical observation was: 'edit applied successfully (1 hunk)'
The successful run took: apply_edit (consider this; deviate only with reason).
The failed run took: fs_write_file (this branch did not converge).
```

Il modello ora sa: passo, situazione, scelta giusta, scelta sbagliata. E_invece_ di dire "evita questo prefix" diciamo "ecco dove devi pensarci due volte".

## Cosa ho misurato (`scripts/demo_trace_alignment.py`)

Scenario reale, non sintetico: bug fix `return a - b → return a + b` su un calculator. Success path = 4 step `read → apply_edit → run_python → submit`. Failure path = 4 step `read → fs_write_file (overwrite) → run_python (errore import) → submit`.

Allineamento (sentence-transformers, non lo stub):

| Step | F-action       | S-action     | Obs sim | Action match |
|------|----------------|--------------|---------|--------------|
| 1    | fs_read_file   | fs_read_file | +1.00   | =            |
| 2    | fs_write_file  | apply_edit   | +0.64   | X            |
| 3    | run_python     | run_python   | +0.06   | =            |
| 4    | submit_solution| submit_solution | +0.24| =            |

Step 2 è il divergence point: stessa observation (0.64 > 0.55), action diverse. Step 3 ha action match ma obs sim 0.06 — è il *risultato* della divergenza, non la causa. Il detector si ferma al primo step utile e ignora il rumore downstream.

Funziona.

## Cosa NON funziona / limiti onesti

**Lo stub embedding mente sui simboli.**
Il `_StubModel` in `tests/conftest.py` usa hashing-trick su token `[A-Za-z0-9_]+` — i caratteri `+` e `-` non sono nemmeno catturati. `a + b` ed `a - b` collassano sullo stesso vettore. I test funzionano lo stesso perché ho scelto observation diverse anche nel testo, ma è qualcosa da ricordare.

**La soglia 0.55 è tarata per sentence-transformers/all-MiniLM-L6-v2.**
Modelli diversi hanno distribuzioni di cosine diverse. Ho esposto `CONFIG.trace_alignment_obs_threshold` come knob.

**Pick del success-twin è greedy su token overlap.**
Cercare il twin "ideale" sarebbe O(N) embedding sui task texts. Per ora la heuristica è "task con il maggior overlap di parole minuscole". Funziona nei casi reali (task simili tendono a condividere keyword) ma può fallire quando i task usano sinonimi. Marker per follow-up.

**Backward replay è solo half del meccanismo neurale completo.**
Le place cells fanno anche **forward sweep** (forward replay già implementato) e **time compression** durante sharp-wave ripples (replay accelerato). La trace alignment qui è sostanzialmente reverse-replay statico — la versione "compressa" cesserebbe di avere senso senza un loop di esecuzione, e per ora non lo aggiungo.

## Connessione con il resto del sistema

Quando guardi i 6 meccanismi originali del Sprint 6a:

| # | Meccanismo                | Stage  | Cost      | Trovato da agente |
|---|---------------------------|--------|-----------|-------------------|
| 1 | Procedural compilation    | NREM   | 1 LLM     | already there     |
| 2 | Forward replay            | wake   | 0 LLM     | already there     |
| 3 | Hebbian embedding         | wake   | 0 LLM     | already there     |
| 4 | Counterfactual REM        | REM    | 1 LLM     | already there     |
| 5 | Schema formation          | NREM   | 1 LLM     | already there     |
| 6 | Self-suggested practice   | sleep  | 1 LLM     | already there     |
| 7 | Working memory pruning    | wake   | 0 LLM     | Sprint 6a         |
| **8** | **Trace alignment / reverse replay** | **wake** | **0 LLM** | **this nota**     |

Il pattern: i meccanismi a 0 LLM call sono quelli che fanno "computation pura" sui ricordi già esistenti. Sono quelli più *biologici* — l'ippocampo non deve consultare la corteccia per fare reverse replay, lo fa con il proprio circuito. Sono anche i più cheap, e proprio per questo paradossalmente i più ignorati: nessuno li fa perché non sembrano "intelligenti", ma sono dove l'efficienza computazionale del cervello vive.

## Cosa rimane vivo come domanda

1. **Multiple twin alignment**. Allineare il fail contro 3 success diversi e prendere il divergence point più frequente o meno ambiguo darebbe un segnale più robusto. Ma costa O(K * N * M) e bisogna definire una metrica di "consenso". Idea: weight per fitness della skill comune.

2. **Divergence anche quando il fail ha visto cose diverse dal success**. Se step 2 ha obs differenti, attribuire la divergenza a step 1 non è ovvio — è una ricorsione: "il fail non ha visto le stesse cose perché al passo 1 ha preso un'azione diversa che ha cambiato il mondo". Trace alignment cattura solo il caso "decisione sbagliata sotto situazione comparabile". Il caso "decisione che ha cambiato la situazione successiva" richiede *causal* tracking, non *temporal* alignment.

3. **In wake.py, il blocco DIVERGENCE è sotto PREDICTED PATH (forward replay).** Ma cosa succede se vengono insieme? Il modello vede un percorso ottimo + un punto di pericolo. Sembra giusto ma vorrei misurare con un bench reale (Ollama + qwen2.5:7b) se il blocco aiuta o se aggiunge rumore.

4. **Test isolation per il modulo è banale** (zero state). Ma l'integrazione in `_avoid_path_block` ha un comportamento "se trovi divergence, sostituisci il bare prefix". È una scelta — l'alternativa è "mostrare entrambi". Ho scelto sostituzione perché il divergence è strettamente più informativo. Ma il bench reale potrebbe smentirmi.

## Codice

- `hippoagent/trace_alignment.py` — modulo nuovo, 250 LOC, no LLM
- `hippoagent/wake.py::_divergence_block` — integrazione in `_avoid_path_block`
- `hippoagent/config.py` — `trace_alignment_enabled`, `trace_alignment_obs_threshold`
- `tests/test_trace_alignment.py` — 6 test (6/6 verde)
- `scripts/demo_trace_alignment.py` — esecuzione manuale per ispezione
- 563/563 test verdi, ruff pulito.
