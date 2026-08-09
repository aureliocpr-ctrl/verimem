# ② quinquies — La tabella delle porte, eseguita dal lato di chi installa

> **ws2 «Vega» · 08/08 ore 14:35–14:45 · repo SHA `2d64b7b7`, `git status` pulito ·
> pacchetto `verimem 0.7.0` da PyPI, installato oggi 12:53**
> Catena avversariale: io attacco ws1. La sua tabella delle porte è **pronta per il README**, cioè
> per la vetrina che l'utente legge per primo — quindi la eseguo dal lato in cui l'utente la userà.
> **Il suo banco è corretto. La tabella, applicata da chi installa, cade su 2 righe su 4** — e ha un
> secondo difetto che non dipende dalla versione.

---

## 1. Ogni riga della tabella, eseguita

**Dalla CLI del pacchetto installato:**

```
verimem recall     ->  Usage: verimem recall
verimem trust      ->  Usage: verimem trust
verimem search     ->  No such command 'search'
verimem explain    ->  No such command 'explain'
verimem ignorance  ->  No such command 'ignorance'
verimem forget     ->  No such command 'forget'
```

**Dall'SDK: `Memory` ha 34 metodi pubblici nel repo, 26 nel pacchetto.** Gli 8 che mancano:

```
audit_anchor · audit_verify_anchor · correct · epistemic_health · forget · ignorance · label · trust_report
```

## 2. Il verdetto riga per riga

| riga della tabella di ws1 | dal repo | **da chi installa** |
|---|---|---|
| «i fatti che somigliano → `recall` / `search`» | `recall` CLI+SDK · **`search` solo SDK** | uguale |
| «se la memoria può rispondere → `explain` / `trust_report`» | entrambi **solo SDK** | `explain` solo SDK · **`trust_report` ASSENTE** |
| «quali domande non sa → `verimem ignorance` (CLI e SDK)» | ✅ CLI e SDK | ❌ **assente in entrambi** |
| «cancellare un fatto → `Memory.forget()` — solo SDK» | ✅ esiste | ❌ **assente** — nel pacchetto c'è `delete` |

**2 righe su 4 falliscono per chi installa**, ed è la conseguenza diretta di
[02e](02e-chi-installa-riceve-il-22-luglio.md): il pacchetto è il codice del 22/07.

## 3. E un difetto che NON dipende dalla versione

La tabella mette nella stessa colonna `verimem ignorance` (prefisso da riga di comando) e
`Memory.forget()` (metodo Python), e cita `search` ed `explain` senza qualificarli. Ma:

```
comandi CLI nel repo: … recall · trust · ignorance · search-docs …   (36 in tutto)
NON sono comandi CLI, né nel repo né nel pacchetto:  search · explain · forget
```

Un utente che legge «usa `search`» apre il terminale e riceve `No such command` **anche installando
il repo**. `search` ed `explain` esistono, ma **solo come metodi Python**.

🔑 **La tabella risponde a «quale porta» senza dire «da dove».** È la stessa forma che ws1 ha
scoperto e nominato lui stesso — *le promesse non sono del prodotto, sono di ogni porta* — applicata
alla sua tabella: ogni riga ha bisogno di **due** coordinate, quale porta **e quale superficie**.

## 4. La correzione che propongo — la tabella regge, le serve una colonna

| vuoi… | usa | dove vive | NON usare |
|---|---|---|---|
| i fatti che somigliano alla domanda | `recall` | CLI **e** SDK | — |
| | `search` | **solo SDK** | `verimem search` → non esiste |
| sapere **se** la memoria può rispondere | `explain` (campo `abstained`) | **solo SDK** | `recall`: risponde sempre, anche a domande che non c'entrano |
| | `trust_report` | **solo SDK**, e **solo dal repo** | — |
| sapere **quali domande** non sa | `ignorance` | CLI e SDK, **solo dal repo** | il pacchetto su PyPI: `No such command` |
| cancellare un fatto | `forget` | **solo SDK**, **solo dal repo** | la CLI: `verimem forget` → `No such command` |
| | `delete` | solo SDK, in **entrambi** | — |

⚠️ E una riga di avvertenza sopra la tabella: *«queste righe descrivono il repo. Il pacchetto
pubblicato su PyPI è la 0.7.0 del 22/07 e non ha `ignorance`, `forget`, `trust_report`, `correct`.»*

---

**Cosa NON contesto**: il banco di ws1 è corretto e il suo risultato centrale regge — alla domanda
sul fatturato `recall` risponde col magazzino di Verona mentre `explain` dice `abstained=True`. Le
ho rieseguite: `recall` e `trust` esistono in CLI in entrambi gli artefatti, `explain` espone
`abstained`. **Non sto smentendo la misura, sto misurando dove l'utente la applicherà.**

**Caveat**: un pacchetto, un OS, `--help` e `dir(Memory)` come fonti; non ho eseguito le chiamate
SDK, ho verificato la presenza dei metodi. `Memory.delete` non l'ho provato: che sia l'equivalente
di `forget` è **un'inferenza dal nome, non una misura**.
