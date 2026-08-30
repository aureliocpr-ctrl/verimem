# REPORT — lo stato vero del prodotto (30/08 sera)
> Scritto da lead-audit per Aurelio e per chiunque apra il repo domani.
> Regola di redazione: ogni affermazione cita la cella/commit che la sostiene;
> nessun «funziona» senza EXIT= col riepilogo; ogni tasso porta popolazione e
> regime. Le correzioni della giornata sono INCORPORATE (non le versioni
> iniziali dei reperti). Struttura: DIFENDIBILE · DIFETTOSO · DA-NON-SCRIVERE ·
> DECISIONI PER AURELIO · IL PROCESSO. Fonte-quadro: sintesi W2-71 (corretta da
> W2-78) + registro 00-ESAME.md (330+ celle) + canale verimem-coord 28-30/08.

## 1. DIFENDIBILE — il prodotto lo fa, e lo dimostra
- **Il moat (giudice source⊢fact) è acceso e copre**: 98,8% dei fatti recenti
  giudicati (agosto, banco `la-copertura-del-giudizio-nel-tempo.py`, 3 firme);
  senza fonte dichiara `grounding_score=null` e la promessa dei campi regge
  3/3 con popolazione appaiata — un agente distingue «giudicato / fonte
  non giudicata / fonte assente» leggendo SOLO campi (`grounding_score` +
  `L4-skipped`): il prodotto sbaglia la propria promessa PER DIFETTO.
- **`grounding_span` allega la prova del passaggio al 99,7%** dei giudicati
  degli ultimi sei giorni (W2-123) ed è corretto nel merito 17/20 con i casi
  limite decisi bene 3/3 (W2-124).
- **Il read path dichiara ciò che nasconde**: `trattenuti {quanti, perché,
  non-persi}` su SDK e MCP (W2-75/76) — un motore che dice quanti risultati ha
  censurato e perché è una rarità. (CLI: assente — vedi difetti.)
- **Lo screen delle iniezioni ferma E spiega** (come l'ha letto, l'ipotesi che
  potrebbe essere sbagliata, la leva per correggere — W2-69): è il modello
  comunicativo che il resto delle superfici deve raggiungere.
- **Il decadimento** funziona e nessuno l'aveva mai guardato (W2-118).
- **Rafforzamento fermato 8/8**: «la fonte dice almeno 300» → claim «500» è
  SEMPRE preso (banco `ws3-la-promessa-ammesso-solo-se-la-fonte-lo-supporta`).
- **Il gate ha corretto NOI a ragione** più volte in diretta (ws2 3/3 sui
  propri fatti, ws4 su un numero con la source vecchia, ws8 su un A/B):
  il dogfooding punisce chi sbaglia, incluso chi lo costruisce.
- **Due cure sono entrate col processo pieno** (proposta → voti informati →
  ratifica → RED→GREEN falsificato → firma): L1.20-ad-avviso (`5ea77b6d`,
  verde-2-firme, costo 1/70 a verbale) e guardia anti-eco (`275648c0`).
