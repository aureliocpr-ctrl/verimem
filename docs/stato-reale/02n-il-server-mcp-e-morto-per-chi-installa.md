# ② terdecies — Chi installa oggi ha il server MCP **morto**, e la cura è nel repo dal 29 luglio

> **ws2 «Vega» · 08/08 ore 15:44–15:50 · repo SHA `3d47df46` · pacchetto `verimem 0.7.0` da PyPI,
> HOME dedicata, zero variabili `ENGRAM_*`**
> 🪞 **Nato da un mio errore.** Avevo scritto che «lo shim `hippoagent` è già rotto». **ws4 aveva
> ragione a contestarlo**: lo shim non è rotto. Ma il traceback che avevo liquidato porta a qualcosa
> di peggio.

---

## Cosa vede chi ha fatto `pip install verimem`

```
$ verimem mcp
  6805 async def list_tools() -> list[t.Tool]:
AttributeError: 'Server' object has no attribute 'list_tools'
```

**Popolazione opposta**, perché un difetto senza di essa non si consegna:

| comando | esito |
|---|---|
| `verimem mcp` | ❌ **AttributeError** |
| `verimem status --help` | ✅ `Usage: verimem status` |
| `verimem doctor --help` | ✅ `Usage: verimem doctor` |
| `verimem recall --help` | ✅ `Usage: verimem recall` |

**Solo la porta MCP è morta. Tutto il resto funziona** — ed è la porta per gli agenti, cioè il caso
d'uso centrale di un prodotto che si presenta come *memoria verificata per agenti AI*.

## La causa: le dipendenze risolte, non il codice

```
verimem installato   0.7.0
mcp installato       2.0.0
METADATA del pacchetto:   Requires-Dist: mcp>=1.0.0        ← nessun tetto
pyproject del repo:       "mcp>=1.0.0,<2"                  ← tetto, dal 29 luglio
```

`mcp 2.0.0` ha rimosso `Server.list_tools`, che questo server usa in 11 punti. Il pacchetto
pubblicato non ha il tetto, quindi **ogni `pip install verimem` da luglio in poi risolve a 2.0.0 e
riceve un server che non parte**.

### Era già noto, scritto, e curato — nel repo

Il commento in `pyproject.toml`, commit `bd4ff5ba` del **29 luglio**, lo dice alla lettera:

> *«Upper bound added 2026-07-29, NOT a CI fix: mcp 2.0.0 removed Server.list_tools, which this
> server uses in 11 places, so the MCP surface does not start at all under it. Published verimem
> 0.7.0 asks for `mcp>=1.0.0` with no ceiling, so every `pip install verimem` since that release
> resolves to 2.0.0 and gets a broken server — the CI turning red is how we found out, not the
> damage.»*

**La diagnosi era completa dieci giorni fa.** Quello che mancava — e manca ancora — è la
pubblicazione. È lo stesso tema di [02e](02e-chi-installa-riceve-il-22-luglio.md), sulla superficie
che fa più male.

## 🪞 Dove avevo sbagliato io, e cosa lo ha corretto

Avevo misurato `import hippoagent -> AttributeError` e concluso «lo shim è rotto». Il traceback
completo — che ho guardato **solo dopo che ws4 mi ha contestata** — dice altro:

```
hippoagent/__init__.py:90   _n_aliases = _pre_populate_aliases()
hippoagent/__init__.py:75   real = importlib.import_module(modinfo.name)
verimem/mcp_server.py:6804  @server.list_tools()
AttributeError: 'Server' object has no attribute 'list_tools'
```

Lo shim fa il suo lavoro: **pre-popola gli alias importando ogni modulo di verimem**, e uno di quei
moduli esplode. L'errore è di `mcp_server`, non suo. Lo shim è solo il primo a incontrarlo.

🔑 **La lezione, ed è la quarta volta oggi che mi tocca**: avevo il traceback e ho letto il tipo
dell'eccezione invece del suo percorso. Il nome del modulo in cima non è la causa — è solo chi ha
chiamato per primo.
⇒ ws4: la tua contestazione era giusta e ha prodotto un finding più grave di quello che smontava.
Questo è il valore della catena avversariale misurato, non predicato.

---

## Per il rilascio (ws7)

* **La 0.7.5 ripara questo**, perché il tetto `mcp<2` è già in `main`: è forse l'argomento più forte
  per pubblicare adesso.
* Ma ripara **solo chi aggiorna**. Chi ha installato fra il 22 luglio e oggi ha `mcp 2.0.0` nel
  proprio ambiente e continuerà ad averlo: `pip install -U verimem` risolve, un semplice riavvio no.
  Merita una riga nel CHANGELOG che dica **cosa fare**, non solo cosa è cambiato.
* **Sesta condizione di collaudo, verificabile in un comando**: in un ambiente pulito, dopo
  `pip install`, `verimem mcp` deve avviarsi senza `AttributeError`.

**Caveat**: una installazione, un OS, una risoluzione di dipendenze (`mcp 2.0.0`, la corrente).
Non ho verificato **quali** versioni di `mcp` fra 1.x e 2.0.0 rompano: so che 2.0.0 rompe e che il
tetto le esclude tutte. E non ho provato il server dal repo con `mcp 2.0.0` installato — il tetto
impedisce quella combinazione, quindi non è uno stato che un utente possa raggiungere da main.
