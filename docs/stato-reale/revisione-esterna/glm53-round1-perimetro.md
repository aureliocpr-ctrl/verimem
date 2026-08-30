1. **La prova e lo strumento di prova coincidono: il "moat" è dimostrato dal giudice che il report stesso dichiara rotto.**
(a) «Il moat (giudice source⊢fact) è acceso e copre: 98,8%…» contro, 40 righe sotto: «Il giudice è bimodale e cieco all'attribuzione… Sotto i 21 caratteri dà 100 a un claim E al suo contrario».
(b) Errore di categoria epistemico: la sezione 1 usa come metro lo strumento che la sezione 2 dichiara incapace di graduare, cieco all'attribuzione e contraddittorio. Se il giudice assegna 100 sia a un claim sia al suo negato, i tassi della sezione 1 (98,8%, 99,7%) non misurano correttezza: misurano quanto spesso il giudice si accende. Nessuna validazione del giudice contro un gold set etichettato da umani indipendenti. La struttura (DIFENDIBILE prima, DIFETTOSO dopo) impedisce al lettore di vedere che il difetto invalida la difesa.
(c) Chiederei: un gold set di almeno 200 casi etichettati da annotatori esterni al team, con accordo inter-annotatore, e il tasso del giudice su quel set.

2. **"Il prodotto lo fa" non contiene nessuna misura di utilità per l'utente finale (l'agente).**
(a) «## 1. DIFENDIBILE — il prodotto lo fa, e lo dimostra».
(b) Ogni voce della sezione 1 è una proprietà interna (il giudice copre, lo span allega la prova, il decadimento "funziona"). La domanda che un auditor fa per prima — *l'agente con questo layer completa task meglio, più veridicamente, più a buon mercato di un agente senza?* — non compare da nessuna parte. Il report confonde "il meccanismo scatta" con "il prodotto funziona". L'ammissione arriva solo in fondo: «tutte le verifiche sono interne… il registro dimostra di reggere noi, non lui (W2-72)» — dopo aver già raccomandato una release.
(c) Chiederei: un esperimento controllato agente-con-layer vs agente-senza-layer su task standard, con metrica di esito, non di meccanica.

3. **La falsificabilità promessa dalla struttura non è esercitabile da chi legge.**
(a) «Questo report è falsificabile per costruzione: ogni riga cita la cella o il commit, e le celle portano il comando per rifare la misura» e, nello stesso documento: «misura di ws4 nel canale, msg b60e4a22 — cella non ancora scritta, e il numero va letto lì».
(b) Celle W2-123, commit, canale "verimem-coord": per un lettore esterno sono indirizzi irraggiungibili, non prove. Peggio: un dato citato in DIFETTOSO vive solo in un messaggio di chat effimero, in aperta violazione della regola di redazione dichiarata in apertura. Se una regola enunciata come vincolo cade una volta nel documento stesso, ogni altra citazione va trattata come non verificata.
(c) Chiederei: dump pubblico del registro, repo in sola lettura, e la trascrizione del msg b60e4a22 in cella con comando ripetibile.

4. **Il titolo promette "lo stato vero" mentre lo stato del claim centrale è dichiaratamente sconosciuto, e la release viene raccomandata comunque.**
(a) «Il claim centrale (C2) regge solo in parte… Va rimisurato su HEAD con le due cure dentro (assegnato)» accanto a «raccomandazione **C adesso** (0.7.1…)» e a «design di provenienza da decidere nella specifica (**non urgente**, dichiarato)» per un bug che spegne L1 sul «65,1% sui fatti VIVI».
(b) Un report di stato che raccomanda il publish mentre (i) il claim di difesa principale non è stato rimisurato sull'albero attuale e (ii) un difetto noto tocca due terzi dei fatti vivi, non descrive uno stato: descrive una scommessa. Classificare "non urgente" un difetto al 65% di copertura è una decisione di categoria mascherata da priorità.
(c) Chiederei: la rimisurazione C2 su HEAD come prerequisito bloccante alla raccomandazione di versione, e la motivazione quantitativa del "non urgente".

5. **Doppio standard metodologico: le regole della sezione 3 non sono applicate alla sezione 1.**
(a) «Ogni tasso SENZA popolazione, ogni verde CI SENZA età, ogni benchmark SENZA seed» contro «corretto nel merito 17/20», «3/3 con popolazione appaiata», «Rafforzamento fermato 8/8», «24 di quei fatti letti nel merito».
(b) Il report insegna agli altri (sezione "DA NON SCRIVERE") che i numeri senza seed e con popolazioni minuscole sono frasi da smontare, poi fonda la propria sezione dimostrativa su n=3, n=8, n=20, n=24 senza intervalli di confidenza né seed dichiarati. Con n=20, "99,7%" e "17/20" sono aneddoti con decimali.
(c) Chiederei: per ogni tasso della sezione 1 — popolazione totale, criterio di campionamento, seed, ripetizioni, intervallo di confidenza.

6. **Zero valutazione avversariale per un prodotto la cui funzione dichiarata è fermare iniezioni e avvelenamento della memoria.**
(a) «Lo screen delle iniezioni ferma E spiega» e «Rafforzamento fermato 8/8».
(b) Otto e tre casi progettati dagli stessi costruttori non sono una misura di sicurezza: sono esercizi. La domanda prima di qualunque auditor su un memory layer per agenti è il tasso di bypass sotto perturbazioni non viste dal designer (parafrasi, omoglifi, mixing IT/EN — peraltro il report ammette che l'italiano è meno protetto). La struttura del report non ha nessuna sezione "sicurezza", e la sua assenza non si nota perché il tono la copre.
(c) Chiederei: una attack suite redatta da terzi indipendenti, con tasso di evasione per classe di attacco e per lingua.

7. **Nessun contratto di prodotto: tre porte non equivalenti, metriche omonime, performance note solo per aneddoti.**
(a) «Le porte non sono equivalenti (scacchiera)… `recall` ha due significati… una scrittura CON source non risponde entro 190s contro 28,9s in-process».
(b) Se CLI, SDK e MCP restituiscono cose diverse e "recall" significa due cose, la domanda "che prodotto è stato consegnato?" non ha risposta: non esiste una superficie contrattuale normativa. E le performance compaiono solo come anomalie (190s, 141×): mancano p50/p95 del read path, throughput, costo per operazione, comportamento alla crescita del corpus. Un auditor chiede gli SLO prima dei moat.
(c) Chiederei: matrice di parità fra porte con test di conformance automatici, e un profilo di latenza/costo su corpus a tre ordini di grandezza diversi.

8. **La sezione "IL PROCESSO" sostituisce la verifica del prodotto con l'auto-certificazione del metodo, e la struttura la mette dopo le decisioni.**
(a) «~50 autocorrezioni dichiarate in 24 ore, zero smentite incrociate… è il sensore che funziona».
(b) "Zero smentite incrociate" è affermazione non falsificabile (chi conta le smentite? con quale soglia?) e comunque irrilevante al funzionamento: misura il team, non il prodotto. Collocare l'ammissione del limite («un lettore ESTERNO non c'è ancora stato») *dopo* la sezione DECISIONI fa sì che le raccomandazioni appaiano poggiate su evidenza che il documento stesso, in chiusura, squalifica come interna. È l'esatto meccanismo che il report dice di combattere: una superficie ordinata che nasconde dove non si è guardato.
(c) Chiederei: la revisione esterna indipendente eseguita *prima* delle decisioni 1–6, con le decisioni rietichettate come provvisorie fino ad allora.