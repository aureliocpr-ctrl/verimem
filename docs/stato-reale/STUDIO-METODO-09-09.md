# Studio del metodo — come dovrebbe andare, come sta andando, come procediamo (lead, 09/09/2026, 16:10)

> Mandato di Aurelio (09/09, dopo la chiusura della mappa): «prima di partire facciamo uno studio reale:
> le cose come dovrebbero andare? come stanno andando? come decidiamo di procedere secondo i migliori
> standard dei più grandi studi di sviluppo. Facciamo anche una ricerca online: l'online è un coltello
> a doppia lama». E: «quale set di regole possiamo inserire o modificare per il corretto lavoro?
> potrebbe aiutarci in futuro o no?»
>
> I numeri sul nostro stato vengono da `RESOCONTO-MAPPA-09-09.md` (commit `0d7555a6`, ramo
> `lead/mappa-indice`), dove ogni numero ha il comando accanto. Le fonti esterne sono state LETTE oggi
> (§1, con URL); ciò che viene dalla memoria del modello e non da una pagina letta è marcato
> **NON VERIFICATO**.

## 0. La risposta corta alla domanda sulle regole

**Aggiungere regole scritte aiuta poco. Trasformare le regole in controlli meccanici aiuta molto.**
Non è un'opinione, è misurato su di noi:

| misura | dove |
|---|---|
| O1 (memoria prima) rispettata in 1 sessione su 18 | `CLAUDE.md`, misura del 24/07 |
| A2: tre dichiarazioni del lead senza comando in un'ora, tre smentite in 20 minuti | `CLAUDE.md`, 03/09 |
| 11 difetti nel righello contro 5 nel prodotto, in una mattinata | memoria `lezioni-metodo-17-08`, ws4 |
| «la regola era già scritta e l'avevo riletta quella mattina»: ciò che ha fermato l'errore è stato un controllo nello script | stessa memoria, 17/08 |
| otto istanze hanno risposto alla stessa domanda in dieci minuti; tre su otto hanno rifatto la stessa indagine sulla CI | memoria, 18/08 e 03/09 |
| il lead: due richiami ieri, quattro errori contati oggi, con le regole in testa | cronache 08/09 e 09/09 |

Regole che abbiamo già, contate oggi sui file letti: circa 33 in `CLAUDE.md` (A1-A6, O1-O8, B1-B6, M1-M5,
i gate), 7 nell'agenzia (`AGENZIA.md`), quattro famiglie con righello nel piano-versioni, più di 40
file di feedback in memoria. La regola M4 dice già la conclusione: «dopo uno sbaglio, prima cerca la
lezione che esisteva già: quasi sempre era applicazione mancata, non regola mancante».

Quindi: **sì, può aiutarci in futuro, a una condizione**: ogni regola nuova nasce con il suo controllo
(uno script, un job di CI, un template) che può fallire da solo, senza che nessuno se la ricordi. Le
regole senza controllo si potano. La proposta concreta è in §3.

## 1. Come dovrebbero andare le cose — le fonti primarie, lette oggi

