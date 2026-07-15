# Piano: rename totale `engram/` → `verimem/` (DECISIONE APERTA)

**Stato 2026-07-15.** Il rebrand utente-facing è GIÀ completo; questo documento
copre l'ultimo pezzo — il nome del package interno — e i suoi costi. Non si
esegue senza mandato esplicito.

## Cosa è già fatto (nessuna azione)

| Superficie | Stato |
|---|---|
| PyPI / `pip install verimem` | ✅ `name = "verimem"` (0.4.2) |
| Import di prodotto `from verimem import Memory` | ✅ facade `verimem/` funzionante |
| Env di prodotto `VERIMEM_*` | ✅ mirror setdefault (commit 9b1cbed), ~91 setting |
| Sito, licenza AGPL, benchmark, preprint | ✅ brand Verimem ovunque |
| CLI | ✅ `verimem …` |
| MCP tool namespace | ✅ opzionale `ENGRAM_TOOL_NAMESPACE=verimem` |

Per un utente il prodotto è **già** Verimem al 100%: `engram` appare solo se
legge il codice sorgente o i path interni.

## Cosa comporterebbe il rename totale

1. `git mv engram verimem_core` (o `verimem` con fusione della facade) —
   ~150 moduli.
2. Riscrittura import in tutto il repo: package, tests (~6.700 test), scripts,
   benchmark, docs — meccanica ma enorme superficie di regressione.
3. Shim di compatibilità `engram/__init__.py` → re-export (stesso pattern del
   rename hippoagent→engram del cycle #41, con finestra di deprecazione).
4. Migrazione riferimenti `engram.*` in: MCP server registrations, plugin
   Claude Code, config utenti esistenti, articoli/preprint che citano
   `engram/grounding_gate.py` per path.
5. Data dir `~/.engram` → decidere se migrare (rischioso) o mantenere.

**Stima onesta:** 1–2 giornate piene + una finestra di doppio nome di ~3 mesi.
Rischio principale: rompere silenziosamente consumer esterni (MCP config,
import nei progetti di chi ci prova ora).

## Raccomandazione

**Non ora.** Il rapporto costo/beneficio è sfavorevole finché l'adozione
esterna è ~0: nessun utente vede `engram`, e il preprint/i benchmark citano i
path attuali. Rifarlo DOPO la prima ondata di visibilità (HN) significherebbe
rompere i link appena pubblicati — quindi la finestra giusta è **o subito
prima della promozione o molto dopo**, mai nel mezzo.

Se si decide di procedere: replicare il playbook cycle #41
(`engram/_compat.py` + shim `hippoagent/` sono il template già collaudato).
