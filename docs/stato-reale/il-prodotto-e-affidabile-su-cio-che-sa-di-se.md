# Il prodotto è affidabile su ciò che sa di sé

*ws3 «Galileo», 30/08. Otto promesse **dichiarate** del prodotto, misurate una
per una fra le 12:19 e le 16:00. Le misure sono sparse in sei banchi eseguibili
e sparse **non le legge nessuno** — questo documento le mette in fila e, per
ognuna, dice anche **su quanti casi si applica**.*

---

## La tesi in una riga

**Ciò che il prodotto dichiara di sé regge. Ciò che nessuno ha dichiarato è dove
stanno i buchi.** Per un analista è una distinzione più utile di qualunque
tasso: dice **dove fidarsi** e **dove guardare**.

---

## Le otto promesse

Ogni riga: la promessa **come è scritta nel prodotto**, la misura, il commit.
La colonna che conta di più è l'ultima.

| | promessa (dove è scritta) | misura | esito | **su quanti casi si applica** |
|---|---|---|---|---|
| ① | «SDK processes keep the synchronous one-time load» — `CHANGELOG:635` | 3 processi freschi, fonte che NEGA: **0/6** ammissioni a giudice freddo, controllo 6/6 | 🟢 | ⚠️ **non misurato**: quanti usino SDK contro MCP non è osservabile da qui |
| ② | «first write ~32 s → 0.3 s» — `CHANGELOG:716` | **18–36 s → 0,2–0,3 s**, stesso ordine su altra macchina | 🟢 | **una volta per processo**; quanti processi freschi, non misurato |
| ③ | «it is `grounding_score` that carries it … `status` no» — istruzioni MCP | **3/3**, e **un campo in più**: il layer `L4-skipped` separa «fonte non giudicata» da «nessuna fonte» | 🟢 | si applica **a chi legge i campi** — vedi ⑧ |
| ④ | «a session NOTE skips that screen … **the moat is UNAFFECTED: with a source**» — `agent_guide` | screen saltato **2/2**, moat gira **2/2** | 🟢 | ⚠️ **frequenza alta, rischio misurato NULLO**: `W7-70/71` di *Paragone* ha **letto** 24 casi — **0 self-claim nudi**, 11 resoconti e 13 misure — e il controfattuale dice che **senza l'eccezione la porta ne declasserebbe 21 su 24**. ⇒ *compensazione, non buco* |
| ⑤ | la promessa ③, verificata **sulla porta dove è scritta** | firme **identiche** SDK/MCP: `['0.56/False','null/True','null/False']` | 🟢 | entrambe le porte, regime pulito |
| ⑥ | «only when neither an llm nor the local model is present does the gate fail-open» — `README:64` | **binario, non temporale**: `DELEGATE_ONLY` 0 e 1 → **0/6** a freddo con modello presente | 🟢 | **installazioni senza modello**; non misurabile da qui |
| ⑦ | `doctor` esiste per dire perché manca un punteggio | modello assente → **`status='fail'`**, dice il path, distingue «con fonte → avviso» da «**senza fonte → nessun avviso**» | 🟢 | chi esegue `doctor` |
| ⑧ | la separazione deve sopravvivere alla **lettura** | SDK `recall` → gs 99.56 / `None`; MCP `hippo_facts_search` → espone `grounding_score` **e** `meta_narrative` | 🟢 | ⚠️ **«può», non «lo fa»**: quanti chiamanti guardino il campo non è misurabile da qui |

Banchi: `ws3-il-giudice-freddo-ammette-e-lo-dichiara.py` (① ② ⑥ ⑦) ·
`ws3-il-campo-che-distingue-non-giudicato-da-giudicato.py` (③ ⑧) ·
`ws3-le-due-porte-separano-gli-stessi-tre-stati.py` (⑤) ·
`ws3-la-guida-dichiara-la-propria-eccezione-e-vera.py` (④).

---

## 🔑 La colonna che ho imparato a pretendere oggi

La quarta riga è quella che insegna. Ieri avevo verificato l'eccezione
`meta_narrative` e concluso: *«la guida descrive con precisione il proprio buco,
e il moat resta a proteggere»*. **Il meccanismo era ed è vero.** Ma la guida
dice «**with a source** it runs in both modes», e **nei miei quattro casi la
fonte l'avevo messa io**.

Poi *Paragone* ha misurato che il **65% del corpus** salta quello screen, e io ne
ho dedotto un rischio: *«quei fatti non hanno fonte, quindi non sono protetti»*.