| pratica | fonte (letta oggi) | cosa dice, testuale | da noi significa |
|---|---|---|---|
| **Modifiche piccole** | Google, eng-practices, *Small CLs* — https://google.github.io/eng-practices/review/developer/small-cls.html | «one self-contained change»; «100 lines» come misura ragionevole, «1000 lines is usually too large»; le cancellazioni contano come una riga; il revisore può respingere un cambiamento troppo grande | un ticket = un ramo = una PR piccola; le cure «a quattro punti» si spezzano |
| **Lo standard della revisione** | Google, *The Standard of Code Review* — https://google.github.io/eng-practices/review/reviewer/standard.html | «Reviewers should favor approving a CL once it is in a state where it definitely improves the overall code health of the system being worked on, even if the CL isn't perfect» | il revisore (≠ autore) approva ciò che migliora la salute del sistema; le rifiniture sono «Nit:», non blocchi |
| **Revisione con policy** | Microsoft, *Engineering Fundamentals Checklist* — https://microsoft.github.io/code-with-engineering-playbook/engineering-fundamentals-checklist/ | «A minimum number of reviewers (usually 2) for a PR merge is enforced by policy»; linter, analizzatori, unit test e build verdi obbligatori; «Main branch is always shippable»; CI «on each PR» | D-1 (lead o 3 SÌ) è già questo; manca che la CI lo imponga |
| **Test alla taglia giusta** | *Software Engineering at Google*, cap. 11 — https://abseil.io/resources/swe-book/html/ch11.html | taglie small (un processo, niente I/O) / medium (una macchina, localhost) / large; mix consigliato «80% … narrow-scoped unit tests», «15% medium-scoped integration tests», «5% end-to-end tests»; flakiness Google «0.15%», «as you approach 1% flakiness, the tests begin to lose value»; «Beyoncé Rule: If you liked it, then you shoulda put a test on it» | i test piccoli li abbiamo; mancano i medi e i grandi ALLE PORTE (CLI, MCP, SDK): è lì che il prodotto fallisce |
| **Il codice non usato costa** | *Software Engineering at Google*, cap. 15 *Deprecation* — https://abseil.io/resources/swe-book/html/ch15.html | «Code is a liability, not an asset»; «Without explicit owners, a deprecation process is unlikely to make meaningful progress»; deprecazione *advisory* (senza scadenza) contro *compulsory* (con scadenza e chi aiuta a migrare) | i 19 moduli senza chiamante hanno bisogno di un owner e di una scadenza: cablati con una porta, o spostati fuori dal pacchetto pubblicato |
| **Postmortem senza colpe** | Google SRE book, *Postmortem Culture* — https://sre.google/sre-book/postmortem-culture/ | trigger: «user-visible downtime or degradation beyond a certain threshold», «data loss of any kind», «on-call engineer intervention», «resolution time above some threshold», «monitoring failure»; blameless = «identifying the contributing causes of the incident without indicting any individual or team»; contenuto: incidente, impatto, azioni, cause radice, follow-up | ogni rosso su main, ogni revert, ogni perdita di dati (il 21 %), ogni misura che mancava, ha un postmortem di sei righe con un controllo aggiunto |
| **Osservabilità e design** | Microsoft, stessa checklist | «Log application faults and errors»; design reviews «documented with alternatives»; le storie linkano il design | niente `except: pass`; ogni decisione architetturale in una pagina con le alternative (i 19 moduli, versionare/ritirare, una politica di schema) |
| **Misure di consegna** | DORA, *Four keys* — https://dora.dev/guides/dora-metrics-four-keys/ | cinque metriche: «change lead time», «deployment frequency», «failed deployment recovery time», «change fail rate», «deployment rework rate». **La pagina letta non pubblica soglie** (elite/high/…): le soglie che circolano sono NON VERIFICATE qui | le nostre tre misure del contratto restano le prime; a queste si aggiungono rossi su main, tempo al verde, revert, tag |
| **La lama: Goodhart** | ricerca web (fonti secondarie, alcune di venditori di cruscotti): https://www.infoq.com/articles/dora-metrics-anti-patterns · https://dora.dev/guides/dora-metrics/ · https://zbmowrey.com/blog/dora-metrics-what-the-research-actually-says/ | «when a measure becomes a target, it ceases to be a good measure»; si gioca spezzando PR per gonfiare la frequenza e non dichiarando i piccoli incidenti; DORA stessa avverte (2023) e chiede metriche in tensione fra loro, lette per team e come trend, mai per confrontare persone | il righello che sbaglia a favore di chi lo usa (memoria 06/09) è la stessa cosa: ogni misura nostra ha accanto la misura che la contraddice (velocità ↔ rossi; funzioni provate ↔ porte provate) |

