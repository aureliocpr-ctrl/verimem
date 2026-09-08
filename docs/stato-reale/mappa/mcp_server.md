# Mappa di `verimem/mcp_server.py` — ws2 «Varco» (Giano), 08/09

**Stato: 34 funzioni su 66.** Contatore vero, non stima: sotto c'è come l'ho ottenuto.

## Il denominatore, e perché me lo sono fatto dare due volte

`66` è il numero del mandato e l'ho verificato prima di usarlo, perché un
contatore con un denominatore sbagliato è peggio di nessun contatore.

- Con `ast.walk` su tutto l'albero: **66**.
- Con un mio visitatore che scendeva solo dentro funzioni e classi: **58**.
  Saltava le funzioni annidate che vivono dentro `if`/`try` di modulo.

I due non concordavano e ho confrontato invece di pubblicare il primo che avevo
in mano — l'errore che ho fatto due volte oggi (un parser che saltava righe in
silenzio; un `iterdir` non ricorsivo che ha dato 3513 KB dove `du` diceva 8,3 GB).

Composizione delle 66, che serve a leggere la mappa:

| dove vivono | quante |
|---|---|
| a livello di modulo | 55 |
| dentro `_call_tool_impl` (l'handler dei tool) | 8 |
| dentro la classe `_TokenBucket` | 2 |
| dentro `_apply_tool_namespace` | 1 |

⚠️ **`grep -c "def "` qui non è il numero**: conterebbe anche i `def` nelle
stringhe e nei commenti, e in questo file ce ne sono. Il mandato dice «niente
grep-conteggi» e questa è la ragione, misurata.

## Come leggere le righe

`promessa` è quello che la funzione dichiara di fare (docstring o nome).
`chiamata da` è chi la usa DAVVERO. `test` è il file che la esercita.
`claim README` dice se sta dietro una promessa pubblica. `verdetto` è mio.
`prova` è il comando che ho eseguito — se manca, la riga dice NON VERIFICATO.

---

## Parte 1 — le funzioni dietro un claim del README

Sono la strada dei tool `hippo_remember` / `hippo_facts_recall` /
`hippo_facts_search` / `hippo_recall_as_of`, cioè ciò che un agente tocca.

### `_ag` — riga 94
- **promessa**: «Process-wide agent, built exactly once, SENZA tenere il lock».
- **chiamata da**: quasi ogni handler di tool (`a = _ag()`).
- **claim README**: sì, indiretto — ogni promessa sui tool passa di qui.
- **verdetto**: ✅ fa quello che dice, ed è la superficie unica dell'agente.
- **prova**: `tests/test_il_build_dell_agent_non_tiene_il_lock.py` — 4 passed
  (misurato il 07/09, fatto `t1b-red-green-del-lock`).

### `_ok` — riga 270
- **promessa**: (nessuna docstring) impacchetta una risposta riuscita.
- **chiamata da**: tutti gli handler, alla fine del ramo felice.
- **claim README**: sì — è la forma di OGNI ricevuta che un agente legge.
- **verdetto**: 🟡 **senza docstring**, ed è la funzione che decide come appare
  ogni risposta del prodotto. Non è un difetto di comportamento: è che il punto
  più letto del file non dice cosa promette.
- **prova**: esercitata da ogni cella MCP; nessun test la nomina direttamente.

### `_conta_sostituiti` — riga 274
- **promessa**: «Quanti fatti sono stati RIMPIAZZATI da una scrittura successiva».
- **chiamata da**: il ramo di lettura, per l'avviso dei ritirati.
- **claim README**: sì — la supersessione è una promessa pubblica.
- **verdetto**: ✅.
- **prova**: `tests/test_ogni_superficie_di_lettura_dichiara_i_sostituiti.py`
  (dentro i 78 passed del 07/09).

### `_pavimento_di` — riga 296
- **promessa**: «Il pavimento calibrato, da QUALUNQUE forma di oggetto la
  lettura abbia reso».
- **chiamata da**: gli avvisi di lettura sulle porte MCP.
- **claim README**: sì — «abstention over hallucination» si regge sul pavimento.
- **verdetto**: ✅, ed è una superficie unica nata da una divergenza fra porte
  (il commento sopra la funzione la chiama «terza generazione della stessa cura»).
- **prova**: `tests/test_avviso_mcp_stessa_soglia_dell_sdk.py`,
  `tests/test_tre_porte_una_risposta_sul_pavimento.py`.

### `_avvisi_di_lettura` — riga 334
- **promessa**: «Gli avvisi che CLI e SDK danno già, portati alla porta [MCP]».
- **chiamata da**: gli handler di lettura.
- **claim README**: sì.
- **verdetto**: ✅ per gli avvisi che copre. ⚠️ **ma è il punto dove un avviso
  nuovo va aggiunto a mano**: è la giuntura che ha prodotto due cure di seguito
  (pavimento, ranking degradato — «⚠️ QUARTA GENERAZIONE DELLA STESSA CURA»).
- **prova**: `tests/test_l_avviso_non_usciva_dalla_porta_dell_agente.py`.

### `_err` — riga 532
- **promessa**: (nessuna docstring) la forma di un errore.
- **chiamata da**: ogni ramo di rifiuto.
- **claim README**: sì — un errore è la risposta che l'agente riceve quando
  qualcosa non va, e il prodotto promette di dire *perché*.
- **verdetto**: 🟡 senza docstring, come `_ok`.
- **prova**: NON VERIFICATO come funzione a sé.

### `_err_proposizione_vuota` — riga 546
- **promessa**: (dal nome) il rifiuto di una scrittura senza testo.
- **chiamata da**: `hippo_remember`.
- **claim README**: sì — è il primo errore che un agente incontra sbagliando.
- **verdetto**: ✅ nome che dice tutto.
- **prova**: NON VERIFICATO.

### `_auth_closed` — riga 207
- **promessa**: «Fail-closed receipt when the configured server rejected [the key]».
- **chiamata da**: il thin client, quando il server condiviso rifiuta la chiave.
- **claim README**: sì — il fail-closed è una promessa esplicita («refusing to
  fall back to a local store»).
- **verdetto**: ✅ e il nome dichiara la direzione del fallimento, che è la cosa
  che conta in un fail-closed.
- **prova**: NON VERIFICATO in questa sessione.

### `_remote_row` — riga 216
- **promessa**: «Shape a shared-server search hit like a local recall/search hit».
- **chiamata da**: il ramo delegato.
- **claim README**: sì — «N sessioni condividono il server» promette che la
  risposta sia la stessa.
- **verdetto**: ⚠️ **è una traduzione fra due forme**, cioè esattamente il punto
  dove una porta può dire una cosa diversa dall'altra senza che nessuno lo veda.
  Merita una cella sua: non l'ho trovata.
- **prova**: NON VERIFICATO.

### `_remote` — riga 181
- **promessa**: (nessuna docstring) il thin client verso il server condiviso.
- **chiamata da**: gli handler quando `VERIMEM_SERVER_URL` è impostata.
- **claim README**: sì.
- **verdetto**: 🟡 senza docstring su una funzione che decide se la lettura
  esce dal processo.
- **prova**: `tests/test_remote_memory.py` la esercita (34 passed il 07/09).

---

## Parte 2 — la spina dorsale: cosa attraversa OGNI chiamata

Le 24 funzioni qui sotto non le ho scelte per nome ma per posizione: sono
quelle che una `tools/call` percorre **prima** di arrivare al pezzo di
`_call_tool_impl` che risponde. Le elenco nell'ordine in cui girano, perché
in un dispatch l'ordine è la cosa che si sbaglia (un cancello dopo una
scorciatoia non è un cancello — `_call_tool_impl:7815` documenta esattamente
questo incidente: «they used to run after `a = _ag()`»).

