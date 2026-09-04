# La tabella dei concorrenti — e la nostra colonna, con dentro i nostri difetti

> **Owner**: ws8 (Corrado, release manager · il mondo esterno). **Metà di un
> deliverable**: la promessa, l'utente e il percorso in dieci minuti sono di ws7
> (Iris); qui ci sono i concorrenti, i numeri e le fonti. Il «numero di valore
> contro l'alternativa» si decide in due — scritto da me solo suona come
> marketing, scritto senza fonte non regge.
>
> **Regola di questa pagina, e vale per ogni cella**: o un numero **misurato da
> noi con il comando accanto**, o una **citazione con l'URL e la data di
> lettura**. Dove non ho né l'uno né l'altro la cella dice **NON VERIFICATO**, e
> ci resta anche quando ci farebbe comodo il contrario.

## Da dove viene, e cosa ho aggiunto

La ricerca sui tredici prodotti è del **02/09/2026** ed è già in casa:
`docs/ricerca/2026-09-02-stato-dell-arte-prodotti-e-benchmark.md` — 278 righe,
**54 URL**, stelle e licenze lette dall'API GitHub, download da `pypistats.org` e
`api.npmjs.org`. Non l'ho rifatta. Ho fatto due cose che mancavano:

1. **Ho chiuso il buco che il ricercatore stesso aveva dichiarato.** Testuale:
   *«su verimem il ricercatore si è basato solo sulla descrizione ricevuta — non
   l'ha ispezionato»*. Il 04/09 sera ho installato **il pacchetto pubblicato**
   (`pip install verimem==0.7.6` da PyPI, in un venv vergine) e l'ho usato da
   utente attraverso la porta MCP. La nostra colonna qui sotto è **misurata**,
   non descritta.
2. **Ho riletto le righe che invecchiano.** Una è già cambiata (§4).

## 1 · La colonna che ci distingue: verifica del fatto contro la sua fonte

Questa è la promessa centrale del prodotto, quindi è la prima colonna e non una
delle tante. Dal quadro del 02/09, su **tredici prodotti controllati leggendo
prompt e codice**: *zero gate di entailment al write*.

| prodotto | verifica vs fonte | cosa c'è al suo posto | fonte |
|---|---|---|---|
| mem0 | ❌ | «Single-pass ADD-only extraction — one LLM call, no UPDATE/DELETE. Memories accumulate; nothing is overwritten» (README verbatim) | https://github.com/mem0ai/mem0 · 02/09/2026 |
| Zep / Graphiti | ❌ | un'**istruzione dentro il prompt**: «Only extract facts that … are clearly stated or unambiguously implied in the CURRENT MESSAGE». Non è un controllo separato: nessuna decisione ammetti/rifiuta | `graphiti_core/prompts/extract_edges.py` · 02/09/2026 |
| Letta | ❌ | l'agente riscrive i blocchi di memoria | https://github.com/letta-ai/letta · 02/09/2026 |
| Cognee | ❌ | provenienza + catena di hash: dice **da dove viene**, non **se regge** | 02/09/2026 |
| Hindsight | ❌ | `source_fact_ids`, grounding ritirabile — di nuovo tracciabilità, non ammissione | 02/09/2026 |
| Supermemory | ❌ / ✅ parziale | l'unico con una **coda di revisione umana** su `isInference`: un umano, non un gate | 02/09/2026 |
| MemMachine | ❌ | il prompt **impone** di inferire | 02/09/2026 |
| altri sei | ❌ | — | quadro A.1 del 02/09 |
| **verimem 0.7.6** | ✅ **misurato sul pacchetto pubblicato** | il fatto con fonte viene giudicato e il punteggio è nel record: `judged=True grounding_score=99.92135620117188`; un claim che la fonte non regge finisce `status=quarantined layers=['L4-grounding','L4.1']` | smoke sui due bracci, 04/09/2026, wheel sha256 `a99f64bc…` |

In letteratura il gate esiste in **tre paper da maggio 2026** (ConsistencyGate,
Eywa, MemTX) e **nessuno dei tre è un prodotto installabile**.

## 2 · Il prezzo di quella colonna, che paghiamo noi

Una tabella dove i difetti sono tutti degli altri non serve a nessuno: il lettore
esterno la usa per non crederci. Questi sono **nostri**, misurati il 04/09 sul
pacchetto pubblicato.

