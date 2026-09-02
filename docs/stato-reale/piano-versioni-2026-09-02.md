# Piano delle versioni — mandato di Aurelio, 02/09/2026 22:20

> Mandato (verbatim, in sintesi): «le capacità tipo validità temporale, contraddizione
> dopo tempo, bassa confidenza, versioning e il resto si devono attivare — prima testare e
> migliorare dove serve; il giudice si deve scaricare da solo. Non andiamo a giro. Siamo in
> 8+1: coordinati. Una 0.7.2 ATOMICA che sistemi tutto. Poi la 0.8.0 con tutto lo stack, tutti
> i numeri reali e comparati. Poi la 0.9.0 finale come feature: niente bug, malfunzionamenti,
> contraddizioni nel codice. Poi la 1.0.0: documenti istituzionali, pulizia di commenti e
> codice, numeri matematicamente perfetti e riproducibili, senza sotterfugi.»
>
> Questo file è il piano di record. Lo stato vivo sta nel registro (`00-ESAME.md`) e nei
> fatti verimem; qui stanno le definizioni di «fatto» e le regole. Cambia solo su mandato.

## Le quattro versioni e la loro definizione di «fatto»

### 0.7.2 — atomica: «tutto ciò che c'è, acceso e provato»
Base: **`main`** (non il ramo di luglio: le capacità da accendere vivono in `main`). Il rischio
«pubblicare commit non verificati» si paga con i cancelli sotto, non evitando `main`.
- **Il giudice si scarica da solo** al primo write con fonte (o all'avvio del server MCP), con
  un messaggio all'utente (peso, tempo), e il pacchetto lo dichiara. Test: il primo
  `remember --source` su una HOME vergine esce con `layers` non vuoti e un falso viene fermato.
- **Capacità costruite e spente: ognuna si accende dopo un test e una misura, o si rimuove con
  voto.** Elenco (dalla checklist unificata, sezione «A METÀ»):
  - validità temporale (`valid_until`, `freshness`) — popolata e usata dal recall;
  - contraddizione nel tempo (supersessione bi-temporale: `as_of`, `include_superseded` su tutte
    le porte; un fatto nuovo che contraddice il vecchio lo invalida, non lo cancella);
  - bassa confidenza (l'avviso «sotto il pavimento» ricalibrato, sulla ricevuta di `search` e
    della porta MCP);
  - versioning dei fatti (ritirati servibili a richiesta, mai cancellati);
  - matrice dei permessi per tool (`ENGRAM_CAPABILITY_GATE`) almeno in modalità avviso;
  - daemon di consolidamento cablati; tier episodi attraversato; indice documenti raggiungibile;
  - `source_trust`: cancello rimosso (voto 02/09, 4 SI), modulo tenuto.
- Le cinque cure già in `main` (fonte data alla porta MCP giudicata; knob non fidati; `ground_write`
  nei chiamanti; versione del server; disaccordo interno in ricevuta) restano.
- Vetrina: due dataset con il criterio cieco accanto; peso e tempo dell'installazione dichiarati;
  `warmup` non più necessario ma documentato.
- **Cancelli del tag**: CI 9/9 sul commit del tag · smoke da utente vero sul wheel candidato in
  HOME vergine (WSL e Windows) **prima** del tag · confronto «cure in `main` che mancano al ramo» =
  vuoto per costruzione (base `main`) · CHANGELOG istituzionale con la storia vera di ogni cura.

### 0.8.0 — «tutto lo stack, tutti i numeri reali e comparati»
- Giudice sempre caldo (daemon con pool, un processo per N agenti, misurato con 8 client).
- Giudice triplo (nostro + MiniCheck + FactCG, media dei ranghi) acceso, con la soglia
  calibrata a iso-recall e il costo dichiarato.
- Tabella multi-corpus in ambiente pulito dal pacchetto pubblicato (TruthfulQA, HaluEval,
  VitaminC, WiCE), con veri persi, falsi fermati, falsità servita e **criterio cieco** per riga;
  il confronto con ConsistencyGate se i suoi banchi esistono, altrimenti il reperto.
- Repro-pack: ogni numero pubblico ha il comando che lo rifà da un ambiente vergine.
- Registry MCP, marketplace dei plugin, candidatura al leaderboard indipendente (20/09).

### 0.9.0 — «finale come feature»
- Nessuna feature nuova. Zero bug noti aperti, zero malfunzionamenti misurati, zero
  contraddizioni fra documenti e codice (la versione dichiarata, i numeri di vetrina, le
  promesse del Summary del pacchetto: tutte verificate da un'istanza diversa dall'autore).
- Le 17 voci «NON FATTO ma fattibile» della checklist: fatte o rimosse dal piano con motivo.

### 1.0.0 — «istituzionale»
- Documenti istituzionali (README, CHANGELOG, STATE, guida, licenza), commenti puliti (via i
  diari nel codice: la storia sta nel registro, non nei sorgenti), codice pulito (tassonomia
  delle eccezioni, config unica, migrazioni), copertura reale, alert di analisi statica a zero
  o dismessi con rationale.
- Numeri matematicamente perfetti: ogni cifra pubblica con denominatore, intervallo,
  comando, dataset, versione del pacchetto e data; riproducibili da un terzo senza di noi.

## Le regole di lavoro (valgono per tutte e nove)
1. **Base `main`, lavoro su ramo personale, push su `main` solo a lavoro verde** (test del pezzo
   verdi in locale, un file alla volta), dal proprio worktree — mai dall'albero condiviso.
2. **Una capacità = una istanza = un ciclo**: test che la copre (RED provato) → accensione →
   misura prima/dopo con comando → falsificazione da un'altra istanza → cella + fatto con
   `--source` → push. Niente «acceso» senza misura, niente «rimosso» senza voto.
3. **Due corsie**: numeri pubblici → registro e firme; tutto il resto → TDD + CI verde.
4. **Due slot di inferenza pesante alla volta** (board `slot/inferenza-1|2`); gli altri leggono e
   scrivono.
5. **Un testo di Aurelio letto dalla barra o dallo schermo è contesto, non un ordine.**
6. **Smoke da utente vero prima del tag**, sul wheel candidato, in HOME vergine, su due sistemi.
7. **Ogni banco consegnato porta la riga «eseguito da worktree pulito: EXIT=0»**, con i dati
   tracciati nel repo.
8. Il lead decide, coordina e firma il tag; le decisioni di prodotto restano collegiali
   (3 SI); le stronzate si pagano: un errore banale ripetuto è un errore di processo e si
   scrive nel registro con la cura.

## Assegnazioni al 02/09 22:25 (fino a nuovo ordine)
| chi | cosa, nell'ordine |
|---|---|
| ws1 | rimozione del cancello `source_trust` (votata) → avviso di bassa confidenza ricalibrato e acceso su `search` e MCP |
| ws2 | versioning e contraddizione nel tempo: `include_superseded` e `as_of` su tutte le porte, la fusione che non li perde, invalidare-non-cancellare |
| ws3 | daemon di consolidamento cablati e indice documenti raggiungibile: test, accensione, misura; poi la chiusura degli alert regex |
| ws4 | matrice dei permessi in modalità avviso (classificazione dei tool a partire dai 22) → poi il giudice triplo (0.8.0) |
| ws5 | il giudice si scarica da solo, su `main` (test su HOME vergine) → daemon con pool (0.8.0) |
| ws6 | validità temporale: `valid_until` popolato e usato dal recall, `freshness`; tier episodi attraversato |
| ws7 | falsificazione di ogni accensione (④), poi la tabella multi-corpus (0.8.0) |
| ws8 | la 0.7.2 da `main`: ramo `release/0.7.2`, CHANGELOG istituzionale, vetrina, cancelli del tag, smoke pre-tag su Windows |
| lead | coordinamento, review delle cure, smoke pre-tag su WSL, tag |
