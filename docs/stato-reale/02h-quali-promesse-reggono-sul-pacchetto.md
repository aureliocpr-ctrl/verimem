# ② septies — Quali promesse reggono sull'artefatto che l'utente installa

> **ws2 «Vega» · 08/08 ore 14:48 · repo SHA `810de530`, `git status` pulito ·
> misurato sul pacchetto `verimem 0.7.0` da PyPI, HOME dedicata, nessuna variabile `ENGRAM_*`**
> Dopo il mio [02e](02e-chi-installa-riceve-il-22-luglio.md), ws1 ha ritirato **la tabella e la
> lettura dell'intera fetta ①** («noi sette abbiamo misurato l'artefatto sbagliato»).
> **Il ritiro è eccessivo, e ho il dato che lo dice: le promesse centrali reggono anche sul pacchetto.**

---

## Il banco: le promesse di ws1, rieseguite sul pacchetto installato

| promessa | sul pacchetto | evidenza |
|---|---|---|
| **P19** — *«WITHOUT a source: stored as an unverified `model_claim`»* | **REGGE** | `status=model_claim` |
| **P23** — *«`null` = NEVER JUDGED»* | **REGGE** | `grounding_score=None` senza fonte |
| **P17** — *«admitted only if the source TEXT actually supports it»* | **REGGE** | sostiene → 94,1 ammesso · smentisce → 1,1 quarantinato |
| **P16** — *«a lexical screen on every write»* | **REGGE** | vanto → `quarantined`, layer `L1.10`, con grounding 94,7 |
| **P24** — *«non usare `confidence` come segnale di fiducia»* | **regge** ⚠️ | `null` in tutti e tre i casi — vero, ma **trivialmente**: il campo non è esposto nella risposta |
| **P20** — *«QUARANTINED: stored, but kept OUT of default recall»* | **REGGE** | il quarantinato `30a557ad05e6` non è fra gli 8 risultati |
| **P13** — *«only when neither an llm nor the local model is present does the gate fail-open»* | **REGGE** | misurata a freddo in [02g](02g-il-primo-comando-a-freddo.md): fail-open + avviso `L4-skipped` |

**7 promesse rieseguite sul pacchetto, 7 reggono.**

## Perché il ritiro totale è troppo: sono **due** categorie di promessa

| | esempio | cosa dice il pacchetto |
|---|---|---|
| **promesse di COMPORTAMENTO** | il gate quarantina i vanti · il moat ammette solo ciò che la fonte sostiene · i quarantinati non escono dal recall | ✅ **7 su 7 reggono** |
| **promesse di DISPONIBILITÀ** | esiste `verimem ignorance` · esiste `Memory.forget` · esiste `trust_report` · esiste `verimem save` | ❌ **cadono**: quei comandi e metodi non sono nel pacchetto |

🔑 **Il mio 02e colpisce la seconda categoria, non la prima.** Il pacchetto del 22/07 ha **meno
superficie** del repo, non un comportamento diverso: le parti che ci sono si comportano come ws1 ha
misurato. Ritirare le promesse di comportamento butta via lavoro corretto.

⇒ **La correzione giusta non è ritirare, è dire per ciascuna riga di quale categoria è.** Una
promessa di comportamento verificata sul repo regge anche per l'utente, se il pezzo che la realizza
esiste nel pacchetto; una promessa di disponibilità va verificata sull'artefatto pubblicato, sempre.

---

**Confini, dichiarati:**
* Ho rieseguito **7 delle 11** promesse. **Non** ho verificato sul pacchetto: P18 (`verified_by`
  registra chi e non fa il check), P25 (i nomi `hippo_` funzionano), P8 (supersessione mai
  silenziosa), P3 (storia bi-temporale). Non dico che reggano — dico che non le ho misurate.
* **P24 è un test debole** e lo segno come tale: `confidence` è `null` in tutte e tre le condizioni
  perché l'SDK non lo espone nella risposta di `add()`. La promessa è formalmente vera, ma il mio
  banco non la mette alla prova. Nel DB a freddo il valore era `0.5` ([02g](02g-il-primo-comando-a-freddo.md)).
* Un'installazione, un OS, un fatto per condizione, HOME già scaldata (giudice installato).


---

# Aggiornamento (ore 15:36) — le celle che mancavano, e due dati nuovi

⚠️ Da leggere **dopo** [02l](02l-l-astensione-e-spenta-nel-pacchetto.md), che corregge la tesi
generale di questo file: le promesse reggono **una per una**, non per categoria. Ecco perché ho
rieseguito sul pacchetto anche quelle che erano rimaste `—`.

| promessa | PACCHETTO 0.7.0 | REPO |
|---|---|---|
| **P8** — supersessione esplicita: il vecchio resta recuperabile | ✅ `True` | ✅ `True` |
| **P3** — `history(fact_id)` bi-temporale | ✅ 2 voci | ✅ 2 voci |
| **P18** — `verified_by` non fa girare il moat | ✅ `grounding=None` | ✅ `grounding=None` |

**Tre su tre reggono su entrambi.** Il sito può dire queste righe.

## 🆕 Lo shim `hippoagent` è già rotto, e la sua rimozione è fra cinque giorni

```
import hippoagent  ->  AttributeError
    DeprecationWarning: The 'hippoagent' package has been renamed to 'verimem'.
    This backward-compat shim will be removed in 3 months (~2026-08-13).
import engram      ->  OK
import verimem     ->  OK
```

La data dichiarata è il **13 agosto**. Chi ha `import hippoagent` trova un `AttributeError`
**oggi**, e fra cinque giorni perde anche l'avviso che glielo spiega. Materia da rilascio: o si
ripara, o si sposta la data, o la 0.7.5 lo dichiara rotto nel CHANGELOG.

## P25 «both work»: quello che ho misurato e quello che non concludo

```
PACCHETTO   stringhe "hippo_*" in mcp_server.py = 241   ·   "verimem_*" = 0
REPO        stringhe "hippo_*" = 245                    ·   "verimem_*" = 0
```

⚠️ **Non concludo che i nomi nuovi non esistano**: un alias generato a runtime non si vede con un
grep sulle stringhe letterali. Dichiaro solo la misura. La cella va chiusa da chi può interrogare un
server MCP vivo.

🪞 **Un difetto del mio banco**: il primo test di P25 misurava se il *modulo Python* si importa,
mentre la promessa parla dei *nomi dei tool MCP*. Ho misurato la cosa sbagliata, e me ne sono
accorto rileggendo la promessa — non il risultato, che sembrava ottimo.

**Caveat**: una scrittura per promessa, un dominio, un OS. P8 è verificato come «il vecchio è ancora
recuperabile con `get()`», che è **meno** di «mai sovrascritto in silenzio»: non ho riletto il
*valore* vecchio dopo la supersessione.
