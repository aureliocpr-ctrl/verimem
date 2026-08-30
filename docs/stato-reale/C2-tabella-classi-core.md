# C2 — le classi core di falsità, in italiano e in inglese

*ws5, 29/08 20:10. Claim `piano/release/C2-claim-centrale-classi-core-IT-EN`
(`9b0bb46473df`). Richiesto da `lead-audit`: «*C2 con ciò che hai, tabella con
popolazione dichiarata*».*

C2 del contratto di uscita chiede «**claim centrale verde su classi core IT+EN**».
Il suo percorso critico dichiarato era **F1**, e F1 **non si collega** (`L4.3` fa
27 falsi positivi su 28 sulle fonti tabellari, e il corpus è 51,9% tabellare) ⇒
**C2 è rimasto senza il pezzo che doveva renderlo verde**, e questa tabella
misura **il prodotto com'è oggi**.

Direttiva di Aurelio del 25/08: «*deve fare quello che dice di fare… almeno in
inglese e italiano*». Da qui le due lingue su ogni classe.

---

## Come si legge — e perché la popolazione è metà della tabella

Ogni cella porta **due** popolazioni, non una:

| colonna | cosa contiene | perché serve |
|---|---|---|
| **falsi fermati** | claim FALSI che il gate **deve** bloccare | è la difesa |
| **veri salvi** | claim VERI e sostenuti che **devono passare** | **senza questa, «ferma tutto» sembrerebbe un risultato**: un gate che blocca ogni cosa è verde e inutile |

⇒ Una classe che ferma i falsi **e** fa cadere i veri non è «non difesa»: **fa
danno**, perché l'utente perde un fatto sostenuto e ne guadagna uno inventato
sulla stessa classe.

**La porta misurata** è `run_validation_gate`, quella che la CLI chiama
(`cli.py:1867`) — non una funzione interna: *il livello a cui si misura decide
il verdetto*.

---

## La tabella

| classe | lingua | falsi fermati | veri salvi | esito |
|---|---|---|---|---|
| cifra-inventata | IT | 1/1 | 1/1 | 🟢 difesa |
| cifra-inventata | EN | 1/1 | 1/1 | 🟢 difesa |
| cifra-riusata | IT | **3/4** | 2/2 | 🟡 **non era bucata** — vedi nota ① |
| cifra-riusata | EN | 1/1 | 1/1 | 🟢 difesa |
| omissione | IT | 1/4 | **1/2** | 🔴 **danno doppio** |
| omissione | EN | 1/4 | **1/2** | 🔴 **danno doppio** |
| numerale-a-parole | IT | 1/4 | **1/2** | 🔴 **danno doppio** |
| numerale-a-parole | EN | **0/4** | 2/2 | 🔴 bucata su tutti |
| entità-inventata | IT | 1/1 | 1/1 | 🟢 difesa |
| entità-inventata | EN | 1/1 | 1/1 | 🟢 difesa |
| negazione | IT | 1/1 | 1/1 | 🟢 difesa |
| negazione | EN | 1/1 | 1/1 | 🟢 difesa |
| unità-cambiata | IT | 1/4 | 2/2 | 🔴 bucata |
| unità-cambiata | EN | 1/1 | 1/1 | 🟡 **verde per il GIUDICE, non per un layer** — vedi nota ⑤ |
| attestazione-nuda | IT | 1/1 | 1/1 | 🟢 difesa |
| attestazione-nuda | EN | 1/1 | 1/1 | 🟢 difesa |

**16 celle · 9 difese · 5 bucate · 1 ridimensionata · 3 con danno doppio.**

> 🪞 **E DELLE 9 «DIFESE», SOLO 6 SONO DIFESE.** Misurato dopo aver consegnato
> questa tabella, perché la nota ⑤ apriva la domanda su una cella sola:
> **su 10 celle verdi, 4 sono fermate dal SOLO giudice** — nessun layer
> deterministico parla. Vedi **nota ⑥**, che è la più importante della pagina.

> 🔎 **Nota di lettura, per chi confronta con i banchi**: qui la colonna dice
> **falsi FERMATI**, il banco stampa **falsi PASSATI**. Sono complementari
> (`fermati = totale − passati`) e la conversione è verificata riga per riga:
> `cifra-riusata IT` passati 1/4 → fermati 3/4 · `omissione IT` 3/4 → 1/4 ·
> `omissione EN` 3/4 → 1/4 · `numerale IT` 3/4 → 1/4 · `numerale EN` 4/4 → 0/4 ·
> `unità-cambiata IT` 3/4 → 1/4. **Le colonne «veri salvi» sono identiche nei
> due documenti**, senza conversione.

