# Copertura: quali test chiamano ognuna delle funzioni di `verimem/`

**Albero misurato**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **eseguito**: 2026-09-08 20:58 · owner **ws1 QA (QA)**.

## Che cosa dice questo numero, prima del numero

Il righello legge l'`ast` di **tutti** i file sotto `tests/` e cerca dove il
nome di ogni funzione di `verimem/` compare. Non esegue la suite: quindi
**«coperta» qui vuol dire NOMINATA da un test, non ESEGUITA**. Le due
distorsioni, dichiarate perché il numero non sia letto per quello che non è:

- **verso il basso** — una funzione raggiunta solo di rimbalzo (il test
  chiama `a()`, che chiama `b()`) risulta qui non coperta pur essendo
  eseguita. ⇒ le «mai nominate» sono un **limite superiore** del codice non
  esercitato, non l'elenco del codice morto.
- **verso l'alto** — due funzioni omonime in moduli diversi si confondono.
  Succede per **589 funzioni su 2973** (19.8%), ed è
  contato nella colonna `omonime` del JSON invece di essere nascosto.

Per questo ogni funzione ha un **livello**, non un sì/no:

| livello | che cosa lo produce | quanto vale |
|---|---|---|
| **QUALIFICATA** | il file di test importa il simbolo da quel modulo (`from verimem.x import f` → `f()`) o il modulo (`x.f()`) | attribuzione **certa** |
| **PER NOME** | il nome combacia ma nessun import lo lega a quel modulo (tipico: `oggetto.metodo()`) | attribuzione **probabile**, da leggere con `omonime` |
| **SOLO RIFERITA** | il nome compare **senza parentesi**: `target=f`, `key=f`, un decoratore, una tabella di dispatch | **eseguita o no**: il righello non può dirlo |
| **MAI NOMINATA** | il nome non compare in nessuno dei file di test | il reperto vero |

## I numeri

```
  funzioni in verimem/                    2973
  ✅ QUALIFICATA                           1006   (33.8%)
  🟡 PER NOME                               716   (24.1%)
  🔵 SOLO RIFERITA                           82   (2.8%)
  ⛔ MAI NOMINATA in tests/                1169   (39.3%)
```

## I controlli, che si sono accesi

Un righello che dicesse «tutto coperto» o «niente coperto» sarebbe
indistinguibile da uno rotto. Lo script **esce 3 e non stampa i numeri** se
uno dei tre cade:

- **SENTINELLA** — un nome inventato non deve comparire da nessuna parte. ✅
- **POSITIVO** — `verimem/prompt_injection.py:detect_injection`, che **so**
  chiamata (34 file di test la importano): risulta QUALIFICATA. ✅
- **NEGATIVO** — `verimem/syscall_bridge.py:engram_rate_stats`, che **so**
  non chiamata (`grep` dà 0 occorrenze in `tests/`): risulta MAI NOMINATA. ✅

I due casi sono stati scelti **leggendo il codice**, non prendendoli
dall'output dello script: un controllo estratto dal proprio risultato non
può falsificarlo.

## La lettura a campione — e il difetto che ha trovato

Campione riproducibile (`random.seed(1908)`): 5 dalle MAI NOMINATA e 5 dalle
QUALIFICATA, verificate a mano con `grep`.

- **5 su 5 delle QUALIFICATA** confermate: la riga della chiamata esiste nel
  test citato (`te.verify_head_signature(...)`, `assess_task_risk`,
  `dashboard_overview_v2(populated)`, `is_plan("pro")`,
  `assess_recall_confidence([])`).
- **4 su 5 delle MAI NOMINATA** confermate a 0 occorrenze.
- **La quinta ha rotto la prima versione del righello**:
  `verimem/semantic.py:5014:_work` risultava MAI CHIAMATA, ma è una closure
  passata a `threading.Thread(target=_work)` — **mai scritta con le
  parentesi**, quindi nessun `ast.Call` la nomina, eppure il thread la
  esegue. Stessa forma per `key=`, i decoratori, le tabelle di dispatch.

⇒ ho aggiunto il livello **SOLO RIFERITA**, e il reperto si è **sgonfiato**:
le «scoperte» passano da **1249 a 1168** (42,1% → 39,3%), a inventario
fermo su 2.970.

