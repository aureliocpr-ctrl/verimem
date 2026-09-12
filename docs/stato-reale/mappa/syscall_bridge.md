# `verimem/syscall_bridge.py` — 383 righe, 11 funzioni

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) ·
**08/09**.

## Che cosa promette

Un **confine tipizzato** per le operazioni di memoria: ogni chiamata passa da
`engram_invoke`, che valida l'op contro un manifesto (anti-allucinazione),
applica un rate-limit e scrive una riga di audit JSONL.

**Claim del README**: nessuno (`grep -inw "syscall\|engram_invoke" README.md` → 0).
**Chiamanti nel prodotto**: `dashboard_widget.py:48` (legge il manifesto, i
bucket del rate-limit e la coda dell'audit) e `capability_token.py`, che
descrive il token verificato da `engram_invoke`.

## Il perimetro

```
5 file di test (test_syscall_bridge.py, test_capability_token.py,
                test_op_supervisor.py, test_dashboard_widget.py,
                test_engram_stack_e2e.py)
25 passed in 79,67 s                                           EXIT=0
verimem\syscall_bridge.py   153 stmts   35 miss   42 branch   10 BrPart   73,8%
```

## Il contratto falsificabile del docstring — **provato**

`engram_invoke` dichiara a `:215-220`, testualmente:

```
(a) op not in manifest → ok=False, blocked_by="not_in_manifest"
(b) rate-limited       → ok=False, blocked_by="rate_limit_exceeded"
(c) handler raises     → ok=False, blocked_by="exception"
(d) success            → ok=True,  result=handler output
All paths write 1 audit JSONL row.
```

Un contratto scritto così non si crede: si prova. Banco
`contratto_engram_invoke.py`, log di audit in una cartella temporanea (**nessun
contatto con lo store vivo**):

| clausola | esito misurato | audit |
|---|---|---|
| **(a)** op fuori dal manifesto | `ok=False`, `blocked_by='not_in_manifest'` ✅ | **1 riga** ✅ |
| **(b)** rate limit | **38 chiamate su 40 bloccate** ✅ | **40 righe su 40 chiamate** ✅ |
| **(c)** handler che solleva | `ok=False`, `blocked_by='exception'` ✅ | **1 riga** ✅ |
| **(d)** successo | **NON PROVATO** — chiamerebbe un handler vero sullo store | — |

La riga di audit dell'ultimo caso porta:
`op`, `actor`, `args_keys`, `audit_id`, `blocked_by`, `elapsed_sec`,
`exception`, `message`, `ok`, `ts` — e **non** i valori degli argomenti, come il
commento a `:230` promette («*Don't audit args VALUES; just keys*»).

⇒ **la clausola dell'audit vale anche per le chiamate BLOCCATE**, che è la parte
che nessuno guarda perché non cambia il valore di ritorno.

⚠️ **Un costo che non avevo previsto e che dichiaro**: la clausola (b) chiama
l'handler vero di `recall`, che **carica l'embedder** (103 pesi di torch). Due
chiamate su 40 sono passate. Nessuna scrittura, ma è CPU che non avevo messo a
claim: un banco del rate-limit deve usare un'op finta anche per (b).

## La tabella

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | esercitata? | verdetto | prova |
|---|---|---|---|---|---|---|
| 1 | `verimem/syscall_bridge.py:60` `_audit_write` | scrive una riga JSONL nel log di audit | ogni percorso di `engram_invoke` | PARZIALE — 2 statement su 6 | **FUNZIONA COME PROMESSO** | il banco: 1 riga per (a) e (c), 40 per 40 chiamate in (b) |
| 2 | `verimem/syscall_bridge.py:71` `_check_rate_limit` | vero se l'op sta sotto `limit` chiamate al secondo | `engram_invoke` | PARZIALE — 1 su 9 | **FUNZIONA COME PROMESSO** | 38/40 bloccate con `rate_limit=1.0` |
| 3 | `verimem/syscall_bridge.py:87` `_op_recall` | handler `recall` | `ENGRAM_OPS_MANIFEST` | PARZIALE — 3 su 12 | **FUNZIONA COME PROMESSO** | 2 chiamate riuscite nel banco (b) |
| 4 | `verimem/syscall_bridge.py:114` `_op_topk_embeddings` | handler `topk_embeddings`, privacy-preserving | manifesto | **CORPO MAI ESEGUITO** | **NON MISURATO** | nessuno dei 5 file lo percorre |
| 5 | `verimem/syscall_bridge.py:130` `_op_mesh_query` | handler `mesh_query` | manifesto | PARZIALE — 1 su 6 | **FUNZIONA COME PROMESSO** | 25 passed |
| 6 | `verimem/syscall_bridge.py:141` `_op_mesh_fetch` | handler `mesh_fetch` | manifesto | PARZIALE — 1 su 7 | **FUNZIONA COME PROMESSO** | 25 passed |
| 7 | `verimem/syscall_bridge.py:158` `_op_resonant_merge` | handler `mesh_resonant_merge` | manifesto | **CORPO MAI ESEGUITO** | **NON MISURATO** | idem |
| 8 | `verimem/syscall_bridge.py:190` `engram_invoke` | il confine tipizzato: manifesto · rate-limit · token · audit | `dashboard_widget`, MCP, agenti | PARZIALE — 1 statement su 50 | **FUNZIONA COME PROMESSO** su (a)(b)(c) | il banco sopra + `test_capability_token.py::test_syscall_bridge_token_integration` |
| 9 | `verimem/syscall_bridge.py:353` `engram_audit_tail` | le ultime N righe di audit | `dashboard_widget.py:54` | PARZIALE — 6 su 14 | **FUNZIONA COME PROMESSO** | `test_dashboard_widget.py` dentro i 25 |
| 10 | `verimem/syscall_bridge.py:373` `engram_rate_stats` | lo stato dei bucket del rate-limit | **nessun chiamante** in `verimem/` né in `tests/` | **CORPO MAI ESEGUITO** (l'unico statement, :375) | **MAI CHIAMATA** | `grep -rn "engram_rate_stats" verimem/ tests/` → 0 fuori dalla def |
| 11 | `verimem/syscall_bridge.py:381` `engram_available_ops` | l'elenco delle op del manifesto | test | ESEGUITA | **FUNZIONA COME PROMESSO** | 25 passed |

## Codice mai chiamato, e due handler mai esercitati

- **`engram_rate_stats` (:373-377)** — zero chiamanti nel prodotto e nei test.
  Il suo gemello `engram_audit_tail` è usato dal widget della dashboard; questo
  no. ⇒ **MAI CHIAMATA**: propongo la rimozione **oppure** il suo uso nel widget
  accanto all'audit (il rate-limit è invisibile a chi guarda il pannello). Non
  decido io, e non la tocco (regola 2).
- **`verimem/syscall_bridge.py:114` `_op_topk_embeddings`** e **`verimem/syscall_bridge.py:158` `_op_resonant_merge`** — due
  handler **registrati nel manifesto** e mai percorsi da un test. Sono
  raggiungibili dall'esterno via `engram_invoke("topk_embeddings", ...)`:
  ⇒ **superficie invocabile non misurata**. È il reperto più serio di questo
  file, e vale più delle percentuali: un'op che il manifesto accetta è una porta
  aperta, e due di queste porte non hanno un test.

## T42 — `clp` non è una dipendenza: che cosa riceve un utente che non ce l'ha

Dato di @lead-audit: il pacchetto importa `clp.agentos` in tre punti e `clp`
**non compare in `pyproject.toml`** (`grep -nE "clp|agentos" pyproject.toml` →
nessun match, exit 1). Per un utente quel modulo non esiste. La domanda era: se
cade, è un NON COME PROMESSO.

**I tre import sono tutti guardati** — letti uno per uno:

| punto | forma | che cosa succede senza `clp` |
|---|---|---|
| `syscall_bridge.py:102-106` | `try/except ImportError` | ritorna `{"ok": False, "error": "vec_bus.embed_text unavailable"}` |
| `mesh_memory.py:74-79` | `_vec_bus()` con `try/except` | ritorna `None` |
| `op_supervisor.py:226` | dentro un `try` | l'allarme best-effort non parte (è nella parte del lead) |

⇒ **non cade.** Ma la lettura non basta: ho simulato l'assenza di `clp` con un
finder che solleva `ImportError` su quel nome (controllo positivo: il banco
verifica di *aver davvero* reso `clp` irraggiungibile, e si ferma se non ci
riesce) e ho chiamato `engram_invoke` come lo chiamerebbe un utente:

```
✅ CONTROLLO: `clp` è irraggiungibile in questo processo
verimem importato da: <home>

ok         = False
blocked_by = None
result     = {"ok": false, "error": "vec_bus.embed_text unavailable"}
riga di audit: ok=False blocked_by=None op='recall'
```

**La mia predizione era che uscisse `ok=True`** (l'handler non solleva, quindi
pensavo scattasse la clausola (d) «success») **ed è stata smentita**:
`engram_invoke` riporta il fallimento, e il log di audit pure. Bene così.

🔴 **Ma il banco fa emergere un quinto esito che il contratto non enumera.** Il
docstring dichiara quattro casi — `not_in_manifest`, `rate_limit_exceeded`,
`exception`, successo — e questo non è nessuno dei quattro:

```
ok=False  ·  blocked_by=None
```

Un handler che **ritorna** un errore invece di sollevarlo produce un fallimento
**senza causa nel campo che porta le cause**. Chi legge il log di audit per
sapere *perché* una chiamata è fallita trova `blocked_by=None` e deve andare a
cercare dentro `result` — che l'audit, per scelta esplicita (`:230`, non si
registrano i valori), **non contiene**.

⇒ **T42 — NON COME PROMESSO, e la promessa infranta è quella del docstring, non
del codice**: il «Falsifiable contract» elenca quattro esiti e ne esiste un
quinto, che è anche il più probabile per un utente senza `clp`. **Owner: ws1
QA.** La cura è una riga sola (un `blocked_by="handler_error"`, oppure il
contratto che enumera il caso), ma **non la scrivo adesso** — regola 2 del
mandato. Il ticket resta con la sua prova.

## Che cosa NON ho misurato

- **(d) del contratto**: il percorso di successo con un handler reale.
- **Il token di capability** (`require_token=True`): esiste un test di
  integrazione (`test_capability_token.py`), **non l'ho letto riga per riga** e
  non ho verificato il suo perimetro.
- Le **10 diramazioni parziali** (`BrPart 10`) non le ho aperte una per una.