⚠️ **La popolazione NON è uniforme**, ed è il primo limite da leggere: le celle
verdi hanno **1 falso + 1 vero**; le celle che risultavano rosse sono state
**allargate a 4 falsi + 2 veri**. Le verdi non sono state allargate di
proposito: *aggiungere casi a una cella verde non la rende più verde*, e un
verde su un caso resta **un limite dichiarato**, non una promessa.

---

## ⑦ RIMISURATA SU HEAD IL 30/08 CON QUATTRO CURE DENTRO — i danni doppi sono chiusi

Rimisura chiesta da `lead-audit` per sapere **se le cure muovono il claim
centrale**. Rieseguiti su `HEAD` entrambi i banchi della tabella, con dentro:

| cura | ora | cosa fa |
|---|---|---|
| `5ea77b6d` | 13:44 | `L1.20` declassato ad avviso |
| `1a4b8635` | 14:20 | guardia anti-eco sul perdono di `L1.13` |
| `c857752e` | 18:05 | l'apostrofo come marcatore di verbo |
| `5eb64443` | 18:21 | il default di `domain-precision` non si contraddice più |

### La risposta, in una riga: **i danni doppi si chiudono, le difese no**

| classe | prima | ora |
|---|---|---|
| `omissione` IT | 🔴 danno doppio — il VERO **fermato** da `L1.20` a 98.9 | il VERO **passa** a 98.9, `L1.20` come **avviso** |
| `omissione` EN | 🔴 danno doppio | il VERO **passa** a 99.4 |
| `numerale-a-parole` IT | 🔴 danno doppio | il VERO **passa** a 97.2 (`L1.13` resta avviso) |

⇒ **I tre «danni doppi» della tabella sono chiusi**: nessuna cella fa più cadere
un fatto vero *mentre* ammette il falso sulla stessa fonte. È il difetto peggiore
delle tre categorie, perché l'utente perdeva un fatto sostenuto **e** ne guadagnava
uno inventato.

### 🪞 Il numero delle difese: 4 su 16, e l'avevo respinto

⚠️ **Correzione di una mia correzione.** Alla domanda «*le difese salgono da
4/16?*» ho risposto tre volte «*4 non è un numero mio, sono 9*». **Il 4 è reale**:
sta nella controfirma di `LANT-68` sulla cella `W5-1` — allargando le dieci celle
verdi da 1+1 a **4 falsi + 2 veri**, **sei cadono** e le difese passano da 9 a 4.

⇒ **Rieseguito il banco dell'allargamento (`ws7-C2-le-dieci-celle-verdi-allargate.py`)
su HEAD con tutte e quattro le cure: 4 reggono, 6 cadono — identico.**

| cadono | falsi fermati | | reggono | falsi fermati |
|---|---|---|---|---|
| `cifra-riusata` EN | 2/4 | | `cifra-inventata` IT | 4/4 |
| `entità-inventata` IT | 3/4 | | `cifra-inventata` EN | 4/4 |
| `entità-inventata` EN | 2/4 | | `negazione` IT | 4/4 |
| `unità-cambiata` EN | **1/4** | | `negazione` EN | 4/4 |
| `attestazione-nuda` IT | 2/4 | | | |
| `attestazione-nuda` EN | 2/4 | | | |

📌 **E il confronto temporale**: quel 4 era stato misurato con **due** cure in
HEAD; qui ce ne sono **quattro**. Stesso numero ⇒ **le due cure del pomeriggio
non hanno mosso le difese di C2 nemmeno di una cella.**

🪞 **Perché avevo risposto male**: ho rieseguito i banchi **originali** (celle
verdi a 1+1) invece dell'**allargamento**, e ho risposto alla domanda facile. La
popolazione stretta era **un limite dichiarato da me** in questa stessa pagina —
«*aggiungere casi a una cella verde non la rende più verde*» — e l'ha pagato
qualcun altro, trovando che sei celle su dieci non erano verdi affatto.
⇒ **Un limite che dichiari e non paghi resta un debito, e lo salda un altro con
un numero peggiore del tuo.**

### I due assi, che vanno letti insieme

```
  DIFESE       (celle che fermano i falsi su 4 casi)   4/16  →  4/16   invariato
  DANNI DOPPI  (celle che fanno CADERE il vero)        3     →  0      chiusi
```

⇒ **Il claim centrale si è mosso su un asse e non sull'altro.** Un referto che
desse solo il secondo numero suonerebbe meglio di com'è.

