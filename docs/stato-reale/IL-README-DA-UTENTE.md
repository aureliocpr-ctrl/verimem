# Il README come lo legge un utente — **le tre porte sono presentate come intercambiabili, e non lo sono**

**Iris (ws7, Product Owner), 06/09 02:57.** Deliverable di ruolo: non «cosa dice il
README», ma **cosa costruisce nella testa di chi lo legge**, e cosa gli succede dopo.

📏 **Regime**: `git show v0.7.6:README.md` — **il README che l'utente ha in mano**,
**812 righe**, non quello di `main` (805). Ogni numero qui sotto è un `grep` su quel file.

---

## La domanda era aperta dall'8 agosto, e nessuno l'aveva chiusa

`01b-le-promesse-mancanti.md` (ws1, 08/08) elencava tre cose non promesse da nessuna
parte. Due sono state colmate. La terza è rimasta lì, con la nota giusta accanto:

> *«**quale porta usare** — 🤷 non l'ho verificata: ho cercato con termini miei e non ho
> trovato la promessa, ma **un'assenza trovata con le parole sbagliate non è un'assenza**.
> Resta aperta.»*

**Adesso è misurata**, con tre famiglie di termini e un controllo positivo acceso.

---

## ① Cosa c'è: **tre porte, tre sezioni, nessun confronto**

```
grep "^## " README.md (v0.7.6)
  423   ## Quickstart (Python)
  475   ## Quickstart (Claude Code / MCP)
  501   ## CLI
```

⇒ Le tre porte **ci sono tutte**, ognuna con la sua sezione, tutte e tre complete. Un
lettore le trova. **Il problema non è l'assenza: è la forma.** Tre sezioni parallele, con
lo stesso nome e la stessa struttura, dicono al lettore una cosa precisa e non scritta:
**«sono tre modi di fare la stessa cosa, scegli quello che ti è comodo».**

## ② Cosa manca: **la scelta non è mai presentata come una scelta**

```
CONTROLLO POSITIVO (deve accendersi)      quickstart -> 2 occorrenze · MCP -> 27   ✅
A · scelta esplicita   "which door|which interface|when to use|should i use|choosing"
       -> 2 occorrenze, righe 736 e 741, ENTRAMBE sulla cancellazione
B · confronto fra porte  "SDK vs|CLI vs|MCP vs|vs SDK/CLI/MCP"
       -> 0
C · enumerazione delle tre  "three ways|three interfaces|three surfaces|three doors"
       -> 1, riga 270, e riguarda l'indicizzazione dei documenti
```

⇒ **Zero confronti. Zero avvisi. Nessuna riga dice che la porta cambia il risultato** —
tranne una, e non è dove serve.

## ③ 🔑 L'eccezione che dimostra che il README **sa farlo**

Alla **riga 736 su 812** — oltre il 90% del documento — c'è esattamente la cosa giusta,
scritta bene:

> *«What deletion looks like depends on **which door you use**, so here it is per door»*
> *«**which door you use decides whether the text is really gone.** Five doors delete and
> they do NOT make the same promise — the table below says which.»*

E sotto c'è **una tabella per porta** (righe 749-753): SDK, MCP, CLI, e cosa lascia
ciascuna nel registro di annullamento.

⇒ **Il README possiede già la forma che serve** — l'avviso più la tabella per porta — e
**l'ha usata una volta sola, per la cancellazione, in fondo.** Per tutto il resto: niente.

---

## Perché questo conta più dei singoli ticket: **è la loro causa comune**

I quattro difetti che questa notte ha prodotto o precisato dicono **tutti la stessa cosa**,
ed è la cosa che il README non dice:

| ticket | cosa cambia fra le porte |
|---|---|
| **T16 · P0** | la riga del Quickstart Python scrive dove **solo l'SDK** può guardare; la CLI dice `no facts found` con `exit 0` |
| **T14 · P0 su MCP** | il verdetto del gate sulla correzione **non arriva** sulla porta degli agenti |
| **D-6 · P0** | `as_of` accettato e **ignorato senza dirlo** su entrambe le porte MCP — ⚠️ **curato in `main`** (`db7dfd11`), non ancora in un rilascio |
| **T12 · P2** | le porte gemelle divergono su **cinque livelli di contratto** (massimo, nome del parametro, nome del campo, campi della ricevuta) |

🔑 **Chi legge il README ha ogni ragione di credere che le tre porte siano equivalenti: il
README non gli dice mai il contrario.** Poi ne sceglie una, e scopre da solo — o non
scopre affatto — che la sua scelta ha deciso cosa il prodotto sa fare per lui.

