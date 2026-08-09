# ② duodecies — Le promesse su `origin/main`: la colonna che serve al rilascio

> **ws2 «Vega» · 08/08 ore 15:37–15:42 · `origin/main` `793dd4c7` in worktree separato,
> `git status` VUOTO · store fresco per ogni esecuzione**
> Avevamo la colonna «pacchetto» e quella del mio ramo. Mancava **quella che verrà pubblicata**.
> Il mio albero ha 48 commit oltre main e modifiche di altre istanze: per questa misura **non l'ho
> usato**.

---

## La tabella completa

| promessa | pacchetto 0.7.0 | **`origin/main` 793dd4c7** |
|---|---|---|
| P16 — screen lessicale su ogni write | ✅ | ✅ `quarantined`, grounding 94,7 |
| P17 — ammesso solo se la fonte sostiene | ✅ | ✅ sostiene 94,1 · smentisce 1,1 quarantinato |
| P19 — senza source → `model_claim` | ✅ | ✅ |
| P20 — quarantinato fuori dal recall | ✅ | ✅ non è fra i risultati |
| P23 — `null` = mai giudicato | ✅ | ✅ |
| P8 — supersessione esplicita, il vecchio resta | ✅ | ✅ recuperabile |
| P3 — `history(fact_id)` bi-temporale | ✅ | ✅ 2 voci |
| P18 — `verified_by` non fa girare il moat | ✅ | ✅ `grounding=None` |
| **astensione** — `explain` si astiene | ❌ **FALSA** — `min_relevance 0.0` | ✅ **VERA** — 2/2, `min_relevance 0.8688` |
| P24 — `confidence` non è un segnale di fiducia | ⚠️ regge trivialmente | ⚠️ regge trivialmente |
| P25 — i nomi legacy funzionano | ⚠️ vedi sotto | ⚠️ **non misurabile così** |

**Su main reggono tutte le promesse verificabili, e l'unica che cadeva sul pacchetto — l'astensione
— è vera.** La cura è **già in main**: non dipende dai sei rami non ancora mergiati.

## 🪞 Due celle che il mio banco NON misura, e vanno dette

* **P24** regge in modo **triviale**: `confidence` è `null` in tutte le condizioni perché l'SDK non
  lo espone nella risposta di `add()`. Formalmente vera, ma il banco non la mette alla prova.
* **P25 è contaminata dal percorso.** Su un worktree `import hippoagent` riesce perché la directory
  `hippoagent/` **è lì**, non perché il pacchetto la installi. Su `origin/main` risulta «import OK»
  e non significa nulla. L'unica misura valida è sul **wheel costruito da main**, ed è quella che
  `tests/test_il_pacchetto_ha_cio_che_promettiamo.py` sa fare.

## Per chi pubblica

Due controlli, entrambi già scritti:

1. **il pavimento**: due `Memory()` su store vuoti, `explain()` su una domanda estranea, si guarda
   `min_relevance`. **0.8688** → l'astensione è viva; **0.0** → la promessa è di nuovo falsa.
2. **il banco del pacchetto**: `pytest tests/test_il_pacchetto_ha_cio_che_promettiamo.py`
   (oggi `2 passed, 2 xfailed`). Il test sulla distanza **xpassa** al bump della versione — è il
   segnale che l'artefatto e il codice sono tornati a coincidere.

**Caveat**: 3 domande e 2 fatti per l'astensione, una scrittura per promessa, un dominio, un OS.
Misurato tramite l'SDK: **le porte MCP e gateway su main non le ho provate** — la prima la può fare
solo ws1, che è un client MCP vivo. E P13 (fail-open senza giudice) non l'ho **rimisurata** su main:
resta la misura sul pacchetto in [02g](02g-il-primo-comando-a-freddo.md).
