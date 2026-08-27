# 00 — L'ESAME DEL PRODOTTO

> **Registro unico delle celle misurate.** Istituito dalla direttiva di Aurelio del
> 27/08 (trasmessa da `lead-audit`, messaggio A2A `d2d5c2944c8f457e`), nelle sue parole:
> *«cosa dovrebbe avere teoricamente un progetto del genere? Le ha? Rispetta quello che
> promette? **Lo fa davvero?**»*
>
> Questo file **non giudica il codice: registra le misure**. È il posto dove un referto
> smette di essere un messaggio sul canale e diventa una riga che qualcun altro può
> attaccare.

## I quattro livelli di ogni domanda

| livello | domanda | chi lo può dire |
|---|---|---|
| ① | dovrebbe averlo? | discussione |
| ② | ce l'ha? | `git grep` |
| ③ | lo **promette**? | README / CLI / docstring |
| ④ | **lo fa davvero**, misurato **alla porta** *e nel regime che un utente userebbe*? | solo un'esecuzione |

> 🔴 **«Alla porta» da solo non basta — obiezione di ws3, accolta il 27/08, e nasce da un
> errore pagato la sera stessa.** Il «muro» dei 24 secondi è stato misurato **alla porta**,
> correttamente, e il verdetto era **falso lo stesso**: la porta era giusta, il **regime** era
> l'anti-pattern che il repo dichiara tale (riga 8 contro riga 10, **1,5 → 14,3 ops/s**).
> ⇒ **Una misura alla porta nel regime sbagliato non è una misura debole: è un verdetto
> invertito.** Chi compila una cella dichiara il regime **accanto** alla porta, e se il regime
> non è quello di un utente lo scrive nel verdetto, non nelle note.


> 🔴 **Una promessa senza il livello ④ verde è marketing.** Questa è la riga che
> l'esame esiste per far rispettare, e vale anche per le righe scritte qui dentro.

## Come si scrive una riga — le regole pagate, non inventate

1. **Il regime sta nell'intestazione, non nella memoria di chi ha misurato.** Macchina,
   variabili d'ambiente, versione, `n`. *(Un verde senza regime vale come un numero senza
   unità: misurato il 20/08, due istanze hanno contato «caduto» un bersaglio che nel
   regime giusto era verde **prima** della cura.)*
2. **Niente numeri nei titoli.** Un titolo con una cifra invecchia e nessuno lo rilegge;
   la cifra sta nella cella, dove ha accanto il suo denominatore.
3. **Il denominatore accanto alla cifra, sempre.** *(Dei sei difetti di vetrina trovati
   in due giorni, **cinque erano la stessa cosa**: un numero corretto sotto un'etichetta
   che non definisce la popolazione.)*
4. **Dichiara il livello a cui hai misurato.** Regex interna < funzione pubblica < porta
   che il prodotto usa — e ogni salto può ribaltare il verdetto, **in entrambe le
   direzioni**.
5. **Un controllo che DEVE fallire**, o «4 su 4» non distingue un presidio che funziona
   da uno spento.
6. **Un metadato non è il contenuto.** Un orario, un nome, una versione sono indizi; la prova
   è il **diff dell'artefatto**. *(Il 27/08 «il tag è posteriore all'upload di 1h27» — fatto vero —
   ha quasi invalidato tutte le misure sul tag; il confronto file per file ha dato 397 su 397
   identici.)*
7. **Se le colonne non sommano al totale, il difetto è nel misuratore.** *(ws1 se n'è accorta
   dall'aritmetica, non dal codice: «366 identici + 9 diversi + 22 assenti» su 397 file — gli
   identici superavano gli esistenti perché il confronto andava per nome base.)*
8. **Chi riporta la misura di un altro lo scrive.** La colonna `misurata da` non è un
   credito: è il modo di sapere a chi chiedere quando la riga verrà attaccata.

## Le celle misurate

Legenda verdetto: 🟢 fa quello che promette · 🔴 non lo fa · 🟡 lo fa in parte / con limite
· ⚪ non misurato.

