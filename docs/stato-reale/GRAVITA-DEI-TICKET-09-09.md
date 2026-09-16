# La gravità dei ticket, per l'utente — Product Owner (09/09, sera)

> Chiesto dal coordinamento: *«la gravità di ogni ticket (blocca un percorso d'uso?
> blocca la promessa centrale?)»*. Questo file è un **giudizio di prodotto**, non
> una misura: dice quale difetto fa più male all'utente, non quale è più difficile
> da curare. Chi non è d'accordo ha il criterio scritto sotto e può ribaltarlo con
> un argomento, non con un'opinione.
>
> ⚠️ **Nota di lettura (12/09)**: i nomi delle persone-agente sono stati sostituiti
> dai ruoli. I **percorsi di file e i nomi dei rami restano com'erano**: sono
> riferimenti a oggetti reali, e cambiarli nel testo li scollegherebbe senza
> anonimizzarli. Se quegli oggetti vanno rinominati, è un lavoro a sé.

## 0. Che cosa ho misurato io stasera e che cosa cito

Il resto di questo documento distingue le due cose riga per riga, perché mescolarle
è il modo più comodo per farsi dare ragione da numeri di altri.

**Misurato da me adesso** — il banco è `docs/stato-reale/banchi/ws7-porte-e-etichetta.py`,
`EXIT=0`, controllo positivo a due facce acceso (`briefing.py` visto, nome inventato
rifiutato). ⚠️ Sono conteggi di **righe di sorgente** con un criterio dichiarato, non
misure di comportamento: il banco lo stampa da sé in fondo, invece di lasciarlo credere.

| fatto | comando | esito |
|---|---|---|
| `hide_low_trust` esiste in 4 punti di `verimem/`: la firma, il suo uso, un commento, **una sola chiamata che lo passa** (`briefing.py:136`) | `grep -rn "hide_low_trust" verimem/ --include=*.py` | 4 righe |
| le chiamate a `list_facts` nel prodotto | `grep -rn "list_facts(" verimem/ --include=*.py \| grep -v "def list_facts"` | **38** |
| di cui in `mcp_server.py` | stesso grep, raggruppato per file | **31** |
| le 2 di `client.py` stanno a 3550 e 3962, **non** dentro `search` (1217) | `grep -n "list_facts(" verimem/client.py` | 2 righe |
| `verimem/oracle.py` è 147 righe; `status` vi compare **una volta** (riga 104, per saltare le *skill* `retired`); `grounding` e `quarantin` **zero volte** | `grep -n "status\|grounding\|quarantin" verimem/oracle.py` | 1 riga |