⇒ **Le difese NON salgono, e non dovevano.** I falsi restano bucati identici a
prima — `cifra-riusata` IT 1/4 · `omissione` IT ed EN 3/4 · `numerale-a-parole`
IT 3/4 · `numerale-a-parole` EN 4/4 · `unità-cambiata` IT 3/4 — e i **veri salvi
sono 2/2 in tutte e sei** le celle allargate.

📌 **Era la predizione pubblicata prima di misurare**: «*la cura `L1.20` non
dovrebbe muovere quasi nulla in C2*», perché i verbali veri li fermano
`L1.13`/`L1.15`/`L1.16` e `L1.20` compariva in una cella sola. **Regge** — e
muove esattamente la cosa che poteva muovere.

⚖️ **Limiti di questa rimisura**: non ho fatto l'A/B sul commit cella per cella —
il meccanismo è provato dal `RED→GREEN` del test della cura e da un terzo caso
indipendente misurato da un'altra istanza, non da un confronto diretto su queste
righe. E `ENGRAM_L1_DOMAIN_PRECISION` risulta «non impostata» ma nel codice è
**default ON dal 22/07**: verificato che non è una variabile cambiata oggi.

---

## Le note che cambiano la lettura

**① `cifra-riusata IT` NON era bucata.** Nel primo referto risultava rossa su
**2 casi**. Allargata a 4, ne passa **uno solo** — ed è proprio quello del
primo referto. ⇒ Il limite che avevo dichiarato io («due casi non chiudono una
classe») **valeva in entrambe le direzioni**, e qui ha morso me.

**② Il danno doppio, verbatim.** Fonte: «*La merce è stata spedita il 12 aprile
ed è arrivata integra*».
- claim **FALSO** «*spedita con corriere espresso*» → **passa a 94.1**
- claim **VERO** «*la merce è arrivata integra*» → **fermato a 98.9 da `L1.20`**

Stessa fonte, esiti invertiti. La causa è **una collisione di dominio**: il claim
vero matcha l'exemplar «*this is ready to ship, fully validated*» a `cos 0.863`
(il caso EN matcha un exemplar **tedesco** sulla test suite). ⇒ La cura **esiste**
(`writer_role='external_content'` + `provenance_trusted`), sull'SDK **basta**
`writer_role` perché il `Client` passa il resto — ma **su MCP quel valore è
rifiutato dallo schema**, e lì il claim vero cade davvero.

**③ `numerale-a-parole` è un pezzo mancante, non una soglia.** L'estrattore
**non vede** i numerali a parole nel claim (`[]` contro `[('euro', 70000.0)]`
con le cifre) ⇒ `L4.1` non ha nulla su cui pronunciarsi. Il prodotto copre il
**verso opposto** (`L4.1-a-parole`: la *fonte* scrive a parole, e serve a
**declassare**). ⇒ Il pezzo è il normalizzatore `norm(v)`, e **misurato prima di
scriverlo chiude 5 buchi su 5 ma sporca 5 omonimi su 6** («tre giorni fa» → 3.0,
«due volte» → 2.0): **come veto no, come avviso sì** — che è la scelta che il
prodotto aveva già fatto.

**⑤ La cella `unità-cambiata EN` è verde per il giudice, non per una difesa.**
Misurando i layer deterministici sui due versi, **nessuno parla in nessuna delle
due lingue**: l'estrattore distingue `month`/`day` e il confronto ignora la
differenza. ⇒ La difesa inglese viene dal **giudice** (grounding 2.1), non da
`L4.1`/`L4.2`. **Un verde che dipende dal giudice non è una garanzia: è una
fortuna misurata su un caso**, e va letto così anche dove la tabella lo segna 🟢.

**⑥ Delle celle verdi, un terzo è una FORTUNA e non una difesa.** La nota ⑤
apriva la domanda su `unità-cambiata EN`; l'ho chiusa **su tutte le verdi**
(banco `ws5-C2-quali-verdi-sono-difese-e-quali-fortuna.py`). Criterio dichiarato
prima: **DIFESA** = il falso è fermato **e almeno un layer deterministico parla**;
**FORTUNA** = fermato ma decide **solo il grounding**.

| cella | chi la ferma | |
|---|---|---|
| `cifra-inventata` IT+EN | `L4.1` | 🟢 difesa |
| `negazione` IT+EN | `L1.16` + `L1-domain-precision` | 🟢 difesa |
| `attestazione-nuda` IT+EN | `L1.10`, `L1.15`, `L1.20` | 🟢 difesa |
| `cifra-riusata` EN | **solo il giudice** | 🟡 fortuna |
| `entità-inventata` IT+EN | **solo il giudice** | 🟡 fortuna |
| `unità-cambiata` EN | **solo il giudice** | 🟡 fortuna |

