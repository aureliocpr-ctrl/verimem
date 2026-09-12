# `verimem/trusted_writer.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

**NESSUNO.**

Cercato nel README con i termini del modulo (`grep -in`) e **nessuna
riga lo copre**. Il claim `README:704` è della famiglia dei detector
L1 e questo file non è uno di quelli: attribuirglielo sarebbe
inventare l'attribuzione — in un documento fatto per collegare i
claim al codice, l'errore peggiore.

⇒ come `ide.py` e `sandbox.py`: **superficie viva fuori dalla
vetrina**. Non è un difetto; è un dato per chi decide che cosa il
prodotto dichiara di essere.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 100.0%
statement non eseguiti: —
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/trusted_writer.py:32` `verify_trusted_writer` | funzione: True solo se ``writer_role`` e' trusted E ``token`` combacia col segreto | `verimem/anti_confab_gate.py:147`; `verimem/anti_confab_gate.py:2037`; `verimem/anti_confab_gate.py:2039` (+6) | `tests/test_cli_facts_add.py`; `tests/test_engram_gate_falsification.py`; `tests/test_trusted_writer.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.


---

## Il banco nel merito: 13 promesse su 13 — e un docstring che **regge alla riverifica**

47 righe, una funzione, ed è un presidio di sicurezza: il ruolo «trusted» vale
solo se accompagnato da un token server-side che un client MCP non conosce.

**Perché merita un banco più di altri moduli da una funzione**: il suo docstring
**è già stato stale una volta**, e lo dice da sé —

> «WIRATA in produzione (il paragrafo precedente diceva "NON wirata" ed era
> STALE — corretto 2026-07-21 […]; per un prodotto che vende memoria verificata,
> **un file che mente sul proprio stato è la stessa classe di difetto che il gate
> esiste per bloccare**)»

Un documento che si è già sbagliato una volta sul proprio stato va **riverificato
oggi**, non creduto perché la correzione è scritta.

```
── il predicato ──
OK  (A) ruolo non trusted, token GIUSTO → False
OK  (B) ruolo trusted + token giusto → True          ← controllo positivo
OK  (B') l'altro ruolo trusted (trusted_hook) → True
OK  (D) token assente (None) → False
OK  (D') token vuoto → False
OK  (E) token sbagliato → False
OK      ruolo None → False

── fail-closed ──
OK  (C) env ASSENTE + ruolo trusted + token qualsiasi → False
OK  (C') env VUOTO → False (non basta che la variabile esista)

── il red-team vettore #1 ──
OK  (F) la firma NON ha `env_var`      parametri=['writer_role', 'token']
OK      e non accetta **kwargs         (writer_role, token) -> bool

── la wiratura dichiarata ──
OK  (G) anti_confab_gate.py lo nomina ancora    3 occorrenze
OK  (G') semantic.py lo nomina ancora           3 occorrenze

13 casi · tutte le promesse reggono                                   EXIT=0
```

### «Lo nomina» non è «lo usa come promesso» — quindi ho letto le righe

Il docstring non dice solo *che* è cablato: dice **come** — il bypass vale «solo
se `meta_narrative and verify_trusted_writer(...)`». La forma è quella:

```
anti_confab_gate.py:2039
    if meta_narrative and verify_trusted_writer(writer_role, hook_token):
        return GateResult(action="persist")

semantic.py:3096-3100
    _trusted_provenance = (
        bool(getattr(fact, "meta_narrative", False))
        and verify_trusted_writer(
            getattr(fact, "writer_role", "agent_inference"), hook_token)
    )
```

**Entrambi in `and` con `meta_narrative`**, come promesso, e in entrambi i punti
il commento accanto spiega il perché (`writer_role` è spoofabile dal client via
gli argomenti MCP).

⇒ **FUNZIONA COME PROMESSO** su tutte e tre le promesse: il predicato,
il fail-closed, e la wiratura **nella forma dichiarata**.

📌 **Vale la pena dirlo perché è il caso opposto a quelli che abbiamo trovato
stasera.** Un docstring che aveva mentito è stato corretto, la correzione ha
lasciato scritto *che cosa* mentiva, e oggi la riverifica lo conferma. È il modo
in cui un documento diventa affidabile: non promettendo di non sbagliare, ma
lasciando la traccia dell'errore accanto alla cura — così chi passa dopo sa
**che cosa** ricontrollare.
