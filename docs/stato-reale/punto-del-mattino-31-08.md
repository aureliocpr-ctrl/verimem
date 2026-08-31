# Punto del mattino — la notte 30→31/08 in una pagina
> Composto da lead-audit alle 05:15 (v1; rifinitura con gli ultimi bilanci
> entro le 07:00). Ogni numero cita la fonte; il dettaglio vive nel canale
> (verimem-coord), nel registro (00-ESAME.md, **652 celle alle 05:35**) e nei
> commit.
>
> *(ws7: il «568 celle» della v1 non era sbagliato — era **vecchio di tre ore**:
> il registro ne aveva 556 alle 02:00 e 580 alle 03:00, quindi quel numero vale
> per le ~02:25. Sostituito col conteggio delle 05:35 **e con l'ora**, perché è
> una grandezza che cresce mentre la si scrive. Righello dichiarato:
> `python scripts/conta_celle_esame.py` — righe che cominciano con `| ID |` e
> hanno almeno dieci colonne separate su una barra non preceduta da backslash;
> esclude le 93 intestazioni di tabella, che lo stesso schema matcherebbe.)*

## Il titolo della notte
**Il treno 0.7.1 è pronto sul binario, col cancello.** Da ieri sera «pubblicare»
è passato da progetto a bottone: branch `hotfix/0.7.1` su origin (v0.7.0 +
pin `mcp<2` + due stringhe runtime ripulite + i 4 file di infrastruttura di
rilascio che il branch NON aveva — il suo publish.yml era del 4 luglio, con un
cancello su cinque). Wheel costruito e verificato SULL'ARTEFATTO: veto
identificativi EXIT=0, smoke da venv vergine EXIT=0 (`mcp 1.29.1` risolto —
il crash dell'utente nuovo è curato). **Mancano solo: il run `ci` verde sul
branch (primo run della sua storia, in coda da ~4h30) e il TUO tag+publish.**

## Cancelli mossi (chi, cosa)
1. **CANCELLO-A votata (3 SI) ed eseguita** — il gate del publish accettava
   solo `main`: ora accetta anche `hotfix/**` (fail-closed intatto, scappatoia
   spenta, stampa cosa accetta) e `ci` gira sui rami hotfix. Main `3d4d18b5`,
   branch `53ec00c7`. I numeri della diagnosi sono di ws8 (CI mai partita sul
   branch: total_count=0; run di main che SCADONO a 24h esatte — la coda non è
   lenta, scade).
2. **C10 CHIUSO con barre d'errore** (ws7 + 2ª firma lead su n=600): di ciò
   che verimem serve è falso il **15,9%** contro il **50,0%** dello stesso
   corpus senza gate; veri persi 29,3% [24,5–34,7]; replica su campione
   disgiunto 16,0%. È l'unico numero con ground truth umana esterna — nel
   report è dichiarato come l'unica riga il cui metro non è il giudice stesso.
3. **Il primo lettore esterno è arrivato** (GLM-5.3, mandato tuo): 24 finding
   sul report, 8 già convertiti in correzioni — fra cui una firma dichiarata
   e mai scritta (ora data per davvero: LANT-105) e i numeri di copertina
   riscritti con denominatori e caveat (98,8%→98,1% rimisurato, corpus intero
   59,6% dichiarato accanto).
4. **F3-① eseguita sulle due porte** (ws2): la ricevuta ora dice
   `withheld_despite_judge` quando un layer trattiene col giudice a favore;
   il fix `agito` (la porta MCP nominava `gate` invece del layer) ha due
   firme (LANT-108 lead + ws3) e da stanotte un SENSORE provato nei due
   versi (ws3: stessa funzione con/senza il parametro, A/B in una sola
   esecuzione). Sul campo in ricevuta il test esiste ma è condizionato da
   uno skip di regime (formulazione di ws2: «c'è, non incondizionato») —
   ultima rifinitura possibile, dichiarata, non un buco.
5. **CURA-PAVIMENTO ratificata in blocco** (5 pezzi, 3+ SI ciascuno): il floor
   degenere 0.0 serviva avvisi rotti su tre cause in AND. L'evento naturale
   delle 02:52 (ricalcolo automatico: floor 0.0→0.8781) è stato catturato con
   QUATTRO predizioni registrate prima — e una (P4: «la prima recall
   costerà >20s») è CADUTA con onore: 18,44s misurati. Le altre tre rette,
   tutto in pubblico. La (ii) è ESEGUITA e in main (`eaa464dc`, verificata alla
   porta vera sul corpus); le altre in corso (ws3/ws6).
6. **Cure minori col processo pieno**: pre-commit staged-only (il file a metà
   di una non blocca più le altre — 50143a1a + .gitattributes 691ede4e),
   stop-list bilingue W7-100 (ws4, A/B appaiato su 459 episodi), porta-layer
   `2c85984f`.

## I numeri per l'analista ostile (li abbiamo trovati noi prima di lui)
- **Il criterio «verde = due firme» è oggi soddisfatto sul 5% delle celle**
  (30/568; censimento ws2 delle 04:35). Lettura giusta: misure mai riviste,
  non falsità — ma se il contratto promette due firme, questo è il primo
  numero che un esterno troverebbe. Campagna controfirme avviata (raddoppia
  con 2-a-testa) e proposta di criterio per te: due firme ESIGIBILI sulle
  celle load-bearing (citate da report/vetrina/quadro), il resto dichiarato.
- **~1 fatto vivo su 5 non ripasserebbe la porta di oggi** (W7-89, 18,4%
  medio) — il livello dell'acqua sul corpus vero, stesso ordine del 29,3% del
  benchmark. E l'attribuzione «è il moat che butta i veri» era una lettura
  del solo campo — l'aritmetica vera (ws4, W7-93/95): **5/88 li boccia solo
  il moat, 15/88 solo un layer, 68/88 ENTRAMBI** ⇒ nessuna cura di un lato
  libera la coda (solo-layer ne libera il 17%, solo-moat il 5,7%): i 68
  doppi esigono la coppia.
- **Il flip `GRADED_ADMISSION` è veleno misurato** (ws7): falsi ammessi da
  13,3% a 98,7% — il «33% di veri salvati» del codice costava 3,1× in falsi.
  Chiuso: non si accende.
- **11 interruttori DEFAULT OFF e nessuno acceso** (censimento ws2) + le
  capacità implementate-e-spente di ws6: la classe «il prodotto sa fare la
  cosa e non la fa» è ora censita.
- **~20% delle celle porta una correzione dell'autrice** (censimento con
  auto-inclusione corretta): il numero non misura quanto si sbaglia — misura
  quanto si verifica dopo aver scritto.
- **L'86% di avvisi sul traffico reale non è rumore del misuratore** (ws6,
  doc 61): il punteggio SEPARA senza sovrapposizioni (22 letture attese
  ≥0,8645 contro 10 fuori-dominio ≤0,8474) ⇒ quel tasso dice che le nostre
  letture spesso non trovano ciò che cercano — priorità di prodotto, non
  bug dell'avviso.
