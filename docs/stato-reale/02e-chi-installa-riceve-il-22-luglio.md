# ② quater — Chi installa oggi riceve il prodotto del 22 luglio, e nessun numero glielo dice

> **ws2 «Vega» · 08/08 ore 14:40 · repo SHA `3c4c2e1b`, `git status` pulito**
> Punto (b) del ruolo assegnato da ws3: *«il divario 26 comandi su PyPI contro 37 nel repo (manca
> `save`, che il protocollo O3 prescrive)»*. Rimisurato: **28 contro 36**, e la causa non è quella
> che sembra.

---

## 1. Il divario, misurato

```
comandi che l'utente vede con `verimem --help`   28
comandi definiti in verimem/cli.py               36        (+ 49 sotto-comandi in 12 gruppi)
in comune                                        20
```

**16 comandi esistono nel repo e non nel pacchetto installato:**

```
ask · benchmark · chat · code · correct · digest · ignorance · recent
run · save · sleep · sleep-now · telemetry · tip · tui · wake
```

```
$ verimem save --help
Error: No such command 'save'.
```

📌 *(Gli 8 nomi che comparivano «solo nel pacchetto» — `facts`, `episodes`, `skills`, `providers`,
`gateway`, `flow`, `consolidate`, `agent` — non sono un divario: sono i **gruppi di sotto-app**, che
la mia estrazione contava in un'altra categoria. Correzione mia, non difetto del prodotto.)*

## 2. La causa: **stessa versione dichiarata, 375 commit di distanza**

| | |
|---|---|
| versione installata da PyPI | **0.7.0** |
| versione nel `pyproject.toml` del repo | **0.7.0** |
| ultimo bump di versione | `304565bd`, **22/07** |
| commit sul repo dopo quel bump | **375** |

I 16 comandi mancanti sono entrati **dopo** la pubblicazione:

| comando | entrato il | commit |
|---|---|---|
| `save` · `tip` · `recent` · `digest` | 23/07 | `7efdb998` |
| `ignorance` | 30/07 | `1f26ea86` |
| `correct` | 01/08 | `d490adcd` |
| `ask` | 02/08 | `32f3ace5` |

⇒ **Non è che il pacchetto nasconda dei comandi: è che `0.7.0` su PyPI e `0.7.0` nel repo sono due
artefatti diversi a 375 commit di distanza, e il numero di versione non lo dice.** Chi installa oggi
riceve il codice del **22 luglio**, diciassette giorni fa.

### Verificato leggendo il codice installato, non dedotto

| | pacchetto installato | repo |
|---|---|---|
| `_WORKS_PATTERN` (lista dei vanti) | **identica** | identica |
| `ENGRAM_L1_DOMAIN_PRECISION` | presente (4 occorrenze) | presente |
| `grounding_span` (cura di ws3, oggi) | **0 occorrenze** | presente |

## 3. Cosa perde l'utente, in concreto

* **`save`** — il comando che il nostro protocollo O3 prescrive per ogni salvataggio verificato. Chi
  legge la nostra documentazione e installa il prodotto **non ha il comando che la documentazione usa**.
* **`ignorance`** — ws5 lo ha misurato oggi: *«segnala 8/8 le domande da non credere con 1 solo falso
  allarme su 6, e dice cosa manca»*. È forse la risposta migliore che il prodotto dà oggi sulla
  domanda «di cosa non ti puoi fidare», **e l'utente non ce l'ha**.
* **`correct`** — ed è l'unico dei tre comandi di scrittura che ha il controllo che distingue ammesso
  da quarantinato ([02c §5](02c-il-numero-mostrato-e-chi-decide.md)). La cura c'è, non è pubblicata.
* **`doctor`** — esiste in entrambi, ma quello dell'utente è del 22/07: la cura di ws7 di oggi
  (`63eab6f4`, il doctor che dichiara la soglia in vigore) non è nel pacchetto.

## 4. ⚠️ Conseguenza sul metodo, e riguarda tutte

**Una misura fatta «da utente» con `pip install verimem` misura il 22 luglio; una misura fatta
importando dal repo misura oggi.** Non sono lo stesso prodotto, e finora nessun referto lo ha
dichiarato — inclusi i miei.

* I miei [02c](02c-il-numero-mostrato-e-chi-decide.md) e [02d](02d-la-lista-dei-vanti-e-il-carve-out.md)
  mischiano le due fonti (CLI dal pacchetto, SDK dal repo) e lo dicevano, ma senza sapere che il
  divario fosse di 375 commit. **Restano validi**: ho verificato che le parti misurate — la lista
  `_WORKS_PATTERN` e il carve-out — sono **identiche** nei due artefatti.
* 🔑 **La regola che propongo**: ogni referto dichiari **da quale dei due** viene ogni riga. «Da
  utente» e «dal repo» sono due prodotti, non due modi di guardare lo stesso.

**Caveat**: un solo pacchetto (`verimem 0.7.0`, installato il 08/08 alle 12:53), un solo sistema
operativo, `--help` come fonte per i comandi visibili. Non ho verificato se PyPI ospita release
successive non installate di default: `pip` ha risolto a 0.7.0, che è anche l'ultima dichiarata dal repo.
