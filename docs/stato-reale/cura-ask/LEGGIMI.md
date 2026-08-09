# `verimem ask` non avverte dove `recall` avverte

Materiale di lavoro: diff pronto, guardiano e banco di verifica. **Non applicato al ramo principale.**

## Il difetto

Sulla stessa domanda senza risposta, con lo stesso store e gli stessi punteggi:

```
verimem recall  ->  ⚠ il migliore di questi (0.786) sta sotto il pavimento che lo store
                    ha misurato su se stesso (0.874): sono i fatti più vicini alla
                    domanda, non necessariamente una risposta.
                    - Il pagamento delle fatture e fissato a 60 giorni. [0.78]

verimem ask     ->  intento: find
                    - Il pagamento delle fatture e fissato a 60 giorni. [0.78]
                    (e basta: identico a una domanda che HA risposta)
```

Le due porte rispondono alla stessa domanda: quale delle due venga digitata non dovrebbe
decidere se l'avviso compare. `ask` mostra già il punteggio `[0.78]` — l'informazione c'è,
manca il confronto col pavimento.

Verificato su **tre artefatti**: repo `7bf3b6ac`, wheel `00581a4f`, wheel `51438109`.
Muto in tutti e tre. Non è una regressione: il blocco dell'avviso non è mai esistito in
`ask_cmd`.

## Contenuto

| file | cos'è |
|---|---|
| `cura_ask.diff` | diff su `verimem/cli.py` (97 righe), contro **`391ef6a1`** |
| `test_ask_taceva_dove_recall_avvisava.py` | guardiano, 4 test, controllo positivo incluso |
| `banco_verifica_cura.py` | banco a due popolazioni: misura l'esito, non la presenza del codice |

## La cura, in tre mosse

1. **estrae** `_avviso_pavimento(m, hits, query)` dal corpo di `recall_cmd`, col commento
   originale (spiega una decisione, non un'implementazione);
2. `recall_cmd` **chiama** invece di contenere il blocco inline;
3. `ask_cmd` **conserva l'oggetto `Memory`** (oggi `_open_memory().ask(...)` lo scarta) e
   **chiama l'avviso nel solo ramo `find`**.

> ⚠️ **Non è copia-incolla.** Duplicare il blocco produce due superfici che divergono, difetto
> già pagato su questo prodotto. Il ramo `count` esce prima con `typer.Exit(0)` e va lasciato
> invariato: non ha punteggi da confrontare.

## Verifica — eseguita in copie congelate, ramo principale intatto

`git diff --stat -- verimem/cli.py` sul repo condiviso: vuoto.

| | domanda senza risposta | domanda con risposta |
|---|---|---|
| `recall` prima e dopo | avvisa | tace |
| `ask` **prima** | **muto** | muto |
| `ask` **dopo** | **avvisa** | **tace** |

Nessun avviso aggiunto dove non serve; `recall` e il ramo `count` invariati.

**RED falsificato in due modi:**

```
codice SENZA la cura            -> EXIT=1   (cade test_sotto_il_pavimento_ask_lo_dice)
codice CON la cura              -> EXIT=0   (4 passed)
cura applicata, chiamata TOLTA  -> EXIT=1
```

**Test esistenti invariati** — `test_recall_dice_quando_e_sotto_il_pavimento`,
`test_la_cli_non_mostrava_perche_il_conteggio_era_zero`,
`test_la_porta_del_pavimento_sulla_riga_di_comando`: EXIT=0 prima e dopo.

## Due trappole emerse durante la stesura

- **Una patch può compilare, avere le chiamate al posto giusto ed essere inerte.** Una prima
  stesura chiamava se stessa — la funzione era stata inserita col blocco all'interno e il blocco
  sostituito dopo. Il `RecursionError` veniva assorbito dal `try/except`, quindi `ask` restava
  muto e la cura sembrava inefficace. Lo rileva solo un banco che misura l'**esito** su due
  popolazioni, non la presenza del codice. Il diff qui incluso supera un controllo AST che
  verifica l'assenza di ricorsione.
- **Il verdetto va letto dal codice di uscita, mai dal testo**: un pipe può assorbire il rosso.

## Stato

Diff verificato e non integrato. Se il ramo si è mosso, `git apply` può non attaccare: in tal
caso va rigenerato eseguendo il banco sulle due copie.