- **Vetrina** (ws7, 5 numeri ricontati): il primo è A FAVORE — il README
  pubblicato dichiara i propri default (11 env censite, zero capacità
  nascoste, LANT-127); il Summary del pacchetto fa 4 promesse e 3 reggono
  (la quarta è a registro col suo numero).

## Decisioni che aspettano TE (in ordine di leva)
1. **Tag v0.7.1 e publish** — quando il run del branch è verde: tutto il
   resto è pronto (quadro: `quadro-decisione-versione-30-08.md`, forma C′).
2. **Criterio firme** — la proposta load-bearing qui sopra.
3. **Proposta-B paths-ignore** (ws8): filtra i run doc-only dalla CI di main
   (1514 run risparmiati nel banco) — matura, va al voto oggi.
4. **La riga O3 del protocollo** — «spezza» senza «su source distinte» attiva
   la supersessione fra i pezzi (banco ws2 a 5 bracci: la causa è il NUMERO
   nei pezzi): una riga da aggiornare in CLAUDE.md, testo pronto.

## Rischi e aperti, senza trucco
- Il run `ci` del branch è in coda da ~4h30 (la coda di main scade i run a
  24h: se scade anche lui, si riprovoca con dispatch — la via è dichiarata).
- La «cura grande» L1 non è iniziata (resta il piano dopo il contratto).
- C3/latenza MCP-stdio e C2-difese (4/16, tre regimi concordi) restano i due
  C aperti più pesanti.
- ws5 e ws8 hanno prompt di permesso che di notte nessuno approva (tue parole)
  — tenute attive come da ordine, da valutare oggi.

## Il processo, in una riga
~10 ore, otto istanze più il lead: 4 voti collegiali ratificati (F3-①,
FIRMA-AB, CANCELLO-A, CURA-PAVIMENTO + W7-100), zero veti scavalcati, ogni
cura col suo RED→GREEN, le correzioni dentro le celle — e il lettore esterno
che ci ha corretto è stato incorporato, non archiviato.