| # | domanda | classe | lingua | porta | verdetto | misurata da | regime / limite |
|---|---|---|---|---|---|---|---|
| 1 | i comandi che il README pubblicato promette esistono nel pacchetto? | — | EN | CLI | 🟢 **14 su 14** | ws7 | `git show v0.7.0:`. ✅ **Il limite che avevo dichiarato è CADUTO**: ws1 ha confrontato **l'artefatto installato da PyPI** contro il tag, file per file — **397 identici · 0 diversi · 0 assenti** (perimetro: i `.py` sotto `verimem/`) ⇒ **il tag *è* ciò che sta su PyPI**, e la misura vale per il pubblicato. ⚠️ Il timestamp anomalo di ws6 (tag posteriore di 1h27) **resta un fatto vero**: cade l'inferenza «orario diverso ⇒ contenuto diverso» |
| 2 | il server MCP parte, per chi installa da PyPI? | — | — | MCP | 🔴 **no** | ws1 | venv pulito, `pip install verimem==0.7.0` → `mcp 2.1.1` → `verimem mcp` **exit 1**, `AttributeError`. **Controllo positivo**: forzando `mcp<2` nello stesso venv → **exit 0** |
| 3 | il gate vede un numero inventato dentro una fonte lunga? | C4 | — | — | 🔴 **no, se il numero è comune** | ws5 | A/B a fonte fissa: `3`,`7`,`9` collidono a **200 parole**; `47`,`617`,`4291` mai in 7000. **Non è la lunghezza: è la rarità** |
| 4 | il gate ferma un numero **inventato** scritto all'italiana? | C4 | IT | SDK | 🟢 **sì** | ws8 | A/B end-to-end, source fissa, cambia solo il separatore: vero-punto e vero-virgola **admitted**, inventato-punto e inventato-virgola **quarantined**. ⚠️ **Riga ribaltata**: alle 20:48 era 🔴 sulla *regex interna* (3 famiglie su 3 spente dalla virgola — vero e ancora vero); alla **porta** il verdetto si inverte perché `L1` non veta e il grounding ferma comunque. **La difesa non è a punto singolo** |
| 5 | l'unità di misura entra nel confronto? | C4 | IT | — | 🔴 **no** | ws5 | una «penale del **7%**» nella fonte valida «**7 giorni**» nel claim; il campo `.unita` esiste e viene ignorato. Bastano due frasi |
| 6 | il punteggio di grounding cresce con il contesto? | — | — | — | 🔴 **non è monotono** | ws4 | stesso claim falso, stesso documento: **0.3** a 1000 char e **99.3** a 6000, **deterministico su due esecuzioni** |
| 7 | le due porte restituiscono gli avvisi con lo stesso nome? | — | — | SDK vs MCP | 🔴 **no** | ws2 | SDK → `warnings` · MCP → `anti_confab_warnings`. Chi cambia porta legge una lista vuota e conclude che il gate taceva |
| 8 | quanto costa davvero una scrittura? | — | — | processo singolo | 🟡 **il costo è di NASCERE, non di scrivere** | ws3, ws6, ws2 | primo write ~26 s / 1,9 GB · dal terzo **0,4–0,5 s** (**23,7×**). Regime: N processi effimeri, ognuno carica i propri modelli — **il repo lo chiama anti-pattern dal 21/07** |
| 9 | il banco del regime che un utente userebbe è mai stato eseguito? | — | — | gateway | 🟢 **eseguito il 27/08** (era 🔴 «mai, dal 21/07») | ws7 (trovato), ws3 (eseguito) | `benchmark/concurrency_shared_server.py` aveva **1 commit · 0 artefatti · 0 citazioni** dal 21/07. Commit dell'esecuzione: `f8836233` |
| 10 | il sistema regge il carico nel regime di un servizio? | — | — | gateway | 🟢 **sì** | ws3 | `--workers 2 --secs 60`, uvicorn in un processo suo, store `mkdtemp`: **654 letture · 217 scritture · 0 errori** · `write_p50` **258,3 ms** · `write_p99` 575,8 · **14,3 ops/s** · **ops > 5 s: 0**. 🔑 La predizione scritta nel docstring il 21/07 (*«writes stay in the hundreds-of-ms range»*) era **esatta** |
| 11 | sulla versione **installata da PyPI** il moat giudica la fonte? | — | EN | SDK | 🔴 **no** | ws1 | stessa macchina, stesso minuto, stessa frase e fonte: **0.7.0** → `grounding_score=None`, `source_signature=None` **anche con `--source`**; **HEAD** → **98.39** + firma sha256. **Controllo**: con `ENGRAM_GROUNDING_WRITE=1` il giudice **si carica** e il punteggio resta `None` ⇒ non è un opt-in |
| 12 | il gate rifiuta un claim che la fonte **nega**? | C7 | IT+EN | SDK | 🔴 **no: 46 su 108 (42,6%)** | ws6 | **sei schemi × 18**: «non» esplicito **0/18** ✅ · quantificatore zero 8 · assenza 9 · **stato («il registro è vuoto») 12/18** 🔴 · sostituzione 8 · cessazione 9. **IT 30/54 · EN 16/54**. 🔑 **Il gate riconosce la parola «non», non la negazione**: «*il registro ALFA è vuoto*» è giudicato una **prova** di «*il registro ALFA elenca le misure*», 12 volte su 18, con punteggi 96–99,99. Commit `f51f9845`. ⚠️ Era 5/24 con **un solo** schema: il numero è raddoppiato allargando il banco |
| 13 | su una licenza reale il gate ferma un claim che **ricalca** la fonte cambiando un numero di clausola? | C4 | EN | — | 🔴 **no, 2 su 3** | ws5 | «section 7» al posto di «section 10» entra a **99.1 senza alcun layer**. Il rischio è la **congiunzione** (ricalco + numero comune), non `L4.1` da solo |
| 14 | il presidio metrico riconosce la copula italiana in tutte le sue scritture? | C4 | IT | SDK | 🟢 **sì, dopo cura** (era 🔴) | ws2 | 5 forme dello stesso claim senza attestazione: `è`, `e` nudo, senza copula e l'inglese cadevano; **`e'` con l'apostrofo passava**. Sul corpus prima della cura: **48** claim metrici scritti con `e'` e **0** quarantinati, contro **8 su 31** (25,8%) di quelli con `è`, su una quota complessiva dell'8,5%. Curato in `f5dedf34`, TDD senza stash: RED `5 failed EXIT=1` → GREEN `11 passed EXIT=0`, non-regressione `tests/test_l1_quantitative_detector.py` `19 passed`. ⚠️ Limite: misurato sulla porta SDK, **non** su MCP/CLI/gateway |
| 15 | il pattern delle percentuali riconosce i sostantivi italiani? | C4 | IT | SDK | 🟢 **sì, dopo cura** (era 🔴) | ws2 | i sei sostantivi erano **tutti inglesi** (`coverage|uptime|availability|accuracy|precision|recall`) mentre la copula accanto era italiana ⇒ quella `è` era **codice irraggiungibile**: il pattern accettava «coverage è 42.6%», che nessuno scrive, e rifiutava «la copertura è 42.6%». Delle 5 scritture dello stesso claim passava **solo l'inglese**. Trovato dal test, non cercato. Stesso commit `f5dedf34` |
| 16 | posizione e lunghezza della fonte spostano il verdetto del giudice? | C4 | IT | SDK | 🟢 **no — decide il rumore numerico** | ws2 | matrice 2×2, stesso claim vero: coda+numeri **0,13** · coda+**senza** numeri (fonte **più lunga**, 4075 char) **99,98** · testa+numeri 99,98 · testa+senza 99,98. ⇒ posizione ininfluente, lunghezza ininfluente, **collide il numero**. Rinforzo indipendente della riga 3 (ws5), arrivato cercando altro |
| 17 | il prodotto mantiene, **all'agente dell'utente**, la quarantena che gli promette? | — | EN | SDK | 🟢 **sì, e meglio di quanto prometta** | ws8 | «*It works, verified, all tests pass, done*» su SDK → **`quarantined`, 4 layer** (`L1.10/13/15/20`), dove la guida ne promette uno. ⚠️ **Riga corretta dall'autrice**: alle 20:58 diceva «promette una quarantena che non avviene» — **falso**, era misurata sulla porta CLI e sullo store di Aurelio, due variabili confuse. **Ciò che regge è la riga 23** |
| 18 | su un testo normativo reale il gate ferma un valore inventato? | C4 | EN | — | 🟢 **sì, 3 su 3** | ws5 | GDPR art. 33: protegge i valori **affermati** («72 ore») e non i **riferimenti** («articolo 10»). ⚠️ **Terza restrizione consecutiva dello stesso allarme** dell'autrice — il difetto è reale e più stretto di come è nato |
| 19 | l'affidabilità è la stessa per ogni **classe di falsità** e lingua? | C7, C5 | IT+EN+8 | — | 🔴 **no, varia di 10×** | ws3 | negazione **IT 0/10 · EN 0/10 · TH 6/10** · entità scambiata IT 1/10 · EN 2/10 · **TH 10/10** · implicita IT 3/10 · EN 0/10 · **AR 4/5** · dettaglio IT 8/10 · EN 9/10 · passiva IT **2/10 veri rifiutati**. 🔑 Omissione, vaghezza e numerali-a-parole sono **una classe sola**: in nessuno il claim porta una cifra |
| 20 | quanto ci mette un utente **nuovo** alla prima scrittura+lettura? | — | EN | SDK | 🟡 **8 s, ma con ZERO byte scaricati** | ws1 | 0.7.0 installata, `HF_HOME` e `HF_HUB_CACHE` su cartella **vuota**, store nuovo: `remember` 6 s + `recall` 2 s, fatto ritrovato. 🔑 **Zero byte scaricati spiega la riga 11**: il giudice non c'è e non viene preso ⇒ il moat non può giudicare |
| 21 | l'attestazione è onorata **su tutte le porte**? | C4 | IT | SDK vs MCP | 🔴 **no: sì su SDK, no su MCP** | ws2 | **il gate è scagionato con A/B**: la divergenza nasce **attorno** al gate, non dentro. Perimetro ristretto per eliminazione, **quattro ipotesi dell'autrice cadute**. Causa ancora **aperta** |
| 22 | è la **lunghezza** della fonte a spostare il verdetto? | C4 | EN | — | 🔴 **no: è la RIPETIZIONE** | ws5 | confondente eliminato: a **pari lunghezza** il testo neutro **peggiora** (73.3). Otto banchi, **cinque predizioni dell'autrice sbagliate**, sei debiti dichiarati e pagati |
| 23 | lo **screen lessicale** gira su **ogni** porta, come il prodotto promette? | — | EN | CLI vs SDK | 🔴🔴 **no: non gira sulla CLI** | ws8 | stessa stringa, **stesso store temporaneo pulito**, due porte: **SDK** → `quarantined`, 4 layer · **CLI** → `model_claim`, `layers=[]`, **entra**. ⇒ `agent_guide.py:31` dice «**ALWAYS**: a lexical screen on **every write**»: falso sulla CLI. 🔴 **Ci riguarda tutte: `verimem save` È la CLI**, ed è la scrittura che la regola O3 prescrive come canonica |
| 24 | da dove vengono i venti secondi di alcune scritture? | — | — | — | 🟢 **spiegati: escalation della banda** | ws4 | A/B **a tre stati** con `ENGRAM_BAND_LLM`: **52.030 ms accesa · 235 spenta · 22.270 riaccesa**. A parità di fonte, il punteggio **centrale** costa 43.630 ms e quello **estremo** 208 |
| 25 | la soglia calibrata su un campione piccolo regge sul corpus reale? | — | — | — | 🟢 **sì** | ws4 | la promessa del codice, calibrata su **n=14**, regge su **8.116 fatti** (533 su 551 in banda). E la banda è il **6,8%** dei giudicati, **non il caso normale** ⇒ due misure su tre **a favore del prodotto** |

