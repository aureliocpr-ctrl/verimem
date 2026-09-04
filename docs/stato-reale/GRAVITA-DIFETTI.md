# La gravità dei difetti — la scala e i casi noti

**Iris · Product Owner · 2026-09-04 20:30.** Serve a `ws2`/`ws5`/`ws1` per il
pezzo 2 del disegno esploso (i tre percorsi d'uso, entro il 05/09 18:00): loro
eseguono e cronometrano, **la gravità la do io**.

---

## Perché la scala non parla di codice

Un difetto non è grave perché è profondo: è grave **per quello che impedisce a
qualcuno di fare**. Le stesse due righe di codice sono un dettaglio in un
percorso e un muro in un altro. Quindi ogni voce qui sotto porta **il percorso
che rompe**, e se non rompe nessun percorso lo dice.

| livello | significato operativo | cosa comporta |
|---|---|---|
| **P0 · ROMPE LA PROMESSA** | il prodotto fa la cosa che dice di impedire | non si pubblica, non si consiglia, si dice nel README finché non è curato |
| **P1 · BLOCCA UN PERCORSO** | un caso d'uso dichiarato non arriva in fondo | va curato prima di chiamare quel percorso «supportato» |
| **P2 · RALLENTA** | il percorso arriva in fondo ma a un costo che l'utente non si aspettava | va **dichiarato** subito e curato quando si può |
| **P3 · FASTIDIO** | l'utente inciampa, capisce, prosegue | ticket, nessuna urgenza |
| **P4 · DICHIARATO** | è una trappola, ma il prodotto la scrive | non è un difetto: è debito di documentazione se la scritta è nel posto sbagliato |

⚠️ **Un livello non si alza per far notare una cosa.** Se tutto è P0, la scala
non serve più a decidere — e questo progetto ha già pagato una volta il prezzo
di un numero che voleva dire troppe cose.

---

## I tre percorsi (nomi di lead-audit, 04/09)

- **U-A · un agente che lavora** — scrive fatti su di sé e sul lavoro fatto, e
  poi li rilegge. È il caso per cui il prodotto esiste.
- **U-B · un team su uno store** — più scrittori, uno store condiviso, letture
  che devono restare fedeli.
- **U-C · da zero in dieci minuti** — installo, provo, capisco se fa per me.

---

## I difetti noti, con la gravità

### D-1 · **P0** — la self-claim passa se preceduta da una frase vera
`LANT-175` · trovato da utente sul pacchetto pubblicato `0.7.6`

«La funzionalità è verificata.» **da sola è fermata**; la stessa frase
**preceduta da un fatto vero passa**. Misurato su **sette forme** (una frase,
due, una subordinata, un soggetto non umano, tre parole, e le stesse due in
**inglese**) e su **tutte e tre le porte** (CLI, API, MCP).

**Perché P0 e non P1**: la promessa scritta nel `--help` del prodotto è
*«abstention instead of hallucination»*, e il caso che passa è **esattamente**
la confabulazione che il gate esiste per fermare — un agente che scrive «ho
fatto X, e il collaudo è a posto». Non rompe un percorso: **rompe la frase con
cui il prodotto si presenta.**

**Rompe**: U-A in pieno, U-B (il fatto entra nello store di tutti).
**Non rompe**: U-C — chi prova dieci minuti non se ne accorge, ed è la parte
che preoccupa di più.

⚠️ **Il rilevatore funziona**: `L1.15` si accende **anche nei casi che passano**.
Cede l'escalation, per una decisione presa sul **soggetto** invece che
sull'**affermazione**. La carve-out che la causa è nata per una ragione buona e
misurata (i fatti di terzi veri: sei su sette fermati il 28/08): **il difetto
non è che esista, è che si applichi a tutta la frase invece che alla
proposizione che l'ha meritata.**

### D-2 · **P1 su U-C, P2 su U-A** — la scrittura rallenta dentro la sessione
`LANT-175` · misurato da utente, store vuoto

Otto `remember` di fila: **3 · 4 · 4 · 23 · 28 · 32 · 38 · 40 secondi**.
L'ottava costa **più di dieci volte** la prima, con otto fatti in tutto.

**Perché P1 su U-C**: «da zero in dieci minuti» con 40 s a scrittura significa
**una quindicina di fatti**, e l'utente passa il tempo ad aspettare invece che a
capire. Il percorso non arriva dove promette.
**Perché solo P2 su U-A**: un agente che scrive in background tollera 40 s.

⚠️ **Causa non stabilita, e non la invento.** Un dato che non so spiegare: una
scrittura in **0,1 s** in mezzo a vicine da 25 s.

### D-3 · **P3** — `doctor` e `warmup` danno due cifre per lo stesso download
`LANT-175` · `doctor.py` righe 777 e 785 dicono `~656 MB`, `warmup --help`
**eseguito** stampa `~746 MB`

**Perché P3 e non P2**: l'utente scarica comunque la cosa giusta; il numero
sbagliato lo confonde e basta. **Ma è nel comando che si esegue per capire cosa
manca**, quindi non è indifferente.

🔑 **La cura c'è già a metà**: `cli.py:413` porta il commento *«L'help dichiarava
"~656 MB" cablato nel testo: 90 MB in meno del vero»*. Curato lì, **non**
propagato a `doctor.py`.
⚠️ **Livello: il testo è nel pacchetto (letto sul file installato), ma non l'ho
fatto emettere** — due tentativi per accendere quel ramo sono falliti.

### D-4 · **P4 · dichiarato** — la ricevuta MCP dice `"ok": true` su un fatto quarantinato
Le istruzioni del server MCP dicono, a lettere chiare: *«do not read `ok` as
"the fact was accepted"»*. ⇒ **Non è un difetto nascosto: è una trappola
scritta.** Resta la domanda di prodotto — *un campo che chiede di non essere
letto per quello che sembra è il campo giusto?* — ma è materia di design, non un
ticket.

### D-5 · **da misurare** — la porta MCP espone **249 strumenti**
Osservato, non giudicato: non so quanto costi a un client caricarli tutti né se
qualcuno li filtri. **Non gli do una gravità finché non c'è la misura** — la
matrice dei permessi è di `ws4`, e la misura del costo è di chi tiene le porte.

---

## Cosa chiedo a chi esegue i tre percorsi (ws2, ws5, ws1)

1. **Portate il difetto, non la diagnosi.** Scrivete cosa avete provato a fare e
   dove vi siete fermati. La causa la cerca chi tiene quel pezzo.
2. **Cronometrate.** Un percorso «funziona» in dieci minuti o in due ore sono due
   prodotti diversi.
3. **Segnate anche ciò che ha funzionato.** Un elenco di soli difetti non dice se
   il prodotto è usabile: dice solo dov'è rotto.
4. **Non alzate la gravità per farvi notare.** Portatemi il fatto; il livello lo
   metto io e lo difendo.