> 🔑 **Verificare una garanzia condizionale senza misurare la frequenza della
> condizione produce un verdetto VERO e una rassicurazione FALSA.**

🔴 **E POI HO SBAGLIATO UNA SECONDA VOLTA, NELLA DIREZIONE OPPOSTA.** `W7-70` e
`W7-71` (*Paragone*, 15:40 e 15:49) hanno **letto** quei fatti invece di
contarli: su 24 casi campionati **uno ogni 14** — **11 resoconti · 13 misure
verificabili · ZERO self-claim nudi**. E il controfattuale, che è la misura
giusta: **senza l'eccezione la porta ne declasserebbe 21 su 24**, quasi tutti per
`L1.13`. ⇒ **L'eccezione non è un buco lasciato aperto: è una compensazione
misurata**, su un vocabolario — *completo, chiuso, verificato, testato* — che è
quello con cui si parla di CI e di cicli di lavoro.

🔑 **La lezione va raffinata, non buttata**: la frequenza da sola **non dice se
il rischio si realizzi**. Serve il **controfattuale** — *cosa farebbe il layer se
girasse?* Io avevo ragionato su ciò che il layer **non fa**, senza chiedermi cosa
succederebbe se lo facesse.
⇒ **Ho preso un numero e ne ho dedotto un rischio senza leggere la popolazione**,
che è la mia stessa regola («leggi le righe, non contarle») applicata al log
della suite e **non** al numero di un altro.

⇒ Da qui la colonna «su quanti casi si applica». Tre delle otto **non sono
misurabili da dentro il repo**, e sono dichiarate tali: *quanti usano SDK contro
MCP*, *quanti processi freschi*, *quanti chiamanti leggono i campi*. **Dichiarate,
non stimate.**

---

## 🔴 Il contrappeso: ciò che non regge è ciò che nessuno ha dichiarato

- **Il perdono di `L1.13` è a comando del chiamante — 5/5.** Basta ripassare il
  claim come `source`: il testo del match compare verbatim **per costruzione**.
  Il commit che introduce il perdono dichiara «*una self-claim senza fonte resta
  fermata*» — vero alla lettera; ciò che non nomina è che **chi scrive la fonte
  è chi scrive il claim**. `a7f39bf0`
- **Le sei radici di `L1.13`** (*Paragone*, `a83d9605`): un sinonimo fuori
  dall'elenco aggira il layer **senza fonte**. Due vie indipendenti sullo stesso
  strato; la protezione residua è **gergo di collaudo**, e un verbale d'ufficio
  non ne ha nessuno.
- **Il buco dell'irrilevante**: 8 claim su 12 ottengono `moat: passed` senza che
  la fonte ne parli; ne entrano 2. La causa resta **ignota** — sei spiegazioni
  proposte e falsificate.
- **L'asimmetria fra le porte**: con modello locale assente e daemon vivo,
  **l'SDK ammette un claim che la sua fonte NEGA, MCP lo ferma**. Il fail-open
  SDK è dichiarato; che MCP lo **eviti** delegando **non lo è**. `e4c1f199`

---

## Cosa NON dice questo documento

- **Non dice che il prodotto sia a posto.** Dice che le sue **dichiarazioni**
  reggono. Sono due cose diverse, e la seconda non implica la prima.
- **Non è un campione rappresentativo.** Otto promesse **le ho scelte io**,
  guardando dove il prodotto parla di sé. Un altro ne sceglierebbe altre.
- **Non misura il traffico reale.** Tutti i banchi girano su store temporanei,
  con claim scritti da me, in italiano e inglese, e i numeri di frequenza
  mancanti sono segnati come mancanti.
- **Non assolve i miei banchi.** Oggi ho contato **dieci difetti nel mio
  misuratore**, e la famiglia dominante è una sola: *la popolazione non
  conteneva ciò che credevo di misurare* — regime ereditato invece che scelto,
  casi non appaiati, uno stato che non si produce, due fatti che si mangiano a
  vicenda per `same-source`, uno strumento che interroga un'altra tabella, e
  **il decimo non in un banco ma in un ragionamento**: un numero altrui letto
  come rischio senza guardare i fatti che lo componevano.
  ⇒ **Ogni banco qui citato ha ora un controllo che fallisce se la popolazione
  non c'è**, ed è l'unica ragione per cui questi numeri si possono leggere.

## La classe del giorno: la prosa resta ferma dove il codice si è mosso

Quattro istanze, **tre autori diversi**, una forma sola:

| | dove | l'affermazione | il codice |
|---|---|---|---|
| ① | `quantity_match` (mia) | «saltando le **DUE** potature» | ne avevo aggiunta una **terza**, fuori dall'esenzione |
| ② | `anti_confab_gate:2336` | tre vie al giudizio elencate | **il daemon non è nell'elenco** |
| ③ | `anti_confab_gate:24,296` | il downgrade forza `provisional` | scrive **`quarantined`**, in 7 punti |
| ④ | `anti_confab_gate:902` | `return False` (il default vecchio) | il default è **`return True`** — riga **irraggiungibile** |

⇒ Dopo la terza ho smesso di aspettare la quarta e ho usato **la classe come
setaccio**: `git grep` sulle affermazioni che nominano un conteggio, nel mio
perimetro. **Otto candidati, un difetto vero** (④, curato `613306f7`), **sette
no** — e lo dico con la stessa forza con cui avrei annunciato sette reperti.

🟢 **Due dei sette sono la FORMA GIUSTA, e sono già nel prodotto**:
`anti_confab_gate:1196` («*MISURATO su **quattro** aggiornamenti legittimi ne
blocca **due***» — **e li elenca**) e `mcp_server:8159` («*nessuna delle **tre**
superfici (mcp_server 0, cli 0, client 0)*» — **nomina superfici e numeri**).
**Si auto-verificano**: fra sei mesi qualcuno può contare.

🔑 **E il reperto di metodo vale più del difetto.** Due candidati —
«*i **quattordici** layer*», «*i **tre** detector*» — **non sono nemmeno
verificabili**: il mio contatore dà 35 e 4, ma **conto una cosa diversa** (il 35
include varianti `-observe`/`-graded`; «detector» non è «punto di import»).

> **Il puntatore non serve solo a tenere il numero aggiornato: serve a renderlo
> VERIFICABILE.** Un numero senza il suo criterio di conteggio non si può
> nemmeno controllare — e quindi **non invecchia mai visibilmente**.

⇒ È **peggio** di un numero sbagliato: quello prima o poi qualcuno lo smentisce;
un numero **non verificabile** non lo smentisce nessuno. Stessa famiglia di
*«una misura che non c'è si legge come perfetta»*.
📌 **Proposta**: *un'affermazione che nomina un numero, un elenco o uno stato
dica **dove sta scritto nel codice** — o, se è un conteggio, **con quale criterio
si conta**.* Non serve un test: gli esempi buoni sono già nel repo.

### La regola, dimostrata invece che argomentata

`agent_guide.py:77` — la guida che **ogni agente legge** — promette:

> *Measured on a real corpus: **538 of 634** chunks (84.9%) pointed at files that
> no longer existed, while the chunk text was present for **100%** of them.*

È **la forma giusta al massimo grado**: numero · criterio (*cosa* conta) ·
popolazione · contrasto · conclusione operativa. **Manca solo la DATA.** Ho
provato a ri-misurarlo (store dei documenti, **sola lettura**, 30/08 ore 16:58):

```
73 documenti indicizzati
  uri che NON esiste più   42  (57,5%)
  content conservato       73/73  (100%)
  esempi: contract.txt · docs\ROADMAP-v0.7.md · …\Temp\claude\…
```

🟢 **La sostanza REGGE su una popolazione indipendente**: i path si perdono, il
contenuto resta **al 100%** — e con esso la conclusione operativa, *la citazione
è esatta sull'indice, non è una garanzia di riaprire l'originale*. 🟢 **E la
guida nomina già la causa giusta** («*a RELATIVE path resolved from a different
working directory*»): i miei esempi sono esattamente path **relativi** e
**temporanei**.

⚠️ **Ma il numero non è confrontabile**: 57,5% su **73 documenti** contro 84,9%
su **634 chunk** — **popolazioni diverse, istanti diversi**. Il mio numero **non
smentisce né conferma** il suo.
🔑 **Ed è precisamente la dimostrazione della regola**: senza sapere **quando** e
**su quale grandezza** fu preso l'84,9%, nessuno può dire se sia invecchiato.
*Non l'ho argomentato: ci ho provato e non ci sono riuscito.*

## Una regola pratica, che vale oltre questo prodotto

> **Quando un banco stampa `[]` o `0`, la prima ipotesi non è «il prodotto non
> lo fa»: è «non gliel'ho chiesto».**

Oggi mi ha impedito di pubblicare due volte un reperto grave che non esisteva —
la seconda smontata facendo scrivere a MCP **un fatto suo** e chiedendogli di
ritrovarlo.

**Agent: Galileo**
