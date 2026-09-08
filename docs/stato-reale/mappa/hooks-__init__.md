# `verimem/hooks/__init__.py` — 44 righe, e sono quelle che rispondevano alla domanda

## Cosa fa
Dichiara i **punti d'ingresso degli hook di Claude Code** per HippoAgent. Non
contiene logica: dice come si usa il pacchetto.

## 🔑 La riga che mi ha smentito
> *«Each submodule exposes a CLI-shaped `main_stdin_stdout(stdin, stdout)` that
> **`.claude/hooks/*.py` wrapper scripts** can call after delegating the heavy
> import work into the engram package (testable from pytest without subprocess)»*

Tre cose in una frase: **chi** chiama (gli script wrapper sotto `.claude/hooks/`),
**come** (`main_stdin_stdout`, forma da CLI), e **perché** il lavoro pesante sta
qui invece che nel wrapper (così si prova con pytest, senza sottoprocesso).

⇒ **Avevo dichiarato orfano il pacchetto senza aprire questo file.** È il file che
un package usa per dire come lo si usa, ed è l'unico dei due che non avevo letto.
La correzione, con la catena verificata eseguendo, sta in
[`hooks-pre_tool_use.md`](hooks-pre_tool_use.md).

## È raggiungibile dal prodotto? **SÌ**
```
  .claude/hooks/hippo_pre_tool_use.py:60   from engram.hooks.pre_tool_use import main_stdin_stdout
  python -c "import engram.hooks.pre_tool_use"
    IMPORTABILE: …\HippoAgent\verimem\hooks\pre_tool_use.py   ·   ha main_stdin_stdout: True
```

## La regola che ne esce, per chi continua questa mappa
**Prima di scrivere «nessuno lo chiama»: aprire l'`__init__.py`.** Un package
dichiara lì il proprio contratto d'uso, e cercare i consumatori nei soli formati
di configurazione (`*.json`, `*.toml`, `*.yml`) perde quelli scritti **in Python**.