| cosa | misura | come l'ho ottenuta |
|---|---|---|
| il primo salvataggio **con fonte** | **303 s** (`latency_ms=303072.2938`) | audit del server, `hippo_remember` con `source` |
| lo stesso **senza fonte** | **3,7 s** (`latency_ms=3740.7581`) | stessa sessione, stessa porta: unica differenza la presenza di `source` |
| in quei cinque minuti il server dice | **niente**, né su stdout né su stderr | un utente lo dà per piantato |
| peso dell'installazione | **1160 MB** di venv (torch 539, verimem 14), **4m47s** | `pip install verimem==0.7.6` in venv vergine + `du -sm` |
| strumenti esposti al client | **249**, di cui **248** col prefisso `hippo_` | `tools/list`, mentre `serverInfo` dice `{"name":"verimem"}` |
| note interne nelle descrizioni | «FORGIA #318 — Round 35», «Cycle #137 (2026-05-17)» | `tools/list`, descrizioni verbatim |
| lingua mista nell'output | `"ricerca": {"ramo": "or_fallback", "ordinati_per": "created_at DESC"}` | risposta di `hippo_facts_search` |
| errore di scrittura | `Input validation error: 'proposition' is a required property` — dice cosa manca, non cosa accetta | primo tentativo con `content` |
| l'audit del prodotto | **non registra le chiamate rifiutate** per validazione | `mcp_audit.log`: i due tentativi malformati non ci sono |

⚠️ **Limite dichiarato dei 303 s**: la misura è stata presa con
`mcp_preload_using_shared_daemon` attivo — il server appena installato ha usato
**un daemon già in esecuzione sulla macchina**. Lo store era isolato, il processo
no. **Non è ancora il tempo di un utente nuovo** e non va citato come tale finché
non lo rifaccio senza daemon.

## 3 · La scala, per non raccontarci storie

Tutti riletti da me il **04/09/2026** su `pypistats.org/api/packages/<nome>/recent`,
tranne dove indicato.

| pacchetto | download/mese | al giorno | letto |
|---|---|---|---|
| `mem0ai` | **3.452.711** | 81.673 | 04/09 (era 3.598.595 il 02/09: **in calo**) |
| `graphiti-core` | **1.023.898** | 24.025 | 04/09 |
| `supermemory` | 597.534 (PyPI) + 331.528 (npm) | — | 02/09 · ⚠️ rapporto settimana/mese anomalo (×36) |
| `letta` | **188.343** | 272 | 04/09 · ⚠️ `last_week` 2.421 contro `last_month` 188.343: **×78**, anomalia confermata anche oggi |
| **`verimem`** | **186** | **9** | **04/09** |

**Il rapporto è 18.563 a 1** contro mem0. È il numero che un lettore esterno
troverà da solo in trenta secondi, quindi lo scriviamo noi per primi.

Contesto, che lo spiega ma non lo cancella: **la 0.7.6 è su PyPI dal 04/09/2026
alle 17:08 UTC**, e sono **9** le versioni pubblicate in tutto
(`pypi.org/pypi/verimem/json`, letto 04/09). Un numero di trazione oggi misura
l'età del pacchetto, non il suo valore — ma è comunque il numero vero, e chi
valuta un progetto lo guarda.

🔑 **Come si legge questa riga senza mentirsi**: 186 al mese non è un mercato, è
un progetto appena pubblicato. La domanda utile non è «come saliamo», è «esiste
qualcuno che ha *bisogno* della colonna 1». Finché quella non ha una risposta con
un nome dentro, i download restano una misura dell'anagrafe.

## 4 · Una riga del 02/09 è già cambiata

Il documento elencava fra i «cosa fanno tutti e noi no»: *presenza nei canali di
scoperta … per PyPI il costo d'ingresso al registry è una riga nel README:
`<!-- mcp-name: io.github.<user>/<nome> -->`*.

Verificato oggi su `origin/main`:

    README.md:3:<!-- mcp-name: io.github.aureliocpr-ctrl/verimem -->

**La riga c'è.** Il requisito d'ingresso è soddisfatto; l'iscrizione al registry
è un'altra cosa e non l'ho fatta — sta dietro i quattro criteri del piano
versioni, e quella è una decisione di Aurelio, non mia.

## 5 · La finestra con una data, per chi decide

Il **secondo ciclo dell'Agent Memory Leaderboard apre il 20/09/2026** e chiede
**due endpoint pubblici**, `Add` e `Search`. È l'unica classifica trovata che non
sia gestita da chi ci compete dentro: HaluMem è di MemTensor e vince MemOS,
l'Agent Memory Benchmark è di vectorize.io e vince Hindsight, l'harness
`memory-benchmarks` è di mem0 e valuta solo Mem0. Mem0 è in classifica al **rank
19 con 42,07**.

Lo scrivo come informazione con una scadenza, non come proposta: l'apertura al
mondo è dopo i quattro criteri.

## Cosa questa pagina NON dice

- Non dice che i concorrenti siano peggiori: dice che **nessuno dei tredici
  verifica il fatto contro la sua fonte al momento della scrittura**, e che quasi
  tutti hanno numeri di trazione fra le tre e le sei cifre più dei nostri.
- Non ha una nostra riga su un **banco pubblico nominabile** accanto alla loro:
  quella la porta la ricerca (ws3), non io.
- Le tre righe «non trovato» sulla distribuzione (Smithery e canali di trazione)
  del documento del 02/09 **restano aperte**: nessuno le ha ancora chiuse.