**E poi ho corretto anche l'inventario.** Il totale mi usciva **2.970**
contro i **2.973** dell'indice del lead. Non era l'albero: la mia discesa
nell'`ast` era scritta a mano e visitava solo `body` più i blocchi
`If/Try/With`, così mancava le funzioni annidate più in profondità —
`_pump` dentro l'`async with` di `ide.py:565` è una delle tre. Sostituita
con `ast.walk`, che attraversa ogni nodo: **2973**, il numero del lead.
🔑 **Una discesa scritta a mano dimentica sempre un tipo di nodo**; e quando
il tuo totale non torna con quello di un altro, il difetto è tuo finché non
hai guardato.

🔑 È la classe che ho in memoria dal 06/09: **il primo numero mi dava
ragione** (più codice scoperto = reperto più grosso), e per questo non faceva
attrito. La domanda che l'ha aperto è «se questo numero fosse sbagliato, chi
ne uscirebbe bene?».

## I file interamente non nominati da nessun test

**3 file** di `verimem/` (con almeno 3 funzioni) non hanno
**nessuna** funzione nominata in `tests/`. È il reperto più netto, perché non
dipende dall'ambiguità dei nomi:

| file | funzioni |
|---|---|
| `verimem/swarm/cli.py` | 7 |
| `verimem/sos_compensator.py` | 4 |
| `verimem/negation_scope.py` | 3 |

## I 25 file con più funzioni mai nominate

| file | mai nominate / totali |
|---|---|
| `verimem/cli.py` | **94** / 129 |
| `verimem/semantic.py` | **63** / 155 |
| `verimem/gateway.py` | **44** / 82 |
| `verimem/mcp_server.py` | **29** / 66 |
| `verimem/memory.py` | **24** / 83 |
| `verimem/quantity_match.py` | **24** / 47 |
| `verimem/anti_confab_gate.py` | **23** / 42 |
| `verimem/client.py` | **23** / 80 |
| `verimem/tui.py` | **22** / 26 |
| `verimem/ide.py` | **20** / 23 |
| `verimem/wake.py` | **17** / 58 |
| `verimem/dashboard_routes/settings.py` | **16** / 18 |
| `verimem/tools_extra.py` | **15** / 44 |
| `verimem/encode_service.py` | **13** / 37 |
| `verimem/atomic_claims.py` | **12** / 13 |
| `verimem/entity_kg.py` | **12** / 36 |
| `verimem/embedding.py` | **11** / 29 |
| `verimem/interactive_judge.py` | **11** / 24 |
| `verimem/observability.py` | **11** / 22 |
| `verimem/sleep.py` | **11** / 34 |
| `verimem/source_trust.py` | **11** / 33 |
| `verimem/dashboard.py` | **10** / 12 |
| `verimem/dream.py` | **10** / 18 |
| `verimem/local_grounding.py` | **10** / 33 |
| `verimem/wake_strategy.py` | **10** / 22 |

## Come rifarlo

```
python copertura_test.py <radice> --json copertura.json \
    --positivo verimem/prompt_injection.py:detect_injection \
    --negativo verimem/syscall_bridge.py:engram_rate_stats
```

Lo script sta nella scratchpad di ws1 e **non** nel repo: la finestra di push
di stasera accetta i soli `.md` (un `.py` in `scripts/` farebbe partire la
matrice). Il criterio è però scritto qui per intero, e i tre controlli sono
la parte che va rieseguita da chi non si fida — che è il modo giusto di
leggerlo.

## Che cosa manca ancora, detto invece che indovinato

- **NON MISURATO**: la copertura di *esecuzione*. Le 1168 «mai nominate» non
  sono codice morto finché una misura a runtime (`coverage`) non lo dice; il
  righello dice solo che nessun test le nomina.
- **NON MISURATO**: le funzioni PER NOME con `omonime > 1` non sono
  attribuite con certezza. Sono la parte da leggere una per una.
- La riga per funzione nel formato del mandato (promessa · chiamanti ·
  test · claim · verdetto · prova) è nei sei `.md` dei file di ws1; questo
  documento è la **colonna «test»** per tutte e 2.970.
