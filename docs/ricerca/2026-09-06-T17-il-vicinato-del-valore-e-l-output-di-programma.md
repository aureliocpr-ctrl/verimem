# T17 — `L4.2` e l'output di programma: cinque giunture, una cura misurata

*ws3 Galileo, 06/09/2026, 06:40–07:50. Ticket aperto da Iris (3317d989549f3ac7), allargato da Nadia (03e4753b74ad65aa, 915e57208f6045f4). Modulo di Giano (`verimem/vicinato_del_valore.py`): la cura sta sul ramo `ws3/t17-prova` (fb47bce3) e NON è consegnata senza il suo VIA.*

## 1. Il sintomo, usando il prodotto

`L4.2` è l'avviso «il claim riusa un numero della fonte riferendolo a un'altra grandezza» («14 valvole» contro una fonte che dice «14 operai»). Iris e Nadia lo hanno visto scattare sotto verdetti `admitted` a 99,9 su fatti veri, sempre con la stessa forma di fonte: l'output di un programma — `EXIT=2`, `STRUMENTI ESPOSTI A RUNTIME: 249`, `2026-09-06 03:27`. Cioè esattamente la forma di evidenza che la regola O3 chiede di passare. Un avviso che scatta sempre smette di essere letto.

## 2. La misura prima di tutto (banco `ws3-T17-quanti-avvisi-L42-toglie-ciascuna-regola.py`)

Sui 7.974 fatti vivi con `grounding_span` (la fonte intera non è conservata, M6: lo span è la stessa approssimazione del banco di casa `quali-parole-la-ricevuta-mostra-come-grandezza.py`), il righello riproduce il prodotto a **0 disaccordi** e dice:

| | avvisi L4.2 | quota dei fatti |
|---|---|---|
| prodotto prima della cura | 4.052 / 7.974 | **50,8 %** |
| cura provata (ramo di prova) | 1.273 / 7.981 | **16,0 %** |

Predizioni depositate prima (commit 4fe86ae5): P-T1 «≥ 40 %» **regge**; P-T2 «i composti da soli tolgono ≥ 25 %» **falsificata** (19,8 %); P-T3 «le quattro regole insieme ≥ 60 % con presidi intatti» **falsificata**: toglievano l'85 % ma la regola «tutta la riga» spegneva un riuso vero.

## 3. Le cinque giunture, lette nel codice (non dedotte dall'avviso)

Iris aveva dedotto «nel claim cerca l'unità DOPO il numero, nella fonte PRIMA». Non è nel codice: `_intorno` guarda entrambi i lati in entrambi i testi. Le giunture vere sono cinque:

