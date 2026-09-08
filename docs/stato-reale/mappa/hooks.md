# `verimem/hooks/` — un consumatore scritto per curare del codice morto, e mai collegato

**2 file, 320 righe**: `__init__.py`, `pre_tool_use.py`.

## Cosa fa

`pre_tool_use.py` è un **hook `PreToolUse` di Claude Code**: legge il payload JSON
su stdin, ne estrae il testo del sotto-obiettivo, chiama
`verimem.proactive_step_injector.StepInjector.inject` sullo store semantico locale
e scrive su stdout un banner `<engram-step-recall>…</engram-step-recall>`, così
l'LLM ospite vede i fatti rilevanti **prima** che lo strumento parta. Punto di
ingresso: `main_stdin_stdout` (riga 276). Fail-soft dichiarato in tutto.

## 🔴 Perché esiste — e perché è il punto

Dal suo stesso docstring:

> *«Cycle 169 (2026-05-20) — PreToolUse hook that consumes StepInjector. Closes
> the cycle-168 critic finding from PR #108 (**"StepInjector dead code = no MCP
> wrapper / no consumer"**)»*

⇒ È stato scritto **per dare un consumatore a del codice che non ne aveva**.

## È raggiungibile dal prodotto? **Per le vie che ho controllato, NO**

```
  git grep 'verimem.hooks|from .hooks' -- verimem/     ->  NESSUN file fuori da hooks/
  git grep 'pre_tool_use' -- *.json *.toml *.yml *.sh  ->  nulla (esclusi i docs)
  pyproject.toml [project.scripts]                     ->  verimem · engram · hippo,
                                                           tutti e tre = verimem.cli:main
  chi importa StepInjector, in verimem/:
      verimem/hooks/__init__.py
      verimem/hooks/pre_tool_use.py
      verimem/proactive_step_injector.py     (il modulo stesso)
  chi lo importa nei test: 2 file
```

🔑 **La catena si chiude in sé.** `proactive_step_injector.py` era codice morto; per
curarlo è stato scritto l'hook che lo consuma; **l'hook non è agganciato a niente** —
nessun import dal prodotto, nessun entry point, nessuna configurazione che lo invochi.
**Il consumatore è morto quanto il consumato**, e il finding del critic è stato chiuso
scrivendo codice invece che collegandolo.

⚠️ **Quello che NON ho fatto**: non l'ho eseguito. Dico «non raggiungibile per le vie
che ho controllato», e le vie sono elencate qui sopra. Se qualcuno lo lancia da un
`settings.json` fuori dal repo — la forma in cui gli hook di Claude Code si
configurano davvero — quella configurazione **non sta in questo repository** e il
pacchetto pubblicato non la porta.

## Cosa ne consegue

Non è una proposta di cancellarlo: è un **modulo senza consumatore dichiarato**. Le
strade sono due e vanno decise da chi lo tiene — **collegarlo** (un entry point, o la
riga di configurazione documentata nel README) **oppure dichiararlo esplicitamente
come esempio**, così chi lo trova sa che non gira.
