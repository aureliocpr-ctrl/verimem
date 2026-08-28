# 00 — L'ESAME DEL PRODOTTO

> **Registro unico delle celle misurate.** Istituito dalla direttiva di Aurelio del
> 27/08 (trasmessa da `lead-audit`, messaggio A2A `d2d5c2944c8f457e`), nelle sue parole:
> *«cosa dovrebbe avere teoricamente un progetto del genere? Le ha? Rispetta quello che
> promette? **Lo fa davvero?**»*
>
> Questo file **non giudica il codice: registra le misure**. È il posto dove un referto
> smette di essere un messaggio sul canale e diventa una riga che qualcun altro può
> attaccare.

## Se hai trenta secondi

> Solo fatti contati e puntatori. **Nessun aggettivo**: il registro è il posto dove una frase
> più larga del dato fa più danno che altrove.

    celle misurate  53      🔴 30   🟢 17   🟡 5

**Cosa il prodotto fa, misurato**: ferma la contraddizione in tutti i regimi provati (0/12,
riga 29) · pretende che il soggetto del claim stia nella fonte (riga 31) · regge il carico di
un servizio (258 ms, 14,3 op/s, zero errori — riga 10) · gestisce correttamente un valore che
evolve (riga W7-4) · dà a un agente una ricevuta azionabile (riga 38).

**Cosa non fa, misurato**: nessun presidio ferma un claim che **aggiunge** un dettaglio che la
fonte non contiene (12/12, riga 30) · un vero può essere scartato (≥12 su 58, riga W7-3) · uno
scambio di attribuzione entra 3 volte su 7 e **cancella il fatto vero** se sta nello stesso
topic (W7-7) · il consiglio dato a un agente rifiutato non è eseguibile (W7-1).

**Cosa non siamo in grado di dire**: se il gate abbia avuto ragione nei casi contestati — **la
prova che conserva è troncata a 400 caratteri** (W7-5), e la cura costa zero.

**Cosa manca del tutto**: il vertice — *un agente con verimem sbaglia meno di uno senza* —
**non ha una riga**. Finché non ce l'ha, questo registro dice come si comporta il prodotto,
non se serve.

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

1. **Il REGIME è obbligatorio e va scritto per PRIMO** nell'ultima colonna — *ratificato da
   `lead-audit` il 27/08 come quinto livello dell'esame, su obiezione di ws3.* Non è un dettaglio
   della cella: è ciò che decide se il verdetto vale.
2. **Il regime sta nell'intestazione, non nella memoria di chi ha misurato.** Macchina,
   variabili d'ambiente, versione, `n`. *(Un verde senza regime vale come un numero senza
   unità: misurato il 20/08, due istanze hanno contato «caduto» un bersaglio che nel
   regime giusto era verde **prima** della cura.)*
3. **Niente numeri nei titoli.** Un titolo con una cifra invecchia e nessuno lo rilegge;
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

## Triage delle rosse — F2, richiesto da `lead-audit` il 28/08

> **Conta contata**: `python scripts/conta_celle_esame.py` → **38 rosse** su 69 celle.
> ⚠️ *Il numero «36 rosse» dell'ordine del giorno veniva dal conto vecchio, che sbagliava di
> tre celle: il righello contava rossa ogni cella che **contiene** 🔴, incluse le tre che
> dicono «🟢 sì, dopo cura (era 🔴)».*
>
> **Etichetta = che TIPO di intervento serve, non quanto è grave.** Una `decisione-CEO` può
> essere il difetto peggiore del registro; una `cura-quick` può restare aperta per mesi.
> **L'owner è PROPOSTO da chi tiene il registro, non assegnato**: lo conferma chi lo prende.

### 🔵 decisione-CEO — non si curano, si scelgono (3)

| cella | la scelta, in una riga | owner |
|---|---|---|
| **2** | la 0.7.0 su PyPI non avvia il server MCP: **yank · avviso sulla pagina · release accelerata**. È la VOCE 0 | **Aurelio** |
| **27** | il gate lancia `claude -p` **senza `--model`**: fissare il modello del giudice (e scriverlo nella ricevuta) cambia i punteggi già emessi | **Aurelio** |
| **W7-10** | `backup-all` copre 3 tier su 9: **rinominare** il comando (rompe chi lo invoca) **o estenderlo** (cambia cosa produce) | **Aurelio**, proposta da ws5 |

### 🟢 cura-quick — la cura è nota e il costo è dichiarato (8)

| cella | cura | costo dichiarato da chi ha misurato | owner proposto |
|---|---|---|---|
| **W7-1** | l'advice di `L1.9` suggerisce una forma che non passa mai | «**una riga di testo**» | ws8 |
| **W7-5** | span della prova troncato a 400 | «**una riga**, variabile già esistente; **verdetto identico** con 400 contro 932» | ws1 |
| **W7-6** | `correct` chiede un id che `recall` non stampa | «**la cura è una riga**» | ws5 |
| **7** | SDK dice `warnings`, MCP dice `anti_confab_warnings` | allineare **un nome** (o esporre entrambi) | ws2 |
| **26** | il parser del punteggio rifiuta `**55**` e la prosa | allargare **un pattern** | ws4 |
| **50** | la ricevuta di `add()` non ha la chiave `layers` | aggiungere **una chiave** già calcolata a monte | ws3 |
| **W7-15** | `confidence` anti-correlata · `last_seen` = «letto» | rinominare **o** documentare nel punto d'uso | ws5 |
| **W7-16** | `file:` non è nella lista dei prefissi accettati | aggiungerlo **alla lista** | ws8 |

### 🟠 strutturale · lo strato soggetto-valore (12) — **è F1, la cura che ne chiude tre**

`30` omissione senza presidio · `49` chi decide sullo scambio · `W7-13` `L4.1` tace 0/12 ·
`W7-7` attribuzione 3/7 · `W7-8` conta il **contorno** · `W7-9` (ws4) l'**unità** ·
`W7-14` il contorno ribalta in **entrambe** le direzioni · `3` numeri comuni ·
`5` l'unità non entra nel confronto · `13` il ricalco con clausola cambiata ·
`22` è la **ripetizione**, non la lunghezza · `W7-2` cifra assente 9/10.

> 🔑 **Dodici rosse su trentotto sono lo stesso buco visto da dodici lati.** È il motivo per cui
> `lead-audit` mette F1 davanti a tutto, ed è il miglior rapporto costo/beneficio del registro.
> **Owner: ws3 + ws5 in coppia** (design falsificabile prima, poi review, poi implementazione).

### 🟠 strutturale · architettura del gate (6)

| cella | il nodo | owner proposto |
|---|---|---|
| **37** | **nove chiamanti** validano le scritture, nessuna superficie unica | ws2 |
| **28** | i nove passano **quattro argomenti in comune su diciannove** | ws2 |
| **23** | `verimem save` passa `meta_narrative=True` e **spegne `L1`** | ws8 |
| **21** · **35** | l'attestazione è onorata su SDK e non su MCP (causa: `repo_root`) | ws2 |
| **W7-11** | una quantificazione universale non passa | ws8 |

### 🟠 strutturale · gli altri (9)

`6` grounding non monotono · `12` la negazione non esplicita 46/108 ·
`19` l'affidabilità varia 10× per classe e lingua · `36` la rete sugli errori ad alto punteggio ·
`45` · `W7-17` **N record distinti nello stesso topic** · `47` lo stesso fatto cambia verdetto ·
`W7-3` `L4.1` ferma anche il vero · `W7-12` il gate insegna a chi lo usa.

> ⚠️ **`45` e `W7-17` sono la stessa domanda scritta due volte** («N record distinti nello stesso
> topic coesistono?» / «tre record distinti…»), da due mani in due momenti. **Non le fondo io**:
> i regimi vanno confrontati da chi li ha misurati — @ws2, sono entrambe tue.

### Cosa dice il triage, letto tutto insieme

- **3 rosse su 38 non sono difetti**: sono scelte che aspettano una decisione, e **due
  aspettano Aurelio da ieri**.
- **8 hanno una cura che chi l'ha misurata ha già scritto** — costo dichiarato, nessuna
  richiede progettazione. **Sono il lavoro più a portata di mano del registro.**
- **27 sono strutturali, e 12 di quelle sono la stessa falla.** ⇒ Chiudere F1 non toglie 12
  righe dal registro: **toglie un buco solo, che si presenta con dodici facce**.

## Il ponte con `RELEASE_GATE.md` — quali celle toccano quali cancelli

> `RELEASE_GATE.md` è il gate del **tag**; questo file è la **mappa**, di cui il gate è il
> sottoinsieme bloccante. Finora i due non si parlavano: i dieci cancelli sono stati scritti
> prima delle celle e **non sanno nulla di ciò che è stato misurato il 27/08**.
>
> ⚠️ **Questa tabella NON decide che cosa blocchi il rilascio.** Dice soltanto quale cella
> porta informazione a quale cancello. **La colonna «blocca?» è vuota apposta: la riempie
> Aurelio.** È la differenza fra dargli un criterio di uscita e dargli una lista che si allunga.

| cancello | celle che lo toccano | cosa dicono | blocca? |
|---|---|---|---|
| **G2** install-from-scratch (include «MCP server start») | 2 · 1 · 11 · 20 | il server MCP **non parte** per chi installa da PyPI (controllo positivo: con `mcp<2` parte) · la CLI mantiene **14 promesse su 14** · il moat non giudica **finché non si esegue `verimem warmup`** | |
| **G8** fresh-environment model download | 20 · 11 | un utente nuovo completa scrittura+lettura in **8 s** ma con **zero byte scaricati**: quel regime **è** «senza warmup», e spiega G2 | |
| **G10** multilingual validation | 19 · 12 · 4 · W7-8 | l'affidabilità **varia di 10×** per classe e lingua (negazione IT 0/10 · EN 0/10 · TH 6/10) · la negazione non esplicita passa **46 su 108**, IT 30/54 contro EN 16/54 · tre record distinti si cancellano **in inglese e non in italiano** | |
| **G4** benchmark riproducibili da un comando | 9 · 10 | il banco del **regime reale** esisteva dal 21/07 e non era **mai stato eseguito**; eseguito il 27/08 dà **258 ms · 14,3 op/s · zero errori** | |
| **G6** README claim audit: zero claim non verificati | 1 · 31 · 32 | i comandi promessi dal README pubblicato ci sono **tutti** · il gate **pretende che il soggetto stia nella fonte**, e l'accusa contraria è stata ritirata dall'autrice | |
| **G1 · G3 · G5 · G7 · G9** | *(nessuna cella)* | non toccati da ciò che è stato misurato il 27/08 | |

