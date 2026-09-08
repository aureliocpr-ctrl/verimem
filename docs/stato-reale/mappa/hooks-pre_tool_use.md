# `verimem/hooks/` — l'hook È collegato, e il primo verdetto che avevo scritto era sbagliato

**2 file, 320 righe**: `__init__.py` (44), `pre_tool_use.py` (276+).

> 🔻 **CORREZIONE.** La prima versione di questa pagina diceva «non raggiungibile
> per le vie che ho controllato» e sospettava codice orfano. **È falso**, e il
> file che lo smentiva era nello stesso pacchetto: `hooks/__init__.py`, che non
> avevo aperto.

## Cosa fa

`pre_tool_use.py` è un **hook `PreToolUse` di Claude Code**: legge il payload JSON
su stdin, estrae il testo del sotto-obiettivo, chiama
`verimem.proactive_step_injector.StepInjector.inject` sullo store locale e scrive
su stdout un banner `<engram-step-recall>…</engram-step-recall>`, così l'LLM ospite
vede i fatti rilevanti **prima** che lo strumento parta. Fail-soft ovunque.

## È raggiungibile dal prodotto? **SÌ — e la catena è questa**

```
  .claude/hooks/hippo_pre_tool_use.py:60   from engram.hooks.pre_tool_use import main_stdin_stdout
  .claude/hooks/hippo_pre_tool_use.py:64   return main_stdin_stdout()

  python -c "import engram.hooks.pre_tool_use"
    IMPORTABILE:  …\HippoAgent\verimem\hooks\pre_tool_use.py
    ha main_stdin_stdout: True
```
`engram/` è un **alias** di `verimem/` (il rename del 2026-07-06 ha lasciato il
nome vecchio importabile), quindi il wrapper arriva davvero al modulo. Lo script
wrapper **è dentro questo repository**, non in una configurazione esterna.

## 🪞 Perché mi ero sbagliato, e cosa cambia nel metodo

Avevo cercato il consumatore in `*.json`, `*.toml`, `*.yml`, `*.sh` — **e non nei
`.py` sotto `.claude/`**, che è esattamente dove gli hook di Claude Code vivono.
E `hooks/__init__.py` lo dice in chiaro:

> *«Each submodule exposes a CLI-shaped `main_stdin_stdout(stdin, stdout)` that
> **`.claude/hooks/*.py` wrapper scripts** can call…»*

**Avevo letto `pre_tool_use.py` e non `__init__.py`**: il file che rispondeva alla
mia domanda era l'unico dei due che non avevo aperto.
🔑 **Regola per il resto di questa mappa**: prima di dire «nessuno lo chiama»,
**leggere l'`__init__.py` del pacchetto** — è lì che un package dichiara come lo si
usa — e cercare i consumatori **anche fra i `.py` di configurazione**, non solo nei
formati di configurazione.

## Quello che resta vero del primo verdetto

Il modulo nasce per **dare un consumatore a del codice che non ne aveva**: il suo
docstring cita il finding «*StepInjector dead code = no MCP wrapper / no consumer*».
E il wrapper `.claude/hooks/hippo_pre_tool_use.py` ha un `except ImportError:
return 0` — **fallisce in silenzio** se il package non è sul path. Quella riga è
scritta apposta, ma vuol dire che l'hook **può non fare niente senza dirlo**: è la
stessa forma di T26a, dove una scrittura non giudicata non lo dichiara.