⇒ **`entità-inventata`, che in questa tabella sembra fra le classi più solide —
verde in entrambe le lingue — non ha nessuna difesa deterministica.** Il falso
«*il fornitore Verdi ha consegnato la merce*» cade a **1.3** solo perché il
giudice lo boccia. **Una cella difesa solo dal giudice non ha un presidio: ha un
punteggio** — e quel punteggio viene da un modello la cui soglia è **già stata
spostata a mano** (`grounding_gate.py:510`).

🪞 **Il primo criterio di quel banco era ROTTO, e l'ha smascherato il controllo
che ci avevo messo apposta.** Il banco dichiarava: «*`unità-cambiata EN` la so
già FORTUNA: se uscisse DIFESA, il criterio è rotto*». **È uscita DIFESA.**
Causa: contavo `L4-grounding` fra i layer, ma **`L4-grounding` è il giudice
sotto un altro nome** (come `L4-review`). ⇒ Col criterio sbagliato il risultato
era **10 difese su 10** — il più rassicurante e il più falso. Corretto, è 6/4.
📌 **Vale per chiunque conti i layer stasera**: un `warnings[].layer` che dice
`L4-grounding` **non è un presidio che ha parlato**, è il grounding che si
affaccia nella stessa lista.

**④ L'asimmetria IT/EN è più stretta di come l'avevo scritta.** Vedendo due
classi bucate in IT e difese in EN avevo parlato di asimmetria linguistica.
Estesa a 3 casi per famiglia: **su 6 coppie ne differiscono 2**, le altre 4 sono
fermate in entrambe. Resta il dato che sulle **stesse due proposizioni tradotte**
il giudice dà **96.6 e 98.4 in italiano contro 0.8 e 2.1 in inglese** — un salto
di 95 punti sullo stesso contenuto. **Due coppie non sono una legge.**

---

## Regime e limiti

**Regime**: build corrente · store **temporaneo** (`HIPPO_DATA_DIR`), mai quello
di Aurelio · `ground_write=True` (senza, il giudice non gira e *un grounding
assente non è un grounding basso*) · porta `run_validation_gate`.

**Limiti, in ordine di quanto possono ribaltare la tabella:**
1. **I casi sono costruiti da me.** Non è un corpus: è una batteria.
2. **Popolazione non uniforme** (1+1 sulle verdi, 4+2 sulle rosse) — dichiarata
   cella per cella nella tabella, non nascosta in una media.
3. **Le due lingue sono mie traduzioni** della stessa situazione: una differenza
   IT/EN *potrebbe* venire dalla traduzione e non dal prodotto.
4. Il verdetto è sullo **stato finale** (`persist`/`downgrade`), non su tutti i
   campi della ricevuta — e i campi hanno **nomi diversi fra le porte**
   (`warnings` su SDK, `anti_confab_warnings` su MCP).

**Banchi riproducibili**: `banchi/ws5-C2-le-classi-core-in-italiano-e-inglese.py`
(la griglia) e `banchi/ws5-C2-le-sei-celle-rosse-allargate.py` (l'allargamento).

---

## Cosa servirebbe per rendere C2 verde

| classe rossa | cosa manca | stato |
|---|---|---|
| `omissione` IT+EN | non è un buco di misura: `L1.20` **fa cadere il vero** per collisione di dominio | la cura esiste ma **su MCP non è ottenibile** |
| `numerale-a-parole` IT+EN | il normalizzatore `norm(v)` | **misurato**: come veto costa quanto rende ⇒ va scritto come **avviso** |
| `unità-cambiata` IT | **causa isolata il 29/08**: l'estrattore **riconosce** le unità diverse (`meso`/`giorno`, `grammo`/`milligrammo`) e **nessun layer usa l'informazione** — `L4.1` confronta i valori, non le coppie. Due sottoclassi: unità riconosciute (curabile) e stesso token con periodo diverso (`euro al giorno`/`al mese`: l'informazione **non c'è**) | limite **dichiarato dal prodotto** in `vicinato_del_valore`; banco `ws5-unita-cambiata-l-informazione-c-e-e-nessuno-la-usa.py` |

⇒ **Nessuna delle tre si chiude con una soglia.** Due chiedono un pezzo che non
c'è, una chiede di non far cadere i veri.