### Verdetti che sono cambiati

> Una riga che cambia colore **non è un errore del registro: è il registro che funziona**.
> Si annota qui invece di sparire, perché chi legge solo lo stato finale non impara niente.

| # | era | è | chi l'ha ribaltata | cosa l'ha ribaltata |
|---|---|---|---|---|
| 4 | 🔴 20:48 | 🟢 20:50 | ws8, su se stessa, in **tre minuti** | il salto da **regex interna** a **porta** — e nella direzione buona |
| 9 | 🔴 «mai eseguito dal 21/07» | 🟢 eseguito | ws3 | l'ha eseguito |
| 17 | 🔴 20:58 | 🟢 21:09 | ws8, su se stessa | aveva misurato sulla porta **CLI** e sullo store di Aurelio: **due variabili confuse**. Separandole, su SDK la promessa è **mantenuta** — e il difetto vero si sposta sulla riga 23 |
| 12 | 🔴 5/24 | 🔴 **46/108** | ws6 | stesso verdetto, **numero raddoppiato**: il primo banco provava **un solo** schema di negazione su sei |

### Celle dichiarate scoperte

- 🟡 **porta SDK**: tre celle di conformità (14, 15, 16) più il costo — tutte in **C4 e in
  IT**. Le stesse domande sulle altre porte restano scoperte, e la riga 7 dice perché non
  si possono dare per equivalenti.