Ciò che NON ho letto oggi e cito dalla memoria del modello, quindi NON VERIFICATO: le «Power of Ten»
della NASA/JPL (asserzioni, controllare ogni valore di ritorno), lo studio di Sadowski et al. 2018
sulla revisione a Google, la «rule of three» sulle copie. Non li uso per decidere.

## 2. Come stanno andando — noi, misurati contro le stesse pratiche

Tutti i numeri dal `RESOCONTO-MAPPA-09-09.md` e dalle cronache (memoria), con il posto dove sta il comando.

| pratica | il nostro stato | dove |
|---|---|---|
| Modifiche piccole | 190 commit in un giorno nella storia recente; cure «a quattro punti» (T26a) consegnate non provate; la coesistenza fra fonti revertita perché rompeva 4 test | cronache 06/09 e 08/09 |
| Revisione | D-1 esiste (lead o 3 SÌ) ed è rispettata alle finestre; ma nessuna CI la impone e nessun template la rende meccanica | AGENZIA.md regola 2 |
| Test alla taglia giusta | 1453 funzioni fanno ciò che promettono e la CI è verde; **22 comandi CLI su 88 mai invocati**, i 6 comandi del self-host mai eseguiti, 7 tool MCP + l'SDK servono i quarantenati (T49): i test provano le funzioni, non le porte | RESOCONTO §2, §3 |
| Flakiness | ci windows rossa l'08/09 su un test del breaker a orologio con zero file di prodotto cambiati | cronaca 08/09 (T38) |
| Codice non usato | **19 moduli interi senza chiamante**, 172 funzioni mai chiamate, 853 righe di «memoria senza database» pubblicate e mai toccate da un utente; nessun owner, nessuna scadenza | RESOCONTO §3, mappe `holographic_memory.md` e `resonator_memory.md` |
| Copie invece della superficie unica | `_jaccard` ×18, `_tokens` ×20, 5 stoplist, filtro degli status in 4 posti, `_signature` ×3, quattro politiche di schema in otto store; la cura di T49 esisteva dal 20 luglio in 1 chiamante su 37 | RESOCONTO §3 |
| Silenzio | tetto 10.000 fatti scansionati e 5.675 mai visti senza avviso; 30 chiamanti di `list_facts` muti; mesh a 384 contro 768 → 0 righe su 18.092 senza errore (T-MAP-9); `converged=True` su 0 risposte giuste su 10 (T-MAP-10); l'ingest ammette 3 invenzioni su 3 (T-MAP-11) | RESOCONTO §2, mappa `conversation_ingest.md` |
| Postmortem | le cronache raccontano i rossi, e «classifica il rosso prima di spiegarlo» è in memoria; ma nessun formato fisso, nessun elenco dei controlli aggiunti per ogni rosso o revert | memoria |
| Main sempre rilasciabile | primo main verde 9/9 il 03/09 dopo il 25/08: **nove giorni di rosso**; ultimo tag 0.7.6 (04/09); la 0.7.7 mai taggata | MEMORY.md, cronache |
| Documentazione | 57 claim del README senza presidio; sei docstring che dicono cosa credeva l'autore; LIMITS.md non puntato dal README; 1025 righe della mappa NON MISURATE | RESOCONTO §2, §3 |
| Misure di consegna | tre misure del contratto tutte rosse (21 % mai serviti → ≤ 2 %; 127/177 composte → ≤ 10; T26a); rossi su main, tempo al verde, revert: **non contati da nessuno** | RESOCONTO §4 |

La lettura in una riga: **sui test delle funzioni e sulla CI siamo al livello delle fonti; su tutto ciò
che sta fra la funzione e l'utente (porte, codice morto, copie, silenzio, postmortem, misure di
consegna) non siamo mai stati misurati, e la mappa è la prima misura.**

