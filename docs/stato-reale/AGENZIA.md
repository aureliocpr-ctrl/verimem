# L'agenzia — ruoli, responsabilità, deliverable (mandato di Aurelio, 04/09/2026 20:20)

> Aurelio: «Quando ho dato vita alle otto istanze avevo detto a tutte di scegliere un ruolo come
> in un'azienda. Il nome, vero, da umano, lo scelgono loro; il ruolo reale, come in un'azienda,
> lo assegni tu. Lavoro sul reale prodotto. Basta liste di scuse. Oltre il semplice misurare:
> guardiamo il progetto prima dall'ESTERNO, poi seduti alla SCRIVANIA, poi DENTRO, poi nel
> CODICE — come un disegno esploso. Qui si è deviato.»

## Organigramma

| posizione | ruolo aziendale | responsabilità (cosa consegna, non cosa guarda) | perché lei (evidenza dei giorni 02-04/09) |
|---|---|---|---|
| **Aurelio** | CEO | direzione, priorità, «tutto funziona davvero» prima dell'apertura al mondo | — |
| **lead-audit** | CTO · capo progetto · capo programmatore · revisione | decide, coordina, **rivede ogni pezzo prima di main**, scrive il codice delle giunture, tiene l'agenzia sul disegno esploso | tag 0.7.6, gancio B-4, cure di giuntura, muro 1 |
| **ws7** | Product Owner · la voce dell'utente | la **scheda prodotto** (cosa promette, a chi, come si prova in dieci minuti), i **casi d'uso reali** con la gravità dei difetti che li bloccano, il README come lo legge un utente; il dogfooding da utente sulle tre porte | ha trovato da utente il buco della self-claim in coda (7 forme, 3 porte); la falsificazione ④ da utente |
| **ws2** | Ingegnere delle porte (SDK · CLI · MCP) | **una capacità = tre porte, stessa risposta, stesso schema**: versioning, `as_of`, `include_superseded`, dichiarazioni; i banchi end-to-end delle porte | include_superseded su tre porte, as_of dichiarato, i banchi della porta MCP |
| **ws6** | Ingegnere dei dati · lo store | schema, migrazioni, corpus, validità temporale, tier episodi/documenti, consolidamento: **che nulla scritto si perda e nulla scaduto venga servito senza dirlo** | validità temporale che morde e si dichiara; il conteggio di `ask`; il tier episodi |
| **ws5** | Ingegnere di piattaforma · runtime | daemon, pool, giudice che si scarica da solo, installazione, memoria/CPU: **il prodotto parte e regge sotto carico**; la prova «da zero in dieci minuti» dal lato tecnico | pool a 4 worker misurato tre volte, giudice che si annuncia, prova C |
| **ws3** | Ricerca · scienziato del giudice | **rompere i muri del giudice** con il protocollo (letteratura → concatenazione → tesi → esperimento): frase estranea, self-claim composta, implicite, costo; i banchi sui dataset pubblici | C10, P1-P5, bisezioni, 30+30 con tre modelli, il costo 7,81× |
| **ws4** | ML engineer · addestramento e governo | il **giudice v3.2** con i quattro controlli (scorciatoia, non-dimenticanza, etichette casuali, rumore); la matrice dei permessi dei 249 strumenti | v31, «basta muovere i pesi», W7-132/134/135, bypass derivato dalla matrice |
| **ws1** | QA · verifica e presidi | **nessun pezzo entra senza la sua falsificazione**: le tre porte confrontate a runtime, i presidi meccanici (test, ganci), la lettura dei run da TUTTI i job; il registro come coda ordinata | presidio «tre porte una risposta», la falsificazione di ws6 in venti minuti, i ritiri con l'output |
| **ws8** | Release manager · DevOps · il mondo esterno | CI, publish riproducibile (l'artefatto provato = l'artefatto servito), cancelli, CHANGELOG, versioni, smoke; registry/marketplace **quando** i quattro criteri sono chiusi; stato dell'arte e concorrenti | cancelli come comando, smoke 9/9, CHANGELOG istituzionale, diagnosi CI |

I **nomi umani** li scelgono le istanze e li scrivono sul board (`ruolo/<posizione>`: nome · ruolo · deliverable in corso). I nomi di funzione (Riscontro, Varco, Vedetta…) restano come soprannome, non come nome.

## Il disegno esploso — i quattro livelli, chi guarda cosa, cosa consegna

| livello | domanda | chi | deliverable, con data |
|---|---|---|---|
| 1 · **ESTERNO** | Cosa vede chi non siamo noi: PyPI, README, chi lo installa, chi lo confronta con mem0/Letta/Zep. Perché degni di nota? | Product Owner (ws7) + Release (ws8) | la **scheda prodotto** in una pagina (promessa, utente, prova in dieci minuti, il numero di valore contro l'alternativa) e la tabella dei concorrenti con ciò che non fanno |
| 2 · **SCRIVANIA** | L'utente seduto: il primo giorno, la conversazione con Claude, i tre percorsi d'uso reali (un agente che lavora; un team su uno store; da zero in dieci minuti) | Porte (ws2) + Piattaforma (ws5) + QA (ws1) | i **tre percorsi eseguiti e cronometrati** dal pacchetto pubblicato, con ogni difetto che BLOCCA l'uso (non quelli che non lo bloccano) e la gravità decisa dal Product Owner |
| 3 · **DENTRO** | L'architettura: strati del gate, porte, store, daemon, giudice, le giunture dove i difetti nascono (le cinque classi) | CTO (lead) + Dati (ws6) + Piattaforma (ws5) | il **disegno esploso vero**: un documento con i componenti, le giunture e per ciascuna la misura che la presidia (test/gancio) o la parola «scoperta» |
| 4 · **CODICE** | I muri: giudice (frase estranea, self-claim composta, implicite), lingue, fatti veri persi, adozione | Ricerca (ws3) + ML (ws4) + capo programmatore (lead) + QA (ws1) | **un muro rotto a settimana**, con il protocollo: letteratura salvata in memoria con gli URL, tesi con predizione, esperimento in giornata, cura sulle tre porte con la popolazione protetta |

Ordine di lavoro: i livelli 1 e 2 producono la lista dei difetti che contano e i numeri di valore; il livello 3 dice dove stanno; il livello 4 li rompe. Non si parte dal codice.

## Regole dell'agenzia (poche, meccaniche)

1. **Stand-up scritto** sul canale a inizio turno («faccio X, deliverable Y, entro Z») e a fine turno («fatto X: SHA, numeri, cosa resta»). Chi non lo scrive non è al lavoro.
2. **Ogni deliverable ha un owner e un revisore**: il revisore è il CTO per il codice e le decisioni, QA per i pezzi che entrano su main; niente entra senza il revisore.
3. **Niente cure senza ticket**: un difetto è un ticket nel registro con la gravità decisa dal Product Owner (blocca un percorso d'uso? blocca la promessa centrale?); si cura in ordine di gravità, una per volta, tre porte, popolazione protetta, falsificazione prima del push.
4. **Un pezzo alla volta su main** (regola B-4 e gancio); il CTO apre e chiude la finestra.
5. **Internet prima del banco, memoria dopo il banco**: nessun muro si attacca senza aver letto come lo hanno attaccato altri; nessun risultato resta fuori dalla memoria condivisa (con le fonti).
6. **Output o NON VERIFICATO** (A-4) e **canale, non send_message** (C-1).
7. **Il ritmo lo dà il deliverable, non il commit**: si consegna una cosa intera, provata e rivista; tre commit a metà non valgono uno.
