# 07/09 — la giornata dal lato di chi usa verimem

*Scritto da @ws7 Product Owner (PO) alle 13:25, sulla finestra 12:25 → 14:25, tip letto
`a8ca6fd0`. **Il filtro è quello che Aurelio ha dato ieri**: solo ciò che un
utente **paga o sente**, con i numeri. Ogni numero porta chi l'ha misurato;
quelli che non ho riprodotto io lo dicono.*

---

## ① Che cosa un utente **sente** di diverso, oggi

**Niente.** Nessun tag, nessuna pubblicazione: quello che è cambiato oggi è
**quanto sappiamo**, non quanto il prodotto fa. E il saldo della conoscenza è
**negativo per il prodotto**: due cose che credevamo curate non lo sono.

---

## ② Che cosa un utente **paga**, con i numeri

### La cura del P0 di ieri è un regresso, e la misura è di chi l'aveva scritta

Ieri avevo chiuso T26 con *«la prima scrittura aspetta 42-69 s, e quei secondi
**sono** il giudizio»*. **Non lo sono.** Matrice di **@ws1 QA**, 18 giri nella
stessa ora, tre per cella:

| configurazione | v1 `b4a96369` | v2 `da0f3106` | fattore |
|---|---|---|---|
| default | judged 3/3 — 26,0 · 17,4 · 17,2 s | judged 3/3 — 126,8 · 83,6 · 84,3 s | **4,9×** |
| giudice acceso | judged 3/3 | judged 3/3 | 1,0× |
| senza daemon | 🔴 `L4-skipped` 3/3 | 🔴 `L4-skipped` 3/3 | **5,1×** |

⚠️ **La terza riga è stata ribaltata alle 13:22, dopo che questa tabella era già
scritta**: quella cella **non è un utente**, è la nostra sessione con
`HIPPO_ENCODE_DELEGATE_ONLY='1'` ereditata da `~/.claude/settings.json`. **La CLI
di un utente vero, senza daemon, giudica in 22 s.** *Lasciata qui con la
correzione accanto invece che cancellata: è il numero su cui stavamo per
costruire un P0 sbagliato.*

`grounding_score` **98.36787414550781 / 98.36788940429688**, identico cella per
cella. ⇒ **l'attesa non ha cambiato un solo verdetto su 18 giri.**

**Quanto pesa davvero**: @ws1 alle 12:58 — il costo si paga **una volta per
processo** (seconda scrittura **0,2 s**, 12 giudicate su 12). **@ws5 Piattaforma**, che
la cura l'aveva scritta, **ha portato lei il regresso** alle 12:35 e **ha
ritirato per prima la propria proiezione** alle 13:01 (*«contavo le scritture
invece dei processi»*). 🔑 **E il peso non è uniforme: dipende dalla porta.**

- un agente che tiene aperto il **server MCP**, o uno script che istanzia
  `Memory()` una volta → **lo paga una volta sola**;
- **la CLI apre un processo per comando** → chi lavora a colpi di `verimem save`
  **lo paga ogni volta**, ed è il percorso che il nostro Quickstart insegna.

⇒ **T26b: P1 sulla CLI, P3 su MCP e SDK.** *Lo stesso difetto è un fastidio su
una porta e un ostacolo su un'altra, e finora nessuno dei due numeri lo diceva.*

### La prima installazione: 712 MB e ~3 minuti, e il tempo è quasi tutto scarico

Banco del lead (12:36): installazione nuova → **scarica 712 MB e giudica**
(`99,85`, **184 s**, di cui **176 s di download**, non 15). Con la cartella del
giudice **esistente ma vuota** → nessun download. *(Misura sua, non l'ho
riprodotta.)*

---

## ③ Che cosa un utente **non sa**, e noi sì

### 🔴 La promessa centrale non regge alla porta: 6 self-claim su 7 entrano **giudicate**

È il numero più duro di oggi, e l'ho misurato io (`96c7c4c7`).

Le sette forme del reperto del 05/09 — *un fatto vero seguito da una self-claim*
— chiamando il gate **a mano** sono **fermate 7 su 7** (`L1.15`). Passando da
**`Memory.add`**, cioè la porta che un utente usa:

```
BRACCIO A   1/7 fermate
   sei entrano  status=model_claim  judged=True  grounding 99,94–99,98  layers=[]
   la sola fermata è A4:  grounding 16,51  layers=['L1.15','L4-grounding','L4.1']
```

**Perché è peggio di «passa»**: `judged=True` con `grounding_score 99,98` non
vuol dire *«è sfuggita al controllo»*, vuol dire **che il controllo l'ha
guardata e ha detto sì**. Chi rilegge quel fatto domani vede un numero alto
accanto a *«La funzionalità è verificata»* — e quel numero è ciò che il nostro
README indica come la prova che un fatto è stato giudicato. **La frase con cui
ci presentiamo è che una self-claim non torna come verità: torna, e con la
medaglia.**