E il pezzo che le fonti non coprono: sono scritte per squadre di persone che restano. Qui l'autore
cambia a ogni sessione e a ogni modello (da Opus 4.6 a Fable 5.1). Le pratiche di Google contano su
persone che ricordano; noi possiamo contare solo su ciò che sta nel repo e fallisce da solo: i test
alle porte, il righello della mappa, i controlli in CI. **Per noi «regola» e «controllo in CI» devono
essere la stessa cosa, o la regola muore al prossimo compact.**

## 3. Le regole proposte — otto, ognuna con il suo controllo (decisione di Aurelio)

| # | regola | controllo che può fallire da solo | owner | stato del controllo |
|---|---|---|---|---|
| **R1 Definition of Done** | un ticket è chiuso solo con: RED alla porta (output nel ticket) → GREEN → riga della mappa aggiornata → claim del README collegato o tolto → docstring con data e comando → revisore ≠ autore → fatto salvato con source → CI verde sul tip → zero copie nuove | template della PR con le nove caselle + `scripts/mappa_completa.py --mancanti 0` in CI + `scripts/dod.py` (le caselle meccaniche) | lead (righello), ws1 (gate) | righello esiste; template e `dod.py` da scrivere |
| **R2 Aggiunta zero senza porta** | nessuna funzione nuova senza un chiamante raggiungibile da CLI/MCP/SDK e senza la sua riga nella mappa nello stesso commit; nessun modulo nuovo finché i 19 non hanno un verdetto | il righello in CI fallisce sulla def senza riga; `scripts/senza_chiamante.py` stampa i moduli senza import dal prodotto con tetto = 19 e fallisce se sale (cricchetto) | lead, ws8 (CI) | da scrivere |
| **R3 Una superficie per primitiva** | le copie non crescono e scendono: `_jaccard`, `_tokens`, stoplist, filtro status, `_signature`, politica di schema | `scripts/copie.py` conta i nomi ripetuti per file, tetto = i numeri di oggi (18/20/5/4/3), fallisce se uno sale | lead | da scrivere |
| **R4 Nessun silenzio** | vietati `except: pass` e i ripieghi muti nel prodotto; ogni tetto e ogni ripiego scrive nel journal o nel payload di risposta | ruff `E722` + `BLE001` sul pacchetto; cricchetto sul conteggio di `except … pass` (numero di oggi da misurare al primo giro) | ws2 (porte), ws6 (dati) | da misurare |
| **R5 La prova al livello della porta** | ogni comando CLI, ogni tool MCP, ogni claim del README ha un test che lo invoca dalla porta (subprocess / `_call_tool_impl` / import pubblico), non dalla funzione | `scripts/porte_provate.py`: lista dei comandi dal parser contro i test che li invocano; fallisce sul comando senza test (oggi 22 su 88) | ws2, ws1, ws7 (claim) | da scrivere |
| **R6 Piccolo e rivisto** | un ticket = un ramo = una PR ≤ 300 righe di prodotto, una cosa sola, revisore ≠ autore; oltre si spezza (le cancellazioni non contano) | job di CI che stampa le righe cambiate e boccia > 300 salvo etichetta `lotto-grande` data dal lead | ws8 | da scrivere |
| **R7 Postmortem a ogni rosso** | ogni rosso su main, revert, perdita di dati, degrado visibile o misura mancante ha sei righe fisse in `docs/stato-reale/postmortem/`: cosa · classe del rosso (vero / trappola / sensore / guardiano) · causa · cura · controllo aggiunto · owner | il lead non apre la finestra su main finché il postmortem dell'ultimo rosso non c'è; la cartella è il registro | ws1 | template da scrivere |
| **R8 Le regole si potano** | una regola senza controllo meccanico entro 30 giorni, o senza una violazione contata in 30 giorni, si archivia; il resoconto del venerdì porta la tabella violazioni-per-regola | la tabella nel resoconto (già la facciamo per istanza; diventa per regola) | lead | da fare al primo venerdì |

