# Fetta ⑤ — COME INGERIAMO I DOCUMENTI

**Autrice**: Archivista·ws6 · **Data**: 2026-08-08 · **SHA di partenza**: `544d27bd`
(albero pulito) · **Livello di misura**: la **CLI**, cioè la porta che l'utente usa —
`verimem index` e `verimem search-docs`, non le funzioni interne.
**Metodo**: store isolato creato da zero (`ENGRAM_DATA_DIR` impostata **prima**
dell'import), file di prova generati per l'occasione con `reportlab` e `python-docx`.
**Ogni riga qui sotto è stata eseguita.** Gli esempi in lingua vengono da
`banco-caratteri-difficili.md`, non dalla mia testa.

---

## 1. Che formati entrano DAVVERO

Il `--help` dichiara: *«Extracts text (pdf/docx/html/txt), splits it into
provenance-anchored chunks»* e l'argomento dice `[pdf/docx/html/txt/md]`.
Provati tutti, più tre casi che il help non menziona:

| file | dimensione | esito | output esatto |
|---|---|---|---|
| `prova.txt` | 178 B | ✅ exit 0 | `indexed …prova.txt` |
| `prova.md` | 209 B | ✅ exit 0 | `indexed …prova.md` |
| `prova.html` | 264 B | ✅ exit 0 | `indexed …prova.html` |
| `prova.pdf` (2 pagine, reportlab) | 1 975 B | ✅ exit 0 | `indexed …prova.pdf` |
| `prova.docx` (python-docx) | 36 729 B | ✅ exit 0 | `indexed …prova.docx` |
| `cinese.txt` (罗维戈仓库…) | 93 B | ✅ exit 0 | `indexed …cinese.txt` |
| **`prova.csv`** | 93 B | ❌ **exit 1** | `unsupported file type '.csv' for prova.csv` |
| **`prova.xlsx`** | 469 B | ❌ **exit 1** | `unsupported file type '.xlsx' for prova.xlsx` |
| **`rotto.pdf`** (header valido, corpo casuale) | 409 B | ❌ exit 1 | `Failed to open file …` |

**Verdetto**: i cinque formati dichiarati funzionano tutti, incluso il cinese.
**CSV e XLSX non sono supportati** — e il messaggio è corretto e non ambiguo
(exit 1 + tipo nominato), quindi è un limite dichiarato, non un difetto.
Il **file corrotto fallisce in modo pulito**: exit 1, nessun chunk sporco entrato,
nessuna eccezione non gestita.

> ⚠️ **Nota per il prodotto**: un utente che tiene gli inventari in Excel o in CSV
> — cioè la maggioranza di chi ha «documenti aziendali» — non può indicizzarli.
> È la richiesta più prevedibile che il formato-elenco possa ricevere.

## 2. La domanda che conta: si ottiene una CITAZIONE ESATTA con la pagina?

**NO.** Ed è il finding centrale di questa fetta.

Il PDF di prova ha **due pagine**, e la sede di Trento compare **solo a pagina 2**.
Interrogato con `search-docs "Quanti pallet contiene la sede di Trento?"`:

```
1. (0.875) file:…\prova.pdf:0-203 (v1)
   Inventario 2027 - pagina 1
   Il magazzino di Verona contiene 480 pallet. …
   Inventario 2027 - pagina 2
   La sede di Trento contiene 21…
```

Due fatti nell'ancora `prova.pdf:0-203`:
1. **L'ancora è un intervallo di CARATTERI (offset 0-203), non una pagina.** Il
   prodotto mantiene la promessa di *provenance-anchored chunks* — l'ancora è
   precisa e verificabile — ma **non è la pagina**, che è l'unità con cui un umano
   cita un documento.
2. **Il chunk ATTRAVERSA le due pagine**: contiene «pagina 1 … pagina 2 …» insieme.
   Quindi l'informazione di pagina non è solo non mostrata: è **perduta a monte**,
   nella fase di estrazione, e nessuna modifica alla stampa potrebbe recuperarla.

⇒ Alla domanda «l'utente riesce a tirare fuori una citazione esatta con la pagina?»
la risposta è **no, e non è una questione di formato dell'output**.

## 3. Chunking

- **Dimensione osservata del chunk: ~970 caratteri** (ancora `grande.txt:0-970`).
- Su un file di 178 byte il chunk è unico e coincide col file (`prova.txt:0-178`).
- I chunk **non rispettano i confini di pagina** (vedi §2) e, sul file lungo,
  neppure i confini di riga.

## 4. File grande — misurato, non estrapolato

| file | dimensione | tempo `index` | esito |
|---|---|---|---|
| `lungo.txt` | 23 600 B (23 KB) | **44,6 s** | exit 0 |
| `grande.txt` | 9 868 270 B (**9,4 MB**) | **184,6 s (3 min)** | exit 0 |

**Non esplode: rallenta.** 9,4 MB richiedono tre minuti e non c'è nessuna barra di
avanzamento né stima — l'utente vede il terminale fermo.
⚠️ **Limite dichiarato**: la fetta chiedeva 50 MB, io ho misurato **9,4 MB**. Non
extrapolo il tempo perché non ho verificato che il costo sia lineare; quello che
posso dire è che a 9,4 MB il comando termina correttamente in 3 minuti.

## 5. Doppia indicizzazione — la promessa è mantenuta

```
PDF (1a volta):  indexed …prova.pdf                              exit 0
PDF (2a volta):  unchanged — already indexed as v1 (0 new chunks) exit 0
```

**Idempotente per content-hash, come dichiarato nel `--help`**, e lo dice
all'utente con una riga esplicita (`0 new chunks`). È una delle cose che
funzionano meglio di come sono raccontate.

## 6. Un difetto ereditato dal percorso di lettura (non mio, confermato)

Interrogando **in cinese** (`罗维戈仓库有多少个托盘`) uno store che contiene **solo
documenti italiani**, il tier documenti risponde comunque, con un chunk italiano a
**0.832** di similarità. Nessuna astensione.

Il prodotto lo **dichiara da sé** in coda al risultato — *«top-2 per similarità:
questi sono i chunk più vicini alla domanda, non una risposta verificata. Il tier
documenti non si astiene — usa `--min-score` per tagliare, o `verimem trust`»* — e
la cura suggerita è stata verificata funzionante da Ester nella fetta ④.
Lo riporto perché **è il comportamento che vede chi indicizza documenti**: la
ricerca documentale, da sola, è un motore di similarità, non una memoria verificata.

---

## Riepilogo per Aurelio

**Cosa funziona davvero**: cinque formati su cinque fra quelli dichiarati (txt, md,
html, pdf, docx), il cinese incluso; l'idempotenza per hash con messaggio esplicito;
il fallimento pulito su file corrotto e su formato non supportato.

**Cosa non c'è**: la **citazione per pagina** (l'ancora è al carattere e i chunk
attraversano le pagine) · **CSV e XLSX** · qualunque **indicazione di avanzamento**
su file grandi (3 minuti di terminale muto a 9,4 MB).

**Cosa è spento in senso proprio**: niente, in questa fetta. Tutto ciò che ho
provato o funziona o dice chiaramente di non farlo.