📌 **Quello che questa tabella rende visibile e prima non lo era**: dei dieci cancelli, **cinque
hanno informazione nuova** dal 27/08 e **cinque no**.

🛑 **RITIRO UNA MIA INFERENZA (ws7, 22:22).** Avevo scritto qui che «*le celle che toccano G2 e
G8 descrivono la stessa condizione — chi installa e non esegue `verimem warmup`*». **Si
appoggiava sulla riga 20, che l'autrice del dato ha falsificato alle 22:18**: il giudice è
presente anche con zero byte scaricati. ⇒ **G2 e G8 restano collegati dalla cella 11, non dalla
20, e non sono lo stesso fatto.** 🔑 **Avevo costruito un'inferenza su una cella riportata da
altri, ed è caduta con lei**: è la ragione per cui in questo file il custode non deve dedurre —
solo collegare.

## Come si prende un numero di cella — **letto prima di aggiungere una riga**

🔴 **Il progressivo condiviso COLLIDE, e non è teoria: il 27/08 alle 21:30 due autrici hanno
pubblicato una riga `34` nello stesso minuto** e sono finite entrambe su `origin`. Ognuna ha poi
rinumerato la propria, quindi **il numero 34 resta vuoto: non è una riga persa** (verificato nella
storia del file — chi lo cerca non deve rifare il controllo che ho già fatto io).

✅ **Per una cella NUOVA usa `<la TUA sigla>-<n>`** — ws2 scrive `W2-1`, ws4 scrive `W4-1`,
ws6 scrive `W6-3`. **La sigla è la FIRMA di chi scrive la riga, non il nome della serie.**

🔴 **E questo schema ha già fallito una volta, per colpa di come l'avevo spiegato**: il 27/08
ws4 ha scritto una propria cella come `W7-8` — leggendo il file aveva visto `W7-1`, `W7-2`… e
l'aveva presa per la numerazione corrente invece che per la mia firma. Risultato: **due W7-8**.
⇒ **Ho ceduto il numero alla cella che qualcuno ha MISURATO** (quella di ws4) e rinominato la
mia, che era solo *riportata*: **chi riporta cede, chi misura tiene**. 🔑 *Se lo schema non è
auto-evidente, il difetto è dello schema — non di chi lo sbaglia.* I numeri interi già assegnati restano come sono: sono citati nei
messaggi del canale e rinumerarli romperebbe i riferimenti.

📌 **I numeri che compaiono due volte nella tabella «Verdetti che sono cambiati» non sono
duplicati**: sono *riferimenti* alla cella omonima.

## Le celle misurate

Legenda verdetto: 🟢 fa quello che promette · 🔴 non lo fa · 🟡 lo fa in parte / con limite
· **⛔ NON MISURABILE su quella porta** (il presidio non viene proprio chiamato lì: scriverci 🟢
sarebbe *assenza di misura letta come verde*).

