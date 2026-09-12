# `verimem/negation_scope.py` — 105 righe, 3 funzioni

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **08/09**.

> ⚠️ **File nella parte del lead** (indice: 105 righe, 3 funzioni). Mappato da
> ws1 perché era uno dei **tre file di `verimem/` interamente non nominati da
> nessun test** — il reperto del mio righello, e verificarlo è il mio pezzo.

## Che cosa promette, e perché esiste

Sapere **fin dove arriva** un negatore. Il lessico dei negatori non sta qui
(vive in `quantity_match._NEGATOR_RE`, undici lingue): questo modulo aggiunge la
**portata**.

Il perché è la parte che conta, ed è scritta nel docstring: nove detector L1 su
dodici punivano le frasi oneste —

```
L1.10  «Il modulo NON funziona in produzione.»          scattava
L1.11  «Il sistema NON e' pronto per la produzione.»    scattava
L1.12  «Il servizio NON e' sicuro contro SQL injection» scattava
L1.13  «La migrazione NON e' completata.»               scattava
```

> «Un gate anti-confabulazione che punisce "questo non funziona" scoraggia
> esattamente la scrittura più preziosa per una memoria verificata — la
> smentita, il limite noto, il non-ancora-fatto: **chi è onesto viene
> quarantinato e chi tace no**.»

## Lo stato della misura

**Vivo e usato**: `anti_confab_gate.py:140-141` importa `e_un_claim_negativo` e
`tutte_le_occorrenze_sono_negate`. `l1_tested_detector.py:25` lo cita come
la superficie unica della negazione.

**Nessun test lo nomina** (righello `ast` sui 1.657 file): è esercitato solo di
rimbalzo dai test del gate. ⇒ un modulo che decide **se una smentita viene
quarantinata** non ha un banco proprio.

Le sue tre funzioni sono **pure** (testo → bool), quindi si provano a costo zero:
niente giudice, niente store, niente daemon. **L'ho fatto.**

## Il banco: 16 promesse del docstring, tradotte in predizioni

Ogni caso viene da una frase del modulo, non da me — la traduzione è
contestabile riga per riga.

```
OK  «non è mai stato validato»: 'validato' è governata (25 char, dentro i 60)
OK  «non è stato rilasciato, ma funziona»: 'funziona' NON è governata
OK  un «non» in apertura NON spegne la frase successiva (il punto taglia)
OK  oltre la finestra di 60 caratteri il negatore non governa
OK  «non funziona in staging ma funziona in produzione» → False (un'occorrenza libera)
OK  tutte e due negate → True
OK  la parola non compare → False (niente da negare)
OK  testo vuoto → False
OK  «Il modulo NON funziona in produzione» è un claim negativo
OK  «Il modulo funziona in produzione» NON è un claim negativo
OK  undici lingue: «is not ready» è un claim negativo
OK  testo vuoto → False
OK  i quattro claim dei detector L1.10-L1.13 riconosciuti come negativi   (4 casi)

16 casi · tutti come promesso                                        EXIT=0
```

Le due che valgono più delle altre, perché sono quelle in cui una guardia mal
fatta diventa un'arma:

- **«non è stato rilasciato, ma funziona»** — se il «ma» non chiudesse la
  portata, un fatto con una premessa negativa risulterebbe negato per intero.
- **«Non abbiamo finito. Il sistema è vulnerabile a SQL injection.»** — se un
  «non» in apertura spegnesse tutto il resto, **la guardia diventerebbe un
  interruttore per chi la conosce**: basterebbe aprire con una negazione per
  passare qualunque claim. Il punto taglia. ✅

## La tabella

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | test | verdetto | prova |
|---|---|---|---|---|---|---|
| 1 | `verimem/negation_scope.py:53` `governata_da_negazione` | c'è un negatore che governa la parola a `inizio`? Finestra 60 char, tagliata da punteggiatura e da `ma/però/but/yet/however/tuttavia` | `:80` (`tutte_le_occorrenze_sono_negate`) | **nessuno lo nomina** | **FUNZIONA COME PROMESSO** | 4 casi su 4, incluso il taglio del «ma» e la finestra |
| 2 | `verimem/negation_scope.py:64` `tutte_le_occorrenze_sono_negate` | **ogni** occorrenza è negata? Basta una libera perché il warning resti; `False` se la parola non c'è | `anti_confab_gate.py:141` | **nessuno lo nomina** | **FUNZIONA COME PROMESSO** | 4 casi su 4, incluso «staging/produzione» |
| 3 | `verimem/negation_scope.py:85` `e_un_claim_negativo` | il claim afferma un'**assenza**? Serve al moat, il cui verdetto su quella classe non è affidabile (nessuna assunzione di mondo chiuso) | `anti_confab_gate.py:140` | **nessuno lo nomina** | **FUNZIONA COME PROMESSO** | 8 casi su 8, IT e EN, più i quattro claim L1.10-L1.13 |

## Il verdetto

**FUNZIONA COME PROMESSO su tutte e tre**, con 16 casi eseguiti — e il modulo è
scritto bene: la guardia sta **in un punto solo**, come il suo docstring
rivendica, e non è aggirabile con un «non» in apertura.

⚠️ **Ma resta un presidio mancante**: nessun test nel repo esercita queste tre
funzioni per nome. Se qualcuno le rompesse, se ne accorgerebbero solo i test del
gate, di rimbalzo, e con una diagnosi molto più lontana dalla causa. Per un
modulo che decide **se una smentita onesta viene quarantinata**, un banco
proprio costa dieci righe: **i 16 casi qui sopra sono già scritti** e girano in
un secondo — `<scratchpad>/negation_scope_banco.py`, pronto da promuovere a
`tests/test_negation_scope.py` da chi ha il file. **Non lo promuovo io**:
regola 2, e non è la mia parte.

## Che cosa NON ho misurato

- **Non ho rotto nessuna riga** per verificare che i test del gate se ne
  accorgano: costerebbe far girare il giudice, e non ho preso il claim CPU.
  ⇒ «se ne accorgerebbero di rimbalzo» è una **lettura**, non una misura.
- Le **undici lingue** di `_NEGATOR_RE`: ho provato IT e EN. Le altre nove
  **NON MISURATE** da me — e stanno in `quantity_match.py`, che è di @ws4 ML.