**Citato dai rapporti degli altri ruoli e dal resoconto della mappa**, con l'autore: i
numeri di T-MAP-11 (Ricerca), 1.403 quarantenati e 5.675 fatti fuori dal tetto
(Porte e Piattaforma), i 303 s (Piattaforma), 22 comandi su 88 (mio, misurato l'08/09),
il 21 % (righello di Dati), 127/177 (contratto). **Non li ho rimisurati stasera.**

## 1. Il criterio — tre domande, e la terza è mia

Il coordinamento ne ha date due. Ne aggiungo una terza, perché con due sole si ordina male.

1. **Blocca un percorso d'uso?** L'utente prova a fare una cosa e non gli riesce.
2. **Blocca la promessa centrale?** Il prodotto dice il falso su ciò che *lo
   definisce*: «un fatto fermato dal moat non torna come verità».
3. **L'utente se ne accorge da solo?** — la aggiungo io. A parità di danno, un
   difetto **silenzioso** è più grave di uno **rumoroso**: il rumoroso lo scopri
   e lo aggiri, il silenzioso te lo porti in casa e ci costruisci sopra.
   T31 (`exit 2` in faccia) e T-MAP-9 (0 righe su 18.092, in silenzio) sono
   tutti e due «non funziona», e non hanno la stessa gravità.

E un ordinatore che viene prima delle tre, quando si tratta di scegliere fra due P0:

> **Un difetto che SCRIVE batte un difetto che LEGGE.**
> Curare domani una porta che legge male ripara tutte le letture future. Curare
> domani una porta che ha scritto male non toglie dallo store ciò che è entrato
> oggi. La lettura si cura con una patch; la scrittura lascia residui.

## 2. La scala

| | significato |
|---|---|
| **P0** | il prodotto dice il falso su ciò che lo definisce, e l'utente non ha modo di accorgersene |
| **P1** | l'utente perde qualcosa di vero, o lo paga caro, ma può accorgersene o rimediare |
| **P2** | una promessa scritta non ha una porta o non ha un presidio: nessun danno oggi, falsità sì |
| **P3** | non ripara niente per l'utente: impedisce che peggiori (cricchetti, righelli) |

## 3. La tabella

| # | ticket | owner | 1. percorso | 2. promessa | 3. se ne accorge | **gravità** |
|---|---|---|---|---|---|---|
| 1 | **T-MAP-11** l'ingest ammette 3 invenzioni su 3 | Ricerca | non lo blocca: lo **avvelena** | **sì, è LA promessa** | **no** (poi `search` le serve) | **P0** |
| 2 | **T49** 7 tool MCP + `Memory.get_all` servono i quarantenati | Porte | no | **sì** | **no** — verificato: `oracle.py` non porta lo `status` | **P0** |
| 3 | **T50** `compute_trust_signal` dice `trusted` a 4 status che non lo sono | ML | no | **sì** | **no, e peggio: la difesa mente** | **P0** |
| 4 | **T26a/a** il server delegate-only non giudica, **in silenzio** | Piattaforma | no | **sì** (una scrittura non giudicata venduta per verificata) | **no** | **P0** |
| 5 | **T53** l'iniezione proattiva non porta status né verdetto | ML | no | sì, di riflesso | no | **P0 basso** |
| 6 | **tetto 10.000 + supersede**: 21 % scritti e mai serviti | Dati | **sì**: scrive e non riceve | in parte | **no** (il tetto non avvisa) | **P1 alto** ⚠️ vedi §4 |
| 7 | **T51** `update` ritira il vecchio anche se il gate boccia il nuovo | in coda | no | sì | in parte (la maniglia è nella ricevuta) | **P1** — ma è **perdita di dati** |
| 8 | **T26a/b** primo `remember` con fonte: 303 s contro 3,7 s | Piattaforma | **sì, ed è il PRIMO contatto** | no | **sì**, rumoroso | **P1** |
| 9 | **T31** il Quickstart insegna `verimem health --tools` → `exit 2` | Product Owner | sì, alla prima riga che si copia | no | **sì** | **P1 per posizione**, P2 per danno |
| 10 | **T54** le sonde attive del README non hanno nessuna porta | in coda | no (non riceve una cosa promessa) | no | no | **P2**, ed è il caso limite dei 57 |
| 11 | **i 57 claim senza presidio** | Product Owner | no | **dipende dal claim** (§5) | no | **P2**, con dentro dei P0 |
| 12 | **R5 `porte_provate.py`**: 22 comandi su 88 senza test | QA | no | no | — | **P2 abilitatore** (§4) |
| 13 | **R2/R3/R6 righello e cricchetti in CI** | Release | no | no | — | **P3, ma presto** (§4) |

## 4. Le cinque righe che non si leggono dalla tabella

**① T-MAP-11 prima di T49, e non è una preferenza.** Sono tutti e due P0 e T49 è più
esteso (otto ingressi, 1.403 fatti sul DB di casa). Ma T49 **legge** male e
T-MAP-11 **scrive** male. La cura di T49, il giorno che entra, ripara ogni lettura
futura *e anche quelle passate*, perché i fatti sono ancora etichettati nello store.
La cura di T-MAP-11 non toglie dallo store «il capannone 12 è stato venduto nel
2019»: quello resta, ed è già servito da `search`. Ogni ora che T-MAP-11 resta
aperto aggiunge righe che nessuna patch futura ripulisce.

**② T50 è il meno esteso dei tre P0 e il più insidioso, e va detto a ML.**
T49 lascia l'utente **senza difesa**; T50 gli dà una difesa **che mente**. Chi
filtra per `trusted` sta facendo la cosa giusta, e proprio per questo si porta in
casa il quarantenato con più fiducia di chi non ha filtrato niente. Un difetto che
punisce chi si è comportato bene merita di stare in cima anche quando i numeri sono
più piccoli.

**③ Il tetto di Dati: P1 per danno, prima fila per contratto — e dichiaro la
tensione invece di nasconderla.** Un utente che non riceve un fatto vero fa una
domanda in più; un utente che riceve un fatto falso agisce sbagliato. Per me il
silenzio costa meno della bugia, quindi P1. **Ma** il 21 % è una delle tre misure
del contratto del rilascio, cioè una priorità **già fissata dalla direzione**: non la
declasso io con una tabella. Sta in prima fila per decisione presa, con la mia
gravità dichiarata accanto. Chi legge sa che le due cose non coincidono.

**④ QA e io stiamo guardando la stessa popolazione da due lati — proposta di
confine.** I 22 comandi senza test (suoi) e i 57 claim senza presidio (miei) si
sovrappongono: sei dei 22 sono comandi che il README insegna. Proposta, così non
facciamo due volte lo stesso lavoro: **il comando lo prende QA** (la porta esiste,
manca il test: `porte_provate.py` lo scopre e lo esegue), **la promessa la prendo
io** (il claim del README che nessuna porta mantiene, o che nessun test tiene
fermo). Dove si toccano — un comando insegnato dal README e mai invocato — il test
lo scrive QA e io ci lego la riga del README. Se preferisce il taglio opposto va
bene lo stesso: quello che non va bene è scoprirlo alla terza PR.

**⑤ Il cricchetto di Release è P3 e va fatto presto lo stesso**, e le due cose non
si contraddicono: non ripara niente per l'utente, ma **se arriva dopo le cure non
le ha misurate**. Sette ruoli stanno per cambiare codice; il righello che conta
le copie e le funzioni senza riga deve essere in CI *prima*, o il suo tetto nasce
già gonfiato dal lavoro di stanotte.

## 5. Il pezzo del mio ticket che dipende da questa tabella

I 57 claim non hanno una gravità sola. La ripartizione in tre famiglie decide che
cosa vuol dire «curato»:

- **numeri di banco** (misure con data e regime: 85,7 s, 0.87 recall@5, 15,9 %):
  un test non li ri-misura, e pretenderlo sarebbe un errore di categoria. Il presidio
  giusto lega il numero *scritto nel README* al file *già committato* in
  `benchmark/results/` — costa zero alla CI ed esiste già in casa per una tabella
  sola (`tests/test_il_readme_e_la_cli_dicono_lo_stesso_peso.py`, cinque test fra cui
  `test_il_numero_vecchio_non_e_tornato`);
- **promesse di comportamento** («imports nothing until you pass `--ids`», «falls
  back … fail-soft», «deletion by subject does not exist anywhere»): qui il bianco
  è un buco vero, e qui va il RED alla porta. **È da questa famiglia che esce
  l'ordine di gravità**, ed è quella su cui lavoro stanotte;
- **debito già dichiarato dal README stesso** (i due caveat sull'ANN, «sull'SDK non
  abbiamo una risposta stabile»): qui il bianco è **la forma giusta**. Un limite
  scritto con precisione dice dove guardare; riempirlo con l'ipotesi plausibile
  chiude la domanda. Questi non si «curano»: si lasciano, e si controlla che siano
  ancora veri alla lettera.

E la prima gravità che fisso è contro di me: **`README:348-353`** — la tabella per
porta che ho scritto io l'08/09, entrata su main con `5ac8d9f1`, **senza presidio**.
È la forma che ho denunciato tutto il giorno, applicata alla riga che ho aggiunto io.
Sta nella lista col suo numero, come le altre.
