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

## 2. DIFETTOSO — misurato, riproducibile, con la cura nominata
- **La famiglia L1 decide con le parole, e sbaglia nei due versi.** Le facce
  misurate del buco (convergenti da banchi indipendenti): l'auto-eco comprava
  il perdono (5/5, curato da `275648c0` — guardia in attesa 2ª firma); la
  riformulazione senza trigger passa (banco D `ef234ae0`, resta per la cura
  grande); la polisemia perdona ciò che non deve (W7-61); l'etichetta
  `writer_role='user'` scritta da `verimem save` sulle parole dell'AGENTE
  spegne L1 sul 59,5% del corpus totale (b13a9f32) — 65,1% sui fatti VIVI
  (8822/13561, W7-69): due denominatori, entrambi dichiarati. MA la lettura
  ha due facce (W7-70/71): 24 di quei fatti letti nel merito sono 11
  resoconti e 13 misure, ZERO self-claim nudi — e senza l'eccezione L1 ne
  declasserebbe 21 su 24 A TORTO: l'eccezione è anche COMPENSAZIONE, non
  solo buco (dossier 26). Il
  carve-out non si attivava sui verbali scritti con `e'` invece di `è`:
  `_VERB_MARK` non riconosceva la forma ASCII, il soggetto risultava «non
  risolvibile» e il classificatore falliva prima di guardare il dominio
  (W7-72, che corregge W7-60). Curato in `51eb3022` con doppia firma: 132
  fatti passano a DOMAIN, 0 lo perdono, 0 in prima persona; alla porta
  l'esito cambia in 1 caso su 24 (W7-74) — cura piccola, effetto misurato
  minimo.
- **Il claim centrale (C2) regge solo in parte**: sulla tabella 8 classi ×
  2 lingue le difese scendono a 4/16 quando le celle verdi vengono ALLARGATE
  (firma ws7 su a252adac). Va rimisurato su HEAD con le due cure dentro
  (assegnato). L'italiano è meno protetto dell'inglese (elenco radici
  IT-only per costruzione — lacuna di copertura, distinta da quella di
  architettura, per decisione ratificata).
- **Il giudice è bimodale e cieco all'attribuzione**: decide, non gradua
  (0 valori intermedi su 18 a supporto eroso; 91,8% dei verdetti agli
  estremi, W2-131); dà ~100 a scambi di soggetto in campo vicino (curva
  f466e983: eco 81,4 / solo-soggetto 0,2 / campo-lontano 14,7) e la banda
  40–80 si riempie di rumore posizionale, non di incertezza (misura di ws4
  nel canale, msg b60e4a22 — cella non ancora scritta, e il numero va letto
  lì);
  il ramo review quando è percorso costa 141× e fallisce muto (W7-56).
  Sotto i 21 caratteri dà 100 a un claim E al suo contrario (ws5, 30/08).
- **Il disaccordo interno non è consegnato**: `withheld_despite_judge` esiste,
  è derivato e presidiato, ma vive nel journal — 323 write (2,6% delle
  scritture; 21,4% dei GIUDICATI del corpus) dove giudice e layer hanno detto
  l'opposto e il chiamante non lo vede; `adjudication` mostra margine +59,97
  accanto a «quarantined» senza nominare chi ha ribaltato (F3 al voto).
- **Le porte non sono equivalenti (scacchiera)**: `trattenuti` manca sulla
  CLI; `recall` ha due significati; MCP rispondeva `[]` in silenzio dove SDK
  trovava (avviso ora dichiarato, `5219443a`); su MCP-stdio una scrittura CON
  source non risponde entro 190s contro 28,9s in-process (ws5 — C3/latenza).
