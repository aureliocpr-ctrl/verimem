# Primo avvio — il gate lessicale protegge l'inglese, non l'italiano

**Autore**: ws2 «Vega» · **Data**: 2026-08-08, ore 13:50
**SHA**: vedi `git log` di questo commit · **albero**: pulito al momento della misura
**Ambiente**: `pip install verimem 0.7.0` **da PyPI**, venv nuovo, `HOME` finto,
`env -u ENGRAM_DATA_DIR -u HIPPO_DATA_DIR -u VERIMEM_DATA_DIR`. Moat **ON** (warmup eseguito).

## 1. Il fatto

Stesso vanto, due lingue, nessuna prova allegata, porta di scrittura reale (`remember`):

| comando | esito |
|---|---|
| `remember "the migration is complete"` | **quarantined** |
| `remember "la migrazione e' completata"` | **ADMITTED** |
| `remember "all tests pass"` | admitted |
| `remember "tutti i test passano"` | admitted |

La traduzione letterale dello stesso vanto **passa**.

## 2. La popolazione, misurata su `trust` (stesso gate, più veloce da interrogare)

| claim (nessuna prova) | esito |
|---|---|
| all tests pass | TRUSTED |
| tutti i test passano | TRUSTED |
| the migration is complete | **FLAGGED** |
| la migrazione e' completata | TRUSTED |
| coverage is at 85 percent | TRUSTED |
| la copertura e' all'85 per cento | TRUSTED |
| it works in production | **FLAGGED** |
| funziona in produzione | **FLAGGED** |

**2 FLAGGED su 8.** I due che scattano contengono parole inglesi; il terzo
(«funziona in produzione») scatta perché «produzione» è nella lista.

## 3. Un difetto di documentazione, separato

La docstring di `trust` promette: *«Add a real provenance ref (--verified-by commit:... /
ci:...:green / coverage:N) and watch the same claim pass»*. Misurato:

* «il sistema e' production-ready e tutti i test passano» + `--verified-by ci:main:green`
  → **resta FLAGGED** (`L1.9`: performance claim senza bench evidence)
* «il commit e' stato fatto» + `--verified-by commit:abc123` → **resta FLAGGED**

**2 casi su 2 provati**: la promessa scritta non regge.

## 4. Precisazione su una mia misura precedente

Nella sezione ② avevo segnalato che `trust` risponde `TRUSTED` a una domanda senza dati.
**Non è un difetto del gate**: `trust` chiama `run_validation_gate` (`cli.py:1431`), cioè il
gate di *scrittura*, non `trust_report`. Valuta un claim, non interroga la memoria. Il difetto
è che il **nome** fa aspettare un'altra cosa — e la docstring dice «would Verimem trust this
claim», che è corretto ma si legge come «quanto ti fidi di questa risposta».

## 5. Limiti dichiarati

* 8 claim, una macchina, un giro. **Non è un tasso**: è un banco di rottura con coppie
  minime (stessa frase, due lingue).
* **Non ho letto la lista dei detector**: misuro dalla porta. Chi ha il perimetro del gate
  (ws3) sa se la lista è estendibile — ma la lezione di ieri dice che allungare una lista
  monolingua non è la cura giusta: la decisione è sua.
* Non ho misurato la popolazione opposta di una *cura*, perché non propongo una cura: propongo
  il fatto.


---

# ⚠️ CORREZIONE (ore 14:05) — la mia conclusione era troppo larga

La §1-2 diceva **«il gate protegge l'inglese, non l'italiano»** su 8 claim che avevo scelto
senza coppie. Rifatto con **10 coppie minime** (stessa frase, due lingue, nessuna prova):

| inglese | | italiano | |
|---|---|---|---|
| it works | FLAGGED | funziona | FLAGGED |
| it is verified | FLAGGED | e' stato verificato | FLAGGED |
| it is done | FLAGGED | e' fatto | FLAGGED |
| the bug is fixed | FLAGGED | il bug e' risolto | FLAGGED |
| it is stable | FLAGGED | e' stabile | FLAGGED |
| fully tested | FLAGGED | completamente testato | FLAGGED |
| all tests pass | TRUSTED | tutti i test passano | TRUSTED |
| performance improved by 40% | TRUSTED | le prestazioni sono migliorate del 40% | TRUSTED |
| **the migration is complete** | **FLAGGED** | **la migrazione e' completata** | **TRUSTED** |
| **it is production-ready** | **FLAGGED** | **e' pronto per la produzione** | **TRUSTED** |

**8 coppie su 10 concordano.** Le divergenze sono **2 su 10**, sempre nello stesso verso
(l'inglese ferma, l'italiano no).

## Cosa resta vero, e cosa ritiro

* ❌ **RITIRO** «il gate protegge l'inglese, non l'italiano»: i tre verbi che la promessa
  nomina — *works / verified / done* — sono coperti **in entrambe le lingue**.
* ✅ **RESTA** che la copertura italiana è **parziale**: in 2 casi su 10 un vanto che l'inglese
  ferma passa in italiano. Il caso `remember "la migrazione e' completata" → ADMITTED` della §1
  è **confermato**, ma è un caso specifico, non la regola.
* 🔑 **E la popolazione opposta dice una cosa in più**: 2 coppie sono TRUSTED in **entrambe** le
  lingue (`all tests pass`, `performance improved by 40%`). Quindi **esistono vanti che il gate
  non copre in nessuna lingua** — il difetto non è solo linguistico, è di copertura della lista.

## Attacco alla fetta ① di ws1 (catena avversariale)

ws1 dichiara **P16 VERO** con questa prova: `m.add("La migrazione è stata completata e funziona
perfettamente.")` → `quarantined`. **Rieseguita alla cieca, isolando le due metà:**

| frase | esito |
|---|---|
| «La migrazione è stata completata **e funziona perfettamente**.» (sua) | **FLAGGED** |
| «La migrazione è stata completata.» | **TRUSTED** |
| «Funziona perfettamente.» | **FLAGGED** |

⇒ **La sua P16 regge, ma per la seconda metà della frase, non per la prima.** L'esempio contiene
due vanti e ne scatta uno solo. La promessa («*it works / verified / done*») è verificata da
*funziona*; *completata* non è coperto in italiano.
📌 Non è un errore di ws1: è un esempio che prova meno di quanto sembri. Suggerisco di sostituirlo
con un vanto singolo, così la prova isola ciò che dichiara.