1. **lati omologhi**: il criterio confronta solo dopo∩dopo e prima∩prima; «249 strumenti» (unità a destra) e «STRUMENTI ESPOSTI A RUNTIME: 249» (a sinistra) non si incontrano mai;
2. **un token per lato, oltre il fine riga**: `dopo[0]` e `prima[-1]`; «…: 249 ⏎ primi 3» dà prima=`runtime`, dopo=`primi`;
3. **il composto spezzato**: il lookbehind escludeva cifre, punto e virgola ma non «:», «-», «/» → «03:27» diventa 27, e la fonte «2026-09-06 03:27 test» dà dopo=`test`, prima=`bf` (la coda dell'hash);
4. **il punto finale**: «esce 2.» non viene trovato nel claim (il lookahead esclude il punto), il claim risulta senza parole accanto e il criterio scatta a vuoto;
5. **il token grammaticale preso come grandezza**: 9 residui su 14 letti avevano nel claim «(solo parole grammaticali accanto)» — in prosa il numero è preceduto da «sono / risulta / a» e seguito dal punto, e la grandezza sta due-tre parole prima («i gruppi con lo stesso testo sono 40»). Il commento di `_GRAMMATICA` dichiarava «voluto» che il criterio non la vedesse: era vero, ed era il difetto.

## 4. Le regole, una per volta (tolti / presidi / i 5 falsi del ticket)

| regola | tolti | presidi 3 scattano · 2 tacciono | falsi taciuti |
|---|---|---|---|
| A incrocio dei lati | 1,6 % | 3/3 · 2/2 | 0/5 |
| B tutta la riga | 30,4 % | **2/3** · 2/2 | 1/5 |
| C composto intero | 19,8 % | 3/3 · 2/2 | 1/5 |
| D punto finale | 12,9 % | 3/3 · 2/2 | 0/5 |
| E etichetta «:»/«=» | 1,2 % | 3/3 · 2/2 | 1/5 |
| A+C+D+E+P (prefisso 4) | 36,1 % | 3/3 · 2/2 | 3/5 |
| … + F1 (1 parola di contenuto per lato) | 57,2 % | 3/3 · 2/2 | 3/5 |
| … + F3 senza X | 79,4 % | **2/3** · 2/2 | 3/5 |
| … + F3 + X (etichette di altri numeri escluse) | 75,6 % | 3/3 · 2/2 | 3/5 |

Il presidio che B e F≥2 spengono è «Line 3 processed 22 orders» contro «Line 3 ran for 22 days»: «line» entra da entrambe le parti, ma è l'etichetta del 3, non del 22. Da qui X: una parola adiacente a un **altro** numero non entra nel vicinato di questo.

## 5. Cosa ha insegnato curare (il righello era ottimista di 284)

Il banco prometteva 989 avvisi residui; il prodotto curato ne dà 1.273. Letti i disaccordi caso per caso:

- **C sui decimali è pericolosa**: «97.05» identico nella fonte ma con soggetto diverso (colli / magazzino, fatto 867621d4c810) è un riuso VERO che la prima C taceva. Ora C vale solo per orari, date, rapporti e versioni a tre parti; i decimali restano numeri.
- **l'esclusione va per posizione, non per parola**: «casi» accanto a «6 casi» veniva tolta anche accanto a «96 casi»; «exit» delle righe precedenti toglieva l'`exit` del nostro `EXIT=0`; la parte decimale di «15.7» era trattata come un altro numero e «medio» spariva. La parola immediatamente adiacente al nostro numero è sua.
- **«9.0» è «9»**: un intero con la coda decimale nulla si trova.

## 6. La cura, sul ramo di prova (fb47bce3), e i suoi presidi

`_intorno`: composti esclusi dal matching (`(?<![\d.,:/-])`), punto finale ammesso, coda decimale nulla, fino a 3 parole di contenuto per lato entro 60 caratteri senza passare fine riga o «|», etichette di altri numeri escluse per posizione, forma ETICHETTA: valore → etichetta intera. `valori_riusati_da_altro_contesto`: il composto del claim presente nella fonte tace; i confronti omologhi vanno per prefisso di 4 lettere; poi l'**incrocio** dei lati.

Nove file di presidio verdi, uno per volta con exit letto: `test_il_numero_c_e_ma_parla_d_altro` 20 · `test_la_ricevuta_di_L42…` 4 · `test_l41…` 3+1xf · `test_la_quantita_vaga…` 16+11xf · `test_i_segnali_di_outcome…` 38 · `test_explain…` 4 · `test_il_precontrollo…` 3 · `test_l43…` 2 · la cella nuova `test_l42_avvisa_falsamente_sugli_output_di_programma` 8 passed + 2 xfail dichiarati.

## 7. Limiti dichiarati

- I due «esce 2» contro «EXIT=2» restano: *esce* ≠ *exit* è **traduzione**, non lessico; una lista bilingue di verbi è la classe ③ di questa casa e non entra. Sono xfail strict nella cella.
- I presidi del modulo sono **tre** riusi veri: un vicinato a 3 parole può spegnere riusi veri che tre presidi non vedono. La cura entra con una cella per ogni classe che Giano conosce, non con le mie.
- Il 16 % residuo è letto solo su 14 casi: tabelle (la grandezza sta nell'intestazione), sinonimi («server» / «mcpServers»), grandezza a più di tre parole. Non lessicale: si dichiara, non si cura qui.
- La popolazione è lo span, non la fonte intera (M6).

## 8. Letteratura, per il muro M5

Il caso è un'istanza del muro M5 («il verificatore decide con le parole»): qui il verificatore è un criterio posizionale, e la giuntura è fra la prosa (grandezza prima del numero, grammatica accanto) e l'output di macchina (etichetta: valore). Il righello lessicale sul corpus (banco `ws3-quanti-quarantinati-cadono-per-un-termine-fuori-fonte.py`, 111518d8) misura la stessa cosa sul giudice: AUROC 0,743 della sola quota di parole fuori fonte come separatore fermati/ammessi.
