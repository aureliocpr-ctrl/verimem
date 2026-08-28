# Lo scambio di **date** non ha un proprietario nel prodotto — e ritiro il modo in cui l'avevo detto

*ws3 (Galileo), 28/08 ~21:15. **Nessuna esecuzione**: regime risparmio RAM
(ordine di Aurelio, `d9fc92fbc0d91d41`). Questo referto è ottenuto **leggendo
il sorgente**, e ogni affermazione porta il suo file e la sua riga.*

## Prima, il ritiro

Avevo elencato fra i tre difetti dell'estrattore (`8157a777`):

> «③ le **date** non escono affatto: `«Il termine è fissato al 12 marzo 2027»`
> → `[]`»

**Come difetto è sbagliato, e lo ritiro.** `extract_quantities` esclude le date
**di proposito**, e il modulo lo dichiara: `quantity_match.py:23-26` — «*bare
years are NOT quantities — they belong to the year-disjoint rule in
`validate_claim`, so the two detectors never…*» — e `_spans_delle_date` salta i
numeri di una data **in blocco**, con una motivazione scritta.

⇒ **Non è un buco: è un instradamento.** Le date hanno un percorso loro,
`extract_dates` / `date_conflict`. **Chiamarlo difetto era mio, e nasce dal non
aver cercato il percorso gemello prima di enunciare.**

## Ma la domanda vera resta, ed è più stretta

*Lo scambio di date è coperto da quel percorso?* La risposta è **no**, e per una
ragione **strutturale**, non per una dimenticanza.

`quantity_match.py:1814` — `date_conflict(text_a, text_b)`:

```
"""A sub-year date move about the same subject: same (or unstated) year
but a DIFFERENT month, or same year+month but a different day."""
da, db = extract_dates(text_a), extract_dates(text_b)
if not da or not db or (da & db):
    return None
```

**Due cose, e ognuna da sola basterebbe.**

**① È cablata claim-contro-FATTO, non claim-contro-FONTE.** L'unico chiamante
nel gate è `validate_claim.py:857` → `_date_conflict(claim, f.proposition)`:
confronta il claim con **un fatto già memorizzato**. Lo scambio di attribuzione
è invece claim **contro la propria fonte**, e su quella porta la funzione non
viene mai chiamata.

**② E se anche la si chiamasse, si asterrebbe per costruzione.** La prima
guardia è `if … (da & db): return None` — *se i due testi condividono una data,
non c'è movimento*. Nello scambio la fonte contiene **entrambe** le date:

    fonte:  «Art. 5 - Il termine di CONSEGNA e' fissato al 12 marzo 2027.
             Art. 6 - Il termine per la CONTESTAZIONE e' fissato al 30 aprile 2027.»
    claim:  «Il termine di consegna e' fissato al 30 aprile 2027.»   ← scambio

`extract_dates(claim) = {30 aprile 2027}` è **un sottoinsieme** di
`extract_dates(fonte)` ⇒ `da & db` non è vuoto ⇒ **`None`**.

> 🔑 **E la guardia è giusta per il lavoro che quella funzione fa.**
> `date_conflict` modella uno **spostamento** di data fra **due asserzioni**
> («la scadenza era il 12 marzo, ora è il 30 aprile»). Una data condivisa
> significa, lì, *nessuno spostamento*. **Lo scambio di attribuzione è un
> fenomeno diverso**: le date non si muovono affatto — si scambiano di
> **soggetto** dentro **un solo testo**.

## Quindi

| chi potrebbe coprirlo | perché non lo fa |
|---|---|
| `L4.1` (valori) | le date **non** entrano in `extract_quantities`, per progetto |
| `date_conflict` | cablata **claim vs fatto**, e la guardia `da & db` la fa astenere quando la fonte porta entrambe le date |
| il **giudice** | è la difesa che si sgretola con la lunghezza della fonte (misurato: 7/12 → 10/12 ammessi) |
| `L4.3` (mio) | **inesprimibile**: senza valori estratti non ha nulla su cui lavorare — 2 dei 12 scambi lo sono già |

⇒ **Lo scambio di date non ha un proprietario**, e il motivo non è che qualcuno
se ne sia dimenticato: **è un fenomeno che nessuno dei tre modelli in casa
rappresenta**. Il valore-quantità non le vede, il conflitto-di-data vuole due
asserzioni e un movimento, il giudice non è deterministico.

## Cosa NON propongo, e perché

**Non propongo di far entrare le date in `extract_quantities`.** L'esclusione è
dichiarata, motivata, e ha un percorso gemello che funziona per il suo scopo:
toccarla per far posto a `L4.3` significherebbe **rompere una cosa che funziona
per servirne una che non è ancora validata**. La strada, semmai, è un
estrattore di date **usato da `L4.3`**, che è un pezzo nuovo e vuole il suo
banco — **non stasera, e non senza misura**.

## Limiti, dichiarati

⚠️ **Nessuna esecuzione**: tutto letto nel sorgente all'albero corrente. Le due
affermazioni sopra sono **verificabili leggendo**, ma **non le ho misurate a
runtime** — in particolare non ho eseguito `date_conflict` sul caso dello
scambio per vedere il `None` uscire davvero. **Fino ad allora è lettura di
codice, non evidenza di comportamento**, ed è la distinzione che ci è già
costata dei ritiri.
⚠️ Ho cercato i chiamanti con `grep` su `verimem/*.py`: **un chiamante fuori da
quella cartella, o costruito dinamicamente, mi sfuggirebbe.**
