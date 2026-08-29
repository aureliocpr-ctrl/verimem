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
| unità-cambiata | EN | 1/1 | 1/1 | 🟢 difesa |
| attestazione-nuda | IT | 1/1 | 1/1 | 🟢 difesa |
| attestazione-nuda | EN | 1/1 | 1/1 | 🟢 difesa |

**16 celle · 9 difese · 5 bucate · 1 ridimensionata · 3 con danno doppio.**

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
| `unità-cambiata` IT | il gate confronta i valori, non le coppie (unità, valore) su questo caso | non indagato a fondo |

⇒ **Nessuna delle tre si chiude con una soglia.** Due chiedono un pezzo che non
c'è, una chiede di non far cadere i veri.