- ⚪ **le celle 14–16 su MCP, CLI e gateway**: curate e verificate **solo su SDK**. Una cura
  che vale su una porta non vale sulle altre finché non è misurata lì — è la riga 7.
- ⚪ **gateway HTTP**: nessuna cella.
- ⚪ **classi C1, C2, C3, C6, C8**: misurate **C4** (quantità e formati) e una cella
  di **C7** (negazioni, righe 12 e 19) e una di **C5** (identità, riga 19). **Cinque classi su otto restano scoperte**, ed è il buco
  più grande di questo registro.
- ⚪ **il vertice della piramide** — «un agente con verimem sbaglia meno di uno senza» —
  **non ha ancora una riga qui**, ed è il numero che tutto il resto dovrebbe sostenere.

---

📌 **Chi aggiunge una riga**: aggiorna anche la lista delle celle scoperte. Un registro
che cresce solo dal lato verde racconta una bugia per omissione.

📌 **Provenienza**: le righe 1 e 9 sono misurate da chi scrive (ws7). Le righe 2–8 sono
**riportate dai referti A2A della sera del 27/08** — chi scrive non ha eseguito quei
banchi, e ogni riga nomina l'autore proprio perché la si possa contestare a lui.
Le righe 14–16 sono aggiunte da chi le ha eseguite (ws2).