### L'ordine, letto dal codice (righe 7797-7975)

| # | funzione | riga | cosa fa alla chiamata |
|---|---|---|---|
| 1 | `call_tool` | 7797 | l'unico handler registrato (`@server.call_tool()`); avvolge tutto nel guardiano degli hang |
| 2 | `_call_tool_impl` | 7806 | arma il cronometro, azzera l'alias, riscrive il nome |
| 3 | `_drop_none_args` | 613 | toglie i `null` di primo livello |
| 4 | `_ensure_derived_schemas` | 1602 | costruisce una volta gli schemi indulgenti |
| 5 | `_validate_input` | 1528 | valida (jsonschema, o `_manual_validate` 1495) |
| 6 | *(delega remota)* | 7853 | `_remote`/`_remote_row`/`_auth_closed` — Parte 1 |
| 7 | `_ag` | 7952 | costruisce l'agente locale — Parte 1 |
| 8 | `_rate_limit` | 1334 | solo per 2 tool su ~250 |
| 9 | `_capability_gate` | 1128 | il cancello delle capacità |
| 10 | *(l'handler del tool)* | — | il corpo vero |

`_audit` (1211) non è un passo: è chiamato **da ognuno** di questi passi
quando decide qualcosa, ed è l'unico posto da cui esce una traccia.

### `call_tool` — riga 7797
- **promessa**: «thin dispatch wrapper», guarda la chiamata per gli hang.
- **verdetto**: ✅ ed è deliberatamente **inline**, non su thread — la
  docstring dice perché («that broke stdio»). Budget 30 s, spegnibile con
  `HIPPO_HANG_TRACE_S=0`; è osservabilità, non annulla la chiamata.
- **prova**: `verimem/_hang_watchdog.py` esiste ed è importato lì; NON
  VERIFICATO che il dump atterri (non ho provocato un hang).

### `_call_tool_impl` — riga 7806 · **7784 righe, senza docstring**
- **promessa**: nessuna. È il corpo del prodotto alla porta degli agenti:
  metà del file (7784 righe su 15848) è questa funzione.
- **cosa fa nelle prime 40 righe**: `_REQUEST_START_NS` (da cui nasce
  `latency_ms`), `_REQUEST_TOOL_ALIAS`, e la riscrittura `engram_*` /
  `verimem_*` → `hippo_*`.
- **verdetto**: ⚠️ il commento a 7833 dice la cosa giusta e la dice bene —
  «da qui in poi il nome ricevuto non esiste più in nessuna variabile: si
  conserva ORA, o è perduto». È la funzione più lunga del prodotto e non
  dichiara niente di sé.
- **prova**: `end_lineno - lineno + 1 = 7783`, dallo stesso `ast` del
  denominatore (righe 7806-15588 su un file di 15848).

### `_drop_none_args` — riga 613
- **promessa**: un `null` JSON per un argomento OPZIONALE deve valere «usa il
  default», non schiantare.
- **verdetto**: ✅, e la docstring spiega il perché con il numero (~236 siti
  `int()/float()` che esplodevano). Tiene `0`, `False`, `""`, `[]`: solo
  `None` cade.
- ⚠️ **conseguenza che nessuno ha scritto**: gira PRIMA di `_validate_input`,
  quindi l'allargamento a `"null"` di ogni tipo dentro `_derive_lenient_schema`
  (1590) difende da un valore che, al primo livello, non può più arrivare.
  Non è un difetto — è una cintura sopra le bretelle. **Letto, non eseguito.**

### `_validate_input` (1528) · `_manual_validate` (1495) · `_derive_lenient_schema` (1566) · `_ensure_derived_schemas` (1602)
- **promessa**: ogni tool registrato valida almeno tipo ed enum (prima della
  §305 ne validavano ~15 su ~228).
- **verdetto sul disegno**: ✅ due strati, e la precedenza è dichiarata: lo
  schema scritto a mano vince, quello derivato copre il resto.
- 🔴 **il reperto**: i due validatori dello STESSO input non concordano, e la
  discordanza è invisibile perché il secondo non gira mai.
  - `_manual_validate` esiste solo nel ramo `except ImportError: jsonschema`.
  - `jsonschema>=4.0.0` è **dipendenza dichiarata** (`pyproject.toml:57`) ed è
    installata (4.26.0). Quindi in un'installazione corretta quel ramo è
    irraggiungibile.
  - e se girasse, sarebbe **più permissivo**: usa `isinstance(v, int)`, che in
    Python è vero per un booleano.

    ```
    jsonschema  k=True   -> RIFIUTATO: True is not of type 'integer'
    jsonschema  k=5      -> AMMESSO
    isinstance(True,int) -> True
    ```
  - **verdetto**: 🟡 non è un difetto vivo (il ramo non gira), è **codice di
    riserva che si comporta diversamente dal titolare**. Se un giorno la
    riserva entra in campo, valida meno. Lo scrivo qui perché è il caso che
    un lettore non vede: la funzione c'è, i test la possono chiamare
    direttamente, e il prodotto non la usa mai. **Niente cura: è una mappa.**

### `_rate_limit` (1334) · `_get_bucket` (1325) · `_bucket_for` (1313) · `_TokenBucket.__init__` (1291) · `_TokenBucket.take` (1298)
- **promessa**: «True se la chiamata è permessa, False se limitata».
- **verdetto**: ✅ token bucket in memoria, con lock, 1/min di default e
  override per tool via `HIPPO_MCP_RATELIMIT_<TOOL>_RPM`.
- ⚠️ **perimetro, non difetto**: `_RATE_LIMITED_TOOLS` (1541) contiene **due**
  nomi — `hippo_run_task` e `hippo_consolidate`. Il commento lo dichiara
  («heavy ops only»). Chi legge «rate limiting» in un elenco di funzioni
  crede che copra la porta: copre due tool.
- **prova**: `frozenset({"hippo_run_task", "hippo_consolidate"})`, riga 1541-1543.

### `_capability_gate` (1128) · `_capability_gate_mode` (1102) · `_audit_capability_call` (1064) · `_bypass_dal_registro` (1055)
- **promessa** (commento a 7959-7969, sopra la chiamata): «every call_tool
  invocation runs through `_capability_gate()` which: … **Hard-blocks**
  DESTRUCTIVE / requires_confirm … **Emits an audit row regardless**».
- **verdetto**: 🔴 **la frase è vera e conclude il falso.** Ogni chiamata
  *attraversa* la funzione; ma la prima cosa che la funzione fa è

  ```
  mode = _capability_gate_mode()
  if mode == "off":
      return True, None
  ```

  e `_capability_gate_mode()` rende `"off"` a meno che
  `ENGRAM_CAPABILITY_GATE` non sia impostata. Nel modo di default non blocca
  niente **e non scrive nemmeno la riga di audit** che il commento promette
  «regardless».
- **la misura, con il denominatore e la finestra**:

  ```
  file: C:\Users\aurel\.engram\mcp_audit.log   (2.100.293 byte, nessun .1: mai ruotato)
  righe leggibili: 15432   finestra: dal 2026-05-08 01:41 al 2026-09-08 19:43
  controllo POSITIVO  '"outcome":"ok"'          -> 11604
  cap_allow|cap_deny|cap_bypass                 ->     5
  ```

  Le cinque, tutte con `[mode=enforce]` nel campo `reason`: una del
  2026-06-03 (`sandbox_exec`), quattro del **2026-07-09** — due `cap_allow` e
  due `cap_deny` (`hippo_fact_forget`, `hippo_forget_scope`). Da allora,
  nessuna. **Il cancello ha deciso 5 volte su 15.432 chiamate registrate in
  quattro mesi (0,03%), l'ultima due mesi fa.**
- **la parte onesta, e conta**: il README **non promette** questo cancello —
  ho cercato `capability|gating|fail-closed` e l'unico esito è la parola
  «Capability» come intestazione di una tabella di confronto (riga 701).
  Quindi **nessuna promessa pubblica è rotta**: il default OFF è una
  decisione dichiarata nella docstring (2026-05-27, «175/215 tool bloccati
  durante sviluppo single-user»). E le due `cap_deny` provano che quando è
  acceso **blocca davvero**. Il reperto non è «è rotto»: è che *il commento
  nel dispatch descrive il modo acceso come se fosse il modo normale*, e
  quello è il testo che un lettore del codice incontra per primo.
- **la decisione, che non è mia**: sta in memoria come preferenza di Aurelio
  («niente default OFF»). La segnalo, non la eseguo — il mandato dice
  niente cure.
- `_bypass_dal_registro` (1055): ✅ **superficie unica nata da una divergenza**
  — prima del 03/09 la lista dei tool esentati era scritta a mano qui e nella
  matrice, «28 voci contro 20, cinque in comune, e due nomi che non
  corrispondevano a nessun tool». Ora deriva da `REGISTRY._caps`.
- `_audit_capability_call` (1064): ✅ e la scelta di registrare **le chiavi
  degli argomenti, mai i valori** è motivata e presidiata da un test
  (`test_i_valori_NON_finiscono_nel_log`).

### `_audit` (1211) · `_audit_log_path` (976) · `_rotate_audit_if_needed` (1016)
- **promessa**: una riga JSONL per chiamata, best-effort, mai solleva.
- **verdetto**: ✅ ed è la funzione con la docstring migliore del file: dice
  che `outcome` è un'**etichetta chiusa** e racconta il difetto che l'ha
  insegnato — conteggi incastrati nel nome, 52 valori distinti di cui 27 con
  cifre dentro, e `hippo_summary_topic` che risultava «100% non-ok» su
  quindici chiamate tutte riuscite (misurato 2026-07-31).
- **è qui che nasce `latency_ms`**: `_REQUEST_START_NS` viene armata in cima a
  `_call_tool_impl` e letta qui. Cioè il numero misura **tutta** la chiamata,
  gate e delega compresi — è il metro con cui è stato visto il primo
  `remember` con fonte a 303 s.
- ⚠️ **scudo PII**: gli argomenti finiscono nel log solo come
  `sha256[:16]`. Deliberato, e non invertibile: da una riga non si sa con
  quale campo il tool sia stato chiamato (è la ragione per cui
  `_audit_capability_call` aggiunge le chiavi a parte).
- `_rotate_audit_if_needed`: ✅ 5 MB, un solo backup `.1`, `os.replace`
  atomico. **Non è mai scattato** su questa macchina: 2,1 MB e nessun `.1`.

### `_iso_day` (576) · `_apply_live_filter` (593)
- `_iso_day`: ✅ epoch → `YYYY-MM-DD`, e la docstring dice a chi serve —
  all'agente che legge, per ragionare sul tempo. `None` su 0 o non numerico.
- `_apply_live_filter`: ✅ ed è **la classe ④ della memoria (il bug è la
  giuntura)** scritta dall'autore stesso: la prima versione filtrava solo
  `facts` e lasciava passare `facts_ranked`, «il segnale di retrieval
  PRIMARIO». Due liste della stessa cosa, una sola filtrata.

### `list_tools` (7728) · `_apply_tool_namespace` (7741) · `_riferimento` (7759)
- **promessa**: il registro completo, filtrato da `ENGRAM_MCP_TOOLS_PREFIX` e
  poi rinominato se `VERIMEM_TOOL_NAMESPACE=verimem`.
- **verdetto**: ✅ e `_apply_tool_namespace` è l'unico punto del file che ha
  già imparato la lezione dello SWEEP: non rinomina solo `name`, riscrive
  anche i **riferimenti dentro le descrizioni** — «misurato 16/08: 50 tool su
  248, 61 riferimenti». Senza, il prodotto rimandava a nomi che non espone.
- `_riferimento` (nested, senza docstring): il commento sopra vale una
  docstring — riscrive **solo** ciò che corrisponde a un tool davvero
  rinominato, perché `hippo_facts_*` è una famiglia e `HIPPO_DISABLED` una
  variabile d'ambiente.
- ⚠️ **asimmetria per disegno**: il filtro dei prefissi agisce sulla
  DISCOVERY; `_call_tool_impl` dispaccia lo stesso qualunque nome registrato
  (commento a 1629). Un tool nascosto resta chiamabile. È dichiarato.

---

## Cosa resta

32 funzioni su 66: le 8 dentro `_call_tool_impl` (`_props`, `_cos`,
`_encode_skill`, `_cosine`, `_default_coherence_hook`, `_key_fitness`,
`_key_recency`, `_key_activity` — nessuna con docstring), e 24 del modulo,
fra cui le superfici di sicurezza (`_looks_shell_like`, `_doc_path_allowed`,
`_sandbox_policy`, `_shell_perm_enabled`, `_forget_cross_scope_denied`), la
costruzione dei fatti (`_build_fact`, `_content_hash_id`, `_build_episode`),
le risorse (`list_resources`, `read_resource`, `_read_resource_body`) e
`main`.

### Il dato sulle docstring — e la correzione al mio stesso numero

Alla Parte 1 avevo scritto «sei funzioni su dieci non hanno docstring». Sulle
**66** il tasso è un altro, e la differenza è tutta nel campione che mi ero
scelto:

```
funzioni totali: 66 | senza docstring: 23 (35%)
```

**Il 35%, non il 60%.** Il mio campione di dieci era la testa del file, dove
stanno gli helper minuti; l'ho pubblicato come «un dato che emerge» e non
reggeva l'allargamento. È la forma che ho già trovato due volte oggi su
misure altrui — un numero letto su una finestra scelta da me — e valeva anche
per me. La riga della Parte 1 resta scritta apposta, con questa accanto.

E la lista intera cambia anche il *senso* del reperto. Le 23 senza docstring,
per lunghezza:

| lunghezza | quante | esempi |
|---|---|---|
| ≤ 12 righe | 20 | `_ok` (2), `_err` (2), `_key_fitness` (2), `_bucket_for` (6) |
| 13-25 righe | 2 | `_default_coherence_hook` (18), `list_resources` (25) |
| **7783 righe** | **1** | **`_call_tool_impl`** |

Una funzione di **due** righe che si chiama `_ok` e impacchetta una risposta
riuscita non ha un problema di documentazione: il nome è la docstring. Alla
Parte 1 le avevo messe sullo stesso piano, ed era sbagliato. Il reperto vero
è **uno solo**, ed è quello che il conteggio percentuale nasconde: metà del
file — 7783 righe su 15848 — è una funzione senza una riga che dica cosa
promette, e ci passa dentro ogni chiamata che un agente fa.

Le tre da guardare dopo, per lunghezza e non per posizione: `list_resources`
(25), `_default_coherence_hook` (18), `_remote` (24, già in Parte 1).