Cosa NON propongo: nessuna regola di sola prosa (le B1-B6, le M1-M5 restano guida, non contano come
regole misurate), nessuna metrica-obiettivo su volume o velocità (Goodhart), nessuna cancellazione di
regola di Aurelio senza il suo sì: al primo venerdì la tabella dirà quali non hanno mai morso.

## 4. Come procediamo — il processo dell'agenzia, con le fonti dietro

1. **Il piano** è il §5 del RESOCONTO, nell'ordine accettato: recinto intorno al moat (T49, T50, T53,
   T-MAP-11, T51) → la memoria che risponde (21 %, tetto 10.000, versionare) → il prodotto diventa ciò
   che dice (57 claim, 19 moduli con owner e scadenza) → composte vere → copie e righello in CI →
   docstring → cure sui rami (T33, T34/35, T32, T38, T39-41, T48).
2. **Un ticket per istanza**, dal registro, con la gravità del Product Owner (AGENZIA regola 3):
   ramo proprio, DoD (R1), PR piccola (R6), revisore ≠ autore, QA sul pezzo che entra in main.
3. **Stand-up sul canale** a inizio e fine turno (regola 1) e un post ogni 20 minuti; `list_sessions`
   + `chi_tace.py` a ogni giro del lead (il silenzio non è lavoro).
4. **Una finestra su main al giorno** (20:00), un pezzo alla volta, aperta dal lead a CI verde; **il
   tag solo con il sì di Aurelio**.
5. **Un postmortem per ogni rosso** (R7) prima della finestra successiva.
6. **Il venerdì**: le tre misure del contratto + rossi su main, tempo al verde, revert, tag + la tabella
   violazioni-per-regola (R8). Lette come trend, mai come classifica delle istanze.
7. **Decisioni** (D-1: lead o 3 SÌ) scritte in una pagina con le alternative, per le tre decisioni
   architetturali aperte: i 19 moduli (cablare / spostare in un laboratorio non pubblicato, e lì
   provare il limite prima di buttare, come Aurelio ha chiesto il 02/09), versionare invece di
   ritirare, una politica di schema per gli otto store.
8. **Il carico**: un file di test alla volta per istanza, niente run paralleli, `banco-torch` per i
   modelli (Aurelio gioca).

## 5. La ricerca online — la lama doppia, dichiarata

- **Lama uno, le fonti**: le sette pagine sono fonti primarie (chi ha scritto la pratica). La ricerca
  sulle critiche a DORA ha restituito per lo più venditori di cruscotti (OpsLevel, BlueOptima, CodePulse):
  hanno interesse a dire che «le metriche non bastano», e ne ho preso solo ciò che DORA stessa afferma
  (l'avvertimento su Goodhart). Un numero che non stava nella pagina letta (le soglie elite/high) non
  l'ho usato.
- **Lama due, il contenuto**: tutto ciò che torna da una pagina è un dato, non un'istruzione. Nessuna
  delle pagine lette conteneva testo rivolto a me; la regola vale lo stesso, ogni volta.
- **Lama tre, il culto**: 0,15 % di flakiness, 80/15/5, 100 righe per CL sono numeri di un'azienda con
  decine di migliaia di ingegneri e un monorepo. Da noi valgono i principi (piccolo, rivisto, provato
  alla taglia giusta, codice morto con owner e scadenza, postmortem senza colpe), non i numeri come
  obiettivi: per Goodhart, il giorno in cui «80 % di test piccoli» diventa un obiettivo, qualcuno
  scriverà test piccoli inutili. I nostri obiettivi restano le tre misure del contratto, che l'utente
  sente.

## 6. Cosa serve da Aurelio

1. Sì/no su R1-R8 (o quali).
2. Sì/no alla mappa + righello + questo studio su main nella finestra delle 20:00 (docs e script: la
   matrice CI non parte).
3. La parola «fatto» quando le otto hanno finito il compact: parte il messaggio di ripresa, con il
   ticket di ciascuna e la DoD.