---

## Enunciati RITIRATI — perché nessuno li rimetta

> Un registro che raccoglie solo ciò che è sopravvissuto costringe il prossimo a riscoprire
> gli errori già pagati. Questi sono stati **pubblicati sul canale e poi ritirati dagli
> autori stessi**: se qualcuno li ritrova, il difetto è nel banco, non nel prodotto.

| enunciato ritirato | perché era falso | chi |
|---|---|---|
| «la porta MCP non restituisce gli avvisi al chiamante» | il banco leggeva la chiave `warnings`, che su MCP **non esiste**: si chiama `anti_confab_warnings`. Resta vero solo che i **nomi differiscono** — è la riga 7, molto più piccola | ws2 |
| «un presidio del gate parla solo inglese» | l'A/B era confuso: il claim italiano era scritto `e'` e non `è`. Con l'accento il presidio **scatta**, e la vera causa era l'apostrofo — riga 10 | ws2 |
| «la posizione del dato nella fonte decide il verdetto» | il rumore della fonte lunga conteneva **60 numeri** che collidevano col claim. Con rumore senza cifre, una fonte **più lunga** e col dato in coda prende 99,98 — riga 16 | ws2 |

📌 **La classe comune ai tre**: il comportamento osservato era reale ogni volta; era la
**causa** che ci veniva attaccata sopra a essere più larga del dato. Il presidio che li ha
fermati non è stato misurare di più — è stato **andare a leggere il codice** e **chiedersi
quale altra variabile potesse spiegare lo stesso numero**.

📌 **Una divergenza aperta, dichiarata invece che chiusa**: sul costo *warm* di una
scrittura, due banchi indipendenti danno **0,180 s** (ws2, dal 2º write) e **0,4–0,5 s**
(ws6, dal 3º). Sono state escluse due spiegazioni — il modo di calcolare la mediana (i due
righelli differiscono dello **0,6%**) e la lunghezza della fonte (−11%, e la fonte lunga è
la *più veloce*). **La causa non è nota.** La riga 8 riporta l'ordine di grandezza; questa
nota esiste perché non venga letto come un numero concordato.
