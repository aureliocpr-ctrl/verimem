# Il disegno esploso dello store: i componenti, le giunture, e chi le presidia

**Livello 3 del disegno esploso — 05/09/2026.** Ogni riga porta o la misura che
presidia la giuntura, o la parola **scoperta**. Nessuna cella è compilata a
memoria: dove non c'è un output, c'è scritto **non misurato**.

> Perché il livello 3 esiste: i livelli 1 e 2 dicono *quali difetti contano*,
> questo dice *dove stanno*. La forma che vale la pena scrivere non è «qui manca
> un presidio» — è **«qui il presidio c'è e copre due porte su tre»**. Un
> presidio parziale è più pericoloso di uno assente, perché fa sembrare la
> giuntura sorvegliata.

## 1. La mappa, in numeri misurati

```
moduli .py diretti in verimem/                      391
  raggiungibili dalle PORTE (mcp_server, cli,
  client, __init__ — chiusura degli import)         331
  non raggiungibili                                  60
     con `__main__` (forma di entry point)            6
     importati (AST) da tests/ o scripts/            52
     nessuno li importa                               2   → 441 righe
mcp_server.py                                    15.531 righe · 248 strumenti
```

I due che nessuno importa: `orchestration` (58 righe) e `syscall_bridge` (383).

**Il limite di questa misura, misurato invece che ammesso.** La chiusura è
statica: un import per nome-stringa non si vede. Quanto pesa qui?
`grep -rn "importlib|__import__" verimem/*.py` → **2 occorrenze in tutto**, e una
è `from importlib.metadata import version`, che legge la versione e non carica
moduli. Il buco è una riga, non una possibilità teorica.

**Il limite che invece è grande, e ha una prova.** La scansione guarda dentro il
repository. Un entry point avviato da FUORI — un hook di sessione, un task
schedulato, la configurazione MCP dell'utente — non compare. Prova:
`auto_dream_worker` risulta «nessuna prova di avvio» qui dentro, e nell'ambiente
di sviluppo di questo repo gira davvero (`Auto-Dream worker: cooldown`, `Last
auto-Dream: FIRED`). ⇒ **«nessuna prova di avvio nel repo» non è «non gira».**

| entry point | chi lo nomina, fuori da sé |
|---|---|
| `compose_daemon` | `README.md` |
| `dashboard_widget` | `engram_syscall_mcp.py` |
| `auto_dream_worker` | nessuno nel repo — **ma gira** (vedi sopra) |
| `engram_syscall_mcp` · `resonator_cli` · `transcript_ingest` | nessuno nel repo — **non misurato fuori** |

## 2. Le giunture, e chi le presidia

### G1 — `facts_recall` / `facts_search` scavalcano `Memory.search`

Le due porte MCP chiamano `a.semantic` direttamente e saltano il punto dove il
prodotto costruisce `Risultati`. Tutto ciò che vive lì non può raggiungerle per
costruzione.

**Difetti che ne sono nati, e il codice li conta da solo** (commento nel ramo di
`hippo_facts_recall`): il pavimento (29/07, si fermò a `explain`), il pavimento
di nuovo (02/08: `SDK 0 hit / MCP 3` con `ENGRAM_MIN_RELEVANCE=0.99`), il
ranking degradato, e — «⚠️ QUARTA GENERAZIONE DELLA STESSA CURA» — la guardia
messa su `Memory.search` due ore prima e mai arrivata di là.

**La quinta è l'esclusione per scadenza**, misurata il 05/09 su `build=5d7152d8`:

```
porta                      risponde  dichiara
SDK  Memory.recall         si        SI
CLI  recall                si        SI
CLI  ask (FIND)            si        no      ← toglie e tace
MCP  hippo_facts_recall    si        no      ← toglie e tace
MCP  hippo_facts_search    si        —          NON toglie: serve lo scaduto
```

**Presidio: `tests/test_tre_porte_una_risposta_sugli_scaduti.py`** (05/09),
gemello dichiarato di `test_tre_porte_una_risposta_sul_pavimento.py`. RED→GREEN
falsificato: `GREEN 2 passed EXIT=0` → difetto rimesso → `RED 1 failed EXIT=1` →
`GREEN 2 passed EXIT=0`.