> ⚠️ **`⚪` NON è un verdetto**: si usa solo nell'elenco delle **celle scoperte** più sotto, per
> ciò che *nessuno ha ancora misurato*. Una cella della tabella ha sempre uno fra 🔴 🟢 🟡 ⛔.
> *(Il 28/08 una cella aveva `⚪` nel verdetto e `scripts/conta_celle_esame.py` l'ha trovata:
> i due simboli erano troppo vicini, ed è un difetto della legenda — non di chi l'ha scritta.)*

| # | domanda | classe | lingua | porta | verdetto | misurata da | **regime** + limite |
|---|---|---|---|---|---|---|---|
| 1 | i comandi che il README pubblicato promette esistono nel pacchetto? | — | EN | CLI | 🟢 **14 su 14** | ws7 | `git show v0.7.0:`. ✅ **Il limite che avevo dichiarato è CADUTO**: ws1 ha confrontato **l'artefatto installato da PyPI** contro il tag, file per file — **397 identici · 0 diversi · 0 assenti** (perimetro: i `.py` sotto `verimem/`) ⇒ **il tag *è* ciò che sta su PyPI**, e la misura vale per il pubblicato. ⚠️ Il timestamp anomalo di ws6 (tag posteriore di 1h27) **resta un fatto vero**: cade l'inferenza «orario diverso ⇒ contenuto diverso» |
| 2 | il server MCP parte, per chi installa da PyPI? | — | — | MCP | 🔴 **no** | ws1 | venv pulito, `pip install verimem==0.7.0` → `mcp 2.1.1` → `verimem mcp` **exit 1**, `AttributeError`. **Controllo positivo**: forzando `mcp<2` nello stesso venv → **exit 0** |
| 3 | il gate vede un numero inventato dentro una fonte lunga? | C4 | — | — | 🔴 **no, se il numero è comune** | ws5 | A/B a fonte fissa: `3`,`7`,`9` collidono a **200 parole**; `47`,`617`,`4291` mai in 7000. **Non è la lunghezza: è la rarità** |
| 4 | il gate ferma un numero **inventato** scritto all'italiana? | C4 | IT | SDK | 🟢 **sì** | ws8 | **regime**: A/B end-to-end nella stessa esecuzione, porta SDK, store di Aurelio, source fissa, 4 claim. A/B end-to-end, source fissa, cambia solo il separatore: vero-punto e vero-virgola **admitted**, inventato-punto e inventato-virgola **quarantined**. ⚠️ **Riga ribaltata**: alle 20:48 era 🔴 sulla *regex interna* (3 famiglie su 3 spente dalla virgola — vero e ancora vero); alla **porta** il verdetto si inverte perché `L1` non veta e il grounding ferma comunque. **La difesa non è a punto singolo** |
| 5 | l'unità di misura entra nel confronto? | C4 | IT | — | 🔴 **no** | ws5 | una «penale del **7%**» nella fonte valida «**7 giorni**» nel claim; il campo `.unita` esiste e viene ignorato. Bastano due frasi |
| 6 | il punteggio di grounding cresce con il contesto? | — | IT | SDK | 🔴 **non è monotono** | ws4 | **CASO MINIMO**: claim `Il file wake.py conta 9999 LOC.` · fonte = primi N caratteri di `docs/archive/2026-05-13_FORGIA.md` (che dice «wake.py (1143 LOC)») · `mem.add(claim, source=fonte, validate="full")`. **N=1000 → 0.3 · N=2000 → 55.2 · N=3000 → 20.8 · N=4000 → 98.2 · N=6000 → 99.3 · N=10000 → 98.6 · N=14000 → 0.2**. ⚠️ **REGIME**: fuori da pytest (sotto pytest l'embedder è lo stub SHA-256 di `conftest.py:121`), codice `Code/HippoAgent` `6cbeb283`, `client.py` e `anti_confab_gate.py` puliti. **Deterministico**: due esecuzioni, stessi valori a tutte le cifre. Banco: `banchi/la-forma-della-curva-a-passo-fine.py` |
| 7 | le due porte restituiscono gli avvisi con lo stesso nome? | — | — | SDK vs MCP | 🔴 **no** | ws2 | SDK → `warnings` · MCP → `anti_confab_warnings`. Chi cambia porta legge una lista vuota e conclude che il gate taceva |
| 8 | quanto costa davvero una scrittura? | — | — | processo singolo | 🟡 **il costo è di NASCERE, non di scrivere** | ws3, ws6, ws2 | primo write ~26 s / 1,9 GB · dal terzo **0,4–0,5 s** (**23,7×**). Regime: N processi effimeri, ognuno carica i propri modelli — **il repo lo chiama anti-pattern dal 21/07** |
| 9 | il banco del regime che un utente userebbe è mai stato eseguito? | — | — | gateway | 🟢 **eseguito il 27/08** (era 🔴 «mai, dal 21/07») | ws7 (trovato), ws3 (eseguito) | `benchmark/concurrency_shared_server.py` aveva **1 commit · 0 artefatti · 0 citazioni** dal 21/07. Commit dell'esecuzione: `f8836233` |
| 10 | il sistema regge il carico nel regime di un servizio? | — | — | gateway | 🟢 **sì** | ws3 | `--workers 2 --secs 60`, uvicorn in un processo suo, store `mkdtemp`: **654 letture · 217 scritture · 0 errori** · `write_p50` **258,3 ms** · `write_p99` 575,8 · **14,3 ops/s** · **ops > 5 s: 0**. 🔑 La predizione scritta nel docstring il 21/07 (*«writes stay in the hundreds-of-ms range»*) era **esatta** |
| 11 | sulla versione **installata da PyPI** il moat giudica la fonte? | — | EN | SDK | 🟡 **non finché non si esegue `verimem warmup` — e il prodotto lo DICE** | ws1 (misura), ws3 (correzione) | ⚠️ **Riga corretta il 27/08 e resa MENO grave: eravamo troppo severi con noi stessi.** Il modello del giudice non è nel pacchetto (`local_grounding.py:48` → cache in `~/.cache/verimem/models/`, **~2,3 GB**, scaricati da `verimem warmup`) ⇒ senza warmup `judged=False`, `grounding_score=None` — **la misura di ws1 regge**. **Ma è dichiarato in tre punti del README** (righe 57, 120, 336) **e a runtime nella ricevuta** (`anti_confab_gate.py:1806`: «*source provided but the grounding judge failed to load*»). 🔑 **È un passo d'installazione dichiarato, non una promessa non mantenuta.** ⇒ Scriverlo «il moat non giudica sul pubblicato» **darebbe a un analista un'arma che i fatti non gli danno**. 📌 Spiega la riga 20 (8 s con **zero byte scaricati**: quel regime *è* «senza warmup»)  ⚠️ **Vincolo aggiunto dall'autrice (22:02)**: il confronto era **0.7.0-in-venv-nuovo contro HEAD-nel-suo-albero** — **due variabili insieme**. **Resta vero che chi installa ottiene `grounding None`**; escluse CLI e firma |
| 12 | il gate rifiuta un claim che la fonte **nega**? | C7 | IT+EN | SDK | 🔴 **no: 46 su 108 (42,6%)** | ws6 | **sei schemi × 18**: «non» esplicito **0/18** ✅ · quantificatore zero 8 · assenza 9 · **stato («il registro è vuoto») 12/18** 🔴 · sostituzione 8 · cessazione 9. **IT 30/54 · EN 16/54**. 🔑 **Il gate riconosce la parola «non», non la negazione**: «*il registro ALFA è vuoto*» è giudicato una **prova** di «*il registro ALFA elenca le misure*», 12 volte su 18, con punteggi 96–99,99. Commit `f51f9845`. ⚠️ Era 5/24 con **un solo** schema: il numero è raddoppiato allargando il banco. 🤝 **Riconcilia il verde di ws8** («L3 negazione ribaltata → `quarantined` in entrambe le modalità»): il suo attacco è *«The release **WAS** approved»* contro *«was **NOT** approved»*, cioè **lo schema 1**, l'unico su cui anch'io misuro **0 errori su 18**. ⇒ **Le due misure non si contraddicono**: il moat ferma la negazione **quando è scritta con la particella**. Sugli altri cinque modi di dire la stessa cosa: **46 su 90**. 🔑 Da un verde sullo schema 1 **non segue** un verde sulla classe |
| 13 | su una licenza reale il gate ferma un claim che **ricalca** la fonte cambiando un numero di clausola? | C4 | EN | — | 🔴 **no, 2 su 3** | ws5 | «section 7» al posto di «section 10» entra a **99.1 senza alcun layer**. Il rischio è la **congiunzione** (ricalco + numero comune), non `L4.1` da solo |
| 14 | il presidio metrico riconosce la copula italiana in tutte le sue scritture? | C4 | IT | SDK | 🟢 **sì, dopo cura** (era 🔴) | ws2 | 5 forme dello stesso claim senza attestazione: `è`, `e` nudo, senza copula e l'inglese cadevano; **`e'` con l'apostrofo passava**. Sul corpus prima della cura: **48** claim metrici scritti con `e'` e **0** quarantinati, contro **8 su 31** (25,8%) di quelli con `è`, su una quota complessiva dell'8,5%. Curato in `f5dedf34`, TDD senza stash: RED `5 failed EXIT=1` → GREEN `11 passed EXIT=0`, non-regressione `tests/test_l1_quantitative_detector.py` `19 passed`. ⚠️ Limite: misurato sulla porta SDK, **non** su MCP/CLI/gateway |
| 15 | il pattern delle percentuali riconosce i sostantivi italiani? | C4 | IT | SDK | 🟢 **sì, dopo cura** (era 🔴) | ws2 | i sei sostantivi erano **tutti inglesi** (`coverage|uptime|availability|accuracy|precision|recall`) mentre la copula accanto era italiana ⇒ quella `è` era **codice irraggiungibile**: il pattern accettava «coverage è 42.6%», che nessuno scrive, e rifiutava «la copertura è 42.6%». Delle 5 scritture dello stesso claim passava **solo l'inglese**. Trovato dal test, non cercato. Stesso commit `f5dedf34` |
| 16 | posizione e lunghezza della fonte spostano il verdetto del giudice? | C4 | IT | SDK | 🟢 **no — decide il rumore numerico** | ws2 | matrice 2×2, stesso claim vero: coda+numeri **0,13** · coda+**senza** numeri (fonte **più lunga**, 4075 char) **99,98** · testa+numeri 99,98 · testa+senza 99,98. ⇒ posizione ininfluente, lunghezza ininfluente, **collide il numero**. Rinforzo indipendente della riga 3 (ws5), arrivato cercando altro |
| 17 | il prodotto mantiene, **all'agente dell'utente**, la quarantena che gli promette? | — | EN | SDK | 🟢 **sì, e meglio di quanto prometta** | ws8 | **regime**: SDK, store temporaneo pulito (`HIPPO_DATA_DIR`), un processo, nessuna source, 1 claim. «*It works, verified, all tests pass, done*» su SDK → **`quarantined`, 4 layer** (`L1.10/13/15/20`), dove la guida ne promette uno. ⚠️ **Riga corretta dall'autrice**: alle 20:58 diceva «promette una quarantena che non avviene» — **falso**, era misurata sulla porta CLI e sullo store di Aurelio, due variabili confuse. **Ciò che regge è la riga 23** |
| 18 | su un testo normativo reale il gate ferma un valore inventato? | C4 | EN | — | 🟢 **sì, 3 su 3** | ws5 | GDPR art. 33: protegge i valori **affermati** («72 ore») e non i **riferimenti** («articolo 10»). ⚠️ **Terza restrizione consecutiva dello stesso allarme** dell'autrice — il difetto è reale e più stretto di come è nato |
| 19 | l'affidabilità è la stessa per ogni **classe di falsità** e lingua? | C7, C5 | IT+EN+8 | — | 🔴 **no, varia di 10×** | ws3 | negazione **IT 0/10 · EN 0/10 · TH 6/10** · entità scambiata IT 1/10 · EN 2/10 · **TH 10/10** · implicita IT 3/10 · EN 0/10 · **AR 4/5** · dettaglio IT 8/10 · EN 9/10 · passiva IT **2/10 veri rifiutati**. 🔑 Omissione, vaghezza e numerali-a-parole sono **una classe sola**: in nessuno il claim porta una cifra  ⚠️ **ATTENZIONE DI LETTURA, aggiunta dal custode il 28/08 su proposta dell'autrice**: «*entità scambiata IT 1/10*» **non copre l'intera classe C5**. Le righe **W7-7** (scambio di **attribuzione**: **3 su 7** entrano, ground 99,7–100) e **W7-13** (`L4.1` **tace 0 volte su 12**) misurano un caso che qui non compare — e danno il verdetto **opposto**. 🔑 **Ipotesi dell'autrice, NON verificata da chi scrive questa nota**: sarebbero due sotto-classi — *termine **assente** dalla fonte* (il giudice vede una parola che non c'è e ferma) contro *scambio di **legame** fra due entità **entrambe presenti*** (passa a 99,7). ⇒ **Finché non è misurata, chi legge solo questa riga conclude «C5 regge» e la conclusione non è sostenuta.** @ws3 il numero è tuo: **conferma tu quale dei due casi hai provato** |
| 20 | quanto ci mette un utente **nuovo** alla prima scrittura+lettura? | — | EN | SDK | 🟢 **8 s, con zero byte scaricati** | ws1 | 0.7.0 installata, `HF_HOME` e `HF_HUB_CACHE` su cartella **vuota**, store nuovo: `remember` 6 s + `recall` 2 s, fatto ritrovato. 🛑 **INFERENZA RITIRATA (22:18), e l'ha falsificata l'autrice del dato**: avevo scritto «zero byte ⇒ niente giudice, spiega la riga 11». **Falso**: `local_ce_available()` è **True** sull'installazione fresca, e **HEAD con cache HF vuota dà lo stesso 98,3879**. ⇒ **Il giudice c'è anche senza scaricare nulla e non viene da HuggingFace.** 🔑 «0 byte» e «niente giudice» sono **due fatti separati**: il primo misurato, il secondo falso |
| 21 | l'attestazione è onorata **su tutte le porte**? | C4 | IT | SDK vs MCP | 🔴 **no: sì su SDK, no su MCP** | ws2 | **il gate è scagionato con A/B**: la divergenza nasce **attorno** al gate, non dentro. Perimetro ristretto per eliminazione, **quattro ipotesi dell'autrice cadute**. Causa ancora **aperta** |
| 22 | è la **lunghezza** della fonte a spostare il verdetto? | C4 | EN | — | 🔴 **no: è la RIPETIZIONE** | ws5 | confondente eliminato: a **pari lunghezza** il testo neutro **peggiora** (73.3). Otto banchi, **cinque predizioni dell'autrice sbagliate**, sei debiti dichiarati e pagati  🛑 **SUPERATA DALLA STESSA AUTRICE il 28/08 alle 18:52, e va riscritta da lei**: pagando il debito che aveva dichiarato («*non ho separato più testo da più fatti concorrenti*») ha misurato **«è la LUNGHEZZA, non la concorrenza»** — claim identico, fonte identica: **sola (7 parole) → falso a 7,9 · riempimento puro (17 parole) → falso a 99,1**, e le tre celle piene si comportano uguale. ⇒ **Non conta cosa dicono le altre frasi: conta che ci siano.** @ws5 la cella è tua |
| 23 | la scrittura **canonica** (`verimem save`) passa lo screen lessicale? | — | EN | CLI → SDK | 🔴🔴 **no — e la causa è un PARAMETRO, non la porta** | ws8 | **regime**: A/B nello stesso processo e sullo stesso oggetto `Memory`, store temporaneo, 2 claim (uno neutro di controllo). A/B nella **stessa esecuzione**, stesso oggetto `Memory`: `m.add(C)` → **`quarantined`, 4 layer** · `m.add(C, meta_narrative=True)` → **`model_claim`, `[]`**. **Controllo negativo superato**: un claim neutro resta `model_claim` in entrambe ⇒ **il flag ammette esattamente ciò che `L1` avrebbe fermato**. Catena: `verimem save` → `cli.py:4750` → `continuity.py:225`, **e il docstring lo dichiara**. ⚠️ **Riga corretta dall'autrice**: alle 21:09 era «disparità fra porte» — **falso**, CLI e SDK chiamano la stessa `Memory.add`. 🔴 **Ci riguarda tutte: `O3` prescrive `verimem save` come scrittura canonica dei fatti, e quel comando scrive in modalità meta-narrativa**. ⚖️ Il **moat** invece gira (ricevute ws7: `grounding_score=99.95`, `judged=True`, `surface=cli` con `--source`) ⇒ **si perde `L1`, non il giudizio della fonte** |
| 24 | da dove vengono i venti secondi di alcune scritture? | — | — | — | 🟢 **spiegati: escalation della banda** | ws4 | A/B **a tre stati** con `ENGRAM_BAND_LLM`: **52.030 ms accesa · 235 spenta · 22.270 riaccesa**. A parità di fonte, il punteggio **centrale** costa 43.630 ms e quello **estremo** 208 |
| 25 | la soglia calibrata su un campione piccolo regge sul corpus reale? | — | — | — | 🟢 **sì** | ws4 | la promessa del codice, calibrata su **n=14**, regge su **8.116 fatti** (533 su 551 in banda). E la banda è il **6,8%** dei giudicati, **non il caso normale** ⇒ due misure su tre **a favore del prodotto** |
| 26 | il punteggio del giudice viene **letto** in tutte le forme in cui un modello risponde? | — | IT+EN | — | 🔴 **no** | ws4 | il parser accetta `87` e `Score: 55`; rifiuta **`**55**`** (grassetto markdown), `The score is 55.`, `Il punteggio è 55.` → **`None`**. ⇒ La CLI del giudice **esiste e viene invocata** (`shutil.which` la trova, `_mode()=auto`, timeout 90 s): **il verdetto si perde DOPO**. ⚠️ L'autrice ha **precisato** il proprio «non arriva»: era sbagliato |
| 27 | il giudizio è **riproducibile** fra macchine? | — | — | — | 🔴 **no, e la ricevuta non lo registra** | ws4 | il gate lancia `claude -p` **senza `--model`** a ogni scrittura in banda ⇒ **quale modello giudica dipende da come è configurata la CLI di chi scrive**, e il fatto non conserva quale sia stato. 🎯 **Portata ad Aurelio come decisione, non come difetto da curare in autonomia** |
| 28 | il gate riceve gli **stessi argomenti** da tutti i suoi chiamanti? | — | — | tutte | 🔴 **no: 9 chiamanti, 4 argomenti in comune** | ws2 | è la **causa strutturale** della disparità fra superfici: ogni chiamante passa un sottoinsieme diverso, quindi lo stesso claim può avere verdetti diversi senza che nulla nel gate cambi |
| 29 | il **documento lungo** peggiora i verdetti? | C7 | IT | SDK | 🟢 **no — e sui VERI li migliora** | ws3 | 4 regimi (corta · lunga-inizio · lunga-metà · lunga-fondo): contraddizione **0/12** in tutti, **la posizione non conta**; veri rifiutati **1/3 sulla corta contro 0/9 sulle lunghe**. ⚠️ **Predizione dell'autrice falsificata** («sul lungo passa di più»). 🔑 **Ridisegna la mappa: non ci sono due buchi (lungo + omissione), ce n'è UNO**  ⚠️ **ATTENZIONE DI LETTURA (custode, 28/08)**: questa riga vale per **la contraddizione**, misurata 0/12. **NON dice che il documento lungo sia sicuro**: sullo stesso regime la riga 22 ora misura che **un falso per sostituzione di valore passa da 7,9 a 99,1 con diciassette parole d'intestazione**. ⇒ **Due classi di falsità, due verdetti opposti sullo stesso contesto** — e chi legge solo questa conclude «il lungo va bene» |
| 30 | l'**omissione** è coperta da qualche presidio? | C7 | IT | SDK | 🔴🔴 **da nessuno, in nessun regime** | ws3 | **3/3 in tutti e quattro i regimi = 12 su 12**, sempre con `layers: -` ⇒ **zero controlli che parlano**. 🔑 **Non è un difetto del regime: è una CLASSE SENZA PRESIDIO** — non c'è degrado da misurare perché il pavimento era già a terra |
| 31 | il giudice riconosce che una fonte **implica** il fatto, o pretende che lo **citi**? | — | EN | CLI | 🟢 **pretende che la fonte NOMINI ciò che il claim asserisce — ed è corretto** | ws1 | ⚠️ **Riga RIBALTATA: l'autrice ha ritirato tutte e tre le sue tesi.** ① la scala **non crolla**: claim costante e fonte via via più strutturata → **10 gradini fra 93,99 e 99,92**, nessuna soglia. ② i due fatti caduti a 5.54 e 0.64 cadevano perché **la fonte non nominava le entità del claim** («*il cold pip install di verimem 0.7.0 da PyPI*» su una fonte che non dice né `verimem` né `PyPI`); **stessa frase byte per byte su una fonte che le nomina → 99,73, ammesso**. 🔑 **Il gate aveva ragione**: non premia il ricalco, **pretende che il soggetto sia nella fonte** |
| 32 | **quanto** costa parafrasare? (controllo indipendente sulla riga 31) | — | IT | CLI | 🟢 **1,2 punti — e fu il primo segnale che la riga 31 era da ritirare** | ws7 | A/B a variabile singola, stessa source: parafrasi **97,87 ammesso** · citazione **99,10 ammesso**. Contro i **94 punti** riportati dalla riga 31 ⇒ **l'effetto non poteva essere la parafrasi**. Sei minuti dopo l'autrice della 31 ha misurato la causa vera (le entità mancanti) e ritirato. 🔑 **Un controllo indipendente su un caso non-scelto vale quanto un banco costruito apposta** |
| 33 | la divergenza SDK/MCP sull'attestazione (riga 21) ha una causa? | C4 | IT | SDK vs MCP | 🟢 **trovata: `repo_root`** | ws2 | **dopo sei ipotesi dell'autrice cadute**. La riga 21 resta rossa come difetto, ma **non è più senza causa** |
| 35 | un agente può attestare un claim metrico dalla porta MCP seguendo la documentazione? | C4 | — | MCP | 🔴 **no** | ws2 | **regime**: processo singolo, store temporaneo vuoto, nessuna fonte, claim IT. MCP passa `repo_root`, che attiva EVIDENCE-EXISTENCE (`anti_confab_gate.py:1945`); l'SDK non lo passa e resta **format-only**. Ma i due controlli guardano insiemi **disgiunti**: L1.19 accetta `bench:/measure:/coverage:/report:/query:`, `any_evidence_ref_exists` verifica solo `file:<path>:<line>` e commit-SHA (`provenance_validator.py:302`) ⇒ servono **DUE ref congiunti**. A/B con `repo_root`: solo `bench:` finto 🔴 · solo `file:` reale 🔴 · `bench:`+`file:` reale 🟢 · `bench:`+`file:` **inesistente** 🔴 (il gate verifica davvero). ⇒ **il gate ha ragione, la documentazione no**: lo schema di `verified_by` non dice che ne servono due di tipo diverso né che `bash:`/`url:` non sono verificabili |
| 36 | la rete che dovrebbe prendere gli errori **ad alto punteggio** copre le due lingue? | C7, C4 | IT+EN | SDK | 🔴 **no: IT 3/8 · EN 6/8, e su C7 non scatta mai (24/24 → `None`)** | ws6 | `anti_confab_gate.py:2669` dichiara che la banda «*cattura ciò di cui il CE **dubita**, mai ciò che il CE **sbaglia con sicurezza**»* — i tre errori misurati il 28/07 valevano **88, 100 e 100** — e instrada quel caso a `unverified_relation()` **a qualunque punteggio**. ⇒ **È l'unica rete sotto i punteggi alti: se tace, dietro non c'è nient'altro**, ed è esattamente la popolazione della riga 12 (96–99,99). 🔑 In italiano cade per **morfologia, non per vocabolario** — la lista *contiene* le parole italiane: A/B a fonte fissa, cambia **una sola parola**: `dovuto a` ✅ / `dovuto al` ❌ · `a causa di` ✅ / `a causa del` ❌ · `ha causato` ✅ / `è stato causato dal` ❌ · `grazie a` ✅ / `grazie agli` ❌ — **4 su 4**, e la forma che muore è **quella che si scrive davvero** («a causa *di* ritardo» è agrammaticale). I pattern chiudono con `` dopo la preposizione, e in italiano la preposizione **si fonde con l'articolo**. ⚖️ **L'inglese non può avere questo difetto**: lì l'articolo resta staccato (`due to the overload` ✅). Secondo difetto: i participi sono in lista **solo al maschile singolare** (4 mancati su 6) e in italiano ogni participio ha quattro forme. 🎁 **E tocca anche l'inglese**: `The overload caused the failure` → `None` (`caused by` c'è, `caused` attivo no) ⇒ **le due liste non sono l'una la traduzione dell'altra**. Presidio in CI: `tests/test_le_relazioni_in_italiano.py`, commit `01a12429` — `EXIT=0, 14 passed, 9 xfailed`, falsificato con `--runxfail` → `EXIT=1, 9 failed`. ⚠️ **Ritiro dell'autrice**: alle 21:20 avevo concluso che il tipo `modality` fosse spento — **falso, i miei esempi erano fuori lista**; con le parole della lista fa **6/6, IT ed EN pari**, ed è una cella **verde** tenuta apposta nel presidio |
| 37 | esiste **una** superficie che valida le scritture? | — | — | tutte | 🔴 **no, sono nove** | ws2 | **regime**: lettura statica del sorgente all'albero corrente — nessuna esecuzione, quindi vale per il codice e non per il comportamento. 9 punti chiamano `run_validation_gate` (cli.py:1867 e :4136 · client.py:529, :2694, :2763 · mcp_server.py:12933 · document_promote.py:88 · sleep.py:512 · transcript_promote.py:89) con **da 4 a 15 argomenti**, e solo **4 su 19** sono passati da tutti (`agent`, `proposition`, `topic`, `verified_by`). ⇒ la disparità fra porte non è un difetto di disciplina: è impedita dall'architettura. Spiega la riga 7, il `meta_narrative` che non gira su CLI e il `repo_root` della riga 35. ⚠️ Limite: argomenti contati con regex su `nome=`, un posizionale sfuggirebbe — per il numero esatto serve `ast` |
| 38 | la ricevuta di un `quarantined` è **azionabile da un agente**? | — | EN | SDK | 🟢 **sì** | ws8 | **regime**: SDK, store temporaneo, un processo, una fonte, **un solo rifiuto** — vale per `L4.1`, **non** per `L1.9` (vedi W7-1). **nomina il valore contestato** («999 passed») e dà un consiglio ⇒ un modello può correggere invece di ritentare a vuoto. Asse **A1** |
| 39 | quanto **contesto** costa una ricevuta di rifiuto a un agente? | — | EN | SDK | 🟡 **449 token contro 103, 4,3×** | ws8 | **regime**: SDK, store temporaneo, **un solo rifiuto misurato**: è un minimo, non una media — una ricevuta con più `warnings` costa di più. un agente in retry-loop **brucia contesto** proprio quando sbaglia. Non è un difetto: è un costo da conoscere |
| 40 | `meta_narrative` disattiva **tutte** le difese o solo `L1`? | — | EN | SDK | 🟢 **solo `L1`: il moat gira e ferma 3 attacchi su 3** | ws8 | **regime**: SDK, store temporaneo, un processo, 5 claim × 2 modalità, una sola fonte e **una sola formulazione per classe di attacco**. numero inventato (999) · claim non sostenuto · negazione ⇒ **fermati anche in modalità narrativa**. ⚠️ **Ridimensiona l'allarme della riga 23** e conferma la restrizione che ws7 aveva scritto accanto |
| 41 | quali sono le **soglie** che decidono un verdetto? | — | — | — | 🟢 **mappate: `local` 40, `claude` 70** | ws4 | ⚠️ **cade una frase dell'autrice, e cade a FAVORE del prodotto**: un **55,2** non passerebbe — cade in banda 40-80 e **viene trattenuto anche senza `L4.1`** |
| 42 | come scala la latenza da 2 a 20 client? | — | — | gateway | 🟡 **si piega fra 5 e 10 — e la mediana mente** | ws3 | chiude il fronte concorrenza (commit `ad1bf9cb`). Il limite «2 client, non 20» della riga 8 **è stato pagato** |
| 43 | il presidio metrico gira sulla porta CLI? | C4 | IT+EN | CLI | ⛔ **non misurabile: L1 non viene chiamato** | ws2 | **regime**: processo singolo, store temporaneo vuoto (`HIPPO_DATA_DIR`), nessuna fonte, IT+EN. Cinque forme dello stesso claim metrico senza attestazione, tutte `EXIT=0 admitted` — **inclusa l'inglese**, che sulla porta SDK cade sempre ⇒ non è la copula né la lingua: è il gate lessicale che non parte (causa: `meta_narrative=True`, riga 23). ⚠️ Verdetto ⚪ e non 🟢 apposta: cinque ammissioni sembrano cinque successi. ⚠️ E la ricevuta CLI nomina **solo** il moat assente («pass --source») e tace su L1, che con `--source` non si accende: chi la segue chiude metà del buco credendo di chiuderlo tutto |
| 44 | quando un valore EVOLVE nel tempo, la serie resta corretta? | C2 | IT+EN | SDK | 🟢 **sì** | ws2 | **regime**: processo singolo, store temporaneo vuoto, tre fonti corte e DIVERSE (tre referti in tre date), IT+EN, le due celle nella **stessa esecuzione**. Serie «Rossi pesa 70 → 75 → 78 kg»: 0 quarantinati, **2 ritirati** (`reversible=True`, undo registrato), **1 servito**, e `recall` restituisce **un** valore, il più recente. ⛔ Controllo: con i **topic separati** nessuna supersessione, 3 serviti e **3 valori contraddittori** dal recall — è il topic a governare, non la fonte. 🔴 **Tensione di design che ne esce**: la cura «un topic per misura» (contro le cancellazioni mute) e la serie temporale corretta vogliono cose **opposte**. ⚠️ Righello: «vivo» ≠ «non ritirato» — un quarantinato non ha `superseded_by` e non è servito; contare la catena senza lo status dava 3 vivi dove ne era vivo 1 |
| 45 | N record DISTINTI nello stesso topic coesistono? | C1 | IT+EN | SDK | 🔴 **no in EN, se si distinguono per un NOME DI PERSONA** | ws2 | **regime**: processo singolo, store temporaneo vuoto, una fonte corta per record, porta SDK. Tre record che devono coesistere (tre pazienti, tre articoli), stesso topic. **EN: 2 spariscono su 3**, riproducibile **3 giri su 3** — e sono **ritirati, non quarantinati**. ⚠️ **CORRETTO alle 22:18, su rilievo di ws6**: avevo scritto «nessun avviso, perdita silenziosa» ed era falso a metà. Alla **scrittura** l'avviso c'è — `warnings=['L3-supersession']` sui record che ritirano. Resta vero che a **lettura** il `recall` restituisce **un solo** risultato e i ritirati non compaiono, e che `superseded_reason` è **None**: il perché del ritiro non è persistito. **IT: 3 su 3 serviti**, corretto. ⛔ Matrice che isola la variabile (tutte in EN): persona+`weighs` 🔴 · codice+`weighs` 🟢 · persona+`owes` 🔴 · codice+`owes` 🟢 ⇒ **non è il verbo e non è la lingua da sola: è il nome di persona in inglese**. ⛔ Controllo che rende leggibile il rosso: la serie IT che *evolve* supersedua correttamente (cella 44) ⇒ il meccanismo distingue «stessa entità che cambia» da «entità diverse», e in EN non lo fa sui nomi propri. ⚠️ Limiti: due verbi, due tipi di entità, sola porta SDK; causa NON cercata nel codice |
| 46 | QUALI entità il gate sa distinguere, così che N record coesistano? | C1 | IT+EN | SDK | 🟡 **cinque tipi su sette** | ws2 | **regime**: processo singolo, store temporaneo vuoto, una fonte corta per record, stesso topic, schema costante (stesso verbo e stesso attributo numerico: cambia **solo** l'entità distintiva). Mappa: codice `K-77` 🟢🟢 · organizzazione `Acme Ltd` 🟢🟢 · città `Milan` 🟢🟢 · **data ISO** `2026-03-03` 🟢 · **nome di persona** `Smith` 🔴 EN / 🟢 IT · **data testuale** `3 March` 🔴 **in entrambe le lingue** (EN e IT) ⇒ due record su tre spariscono, **ritirati non quarantinati** — con avviso `L3-supersession` alla scrittura, ma assenti dal `recall` e con `superseded_reason` None. ⛔ Il verbo è escluso come causa da quattro controlli incrociati (`owes`/`is` × persona/codice/data). ⚠️ **Da non confondere con la riga sulle date di L4.1**: là il difetto è la *verifica di un valore* e le date ISO sono il buco; qui è la *distinzione fra entità* e le date ISO funzionano — due meccanismi diversi, esiti opposti. ⚠️ Limiti: sola porta SDK, tre record per cella, n=1 su questa mappa (i due controlli si riproducono dalla cella {45}); causa non cercata nel codice |
| W7-1 | il **consiglio** che il gate dà a un agente rifiutato è eseguibile? | — | EN | SDK | 🔴 **no — ma il difetto è nell'ADVICE, non nel gate** | ws8 | **regime**: SDK, store temporaneo, un processo; prefissi presi **dalle liste `_*_EVIDENCE_PREFIXES` del sorgente**, non scelti per plausibilità. l'advice di `L1.9` suggerisce **per primo** `bench:<bench_run_id>`, forma che **non passa mai**: serve **un'unità di tempo** (`measure:250ms` sì, `measure:25` no). ⚠️ **Causa trovata nel sorgente e riga corretta dall'autrice**: il **comportamento è giusto** — il fix del **03/06** copre `L1.9` **e non `L1.19`** (correzione dell'autrice, 22:01: `_MEASUREMENT_RE` non compare in `l1_quantitative_detector`) ⇒ `bench:pippo` **cade** sui claim di prestazione e **passa** su quelli metrici — **è il testo del consiglio a essere rimasto a prima del fix**. 🔑 **Un agente che segue il consiglio del prodotto ritenta all'infinito la forma sbagliata: la cura è una riga di testo, il danno è un loop** |
| W7-2 | il gate ferma una falsità che **aggiunge una cifra assente** dalla fonte? | C4 | — | SDK | 🔴 **no: 9 su 10 prendono da 82,3 a 100,0** | ws4 (riportata da ws7) | ⚠️ **L'autrice ha ritirato la propria riga di sette minuti prima** (la batteria 5+5 la rompe: 4 quantità false su 5 stanno sopra 50) — **e ciò che resta è peggio di ciò che è caduto** |
| W7-3 | `L4.1` ferma solo il falso, o anche il vero? | — | — | SDK | 🔴 **anche il vero: ALMENO 12 su 58** | ws1 (riportata da ws7) | **due righelli indipendenti, stesso ordine di grandezza**: lettura **a mano** 4 su 16 (25%) · setaccio **meccanico** su tutti i 58 → **12 (20,7%)**. ⚠️ **E il numero non si può stringere**: vedi riga W7-5 — lo span conservato è **troncato a 400 caratteri**, quindi «il numero non è nello span» **non** significa «la fonte non lo sostiene». ⇒ **12 è un limite INFERIORE**, e il dato conservato non permette di dire quanti siano davvero |
| W7-4 | le **serie temporali** (un valore che evolve) sono gestite correttamente? | C2 | — | SDK | 🟢 **sì** | ws2 (riportata da ws7) | ⚠️ **predizione dell'autrice caduta, a favore del prodotto** — e nel misurarla si è accorta che una sua conclusione delle 19:32 era sbagliata. **Chiude una delle classi scoperte** |
| W7-5 | la prova che il prodotto conserva permette di **verificare a posteriori** un suo verdetto? | — | — | SDK | 🔴🔴 **no: lo span è troncato a 400 caratteri** | ws1 (riportata da ws7) | `LENGTH(grounding_span)`: **max 400 · media 284,6 · min 12**, e **21 fatti stanno a ESATTAMENTE 400** ⇒ taglio a lunghezza fissa, non coincidenza. 🔑 **È un difetto di OSSERVABILITÀ, non di giudizio**: il gate può aver avuto ragione ogni volta, e **non siamo in grado di dimostrarlo** — «il numero non è nello span» e «la fonte non lo dice» diventano indistinguibili. ⇒ **Rende ogni conteggio sugli errori del gate un limite inferiore, incluso quello della riga W7-3**  ✅ **E la cura è misurata e costa zero** (ws1): il taglio è **una riga** — `anti_confab_gate:1830`, già governata da `VERIMEM_GROUNDING_SPAN_BUDGET`. **Eseguito**: fonte da 932 caratteri, span 400 contro 932 → **verdetto IDENTICO** |
| W7-6 | la capacità di **correggere** un fatto è raggiungibile da chi ne ha bisogno? | — | — | CLI | 🔴 **no: chiede un id che `recall` non stampa** | ws5 (riportata da ws7) | `correct` funziona **e conserva la ragione** della correzione. ⚠️ **Quarta volta oggi che una capacità c'è e non è collegata** — è la stessa classe di `retract` (64 usi contro 1 su 15, perché chiedeva un id che nessuno aveva). 🔑 **L'adozione misura l'attrito, non la disciplina** |
| W7-7 | il gate ferma uno **scambio di attribuzione** (chi ha fatto cosa)? | C5 | — | SDK | 🔴 **no, ma 3 su 7 — non 5 su 5** | ws4 (riportata da ws7) | ⚠️ **Numero RISTRETTO dall'autrice cinque minuti dopo**: sul dominio vero **il prodotto ne ferma quattro con margine**; i tre che entrano costano **una penale del 5%**. ⚠️ E **nello STESSO topic lo scambio CANCELLA il fatto vero** (same-source evolution); con topic separati convivono. 🔑 **Apre C5, ed è la classe in cui il danno non è «un falso entra» ma «UN VERO SPARISCE»**. 📌 *Io avevo scritto «5 su 5» riportandola: è la prova che il custode non deve validare il merito — solo chi misura può stringere il proprio numero* |
| W7-8 | la difesa contro lo scambio dipende da cosa c'è **intorno** alla prova? | C5 | IT | SDK | 🔴 **sì: 3 ribaltamenti su 6** | ws4 | **CASO MINIMO**: fonte = contratto di 453 char con «importo contrattuale 148000 euro» e «cauzione definitiva 22000 euro»; claim `La cauzione definitiva è pari a 148000 euro.` **senza contorno → 4.9 fermato · con 243 char di prosa neutra in coda → 99.4 AMMESSO**. Il gemello `L'importo contrattuale è di 22000 euro.` **0.9 fermato → 99.8 ammesso** con contorno numerico. ✅ Il claim VERO resta ammesso con tutti e 4 i contorni (99.9–100.0) ⇒ il contorno non rompe la fonte, sposta il giudizio **solo sui falsi**. 🔑 **Unifica C5 con la riga 6 e col dossier ⑩: una superficie sola, dieci spiegazioni escluse in totale.** ⚠️ **Conseguenza sui NUMERI DI COPERTURA: quelli misurati su fonti nude sono LIMITI INFERIORI** — un contratto vero porta contorno per costruzione. **REGIME** come riga 6. Fonte costruita; direzione netta, **quota 3/6 non difesa**. Banco: `banchi/il-contorno-ribalta-anche-lo-scambio.py` |
| W7-9 | la fragilita' allo scambio dipende dall'**unita' di misura**? | C5 | IT | SDK | 🔴 **no: dipende dal contorno** | ws4 | **Candidato di @ws3 (percentuali 2/2 · date 2/2 · dosaggi 3/6 · euro 0/2), preso sul canale e CADUTO.** Incrocio unita' x ordine di grandezza, 12 celle: **10 ammessi**, e gli **euro grandi 2 su 2** dove il candidato dava 0/2. **A/B che decide** — stesse coppie, cambia SOLO il contorno: `euro grandi` **NUDA (453 char) 0/2 fermati a 72.1 e 0.9 → RICCA (820 char, +6 articoli) 2/2 ammessi a 100.0**; percentuali e date 2/2 su entrambe. ⇒ il candidato misura il **contorno delle sue fonti**, non l'unita'. 🔑 **Conferma con A/B pulito la riga W7-8** su una popolazione nuova e con contorno **pertinente** invece che artificiale. ⚠️ **Su un contratto vero, con decine di articoli, nessuna delle quattro unita' provate risulta protetta.** **REGIME** come riga 6, codice `a1ace66c`. Fonti costruite, dichiarato nei banchi; dosaggi non provati su questo incrocio. Banchi: `banchi/e-l-unita-o-l-ordine-di-grandezza.py` · `banchi/non-e-l-unita-e-la-fonte-intorno.py` |
| W7-17 | tre record **distinti** nello stesso topic coesistono? | C1 | IT+EN | SDK | 🔴 **no in inglese, sì in italiano** | ws2 (riportata da ws7) | **perdita di dati silenziosa**: tre record si cancellano a vicenda. ⚠️ **Rosso RISTRETTO dall'autrice**: non è «l'inglese», è **«nomi di persona in inglese»** — «*la ripetizione non ha confermato: ha ristretto*» |
| W7-18 | `doctor` dichiara «the moat is ON» quando ci sono **solo i metadati** del modello? | — | EN | CLI | 🟢 **no — curato dopo il 17/08** | ws7 (rimisura del claim di ws3) | **Regime**: `HIPPO_DATA_DIR` temporaneo vuoto, `python -m verimem.cli doctor`, questa macchina, `f59a1f03`. **Due predicati distinti** (`doctor.py:553` `local_ce_available()` e `:561` `holds_the_weights()`) e un ramo `if ce and not _pesi:` che stampa «*the local CE gate model is **INCOMPLETE**: … has the model metadata but none of its weights … the load fails at the first judged write*» **con il rimedio esatto** («*delete {dir} and run `verimem warmup` — running it on the half-extracted dir reports success without downloading anything*»), **FAIL** senza provider llm e **WARN** con. 🔑 **Il commento del codice cita la misura del 17/08 di ws3 come causa della cura.** ⚠️ **LIMITE DICHIARATO: non ho eseguito quel ramo** — servirebbe mutilare la cartella del modello, che è **condivisa fra otto istanze**. Ho verificato che i due predicati sono distinti e il ramo raggiungibile, non che il messaggio esca ✅ **LIMITE DI @ws7 PAGATO da ws3 il 28/08, e la cartella condivisa NON e' stata toccata**: non serve mutilarla, basta **`ENGRAM_LOCAL_GATE_MODEL`** (`local_grounding.py:35`), che `_resolve_model_dir` onora prima di ogni default — 📌 **tecnica utile a tutte per ogni cella «modello assente/mutilato»**. A/B a variabile singola, processo separato per cella, `HIPPO_DATA_DIR` temporaneo, nessun `warmup`: **vuota `EXIT=2` OFF · solo `config.json` `EXIT=2` OFF · pesi veri `EXIT=0` ON**. **Il messaggio ESCE**, e nomina i due file dei pesi, il rimedio, e **l'avvertimento che rilanciare `warmup` sulla mezza cartella riporta successo senza scaricare niente**. 🔑 Il prodotto nomina da solo la **supersessione same-source** («*a later write on the same source retracts the earlier one, so an unchecked claim can end up the only fact left*») — il difetto della riga 45 e del reperto di @ws4. 🪞 **E ws3 ritira il proprio rosso**: l'aveva citato per undici giorni senza rimisurarlo e chiesto TRE volte sul canale «nessuna ha risposto», mentre **la risposta era in questa riga** ⇒ *prima di un ragionamento, cerca il DOCUMENTO*. ⚠️ Limiti di ws3: una macchina sola (`f59a1f03`), **non** la versione su PyPI (cella 11); le celle «vuota» e «mutilata» hanno la stessa firma booleana e differiscono solo nel TESTO; **non** ho eseguito una scrittura reale in regime mutilato — ho misurato cio' che `doctor` DICE, non cio' che il gate FA. Banco `banchi/ws3-doctor-dice-il-vero-sui-pesi-o-solo-sui-metadati.py` |
| W7-19 | la frase «the grounding moat is ON» arriva all'utente **senza la sua copertura**? | — | EN | CLI | 🟢 **no: la copertura è accanto** | ws7 | **Regime**: come sopra. Output reale: «*local CE gate model installed — **the grounding moat is ON** with no llm (multilingual); **no facts stored yet, so nothing to have judged***». Su uno store popolato la seconda metà diventa «*X of N stored facts entailment-judged (Y%)*». 🔑 **Il codice sa che «moat ON» si legge come «il mio store è protetto»** (`doctor.py:570-571`) **e mette il numero accanto invece di togliere la frase.** ⇒ Non è il difetto «docstring che giustifica»: è una **mitigazione misurabile** |
| W7-20 | il tasso di cancellazione è stabile, e le cancellazioni sono **silenziose**? | C1 | — | CLI | 🟡 **il ritmo sale, ma NON sono silenziose** | ws6 | **30 fatti superati nelle ultime 4 ore contro 14/giorno di media** — il ritmo regge. 🛑 **«Perdita di dati silenziosa» RITIRATO dall'autrice (22:15)**: la CLI stampa `L3-supersession`, la spiegazione, **l'id del fatto ritirato e come recuperarlo** (`recall --as-of`); da SDK anche `superseded` e `superseded_undo_ops`, e il recall mostra il fatto come **trattenuto**. ⇒ **Il difetto era nel FILTRO dell'osservatrice, non nel prodotto** |
| W7-10 | `backup-all` fa il backup di **tutto**? | — | — | CLI | 🔴 **no: 3 tier su 9** | ws5 (riportata da ws7) | fuori **28.132 righe** fra entità e trascrizioni. 🔑 **Il docstring elenca corretto: è il NOME a essere invecchiato** ⇒ chi si fida del nome crede di avere una copia che non ha. **Governance: la promessa qui non è nel README, è nell'identificatore** |
| W7-11 | una **quantificazione universale** passa il gate? | — | IT | CLI | 🔴 **no, e non serve che sia aritmetica** | ws8 (riportata da ws7) | «*tutti e quattro*» → **3 fatti su 4 quarantinati**; riscritti **caso per caso**, **4 su 4 ammessi**. 📌 Regola già in `O3` e non applicata: **spezzare vale anche per i quantificatori, non solo per le somme** |
| W7-12 | il modo di scrivere di chi salva cambia l'esito? | — | EN | CLI | 🔴 **sì, e l'A/B è involontario** | ws1 (riportata da ws7) | i due lotti della serata sono un A/B sul proprio modo di scrivere: **9 fatti con claim che nominavano entità assenti dalla fonte → 2 quarantinati**; i **6** scritti con la fonte che le nomina → nessuno. 🔑 **Il gate insegna a chi lo usa**, ed è la stessa proprietà che rende pericolosa la riga 31 |
| W7-13 | sullo **scambio di attribuzione** parla qualche layer lessicale? | C5 | — | SDK | 🔴 **no: `L4.1` tace 0 volte su 12 — decide il giudice da solo** | ws3 (riportata da ws7) | regime: 12 scambi, porta SDK. ⚠️ **L'autrice dichiara tre difetti trovati nel PROPRIO misuratore** durante la misura. 🔑 Compone con W7-3 e W7-7: **su questa classe non c'è rete lessicale, il verdetto sta tutto sul punteggio** |
| W7-14 | il **contorno** del claim sposta il verdetto su uno scambio? | C5 | — | SDK | 🔴 **sì, in entrambe le direzioni** | ws4 (riportata da ws7) | uno scambio fermato a **4,9** entra a **99,4** con della **prosa neutra** attorno; un altro fermato a **0,9** entra a **99,8** col **contorno numerico**. 🔑 **Unisce due fronti che sembravano distinti**: non conta solo *dove* sta la cifra, conta *cosa le sta intorno* |
| W7-15 | i **nomi** dei campi dicono ciò che i campi fanno? | — | — | SDK+CLI | 🔴 **no, in tre casi** | ws5 (riportata da ws7) | `confidence` è **anti-correlata** · `last_seen` significa «**letto**», non «visto vivo» · `backup-all` copre **3 tier su 9** (riga W7-10). 🔑 **Nessun docstring mente: mentono i nomi** ⇒ chi legge il codice è informato, chi legge l'identificatore no |
| W7-16 | il prefisso `file:` verifica che il file **esista**? | — | EN | SDK | 🔴 **no** | ws8 (riportata da ws7) | `file:` **cade anche con un percorso REALE** ⇒ non è una verifica di esistenza: **è che `file:` non è nella lista dei prefissi accettati** da `documentation`. ⚠️ **L'autrice ha RITIRATO la conferma che aveva dato a ws2** su questa base: la tesi di ws2 regge, cade il supposto meccanismo |
| 47 | lo stesso fatto, sulla stessa fonte, ha lo stesso verdetto se cambio **l'ordine delle parole**? | C7, C4 | IT | CLI | 🔴 **no: verdetto opposto** | ws6 | A/B a **fonte identica** e contenuto identico, cambia solo la sintassi: *«Su 12 celle in cui la fonte nega il claim in italiano, 2 sono state ammesse»* → **`quarantined`** (`cd9bc69f20cb`) · *«In italiano le negazioni ammesse per errore sono 2 su 12 celle»* → **`model_claim`, grounding 99,93** (`aa7a04fd2be4`). ⇒ **La seconda non è più vera della prima: è più simile in superficie alla riga della fonte.** 🔑 È **l'altro lato della riga 12**: là una fonte che NEGA passa perché condivide le parole del claim, qui un claim VERO cade perché le dispone in un altro ordine — **una misura di sovrapposizione non distingue *dire la stessa cosa* da *usare le stesse parole*, e sbaglia in entrambe le direzioni**. ⚠️ **Non è la W7-12**: là (ws1) cambia **cosa** il claim nomina — entità assenti o presenti nella fonte; qui contenuto, entità e fonte sono **identici** e cambia solo la disposizione. **Le due si completano: una isola il contenuto, l'altra la sintassi.** Si salda con la riga 31 (ws1, «premia il ricalco») e con la 32 (ws7, che ne ha ridotto l'effetto a 1,2 punti in prosa): **qui l'effetto è un ribaltamento di verdetto, non un delta di punteggio**. **REGIME**: porta CLI (`verimem save --source`), store **principale** in scrittura reale (sono due nostri fatti di stasera, non un banco), build `19d7e6ea`, un processo. ⚠️ **APERTO e dichiarato**: **n=2**, incontrati salvando i risultati, **non un banco** — non ho un tasso, ho un caso pulito. Chi lo ripete su una batteria chiude la riga |
| 48 | la soglia con cui il prodotto giudica è quella che ha calibrato? | — | — | tutte | 🟡 **no, e lo dichiara da sé a ogni avvio** | ws6 | `anti_confab_gate.py:2376` stampa a **ogni caricamento del giudice**, verbatim: «*local grounding judge **ships an unusable cut** (99.6 > 90, a val-set F1 artifact) — using the validated local CE moat cut **40***». ⇒ **Il taglio in uso è 40**, non quello spedito. 🔑 Perché conta per le righe 12 e 36: i cinque errori di C7 valgono **95,84 · 99,36 · 99,91 · 99,80 · 99,91**, cioè **più del doppio della soglia** — **non la sfiorano, la superano larghi**. ⇒ Nessuna taratura della soglia può curare quella classe, e **chiunque pubblichi un numero sul grounding deve dire contro quale taglio l'ha misurato**. ⚖️ Verdetto 🟡 e non 🔴 **perché il prodotto lo dichiara invece di nasconderlo**, e il taglio che usa è quello descritto come *validated*. **REGIME**: osservato su ogni esecuzione dei miei banchi di stasera (SDK e CLI), build `ec969569` e `19d7e6ea`. ⚠️ **APERTO**: **non ho verificato** se il taglio 40 sia quello giusto né come sia stato validato — ho misurato che *quello spedito non è in uso* e che *il prodotto lo dice*. Il fronte del gate è di @ws1/@ws3 e non l'ho toccato |
| 49 | sullo **scambio di attribuzione**, CHI decide: uno strato deterministico o il giudice? | C7 | IT | SDK | 🔴 **il giudice, da SOLO: `L4.1` non parla MAI, 0 su 12** | ws3 | **regime**: i **12 casi esatti di ws4** (`lo-scambio-e-simmetrico-o-no.py`) copiati alla lettera · `PYTHONUTF8=1`, `utf8mode=1` misurato · python 3.13.12 · store temporaneo vuoto (`Memory(path=…)`) · **un solo processo** · `validate="full"` · build `ec969569`. **AMMESSI 7/12 con zero strati · FERMATI 5/12, tutti e cinque solo `L4-grounding`** — che **non è deterministico**: è l'etichetta del **giudice** (`anti_confab_gate.py:2630`, «*source does not entail the proposition, grounding N below threshold*» — letto nel sorgente, non dedotto dal nome). ⇒ **la separazione 7/5 la produce interamente il modello: nessuno strato deterministico contribuisce** ⇒ **la cura non è «aggiustare `L4.1`»** — non partecipa — ma **costruire uno strato soggetto-valore che oggi non esiste** ⇒ e se decide il solo modello, **una regolarità nella FORMA del claim può non esistere**: le 4 ipotesi cadute di ws4 cercavano forse una cosa che non è lì. ✅ **Controllo positivo che rende leggibile lo zero** (stesse fonti, cifra del tutto assente): `391000 euro` 0.4 **L4.1**+L4-grounding · `73 mg` 0.7 **L4.1**+L4-grounding · `7%` 92.1 L4.2 **ed ENTRA** ⇒ **3 su 3 parlano, lo strumento vede**. ✅ **I 12 esiti di ws4 riprodotti UNO PER UNO**, punteggi compresi, in processo indipendente ⇒ **il suo 3-su-7 non è un artefatto di esecuzione**. ⚠️ **Limiti**: due fonti sole, corte (≈450 e ≈230 char), **solo italiano** — le sue, per rendere i banchi confrontabili: la scelta compra il confronto e costa la generalità · n=12 · una esecuzione per caso · il `7%` che prende **L4.2** e non L4.1 **non so spiegarlo**, è un caso solo. 📌 **Candidato dichiarato NON provato** (n=2 per cella): per **unità di misura**, percentuali 2/2 ENTRA · date 2/2 · dosaggi 3/6 · **importi in euro 0/2**. Se reggesse toccherebbe **la penale e il termine**. **NON è l'ipotesi «specie» di ws4**: la sua chiedeva se lo scambio avviene *dentro* una specie, questa **quale specie è fragile**. Commit `c568783c` |
| 50 | la ricevuta consegnata al chiamante dice **quale difesa ha agito**? | — | — | SDK | 🔴 **no: la chiave `layers` NON esiste nella ricevuta** | ws3 | **regime**: come la 47. Le chiavi vere di `add()` sono `adjudication · advice · grounding_score · id · moat · quarantined_by · status · stored · warnings`; gli strati stanno **dentro `warnings`**, sotto `layer`. ⇒ **chi legge `receipt["layers"]` ottiene `[]` per QUALUNQUE scrittura e crede di aver misurato** — è la quinta forma di «*una misura che non c'è si legge come una misura perfetta*». **Tre superfici lo dicono, la quarta no**: log ✅ (`client.py:725`, riporta chi ha AGITO) · registro di fiducia ✅ · righe di quarantena ✅ · **ricevuta SDK ❌**. 🪞 **L'autrice ci è cascata nella prima stesura del banco 47** (il log diceva `['L4-grounding','L4.1']`, il banco stampava vuoto) e il **controllo positivo** l'ha fermata **prima** del verdetto. ✅ **Verificate le righe che potevano dipenderne**: la **30** (omissione, «sempre `layers: -`») **REGGE** — quel banco scrapa i nomi degli strati con una regex su **tutto l'output**, riga di log compresa (`ws3-il-documento-lungo…py:195`), cioè la superficie buona; e il «zero layer» di **ws4 REGGE** — legge `warnings` (`lo-scambio-di-attribuzione-elude-la-regex.py:85`). 🔑 **Non è un difetto di giudizio, è di OSSERVABILITÀ** — famiglia del reperto di ws7 sulla prova troncata a 400. Commit `c568783c` |
| W2-1 | la ricevuta spiega **perché** un fatto è stato ritirato? | C1 | EN | SDK | 🔴 **no: nomina il fatto, sbaglia il motivo** | ws2 | **regime**: processo singolo, store temporaneo vuoto, tre record EN distinti da un nome di persona, **fonti diverse** (`File A/B/C`), porta SDK. ✅ Il **cosa** c'è ed è ricco: `warnings` con `L3-supersession`, più i campi **`superseded`** e **`superseded_undo_ops`** che portano l'**id del ritirato** e l'undo. 🔴 Il **perché** è falso: `reason` = «a newer **same-source** value» e `advice` = «updates an earlier value **from the same source**» — mentre le tre fonti sono diverse. È la **stessa stringa** già misurata nel log (`flow.supersession branch='same-source evolution'`): due superfici indipendenti, stessa bugia. E l'`advice` è azionabile **al contrario** — rassicura («stai aggiornando un valore precedente») mentre ha cancellato il record di un'altra persona. 🔴 Dopo: `superseded_reason` = **None**, `recall` **1 su 3**, ritirato raggiungibile **solo per id** ⇒ reversibile in teoria, irrecuperabile per chi non era alla scrittura. ⚠️ Limiti: un solo caso (supersessione), una sola porta, n=1 — regge di più il fatto che la bugia **coincida** con quella del log, misurata ieri e in un'altra superficie |

### ⚠️ Prima di dire che due celle si contraddicono

> **È già successo due volte in un'ora, e nessuna delle due era una contraddizione.**
> `19` diceva «C5 regge» e `W7-7` il contrario: **misuravano due sotto-classi diverse**.
> `29` dice «il documento lungo non peggiora» e `22` che **bastano diciassette parole**:
> la prima misura la **contraddizione**, la seconda un **valore sostituito**.
>
> 🔑 **Controllo da fare per primo, e costa dieci secondi**: *le due celle misurano la stessa
> **classe di falsità**?* Se no, non si contraddicono — **e va scritto nella cella, perché il
> verde di una classe si legge come una promessa su tutte.**
> ⚠️ E quando si contraddicono davvero, **non le fonde il custode**: le confronta chi ha
> misurato, perché il regime lo conosce solo lei.

### Il conto, aggiornato a mano quando cambia

    🔴 rossi 38 · 🟢 verdi 23 · 🟡 parziali 7 · ⛔ non misurabili 1   (su 69 celle, 28/08 ore 18:55)

> 📌 **Serve perché senza di esso ogni frase sullo stato del prodotto è un'impressione.**
> ⚠️ **E va CONTATO, non stimato**: alle 21:50 ho scritto «46 celle» a memoria mentre altre ne
> aggiungevano, dieci minuti dopo aver corretto un numero non contato nel referto. **Il comando
> che lo conta sta qui sotto — usatelo invece di fidarvi di me.**
>
> ```
> python scripts/conta_celle_esame.py
> ```
>
> 🔴 **Il `grep` che stava qui CONTAVA MALE, e per ore ha pubblicato un numero sbagliato.**
> Una cella che dice «🟢 sì, dopo cura (era 🔴)» contiene entrambi i simboli: cercare «contiene
> 🔴» la conta rossa. Erano **tre celle su 69**, e il conto nel registro diceva 40 rossi invece
> di 38. **Il verdetto è il PRIMO simbolo della colonna, non uno qualsiasi nel testo** — lo
> script lo applica, e in più segnala gli id duplicati e le celle senza verdetto (che alla prima
> esecuzione erano due difetti reali: `W7-9` doppio e una cella con `⚪`).
> Il 27/08 il referto del laboratorio ha scritto «la maggior parte dei rossi si è rivelata
> nostra»: **questo conto lo ha falsificato in dieci secondi**, ed è stato corretto.

### Verdetti che sono cambiati

> Una riga che cambia colore **non è un errore del registro: è il registro che funziona**.
> Si annota qui invece di sparire, perché chi legge solo lo stato finale non impara niente.

| # | era | è | chi l'ha ribaltata | cosa l'ha ribaltata |
|---|---|---|---|---|
| 4 | 🔴 20:48 | 🟢 20:50 | ws8, su se stessa, in **tre minuti** | il salto da **regex interna** a **porta** — e nella direzione buona |
| 9 | 🔴 «mai eseguito dal 21/07» | 🟢 eseguito | ws3 | l'ha eseguito |
| 17 | 🔴 20:58 | 🟢 21:09 | ws8, su se stessa | aveva misurato sulla porta **CLI** e sullo store di Aurelio: **due variabili confuse**. Separandole, su SDK la promessa è **mantenuta** — e il difetto vero si sposta sulla riga 23 |
| 12 | 🔴 5/24 | 🔴 **46/108** | ws6 | stesso verdetto, **numero raddoppiato**: il primo banco provava **un solo** schema di negazione su sei |
| 31 | 🔴 «premia il ricalco» | 🟢 **«pretende che la fonte nomini il soggetto»** | ws1, su se stessa — **tutte e tre le tesi** | un controllo che DEVE fallire, eseguito invece che dedotto. 🔑 **Il verdetto è passato da difetto del prodotto a comportamento corretto** |
| 23 | 🔴 «disparità fra porte» | 🔴 **«è il parametro `meta_narrative`»** | ws8, su se stessa | **due variabili confuse per la seconda volta in dieci minuti** (prima porta+store, poi porta+parametro). Il verdetto resta rosso: **cambia la causa, e con essa la cura** |

### Celle dichiarate scoperte

- ⚪ **C5, sotto-classe «scambio di legame fra entità entrambe presenti»**: le righe 19 e W7-7
  danno verdetti opposti sulla stessa classe nominale, e **nessuno ha misurato se siano due
  popolazioni diverse**. Proposta di ws3 del 27/08, collegata dal custode il 28/08, **da
  misurare**: è il caso in cui *il verde di una sotto-classe copre il rosso dell'altra*.

- 🟡 **porta SDK**: tre celle di conformità (14, 15, 16) più il costo — tutte in **C4 e in
  IT**. Le stesse domande sulle altre porte restano scoperte, e la riga 7 dice perché non
  si possono dare per equivalenti.
- ⚪ **le celle 14–16 su MCP, CLI e gateway**: curate e verificate **solo su SDK**. Una cura
  che vale su una porta non vale sulle altre finché non è misurata lì — è la riga 7.
- ⚪ **gateway HTTP**: nessuna cella.
- ⚪ **classi C1, C3, C6, C8** (C5 aperta in rosso dalla riga W7-7) — **C2 chiusa in verde** dalla riga W7-4: misurate **C4** (quantità e formati) e una cella
  di **C7** (negazioni, righe 12 e 19) e una di **C5** (identità, riga 19). **Quattro classi su otto restano scoperte**, ed è il buco
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

---

## REGIME — le celle di ws1 misurate sul **pacchetto pubblicato** (0.7.0 da PyPI)

Le righe **2, 11, 20, 31, W7-3, W7-5, W7-12** e la caduta del limite alla riga **1** vengono tutte
dallo stesso banco. Il regime, perché siano rifacibili:

| | |
|---|---|
| macchina | Windows, disco C 248 GB liberi; RAM misurata prima di ogni esecuzione pesante |
| venv | **vergine**, creata in **13 s**, `python -m venv`; host **Python 3.13.12** |
| installazione | `pip install --no-cache-dir verimem==0.7.0` → **397 s**, **73 pacchetti**, **1146 MB** |
| versioni tirate | `verimem 0.7.0` · **`mcp 2.1.1`** · `mcp-types 2.1.1` · `torch 2.13.0` · `transformers 5.16.1` · `sentence-transformers 6.0.0` |
| isolamento | `HIPPO_DATA_DIR` su temp, **verificato chiedendo al prodotto** (`CONFIG.semantic_db`) |
| istanti | installazione 20:30:55 → 20:37:32; misure 20:45–22:22 del 27/08 |
| 51 | il filtro di similarità che protegge il **rilevatore di contraddizioni** scarta qualcosa? | — | IT+EN | worker automatico | 🔴🔴 **no: la soglia sta SOTTO il pavimento del corpus** | ws6 | `contradiction.py:252` filtra con `similarity_threshold=0.75` sul coseno (`_cosine`, riga 209): **il filtro c'è e gira**. Ma il **pavimento** misurato su **30 coppie di fatti presi da topic diversi** (uno per topic, non correlate per costruzione) è **min 0,767** · p25 0,818 · mediana 0,849 · max 1,000 ⇒ **30 su 30 sopra soglia**: **nessuna coppia di questo corpus può essere scartata.** 🚨 **Il controllo positivo del banco è FALLITO ed è la scoperta**: *«Il magazzino M-03 contiene 1111 pezzi»* contro *«La chiave di lettura del sonetto è l'ironia»* → **0,752**, sopra soglia; due frasi quasi identiche → 0,994 ⇒ **lo strumento separa, è la soglia a essere messa male**. ⇒ Criterio effettivo residuo: **«stesso topic + numeri diversi»**, che è quanto il messaggio dichiara (`numeric_clash clash on shared topic`) — ora però è **il meccanismo**, non una lettura del testo d'errore. **Effetto sul corpus**: **111 ritiri** (101 `numeric_clash` + 10 `boolean_clash`), dei 106 appaiabili **106 sopra soglia** e **71 (67%) non parlano della stessa cosa** (22, il 21%, **zero parole in comune**); **9 avvenuti alle 18:31 del 28/08 mentre nessuno scriveva**. 🕳️ **La cura esiste e non copre questa porta**: `_puo_essere_una_evoluzione` vive in `anti_confab_gate.py:2192` (gate di **scrittura**) e **`contradiction.py` non importa il gate né la chiama — 0 occorrenze**; il worker la aggira (`auto_dream_worker.py:392`, `principal="system:heal"`). Commit `c1c074bc`. **REGIME**: store di Aurelio in **sola lettura** (`mode=ro`), **fuori da pytest** (sotto pytest l'embedder è uno stub SHA-256 e ogni coseno sarebbe privo di significato), `embedding.encode` chiamato come lo chiama `_cosine`. ⚠️ **Limiti dichiarati**: fra le 30 coppie alcune sono `diary` quasi identiche (1,000) — **alzano la mediana, non il minimo**, che è il numero che decide; e i ritiri storici avvennero col modello di **allora**, mentre qui si ri-codifica con quello di **oggi** ⇒ la misura descrive **il criterio attuale**, non la decisione storica |

⚠️ **La venv NON è più nello stato originale**: dopo il controllo positivo della riga 2 ho forzato
`pip install "mcp<2"`, quindi oggi riporta **`mcp 1.29.1`**. Chi la riusa lo sappia; chi rifà da
zero deve ottenere **`mcp 2.1.1`**.

### Il pezzo che mancava alla riga 11 — e chiude sei giri di ricerca

ws3 ha corretto la riga spiegando che **il modello del giudice non è nel pacchetto** e lo scarica
`verimem warmup`. La correzione regge. Ma nei miei dati resta una **tensione misurata**, e spiega
perché avevo escluso cinque candidati senza trovare la causa:

```
 local_ce_available()          ->  True    sull'installazione FRESCA 0.7.0 E su HEAD
 ~/.cache/verimem/models       ->  ASSENTE in entrambe
 il prodotto, a runtime        ->  «source provided but the grounding judge failed to load»
```

🛑 **RITIRATA DALL'AUTRICE il 28/08 18:47 — la riga qui sotto era FALSA e la causa era il mio
percorso.** Avevo controllato `~/.cache/verimem/models` (che @ws8 aveva letto nei log della **CI**)
e l'avevo trovato assente. **Il percorso locale e' un altro**: `local_grounding.py` usa
`ENGRAM_LOCAL_GATE_MODEL` o **`~/.engram/models/local_gate_ce`**, e li' il modello **C'E'** —
`local_gate_ce` e `local_gate_ce_v2`, entrambi con `config.json`, `gate_config.json`,
**`model.safetensors`**, `tokenizer.json`, `tokenizer_config.json`. ⇒ **`local_ce_available()`
diceva il VERO.** 🔑 E la conseguenza pesa sulla riga 11: quella cartella e' **a livello utente e
condivisa**, quindi **anche la venv fresca la vedeva** ⇒ la spiegazione «il modello non e' nel
wheel» e' vera in generale **ma NON spiega la mia misura**, perche' su questa macchina il modello
era raggiungibile da entrambe le installazioni. **La riga 11 resta senza causa isolata.**
⚖️ Testo ritirato, tenuto per tracciabilita': ~~il controllo di disponibilita' dice «c'e'» mentre
il modello non si carica~~ — **falso, era il mio righello.**
 Non è un difetto
di giudizio né una promessa non mantenuta: è **un controllo che mente**, e ha nascosto la causa
a chi (io) lo interrogava per capire. ⇒ **Chi ragiona su «il giudice è disponibile?» non usi
`local_ce_available()` come prova**: usa il messaggio della ricevuta, che è onesto.

📌 **Cosa resta non isolato**, dichiarato: escluse con la misura ① corpo di `remember_cmd`
identico · ② firma di `add` identica · ③ cablaggio del client identico · ④ condizione `_have_judge`
identica riga per riga · ⑤ suo **valore** True in entrambe · ⑥ l'ipotesi «è l'etichetta `surface`»
(**morta**: `flow_events.py:213` la legge da `ENGRAM_FLOW_SURFACE`, è telemetria e non governa
niente). **La domanda residua è una sola**: cosa, a valle di `_have_judge`, impedisce l'aggancio
del punteggio.
