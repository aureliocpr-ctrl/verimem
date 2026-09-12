# `verimem/sandbox.py` — 953 righe, 14 funzioni, 4 classi

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) ·
**08/09**.

## Il claim del README: **nessuno**

```
grep -in "sandbox" README.md      → 0 occorrenze
```

⇒ come `ide.py`: superficie viva, fuori dalla vetrina. La promessa che questo
file deve mantenere è **il proprio docstring**, che è esplicito e verificabile:

> «allowlist, dry-run, cwd jail, timeout, env scrub, no network opzionale»
> `SandboxPolicy.timeout_s: int — kill after N seconds`

## Il perimetro della misura, scritto accanto al numero

```
10 file di test (test_sandbox.py, _arbitrary_exec_scan68, _pipe_interpreter,
                 _strict_pytest_args_h3, _exec_shell_gate_h2, test_mcp_sandbox_exec,
                 security/{env_scrub_secrets, sandbox_cwd_jail_wiring,
                 sandbox_git_write_flags, sandbox_redirect_quoting})
160 passed in 42,62 s                                          EXIT=0
verimem\sandbox.py   268 stmts   63 miss   82 branch   7 BrPart   79,4%
```

## La tabella

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | esercitata? | claim | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/sandbox.py:261` `_resolve_sandbox_mode` | `"strict"` se `ENGRAM_SANDBOX_MODE` ∈ {strict, shell-false, 1, on, enforce}, altrimenti `"legacy"` | `:635` (`execute`) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 160 passed; `test_sandbox_exec_shell_gate_h2.py` e `_strict_pytest_args_h3.py` esercitano entrambi i modi |
| 2 | `verimem/sandbox.py:279` `_parse_argv` | `shlex.split`, `None` se le virgolette non bilanciano | `:639` (ramo strict) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | idem |
| 3 | `verimem/sandbox.py:291` `_validate_argv` | allowlist di binari sull'argv (no metacaratteri) | `:646` circa | PARZIALE (298, 303, 387) | — | **FUNZIONA COME PROMESSO** | `test_sandbox_arbitrary_exec_scan68.py`, `_pipe_interpreter.py`, `_git_write_flags.py` dentro i 160 |
| 4 | `verimem/sandbox.py:401` `ValidationResult` | dataclass dell'esito di `validate` | `validate` :582-608 | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 160 passed |
| 5 | `verimem/sandbox.py:409` `ExecResult` | dataclass dell'esito di `execute` (action, rc, stdout, stderr, elapsed) | `execute` in 8 punti | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 160 passed |
| 6 | `verimem/sandbox.py:423` `SandboxPolicy` | allowlist · denylist · `allowed_cwds` · `timeout_s` · `env_scrub_prefixes` · `allow_network` | `SandboxedShell.__init__` :514 | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 160 passed |
| 7 | `verimem/sandbox.py:446` `SandboxPolicy.add_allow_pattern` | aggiunge un pattern all'allowlist | **nessun chiamante nel prodotto**; `tests/test_sandbox.py:200` | ESEGUITA (solo da un test) | — | **MAI CHIAMATA nel prodotto** | `grep -rn "add_allow_pattern" verimem/` → 0 risultati fuori dalla def |
| 8 | `verimem/sandbox.py:449` `SandboxPolicy.add_deny_pattern` | aggiunge un pattern alla denylist | **nessun chiamante, né prodotto né test** | **CORPO MAI ESEGUITO** (riga 450) | — | **MAI CHIAMATA** — candidata alla rimozione | `grep -rn "add_deny_pattern" verimem/ tests/` → 0 risultati fuori dalla def |
| 9 | `verimem/sandbox.py:452` `SandboxPolicy.add_allowed_cwd` | aggiunge una radice consentita | test | ESEGUITA | — | **FUNZIONA COME PROMESSO** | `security/test_sandbox_cwd_jail_wiring.py` |
| 10 | `verimem/sandbox.py:456` `_cwd_within` | la cwd deve stare dentro una radice consentita (cwd jail) | `_validate_security_layers` | ESEGUITA | — | **FUNZIONA COME PROMESSO** | `test_sandbox_cwd_jail_wiring.py` dentro i 160 |
| 11 | `verimem/sandbox.py:484` `_scrub_env` | nasconde le variabili d'ambiente con i prefissi configurati | `execute` | ESEGUITA | — | **FUNZIONA COME PROMESSO** | `security/test_env_scrub_secrets.py`: il segreto non compare in `stdout` |
| 12 | `verimem/sandbox.py:511` `SandboxedShell` · `verimem/sandbox.py:514` `SandboxedShell.__init__` · `verimem/sandbox.py:525` `SandboxedShell.audit_log_path` · `verimem/sandbox.py:529` `SandboxedShell._audit` | costruzione, percorso del log, scrittura di un evento | ovunque nella classe | ESEGUITE | — | **FUNZIONA COME PROMESSO** | `TestAuditLog::test_every_validate_logs` |
| 13 | `verimem/sandbox.py:535` `SandboxedShell._validate_security_layers` | applica in ordine: denylist · allowlist · cwd jail · rete | `validate` :582 | PARZIALE (552) | — | **FUNZIONA COME PROMESSO** | 160 passed |
| 14 | `verimem/sandbox.py:582` `SandboxedShell.validate` | l'esito senza eseguire (dry-run) | pubblica; `execute` | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 160 passed |
| 15 | `verimem/sandbox.py:611` `SandboxedShell.execute` (**328 righe**) | esegue nel modo risolto, con timeout e kill del gruppo di processi | pubblica; `mcp_server` via `sandbox_exec` | **PARZIALE — 85 statement scoperti su 103** | — | **NON MISURATO** su tre percorsi (sotto) | vedi la sezione |

## Le 85 righe scoperte di `execute`, classificate — e due terzi **non sono un buco**

Il numero grezzo direbbe «85 righe della funzione centrale non testate». Letto
riga per riga, si divide in tre cose diverse:

| zona | che cos'è | come si legge |
|---|---|---|
| **713, 847** | `popen_kw["start_new_session"] = True` | **POSIX-only.** Su Windows non *può* essere eseguita |
| **767-792, 892-906** | la cascata `os.killpg(SIGTERM → SIGKILL)` | **POSIX-only.** Il ramo Windows (`CTRL_BREAK_EVENT` a :888, `proc.kill()` a :891) **è coperto** |
| **717-734** | `FileNotFoundError` sul `Popen` del modo **strict** | **NON MISURATO**: binario inesistente in modo strict |
| **758-766** | `TimeoutExpired` nel modo **strict** | **NON MISURATO** |
| **851-856, 926-935** | `except Exception` generici attorno a `Popen` e al kill | **NON MISURATO** |

🔑 **Il 79,4% è una misura di Windows.** Una parte delle righe «mancanti» non è
codice non testato: è codice che su questa piattaforma non è raggiungibile. Chi
legge «79,4%» come «il 20,6% non è testato» **sbaglia in un solo verso**, e
sempre a sfavore del codice. Il numero confrontabile lo dà una misura su Linux —
che **non ho fatto** e non fingo di avere.

## Il test del timeout passa — ma non per il codice che sembra

`tests/test_sandbox.py::TestTimeout::test_short_timeout_kills_long_running`
imposta `timeout_s = 1`, lancia `python -c "import time; time.sleep(5)"` e
asserisce `action == "timeout"`. **Passa.**

Ma `coverage` dice che 758-792 e 892-906 non sono eseguite. Non è una
contraddizione: il test passa dal ramo **legacy + Windows** (`:888
CTRL_BREAK_EVENT`, `:891 proc.kill()`), mentre le righe scoperte sono il ramo
**POSIX** e il ramo **strict**. ⇒ **il timeout è provato in una configurazione su
quattro** (legacy/strict × Windows/POSIX), e le altre tre non lo sono.

📌 Questo conta perché il docstring di `_resolve_sandbox_mode` dice:
*«Flip to strict in production where command-injection-via-metachar must be
impossible»*. **Il modo raccomandato in produzione è quello con i percorsi
d'errore non esercitati** — non rotti: **non misurati**.

## Codice mai chiamato

- **`SandboxPolicy.add_deny_pattern` (:449-450)** — `grep` su `verimem/` e su
  `tests/`: **zero chiamanti**. Il suo gemello `add_allow_pattern` è chiamato da
  un test soltanto (`test_sandbox.py:200`), da nessun punto del prodotto.
  ⇒ **MAI CHIAMATA**: propongo la rimozione, o un test che la usi se la
  denylist dinamica serve. Non la tocco (regola 2 del mandato).

## Che cosa NON ho misurato

- **La coverage su Linux**: senza, non so quanta parte delle 63 righe mancanti
  sia davvero non testata. È la misura che chiuderebbe il conto.
- **`allow_network=False`**: il docstring promette «no network opzionale». Non
  ho verificato quali comandi di rete siano bloccati né con quale elenco.
  **NON MISURATO**.
- **Non ho rotto nessuna riga qui** (per `prompt_injection.py` l'avevo fatto).
  I verdetti di questa tabella sono `coverage` + lettura, non falsificazione.

---

### Nota sullo strumento che ha prodotto queste etichette

`attribuisci_coverage.py` ha sbagliato **tre volte** prima di dare i numeri di
questa tabella, e tutte e tre in modo che valeva la pena inseguire:

1. misurava l'ampiezza di una funzione come `fine - inizio`, cioè **righe
   fisiche**, incluse la riga del `def` e il docstring — che sono eseguite
   all'import, sempre. Così `syscall_bridge.py:373 engram_rate_stats`, il cui
   corpo è **un solo statement e quello statement è scoperto**, usciva
   «PARZIALE — 1 riga» invece di «corpo mai eseguito»: l'etichetta **più mite
   proprio nel caso peggiore**;
2. corretto a statement, la soglia era **80%**, e `ide_term` usciva «CORPO MAI
   ESEGUITO» mentre le sue prime righe girano eccome: etichetta **più dura del
   vero**, stavolta a sfavore del codice;
3. portata la soglia a 100%, il confronto era ancora `len(scoperti) >=
   len(statement)` — **due insiemi diversi confrontati per dimensione**: fra le
   righe scoperte ci sono le continuazioni, che non sono statement, e 99 ≥ 90
   dava di nuovo il verdetto sbagliato. Ora il confronto è per **inclusione**.

🔑 Una soglia arbitraria mente in **entrambi** i versi, e le due volte in cui il
mio righello ha sbagliato non ha sbagliato dalla stessa parte. È il motivo per
cui questa tabella porta **due numeri** (`N statement scoperti su M`) e non
un'etichetta sola: chi legge può rifare il conto.