⚠️ Il presidio copre il contratto («la porta lo dice»), **non il criterio**: sul
percorso dell'SDK il numero nasce da un confronto fra similarità anticorrelato
(in tema servito 0,8969 contro scaduto 0,8159 → tace; fuori tema 0,7552 contro
0,7600 → parlerebbe). Legare il presidio a un criterio non tarato lo renderebbe
rosso il giorno in cui lo si cura.

⚠️ **`ask` FIND resta scoperta**: il campo c'è e il criterio tace.

### G2 — le porte di SCRITTURA: il presidio esiste e copre due porte su tre

`tests/test_i_canali_di_scrittura_sono_allineati.py` (30/07) confronta **SDK
contro MCP** e ha funzionato: il buco che sorvegliava è chiuso. La **CLI non è
nel confronto**, e il buco è lì:

```
campo           SDK Memory.add   CLI remember   CLI save
valid_until          SI               SI           no
asserted_at          SI               no           SI
derives_from         SI               no           no
epistemic            NO               no           no
```

Le due porte CLI hanno **insiemi disgiunti**: chi vuole scadenza e asserzione non
ha una porta sola che le accetti. → **scoperta** dal lato CLI.

### G3 — lo schema temporale è acceso a metà

```
fatti totali        17575
  last_verified_at  17354   (98,7%)
  superseded_at      2328   (13,2%)
  asserted_at            1   (0,0%)
  valid_until            0   (0,0%)
```

Conseguenza, dal docstring di G2: `hippo_justified_audit` pubblicizza quattro
trigger di ritrattazione; due si reggono su `valid_until` e sulla cascata, e sul
corpus vivo davano `would_stale_ids 0 · would_contest_ids 0` — «non perché il
corpus è sano: perché dai canali che lo riempiono quelle colonne non sono
raggiungibili». Il 30/07 erano 0 su 6457 fatti; oggi 0 su 17575.
`verimem remember --valid-until` (04/09) è la prima porta CLI che può popolarla.

### G4 — due implementazioni della stessa regola di scadenza

`_fact_is_stale` (`semantic.py:1002`, riga per riga, percorsi freddi) e la
maschera vettoriale (`view_lv <= now & view_vu > now`, percorso caldo), che il
codice chiama «specchio vettoriale di `_fact_is_stale`». Due strade, una regola.
**Presidio del confronto fra le due: non misurato.** 26 file di test nominano
`valid_until`, ma nessuno confronta le due strade sullo stesso caso.

### G5 — il tier documenti si legge solo per nome

`documents.db` (5.378.048 byte, 73 righe, 59 `source_id` distinti, di cui **31
fuori da cartelle temporanee**: lavoro reale) e `document_index.db` (683 chunk).
Il banco degli attraversamenti (ws3, 05/09): `recall`/`search`/`ask` zero
chiamate al tier, `search_documents` una. **Indicizzato non è letto.**

## 3. Il metodo, perché queste celle valgano qualcosa

Tre misure dello stesso oggetto, nello stesso quarto d'ora, hanno dato **17, 0 e
2** moduli scoperti. Non cambiavano i dati: cambiava il criterio.

- **17** — il filtro `nome.endswith(f"{m}.py")`, messo per non contare un modulo
  come importatore di sé stesso, escludeva anche `tests/test_<modulo>.py`: i
  moduli **meglio coperti** finivano fra gli scoperti.
- **0** — filtro corretto, criterio ancora lessicale: un nome dentro un commento
  contava come un uso.
- **2** — import letti con l'AST, l'unica lettura che distingue un uso da una
  menzione.

Lo stesso è successo due volte sui path: `endswith("/<nome>.py")` non esclude
nulla su Windows, dove il separatore è `\`, e ogni file risultava «avviato da sé
stesso».

🔑 **Il primo numero era quello pubblicabile.** «2.821 righe morte» è un titolo;
«due file» non lo è. A fermarlo è stato un controllo positivo messo prima di
guardare il risultato — *un modulo che so coperto deve risultare coperto* — non
un revisore e non il caso.
