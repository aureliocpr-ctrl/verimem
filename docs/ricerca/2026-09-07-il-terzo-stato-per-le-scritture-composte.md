# Il terzo stato per le scritture composte — proposta con i numeri (07/09)

*ws3 Galileo. Per la decisione del lead sull'innesto della decomposizione
(pezzi 3a/3b/3c, revertati il 06/09 alle 08:42). Nessuna riga di prodotto qui:
è un design, con i numeri misurati che lo motivano e le predizioni da
falsificare prima di scriverlo.*

## Cosa sappiamo, con i banchi

| misura | numero | banco |
|---|---|---|
| Una scrittura «vero **e** falso» con la fonte del vero, giudicata intera, viene AMMESSA | **30/30** su testo nuovo (07/09), 115/200 fermate sul corpus con la coda «ed è verificata» | `ws3-banco-NON-cieco-30-composte-10-controlli-tre-bracci.py`, muro1-fase2 |
| La decomposizione isola la coda falsa | 25/30 (morfologia + regola -ed), 146/200 sul corpus | idem |
| Il giudice, sulla coda isolata (soglie del prodotto: 40 / 80) | quarantena **13**, review **4**, ammessa **8** su 25 | output 2, 12:33 |
| Costo dell'innesto sui veri composti già ammessi (P-A, 800 campionati) | **99–103/800 = 12,4–12,9 %** cambiano verdetto; di questi 14 solo per la regola -ed (curata), il resto è il giudice sui claim brevi | controlli 1–5 |
| Fra i 102 claim caduti letti uno per uno | **68 provati alla lettera** dallo span, 15 malformati/contraddetti, **19 con la prova fuori dalla finestra conservata** (M6) | `ws3-i-102-claim-caduti-etichettati-a-mano.json` |
| Un giudice migliore (interpolato, Nadia) recupera i claim brevi caduti | **1/31 = 3,2 %** sui veri (2/39 = 5,1 % contando un frammento malformato) | Nadia, 07/09 13:34 |

Tre fatti seguono da questa tabella:

1. **Il muro 1 è reale e totale**: la coda falsa entra sulle spalle della testa
   vera in ogni caso misurato fuori dal corpus. Senza decomposizione l'utente
   non ha difesa.
2. **La decomposizione da sola non basta e costa**: isola la coda in 25/30 ma
   il giudice ammette 8 code false su 25 e, sul corpus, cambia il verdetto di
   un fatto vero su otto — quasi sempre perché il pezzo breve, provato alla
   lettera, prende 0–30 dal cross-encoder.
3. **Il difetto non è nel pezzo, è nel verdetto binario**: oggi l'intero
   decomposto eredita il MIN dei claim (pezzo 3b), quindi un claim caduto
   quarantina l'intera scrittura — anche la testa vera, provata.

## La proposta: il verdetto a tre stati sui claim

Quando la scrittura è decomposta in N ≥ 2 claim:

| intero (con la fonte) | claim peggiore | verdetto della scrittura | cosa vede l'utente |
|---|---|---|---|
| ≥ 80 | tutti ≥ 80 | **ammessa** | come oggi |
| ≥ 80 | uno in [40, 80) | **review**, col claim nominato | `held for review: claim 2 «…» 63,0` |
| ≥ 80 | uno < 40 | **review**, col claim nominato — NON quarantena | `held for review: claim 2 «…» 0,7 — the whole scores 96,0` |
| < 80 | qualunque | come oggi (review o quarantena dell'intero) | come oggi |

Il terzo stato esiste già nel prodotto per il giudice locale (la banda
`[tau_lo, tau_hi)`, `L4-review`): qui lo si usa per la **discordanza fra
l'intero e un suo pezzo**, che è un'informazione nuova e non un punteggio in
banda. La ricevuta porta già `claims_verdict` (pezzo 3c, «le porte dicono
quale claim»).

Perché review e non quarantena quando un claim cade e l'intero passa: il
banco dice che quel caso è, in **68 su 102**, un pezzo vero provato alla
lettera che il giudice non legge (M5), e in 19 un pezzo la cui prova sta fuori
dalla finestra conservata (M6). Quarantinare è sbagliato sette volte su otto;
ammettere lascia passare le 13 code false che oggi si fermano. Review tiene le
due cose insieme: la coda falsa non entra come vero, il fatto vero non sparisce,
e la ricevuta dice **quale** pezzo va guardato.

## Cosa cambia sui due banchi, predetto prima di scriverlo

| | oggi (intero) | decomposizione + MIN (3b) | decomposizione + terzo stato |
|---|---|---|---|
| 30 composte nuove: code false AMMESSE | 30 | 8 (+5 fuse) = 13 | 8 (+5 fuse) = 13 |
| 30 composte nuove: teste vere PERSE (quarantinate) | 0 | 13 (la quarantena del pezzo tira giù l'intero) | **0** (review, non quarantena) |
| P-A, 800 veri composti ammessi: cambiano verdetto | 0 | 99–103 | 99–103, **ma in review con il claim nominato, non quarantinati** |
| 96 «crolli»: fatti veri che spariscono dal recall di default | 0 | 96 | **0** (review resta servito? → dipende dalla porta: da decidere) |

Predizioni falsificabili (da misurare sul tip dell'innesto con il terzo stato,
prima di qualunque push):

- **P-T1** sulle 30 composte nuove: 0 teste vere quarantinate, 17 scritture in
  review (13 + 4), 13 ammesse con la coda dentro (8 + 5 fuse). Muore se una
  testa vera finisce in quarantena.
- **P-T2** su P-A: gli stessi 99–103 record cambiano verdetto, tutti verso
  review, 0 verso quarantena. Muore se anche uno va in quarantena.
- **P-T3** i 19 S (prova fuori dalla finestra) restano in review anche con il
  MAX sull'intero (5b5350ce): nessuna frase li prova. Muore se il MAX li
  riporta sopra 80.

## Cosa NON risolve, dichiarato

- Le **8 code false ammesse** (giudice a 86–99 su claim plausibili): è M5, e
  la cura di Nadia non le toglie (1/31 sui veri). Restano il lavoro del giudice, non
  della decomposizione.
- Le **5 code fuse** (verbo + preposizione/aggettivo, «riesce a», «sembra
  pieno»): limite dichiarato della regola morfologica.
- Il **recall**: se la review non viene servita di default, i fatti in review
  sono invisibili come i quarantinati. La scelta «review servito con l'etichetta»
  contro «review trattenuto» è del lead ed è la variabile che decide il costo
  reale del terzo stato.

## Costo di scrittura

Pezzo 3b (`anti_confab_gate.py`, blocco `_decomposed … len(_claims) > 1`): il
MIN diventa una regola a tre esiti; `claims_verdict[i]` porta già `score` e
`via`; la ricevuta aggiunge `held_for` = indice del claim. Cella RED prima:
le 30 composte nuove con la fonte, attese P-T1. Nessun altro file.