**Tre spiegazioni facili sono già escluse**, con un A/B a una variabile:
`provenance_trusted` (il flag che `client.py:745` passa), `agent`, `topic` —
tutte e quattro le combinazioni fermano **7/7**, controllo positivo acceso in
ognuna. 🔬 **Candidato non verificato**: alla porta decide **il moat** (l'unica
fermata ha grounding 16,51, le sei passate 99,9x) e `Memory.add` passa
**`ground_write`**, che il mio banco non passa.

### ⚠️ Quello che **non** ho misurato, e conta

1. **Se il recall li serva.** I banchi girano con `ENGRAM_ENCODE_SERVICE=0` e lo
   store temporaneo scrive **senza embedding**. So che quei fatti **entrano**
   come giudicati; **non** so che una ricerca li restituisca. *Questa misura può
   alzare il livello, non abbassarlo.*
2. **La porta MCP.** Il commento a `client.py:743` dice che il canale MCP **non
   deve** inoltrare `provenance_trusted`: se lì le sette fossero fermate, **la
   stessa frase avrebbe due esiti su due porte**. ⛔ **Non l'ho eseguito**, e la
   ragione è una regola nostra: **non ho trovato** un parametro di store su
   `hippo_remember` né una variabile d'ambiente che lo sposti in
   `mcp_server.py` (cercati `ENGRAM_DATA_DIR`, `VERIMEM_DB`, `HIPPO_DB`: zero
   occorrenze) — ⚠️ *cercato, non provato eseguendo: potrebbe esserci una via
   che non ho visto* — il server usa lo store dell'agente, e `ENGRAM_DATA_DIR`
   **non isola**
   (lezione già pagata). Eseguirlo così scriverebbe sette self-claim **nello
   store vero**. *Serve prima un modo verificato di puntare lo store altrove.*
3. **Il presidio della parità non poteva vederlo.**
   `tests/test_all_write_channels_judge_a_source.py:116` sostituisce l'agente con
   un finto (`monkeypatch.setattr(mcp_server, "_ag", …)`) e verifica
   `judge.calls >= 1`. ⇒ **misura che il canale CONSULTI il giudice, non che
   l'esito sia giusto.** Con un giudice vero, il canale lo consulta *e il fatto
   entra lo stesso*: il presidio è verde e il difetto c'è. Non è un difetto del
   test — è il suo perimetro, e vale la pena saperlo.

---

### 🔑 Il numero che va detto per porta, o inganna

@ws4 ML, 13:50, sola lettura su **10.260 scritture**:

```
scritture CON fonte              10.260
non giudicate                        96   =  0,9 %
   ↳ 26  archivio storico (11/05, prima che il campo esistesse)
   ↳ 12  un LOTTO del 30/08 alle 20:35, un topic solo
   ↳ 31  stillicidio dalla CLI, 30/08 20:41-53
   ↳ 14  ieri, sparsi
fatti CON fonte dalla porta MCP:  0
```

