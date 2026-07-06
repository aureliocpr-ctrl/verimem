# Rename engram/hippo → verimem — piano a fasi (2026-07-06, mandato Aurelio)

**Obiettivo CEO**: un solo nome, *verimem*. Oggi tre — `engram` (package
interno), `hippo_*` (tool MCP), `verimem` (nome pubblico/PyPI). Confonde.

## Inventario (numeri veri, `grep`/`find` 2026-07-06)
| Superficie | Conteggio | Chi la vede |
|---|---|---|
| File `.py` in `engram/` | 354 | nessun utente (interno) |
| `import engram` / `from engram` | 1088 file | nessun utente (interno) |
| Tool MCP `hippo_*` | 234 | **l'utente** (`.mcp.json`, workflow, prompt) |
| Occorrenze `hippo_` in `mcp_server.py` | 517 | — |
| Alias `verimem` (già shipped) | `verimem.X is engram.X` ✅ | l'utente SDK |

## Analisi — cosa vede DAVVERO l'utente
- **SDK**: già 100% verimem. `from verimem import Memory`, `import verimem.X`
  funzionano (alias canonico, iter 58 + fix C7). L'utente Python non vede
  `engram`. **Nessun lavoro utente-facing residuo qui.**
- **PyPI / repo / CLI**: già `verimem`. Fatto.
- **Tool MCP `hippo_*`**: **QUESTO è l'unico nome che l'utente digita e vede
  ancora "hippo"**. 234 tool. È il vero rename che conta per il prodotto.
- **Package dir `engram/`**: cosmesi interna. Rinominarlo (354 file, 1088
  import) NON cambia l'esperienza utente (l'alias già copre). Alto sforzo,
  rischio regressione su tutta la suite, valore-utente ~zero.

## Strategia raccomandata — a fasi, non big-bang

### Fase 1 — tool MCP `hippo_*` → `verimem_*` CON alias di compat (NON-breaking)

> **✅ FASE 1 SHIPPED 2026-07-06** (`9fd1d8d` + namespace switch): il
> dispatch accetta `verimem_*` (→ handler `hippo_*`, byte-identical); con
> `ENGRAM_TOOL_NAMESPACE=verimem` anche `list_tools` li espone come
> `verimem_*` (stesso conteggio, nessun raddoppio). Default = `hippo_*`
> invariato (0.3.x non si rompe). TDD 32/32. Resta: doc utente + il flip
> del DEFAULT a verimem (decisione release 0.4.0).
Il pezzo che conta. Ogni tool esposto due volte: nome nuovo `verimem_*` +
alias deprecato `hippo_*` che dispatcha allo stesso handler (deprecation
warning nel description, non runtime). Gli utenti 0.3.x con `hippo_recall`
nei loro `.mcp.json` continuano a funzionare; i nuovi vedono `verimem_*`.
- Meccanismo: tabella `_TOOL_ALIASES = {"verimem_recall": "hippo_recall", …}`
  generata, dispatch che normalizza alias→canonico prima dello switch.
- Rischio: BASSO (additivo). Rete: `test_mcp_server.py` (_EXPECTED_TOOLS).
- Non tocca la mia memoria `hippoagent` (server separato, `mcp__hippoagent__*`).

### Fase 2 — package `engram/` → `verimem/` (cosmesi interna, quando c'è tempo)
- `git mv engram verimem`, riscrittura 1088 import via codemod (`ast`/`sed`
  ancorato), `engram` diventa l'alias di compat inverso (`import engram` →
  `verimem`), aggiornamento pyproject `packages`, plugin.json, docs.
- Rischio: ALTO (tutta la suite deve restare verde a ogni passo; 6000+ test).
- Valore-utente: ~zero (l'alias già dà l'esperienza verimem). Fare solo dopo
  Fase 1, a suite completamente verde, come unico blocco isolato.

### Fase 3 — memoria interna `hippo_*` (i miei tool CLP/hippoagent)
Fuori scope prodotto (è il MIO stack, non ciò che l'utente installa). Rinviabile
indefinitamente; nessun impatto sul prodotto verimem.

## Ordine di esecuzione
Fase 1 (valore reale, basso rischio) → misura/verde → Fase 2 (cosmesi, alto
rischio) solo se la suite regge → Fase 3 mai o quando ozioso.

## Gate
- Ogni fase: suite verde PRIMA e DOPO, CI verde, un commit per passo logico.
- Compat: nessun utente 0.3.x si rompe (alias in entrambe le direzioni).
- Bump: Fase 1 = `0.4.0` (nuovi tool = minor); Fase 2 può restare 0.4.x.