⚠️ **E T16 è il costo esatto di questa forma.** Non è un caso limite: è la conseguenza
diretta di due Quickstart affiancati che sembrano parlare dello stesso store. **Chi segue
il README alla lettera — Python prima, CLI dopo — finisce lì per costruzione.**

---

## La cura più piccola, e non è un capitolo nuovo

**Due interventi, entrambi su materiale che esiste già:**

1. **Una riga sopra i tre Quickstart** — *«these are not three ways to do the same thing:
   the door you pick changes what the memory can tell you»* — con il rimando alla tabella.
   È la stessa frase della riga 741, spostata dove il lettore la incontra **prima** di
   scegliere invece che 300 righe dopo.
2. **La tabella per porta esiste già**: oggi copre solo la cancellazione. Estenderla alle
   righe che abbiamo misurato — scrivere, rileggere, chiedere il passato, ricevere il
   verdetto — **non richiede un formato nuovo**, richiede quattro righe in più.

✅ **③ FATTA alle 04:17** (`71349110`) — *questa riga proponeva una cura che nel frattempo
era già stata applicata; l'ha trovata l'incrocio, un'ora e venti dopo che l'avevo scritta.*
**Il Quickstart Python ora insegna `Memory()` senza argomento**, con accanto il commento
che dice cosa succede se passi un percorso e il rimando al ticket aperto — chi già usa un
percorso deve sapere cosa gli capita, non solo leggere una riga diversa. **Vetrina verde
con l'exit vero: 30 passed, `EXIT=0`.** Il difetto T16 **resta aperto**: quello che è
cambiato è che **il nostro manuale non ci porta più dentro.**

---

## ⚠️ Limiti, dichiarati

· **È una misura sul testo, non sull'utente.** Dico cosa il README **non dice**; che questo
  produca la convinzione «le porte sono equivalenti» è la mia lettura da Product Owner,
  **falsificabile con la prova della scheda** (`LA-PROVA-DELLA-SCHEDA.md`): se chi non ci
  conosce, dopo aver letto, sa dire che la porta cambia il risultato, **ho torto io**.
· **Tre famiglie di termini e un controllo positivo, non una lettura riga per riga**: se la
  guida alla scelta esiste con parole che non ho cercato, **la mia assenza cade** — ed è lo
  stesso limite che ws1 dichiarò l'08/08, con la differenza che stavolta i comandi sono qui
  e chiunque può rifarli in trenta secondi.
· **Solo `v0.7.6`.** Su `main` (805 righe) non l'ho rifatto.

---

## 🪞 L'incrocio su questa pagina, un'ora e mezza dopo averla scritta

Questa pagina è nata alle **02:57**. Alle **04:26** l'ho incrociata con lo stato di adesso,
e conteneva **due affermazioni superate** — in novanta minuti.

**① La cura che proponevo era già applicata.** Il punto ③ diceva *«la riga del Quickstart va
cambiata»*: l'avevo cambiata io alle 04:17. **Chi legge un documento non ha modo di sapere
che una proposta è già stata eseguita**, e la scambia per lavoro da fare.

**② `D-6` era dato come aperto** — la cura è in `main` da `db7dfd11`. 🔑 **Ed è la QUARTA
copia della stessa frase superata**: l'avevo già corretta in `PERCORSI-UTENTE`, in
`GRAVITA-DIFETTI` e in `SCHEDA-PRODOTTO` alle 02:55, cercando **la frase** e non il
documento — che è la regola che mi ero data.

⇒ **La regola non bastava, e adesso so perché: questo documento non esisteva ancora quando
ho fatto il `grep`.** L'ho scritto due minuti dopo, **attingendo a quello che avevo in
testa** invece che alla fonte già corretta.

### 🔑 La lezione, ed è più stretta di «cerca la frase»

> **Una frase superata si ripropaga nei documenti scritti DOPO la correzione**, perché chi
> scrive attinge alla propria memoria, non al documento che ha appena sistemato.

⇒ Il `grep` non è un'operazione da fare **una volta quando una cosa cade**: va rifatto
**ogni volta che si scrive una pagina nuova che parla di stato**. Non costa niente — e in
novanta minuti mi ha già ripreso una volta.

📌 *E vale in generale: le classi di errore che curiamo tornano dal lato del tempo. Avevo
curato la propagazione **orizzontale** (le copie esistenti) e non quella **in avanti** (le
copie future). È la stessa forma di «curare l'istanza invece della classe», su un altro
asse.*