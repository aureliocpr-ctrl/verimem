# Contratto del prossimo rilascio: completo e funzionante

Aurelio, 08/09/2026 20:18, testuale: «il prossimo rilascio lo vorrei davvero
completo e funzionante, non come la versione attuale pubblicata come buona e
rotta pure questa». Questo file è la definizione di «completo»: **nessun tag
finché ogni riga qui sotto è verde con l'output del comando nello stesso
messaggio, e poi il sì esplicito di Aurelio.** Le cure entrano in main tutti i
giorni dalla finestra di push; il tag aspetta la tabella.

## Le tre misure che dicono se verimem è vera ed è una memoria

| # | misura | righello | oggi (data) | verde se |
|---|---|---|---|---|
| 1 | fatti scritti e mai serviti dal recall | `scripts/quanti_fatti_sono_davvero_serviti.py <data_dir>` sullo store vivo | 21% (02/09: scritti 17070, serviti 13454) | ≤ 2% |
| 2 | fatti VERI composti di terzi che il gate quarantena | banco P-A (177 composte vere) + banco cieco di ws1 (20 vere non provate, 10 pulite, 10 false); le 10 false restano FERMATE | 127 su 177 (08/09) | ≤ 10 su 177, e 10 false su 10 fermate |
| 3 | scritture con fonte entrate senza giudizio dalla porta MCP | cella (e): server MCP, daemon fermo con le due gambe verificate, 3 giri; più il conteggio nello store dei fatti con fonte e `grounding_score` nullo scritti dopo la cura | tutte, senza daemon (96 nello store al 08/09) | 3 giri su 3 giudicati, 0 nuovi non giudicati |

Ogni misura si scrive PRIMA della cura e DOPO, con lo stesso righello, e la
ricevuta va nel CHANGELOG con i due numeri.

## I difetti noti (T24…T41)

Ognuno **chiuso** (cura in main, RED/GREEN, perimetro) **oppure accettato da
Aurelio per nome** e scritto nel CHANGELOG col numero che lo misura e l'owner.
Nessuna riga «Not solved yet» senza numero e owner. La lista viva e gli owner
stanno in `GRAVITA-DIFETTI.md`.

## La prova da utente

- Installazione nuova dal wheel del sha finale su **windows** e su **wsl**:
  smoke 11 passi su 11 sui due bracci, **stessa impronta sha256**, registro in
  `SMOKE-PRE-TAG.md`.
- Le sei superfici (CLI, MCP, SDK, `doctor`, `warmup`, README) esercitate da
  chi **non** le ha scritte, con i comandi e l'output nel post: la prima
  scrittura con fonte viene giudicata, un claim smentito viene fermato, il
  recall al passato risponde col passato, su ogni porta.
- Requisito di memoria scritto nel README col numero misurato (oggi: muore in
  silenzio con 1,6 GB liberi, funziona da 7,7; la soglia esatta è T39).

## La CI

Tre run verdi sul sha finale: `ci`, `security`, `presidi-lenti`, chiesti con
`workflow_dispatch` (un push di soli documenti non fa partire la matrice).

## Cosa NON è nel contratto

I numeri del pannello, le opzioni della CLI, i test a cronometro, la vetrina:
entrano solo se una delle tre misure lo richiede. Una riga sbagliata in un
documento non fa un candidato: si corregge nella finestra del giorno dopo.