- **La CI si satura da sola**: nel picco ~1 run/min in ingresso contro ~2,6/h
  in uscita (16:1), 92,2% dei run da commit solo-docs, nessun filtro path;
  e il verdetto CI descrive un albero di centinaia di commit fa — un verde
  vecchio non è un verde sul presente (regola: si cita con l'età).

## 3. DA NON SCRIVERE — frasi vere a metà che un lettore ostile smonta
- *«Il gate ferma i fatti veri sulle fonti lunghe»* → falso in generale: ferma
  il vero RIFORMULATO (W2-62/64).
- *«I layer lessicali scavalcano il giudice in 323 casi»* → vero come
  conteggio, falso come accusa: sul documento tecnico il layer SALVA il
  giudice (W2-54 corretta da W7-13). La frase giusta: «in 323 write i due
  hanno dato verdetti opposti; il campo che lo registra non arriva a nessuno —
  il difetto è la consegna, non il disaccordo».
- *«Accendere GRADED_ADMISSION non costa nulla»* → falso: la negazione entra
  (W2-69); e curerebbe la faccia sbagliata (i trattenuti-col-giudice-a-favore
  recenti sono di L4.1, non del moat — ws7 30/08).
- *«Il gate rumoreggia su N fatti»* → quel N non esiste: il journal non
  registra gli avvisi sugli ammessi (W2-51).
- Ogni tasso SENZA popolazione, ogni verde CI SENZA età, ogni benchmark SENZA
  seed: il 70%-vs-0,6% divenne 12,5% su prosa vera; il 60/60 è 58–60/60 su 20
  seed; il verdetto CI di oggi descrive un albero di ieri.

## 4. DECISIONI PER AURELIO (le tecniche sono già collegiali; queste toccano
   prodotto/vetrina/release)
1. **Versione** — quadro completo in `quadro-decisione-versione-30-08.md`:
   raccomandazione **C adesso** (0.7.1 = v0.7.0 + sola riga pin), 0.8.0 a
   contratto chiuso; D scartata; prerequisiti di publish comunque (W8-4,
   veto-wheel, smoke).
2. **Bande in vetrina/doctor** — descrivono un ramo riempito dal rumore e
   muto quando percorso: o si toglie la promessa o si ricostruisce
   l'escalation sul DISACCORDO fra segnali (direzione già votata e4d12f25).
3. **Asimmetria di lingua** — decisione di prodotto ratificata come «da
   dichiarare»: la vetrina dica che la protezione lessicale IT/EN non è
   simmetrica finché la cura grande non pareggia.
4. **Etichetta `writer_role='user'` da `verimem save`** — le parole
   dell'agente marcate come parole dell'utente spengono L1 sul 59,5% del
   corpus totale (65,1% dei fatti vivi, W7-69 — ma su un campione letto nel
   merito L1 sbaglierebbe 21/24: l'eccezione compensa, W7-70/71): design di provenienza da decidere nella specifica (non urgente,
   dichiarato).
5. **Namespace `verimem_*`** — il flip del default cura 1 superficie su 3
   (voto ws7): le altre due a registro; incoerenza di marca visibile
   all'utente nuovo.
6. **MCP-stdio 190s** — la porta headline non risponde su scrittura-con-source
   entro 190s (in-process 28,9s): C3/latenza, priorità alta post-cura-grande.

## 5. IL PROCESSO — perché a questo report si può credere
- **~50 autocorrezioni dichiarate in 24 ore, zero smentite incrociate**: ogni
  errore trovato è stato trovato dall'autore o da un banco, mai nascosto
  (campioni contati: 9-su-9 di ws7 alle 02:00, 5-su-5 di ws1, 14/71 celle di
  ws2 con la correzione DENTRO la cella; poi 37+ righelli dichiarati da ws2 da
  sola). Il tasso non è vergogna: è il sensore che funziona.
- **Le regole sono nate da errori misurati, non da principi**: regola-verde v3
  (un EXIT senza riepilogo pytest è la firma di come è morto il processo — il
  PC spento del 29/08 l'ha insegnato); la firma va SCRITTA sulla cella (195/331
  invisibili finché ws7 non l'ha contato); le popolazioni si confrontano
  APPAIATE (il 3/5→5/5 di ws3); il pre-commit linta lo STAGED (la copia
  condivisa bloccava tutte); un finding «nuovo» porta la riga «memoria
  interrogata con:» (l'attribuzione del tag ripetuta più volte perché la
  lezione stava sul canale effimero); lo SHA si cita dopo il push (i rebase
  l'hanno riscritto due volte); un'assenza si dimostra solo enumerando dove
  si è guardato (la tesi principale di F3 corretta così).
- **Il registro (330+ celle) tiene le correzioni dentro le celle sbagliate**,
  per costruzione: un lettore ostile vede gli errori accanto ai numeri, non
  una superficie ripulita.
- **Limite dichiarato del processo**: tutte le verifiche sono interne; un
  lettore ESTERNO non c'è ancora stato, e il registro dimostra di reggere
  noi, non lui (W2-72). Il comparativo C10 su dataset pubblici è il primo
  passo per cambiarlo.

**Chiusura.** Questo report è falsificabile per costruzione: ogni riga cita la
cella o il commit, e le celle portano il comando per rifare la misura. Chi
trova una riga che non regge la corregga DENTRO il registro — è così che è
stato scritto tutto il resto.
