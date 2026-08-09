# ② nonies — `trust`: due modi di dire TRUSTED, e due esempi su tre che non funzionano

> **ws2 «Vega» · 08/08 ore 14:58–15:05 · repo SHA `a9969ccf`, `git status` pulito ·
> pacchetto `verimem 0.7.0`, HOME dedicata, zero variabili `ENGRAM_*`**
> Punto (c) del ruolo assegnato: *«`trust` risponde TRUSTED con provenance (none) su domande senza
> dati»*. ws5 lo aveva ridimensionato («valuta la formulazione, non la verità»). **Hanno ragione
> entrambe: sono due casi diversi** — e sotto c'è un terzo difetto che non dipende dalla versione.

---

## 1. `trust` dice TRUSTED con `(none)` in **due** modi diversi

```
$ verimem trust "Roma e' la capitale d'Italia"
  Anti-confab trust check   TRUSTED ✓
    provenance:  (none)
    no anti-confab flags — adequate evidence / not a risky assertion

$ verimem trust "il fatturato del 2019 e' stato di 4 milioni"
  Anti-confab trust check   TRUSTED ✓
    provenance:  (none)
    no anti-confab flags — adequate evidence / not a risky assertion
```

```
$ verimem trust "the deploy succeeded"
  Anti-confab trust check   TRUSTED ✓
    provenance:  (none)
    flags (why it's not trusted):
      • [L1.10] Proposition contains works/confirmed claim 'succeeded' but no runtime evidence…
      • [L1-domain-precision-observe] unset ENGRAM_L1_DOMAIN_PRECISION to restore L1 escalation
```

| caso | verdetto | flag | il problema |
|---|---|---|---|
| «Roma è la capitale d'Italia» | TRUSTED | nessuno | nessuno: coerente |
| **«il fatturato del 2019 è stato di 4 milioni»** | TRUSTED | nessuno | **«adequate evidence» su un numero inventato di cui la memoria non sa nulla** |
| **«the deploy succeeded»** | **TRUSTED** | **2** | **il verdetto contraddice i suoi stessi flag** |
| «the migration succeeded» | FLAGGED | 1 | nessuno: coerente |
| «the module works» | FLAGGED | 1 | nessuno: coerente |

**ws5 ha ragione**: `trust` valuta la **formulazione** del claim, non la sua verità — ed è legittimo
e utile. **Il difetto è che la sua interfaccia dice altrimenti**, con quattro parole:
«Anti-confab **trust** check» · «**TRUSTED** ✓» · «adequate **evidence**» · «flags (why it's **not
trusted**)». Quattro elementi che parlano di fiducia e di prove, per uno strumento che misura la forma.

📌 La riga «no anti-confab flags — **adequate evidence** / not a risky assertion» offre due letture
alternative, e l'utente legge la prima. Su un fatturato inventato la seconda sarebbe onesta
(«non è un'asserzione rischiosa»), la prima no.

## 2. 🔴 Due dei tre esempi che il comando stesso dà **non funzionano**

La docstring ([`cli.py:1428`](../../verimem/cli.py)) e l'help del parametro dicono:

> *«Add a real provenance ref (`--verified-by commit:…` / `ci:…:green` / `coverage:N`) and watch the
> same claim pass»* · *«`--verified-by` Provenance ref (repeatable): `commit:abc123`, `bash:test_PASS`»*

Misurato sullo stesso claim, cinque prefissi:

| `--verified-by` | esito | citato dalla docstring? |
|---|---|---|
| `commit:a1b2c3d` | **FLAGGED** ✘ | **sì, per primo** |
| `coverage:87` | **FLAGGED** ✘ | **sì** |
| `ci:build-42:green` | TRUSTED ✔ | sì |
| `pytest:test_deploy_PASS` | TRUSTED ✔ | no |
| `bash:deploy.sh:exit0:1` | TRUSTED ✔ | no |
| *(nessuna, controllo)* | FLAGGED | — |

**3 su 5 funzionano** — e sono esattamente quelli nella lista che il detector accetta:

```python
_RUNTIME_EVIDENCE_PREFIXES = ("pytest:", "test:", "bash:", "cmd:", "smoke:", "runtime:", "ci:", "smoke_test:")
```

`commit:` e `coverage:` **non ci sono**. L'utente segue l'esempio che il prodotto gli dà per primo,
e il claim resta FLAGGED senza che nulla gli dica perché.

⚠️ **Questo NON dipende dalla versione**: la lista è **identica** nel repo e nel pacchetto, e la
docstring pure. È un difetto stabile, non un effetto del [22 luglio](02e-chi-installa-riceve-il-22-luglio.md).

### 🪞 Correzione a una mia misura precedente

In [02b](02b-primo-avvio-gate-lingua.md) avevo scritto che questa promessa era «misurata falsa 2 casi
su 2». **Era vero ma incompleto**: su 5 prefissi ne funzionano 3, e ora so *quali* e *perché*. La
promessa non è falsa in blocco — sono **falsi due dei tre esempi che cita**, il che è più preciso e
più facile da curare.

---

## Cosa propongo (a ws3 — io non tocco codice)

1. **Una riga di documentazione**, non di codice: sostituire `commit:…` e `coverage:N` negli esempi
   con prefissi che il detector accetta. Zero rischio, e chiude il caso più comune.
2. In alternativa, aggiungere `commit:` e `coverage:` alla lista — **ma prima serve la popolazione
   opposta**, che io non ho misurato: uno SHA di commit non è evidenza che qualcosa *funzioni*, e
   accettarlo indebolirebbe L1.10. **La via 1 è quella che consiglio.**

**Caveat**: 5 prefissi su un claim solo, un OS, `trust` come unica porta. Non ho verificato se
`remember --verified-by` si comporti allo stesso modo (atteso di sì, stesso detector — **non
misurato**). E la lettura «adequate evidence» è mia interpretazione di una riga che offre due
alternative: il difetto è che ne offre due, non che ne scelga una sbagliata.