🪞 **Questa tabella è la SECONDA versione**: la prima riportava tassi per porta
(«l'SDK sta nove volte peggio, 5,53%») che **la loro autrice ha ritirato alle
13:56 come artefatto del denominatore** — e io li avevo pubblicati alle 13:57,
**un minuto dopo il ritiro**. *I 96 non sono un tasso: sono **tre lotti in nove
mesi**.*

**Due conseguenze, e la seconda tocca il testo che leggerà Aurelio:**

1. 🔑 **Alcune scritture con fonte vengono giudicate e altre no, e non è il
   daemon.** @ws4 l'ha **provato**: nella finestra `30/08 20:30-21:00`, **233
   giudicate contro 43 no** — se il daemon fosse stato giù non ne sarebbe
   passata nessuna. ⇒ è **lo stesso fenomeno** che ho visto io alle 13:47:
   stessa porta, daemon **verificato** usabile, esiti opposti a 37 minuti di
   distanza. **Due strade indipendenti, lo stesso fatto, e nessuno sa la
   causa.** *(Non è un tasso e non è una porta: è una cosa che non capiamo.)*
2. **Il denominatore di T26a è vuoto**: dalla porta MCP **non esiste una sola
   scrittura con fonte** nello store. ⇒ *lo storico non conferma e non smentisce
   il ticket*: T26a è dimostrato **dal codice** e **dalla prova di @ws1**, non
   dai fatti nel corpus. **Se nel testo compare «il difetto ha colpito N
   scritture», va detto da quali porte** — i 96 vengono da CLI e SDK, non dalla
   porta che il ticket accusa. *Un numero vero attaccato al ticket sbagliato
   inganna più di un numero assente.*

## ④ I P0 come stanno adesso

| # | stato al 07/09 13:25 |
|---|---|
| **D-1** | 🔴 **confermato alla porta, 1/7** — misurato oggi, tre cause escluse, una da provare |
| **T26a** | 🪞 **ribaltato alle 13:22, e il numero capovolto era mio.** La cella «senza daemon» **non è la configurazione di un utente**: era la nostra sessione, con `HIPPO_ENCODE_DELEGATE_ONLY='1'` **ereditata da `~/.claude/settings.json` su tutte le istanze** (@ws4 lo rileva, @ws1 lo verifica su di sé e ritira il proprio reperto). **La CLI di un utente vero, senza alcun daemon, GIUDICA in 22 s** (`98.36788940429688`) contro 79 s `L4-skipped` con la variabile. ⇒ **resta P0**; il percorso certo è **U-B (un agente via MCP)**, **ma non solo**: alle 13:47 anche la porta **SDK** ha scritto con fonte un fatto entrato **non giudicato**, col daemon verificato usabile — mentre alle 13:10 la stessa chiamata giudicava a 99,9. **Non sappiamo perché**, e il perimetro è quindi **più largo di come l'avevo scritto io alle 13:35**: colpisce la configurazione `delegate-only`, che è come il server MCP gira per costruzione |
| **T8-bis** | 🔴 **sale a P0 `[VETRINA]`, e la faccia nuova è l'opposta della mia** (reperto di @ws1, 13:26): nella configurazione **esatta** in cui la scrittura torna `L4-skipped`, `verimem doctor` risponde **otto righe tutte ✓** — *«the grounding moat is ON»*. **Chi chiede «perché la mia scrittura non è giudicata?» riceve «va tutto bene»**, e la ricevuta del prodotto lo manda proprio lì |
| **T19 · D-6 · T1** | invariati, nessuna misura nuova oggi |
| **T16** | ✅ curato, invariato |

**Cosa dice questo quadro sul tag**: la 0.7.7 non ha perso nulla oggi, ma **due
delle cose che ieri contavamo come curate non lo sono** — la cura del P0 (che
costa e non compra) e la promessa centrale alla porta. *Un rilascio si giudica
su ciò che l'utente riceve, non su quante caselle abbiamo chiuso.*

---

*Ogni riga di questo documento porta chi ha misurato. Le misure di @ws1 e @ws5
non le ho riprodotte e lo dico. La misura alla porta è mia, con il regime
dichiarato.*

---

## 🔖 RIPRENDI DA QUI — scritto alle 14:12, prima dello STOP delle 14:25

*La giornata ha ribaltato un reperto ogni dieci minuti: **sette righe mie
ritirate o corrette in due ore**, e quattro numeri caduti mentre erano già
scritti. Questo blocco esiste perché domani nessuno debba ricostruire **quale
numero è sopravvissuto**.*

### ✅ Cosa regge, e su quale evidenza

| il fatto | l'evidenza | di chi |
|---|---|---|
| **D-1 alla porta: 1/7 fermate** contro **7/7** chiamando il gate a mano; sei self-claim entrano `judged=True`, `grounding` 99,94–99,98 | banco `ws7-d1-dalla-porta-sdk.py`, verdetto letto dallo store | mia |
| **`provenance_trusted`, `agent`, `topic` NON sono la causa**: 7/7 in tutte e quattro le combinazioni | A/B a una variabile, controllo positivo acceso | mia |
| **Una scrittura con fonte a volte è giudicata e a volte no, e NON è il daemon** | `30/08 20:30-21:00`: **233 giudicate contro 43 no** · e in vivo alle 13:47 con `daemon_usable()=True` | @ws4 + mia |
| **Dalla porta MCP: ZERO scritture con fonte** ⇒ il denominatore di T26a è vuoto | conteggio sul corpus | @ws4 |
| **96 non giudicate su 10.260 (0,9%), in TRE LOTTI in nove mesi** — non un tasso | conteggio sul corpus | @ws4 |
| **Il prodotto sana l'embedding mancante e NON il giudizio** (T29) | `mcp_server.py:8685`, `cli.py:4727` · nessun `rejudge` trovato | mia |
| **`doctor` dà otto ✓ nella configurazione del fallimento** (T26c) | otto righe lette nella cella esatta | @ws1 |

### ⛔ Cosa NON sappiamo, in ordine di quanto pesa

1. 🔬 **PERCHÉ una scrittura con fonte a volte è giudicata e a volte no.**
   Due misure indipendenti dicono che il fenomeno c'è; **nessuna dice la causa**,
   e le spiegazioni facili (daemon giù, la fonte, la porta, il momento) sono
   **tutte già escluse** — da @ws4 le prime tre, da me la quarta.
   ⇒ **primo pezzo di domani**, e senza questo T29 non si può misurare.
2. **Se il recall serva i non giudicati come gli altri** — il banco è uscito
   `NON MISURATO` perché non è riuscito a costruire il caso giudicato (che è,
   di per sé, un'istanza del punto 1). Rifarlo **dopo** ①.
3. **Perché la porta scarta il verdetto di `L1.15`** (D-1): tre candidati
   esclusi, resta il moat e l'argomento `ground_write`.
4. **Quanto spesso il daemon non parte** su una macchina senza il nostro
   `settings.json` — il denominatore che manca a T26a.

### 📌 Il ramo

`ws7/su-2b82497f`, **14 commit, ZERO push oggi** *(contati con `git rev-list --count origin/main..HEAD`, non a memoria: avevo scritto 16)* (main è in freeze). Dentro:
gli **owner** delle sei voci di «Not solved yet» con l'evidenza accanto a ogni
nome, **T24** e **T25** che nel file non esistevano, **T28** e **T29** nuovi, la
**mappa dei nomi** T26a/b/c, **quattro banchi** di D-1 e T29, e questo documento.
