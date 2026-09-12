# `verimem/trace_alignment.py` — 370 righe, 8 funzioni, 3 classi

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) ·
**08/09**.

## Che cosa promette

Date una traiettoria **fallita** e una **riuscita** che hanno usato la stessa
skill, allinearle passo per passo sulle *osservazioni* (la verità esterna, non le
azioni del modello) e trovare il **primo passo in cui le azioni divergono mentre
le osservazioni erano ancora allineate**. Quel punto è l'errore di predizione, il
substrato dell'assegnazione di merito.

**Claim del README**: nessuno.
**Chiamanti nel prodotto**: `wake.py:956` (`align_traces`,
`find_divergence_point`), sotto la bandiera `config.py:433
trace_alignment_enabled: bool = True` con soglia
`trace_alignment_obs_threshold: float = 0.55` (`config.py:440`).
⇒ **è acceso di default** e gira dentro il ciclo di veglia.

## Il perimetro

```
2 file di test (tests/test_trace_alignment.py, tests/test_active_memory_integration.py)
11 passed in 31,80 s                                           EXIT=0
verimem\trace_alignment.py   129 stmts   4 miss   54 branch   7 BrPart   94,0%
```

**Il file meglio coperto dei sei.** Le 4 righe scoperte sono, una per una:

| riga | codice | che cos'è |
|---|---|---|
| 104 | `text = text[:_OBS_TRIM]` | il taglio di un'osservazione troppo lunga |
| 112 | `return 0.0` | coseno fra vettori di norma nulla |
| 304 | `continue` | un salto dentro `_scan_input_divergence` |
| 314 | `continue` | idem |

Nessuna di queste è una promessa del docstring: sono rami difensivi e di
controllo. **NON MISURATI**, e scritti come tali — non «banali».

## La tabella

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | esercitata? | verdetto | prova |
|---|---|---|---|---|---|---|
| 1 | `verimem/trace_alignment.py:50` `AlignedPair` | la coppia di passi allineati | `Alignment` | ESEGUITA | **FUNZIONA COME PROMESSO** | 11 passed |
| 2 | `verimem/trace_alignment.py:58` `Alignment` | l'allineamento completo fra due tracce | `align_traces` → `wake.py:956` | ESEGUITA | **FUNZIONA COME PROMESSO** | 11 passed |
| 3 | `verimem/trace_alignment.py:63` `Alignment.length` | il numero di coppie allineate | `find_divergence_point` | ESEGUITA | **FUNZIONA COME PROMESSO** | 11 passed |
| 4 | `verimem/trace_alignment.py:68` `DivergencePoint` | il punto di divergenza trovato | `find_divergence_point` → `wake.py` | ESEGUITA | **FUNZIONA COME PROMESSO** | 11 passed |
| 5 | `verimem/trace_alignment.py:93` `_obs_vec` | il vettore dell'osservazione di un passo | `align_traces` | PARZIALE — 1 statement su 4 (:104) | **FUNZIONA COME PROMESSO** | il taglio a `_OBS_TRIM` non è esercitato |
| 6 | `verimem/trace_alignment.py:108` `_cosine` | il coseno fra due vettori | `align_traces` | PARZIALE — 1 su 5 (:112) | **FUNZIONA COME PROMESSO** | il caso «norma nulla» non è esercitato |
| 7 | `verimem/trace_alignment.py:129` `align_traces` | allinea sulle **osservazioni**, non sulle azioni | `wake.py:956` | **ESEGUITA** | **FUNZIONA COME PROMESSO** | 11 passed, 94,0% |
| 8 | `verimem/trace_alignment.py:217` `find_divergence_point` | il primo passo con azioni divergenti e osservazioni ancora allineate | `wake.py:956` | **ESEGUITA** | **FUNZIONA COME PROMESSO** | 11 passed |
| 9 | `verimem/trace_alignment.py:255` `_scan_action_divergence` | la scansione sulle azioni | `find_divergence_point` | **ESEGUITA** | **FUNZIONA COME PROMESSO** | 11 passed |
| 10 | `verimem/trace_alignment.py:281` `_scan_input_divergence` | la scansione sugli input | `find_divergence_point` | PARZIALE — 2 su 19 (:304, :314) | **FUNZIONA COME PROMESSO** | due `continue` non percorsi |
| 11 | `verimem/trace_alignment.py:336` `format_divergence` | la resa leggibile del punto di divergenza | `wake.py` | ESEGUITA | **FUNZIONA COME PROMESSO** | 11 passed |

## Perché questo file sta bene e gli altri no

Due file di test per 8 funzioni, e **le funzioni pubbliche sono tutte
esercitate**. La differenza rispetto a `ide.py` (61,0%) non è la dimensione: è
che qui i test chiamano le **funzioni**, mentre lì bisognerebbe passare da un
router HTTP e da un WebSocket, e nessuno ha scritto quel giro.

📌 Vale come dato per chi decide dove mettere il prossimo test: **il codice
raggiungibile solo attraverso un trasporto è quello che resta scoperto**, e non
perché sia meno importante.

## Che cosa NON ho misurato

- **Le 7 diramazioni parziali** (`BrPart 7`): non le ho aperte.
- **La soglia `trace_alignment_obs_threshold = 0.55`**: è il numero che decide
  quando due osservazioni sono «ancora allineate», ed è il cuore del metodo.
  Nessun test ne esplora il comportamento al variare del valore. **NON
  MISURATO** — e questo lo segnalo come il candidato di questo file: una soglia
  che nessuno ha mai fatto variare è un numero scelto una volta.
- Il modulo dichiara un **analogo cognitivo** (replay ippocampale, Foster &
  Wilson 2006). È una **motivazione**, non una promessa verificabile: non la
  tratto come un claim.
