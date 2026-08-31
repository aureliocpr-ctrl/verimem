# Due porte, garanzie diverse — e la differenza è sempre un default o un nome

**ws2 «Varco», 22/08/2026, finestra 15:04–16:40.** Misurato da utente: venv separato,
wheel `0.7.5` installato da zero, `HIPPO_DATA_DIR` su cartella nuova, ambiente ripulito
per **enumerazione del prefisso** `HIPPO_`/`ENGRAM_`/`VERIMEM_`.

> 🔗 **I NUMERI DI RIGA SCADONO — verificato su questo stesso documento.** Alle
> 20:53 del 24/08, su `a99c0b54`, **2 dei 10 riferimenti qui dentro erano già
> morti** dopo ~4 ore e una decina di commit: `mcp_server.py:14921` puntava a
> `"hippo_skill_retire"` invece che al `setdefault`, e `cli.py:1155` a un
> `typer.Option` invece che alla promessa dei due secondi. **Un indirizzo morto
> è peggio di nessun indirizzo: manda chi legge alla riga sbagliata senza
> avvisarlo.** ⇒ Cura di ws1 (24/08 20:51), applicata qui: **il TESTO da
> cercare, e il numero CON lo SHA**. Quando trovi `file.py:NNN @sha`, se la
> riga non torna cerca la stringa citata.

> ⚠️ **Limite dell'isolamento, dichiarato perché mi ha già ingannata una volta.**
> `DISCOVERY_PATH = Path.home() / ".engram" / "encode_service.json"` sta nella **HOME**,
> non nella data dir: `HIPPO_DATA_DIR` **non isola il daemon**. La cache HuggingFace
> è anch'essa dell'utente, quindi **il modello CE c'era in tutte le celle**.
> La ricetta completa (spostare `HOME`+`USERPROFILE`) è di ws5, misurata il 22/08.
>
> **Verificata anche qui, in sola lettura (16:59):** con `HOME`/`USERPROFILE` spostati,
> `DISCOVERY_PATH` li segue, il discovery risulta **ASSENTE** e `daemon_usable()` è
> `False` — la ricetta isola davvero. ⚠️ **E per la stessa ragione non l'ho applicata:**
> in quel regime `memory.py:114` e `:618` chiamano `ensure_running()`, che **spawna un
> secondo daemon (~400 MB)**. È una decisione di risorse — la stessa classe di
> `ollama serve` — e non è mia da prendere mentre la macchina è in uso.
> **L'esperimento è definito e il suo costo è quantificato: manca solo il via.**

---

## Il fatto centrale

Il prodotto ha **due porte** — la CLI che usa un umano e il server MCP che usa un
agente — e **su tre assi diversi le due porte danno garanzie diverse**. Nessuna delle
tre è una bugia; tutte e tre fanno sì che chi prova una porta non sappia cosa succede
sull'altra. **Non esiste un posto dove sia scritto quale garanzia vale su quale porta.**

| asse | CLI | MCP | conseguenza misurata |
|---|---|---|---|
| `HIPPO_ENCODE_DELEGATE_ONLY` | non se la mette | `mcp_server.py:14994` @`a99c0b54` — cerca `setdefault("HIPPO_ENCODE_DELEGATE_ONLY"` | **16,2 s** contro **4,6 s** sulla stessa scrittura |
| `min_relevance` | default `0.0` in firma | la porta passa `0.0`, ma accende `ce_gate` | l'astensione viene dal **CE**, non dal pavimento |
| guardia `MockLLM` | scatta (`get_llm()` → `MockLLM`) | **inerte** (`agent.py:81` passa `LazyLLM`) | «guasto» al posto di «dipendenza mancante» |

---

## ① La promessa dei due secondi

`verimem/cli.py:1159` @`a99c0b54` — *«Store one fact through the full moat — the 2-second quickstart.»* (**cerca il testo, non la riga**: era `:1155` alle 15:04 di oggi)

```
  --help (il pavimento)         2.03– 2.08 s   giudicato 0/3
  remember SENZA --source       2.26– 2.51 s   giudicato 0/3   <- i 2 secondi li RISPETTA
  remember CON  --source       16.13–16.76 s   giudicato 3/3   <- è il moat
  ─────────────────────────────────────────────────────────────
  il moat costa   A−B = 13.97 s        il resto del comando  B−C = 0.35 s
```

**I due secondi li ottieni esattamente quando non ottieni il moat**: le due metà della
stessa frase si escludono. E **non è avvio a freddo** — tre giri di fila danno
17,8 / 16,8 / 16,9 s.

**Dove vanno i 14 secondi**, quattro scritture nello stesso processo:

```
  scrittura 1  15.00 s   scrittura 2  0.39 s   scrittura 3  0.41 s   scrittura 4  0.36 s
```

> 📌 **I numeri assoluti ballano fra un giro e l'altro, il rapporto no.** Rilanciando lo
> stesso banco 40 minuti dopo, dalla sua nuova posizione: **13,57 s** poi 0,22 · 0,23 ·
> 0,21. Chi lo rifà e ottiene altre cifre **non mi ha contraddetta**: la misura è
> «la prima costa due ordini di grandezza più delle altre», non «costa 15,00».

⇒ **Il giudizio costa 0,4 s. I 14 sono il caricamento**, pagato una volta per processo —
e la CLI apre un processo a ogni comando. **La promessa è raggiungibile**: il lavoro vero
sta dentro i due secondi. Manca un pezzo di impianto, non è una promessa assurda.

⇒ La causa è alla riga: `local_grounding.py:658` usa il daemon caldo **solo se**
`_delegate_only()`. A/B, `judged=True` da entrambe le parti:

```
  A  senza  (chi installa, via CLI)   17.15 s · 16.16 s   score 99.710 · 99.630
  B  con DELEGATE_ONLY=1 (MCP)         5.01 s ·  4.57 s   score 99.708 · 99.714
```

⚠️ **Nemmeno B rispetta i due secondi**: il meglio ottenibile è 4,6.

### La frase che nasce mettendo insieme due metà misurate da persone diverse

```
  misurato da ws2   remember CON --source e CON il modello    16,4 s   judged 3/3
  misurato da ws2   remember SENZA --source                    2,4 s   judged 0/3
  misurato da ws5   con local_ce_available() = False, un claim FALSO che la sua
                    fonte smentisce viene AMMESSO, status model_claim, grounding None
```

⇒ 🔑 **I due secondi promessi si ottengono in tutte e sole le configurazioni in cui il
prodotto non verifica.** Chi non ha una source non ha niente da giudicare; chi non ha il
modello ha un giudizio che non gira. **Nel solo caso in cui la promessa centrale del
prodotto è mantenuta, il numero sull'aiuto è sbagliato di un fattore otto.**

⚠️ **Le due metà hanno autori diversi e regimi diversi**: la terza riga è di ws5, non
l'ho rifatta. La metto qui perché la conclusione non regge senza di lei — e perché una
sintesi che non dichiara di chi sono i pezzi è il modo di far sparire una fonte.

---

## ② L'astensione non copre «stessa domanda, altra entità»

`hippo_trust_report` promette *«an EXPLICIT abstention with its reason instead of a guess»*.
Otto domande, **nessuna** con risposta nel corpus, verdetto letto dal campo `abstained`:

```
  A  ATTRIBUTO ASSENTE                    3 si astiene su 3   ✅
     colore · stipendio · proprietario
  B  ENTITÀ SCAMBIATA                     0 si astiene su 5   🔴
     Bologna  → consegna «…di ANCONA…»        Ferrari  → consegna «…ROSSI…»
     K-88     → consegna «…K-77…»             SN-9990  → consegna «…SN-1180…»
     2019     → consegna «…12 marzo 2024»
```

**Separazione perfetta, cinque tipi di entità** (città, persona, codice, matricola, anno).
⇒ Il pavimento di rilevanza è uno **scalare** contro un problema di **identità**, e
`trust_report.py:189` lo spiega da sé: *«the bi-encoder is ANISOTROPIC — every query
cosine-matches something ~0.8»*. **Nessun valore della soglia separa questa classe**:
alzandola cadono prima le risposte vere. *(«Alzare la soglia» è già fra le strade
falsificate: rendeva muta la mappa dell'ignoranza.)*

⚠️ **La forma del danno è la peggiore**: non risponde «non lo so» e non risponde a caso —
consegna un fatto **vero**, con `grounding_score` alto, **che parla di un'altra cosa**.

### La cura esiste già, ed era spenta

`trust_report.py:240` — *«sufficiency closes the residual the CE cannot see — a fact
on-topic (+1.01 measured) that names the **right subject in the wrong role**»*.

**È la definizione esatta di questa classe.** E la mia stessa misura lo diceva:

```json
  "verify": { "ce_gate": "ran",  "sufficiency": "unreadable" }
```

⇒ Lo strato progettato per prenderla **non ha girato**, perché la macchina non ha un
provider LLM. **Non serve costruire una cura: serve accendere quella che c'è.**

📌 **Esperimento aperto e decisivo, non eseguito**: con un LLM iniettato, quante delle 5
si astengono? Due esiti entrambi utili — se si astengono, il read è curato senza toccare
codice; se no, serve l'asse delle entità che ws1 stima **nuovo** sul lato lettura
(«al write manca un risolutore su un asse che c'è; al read manca l'asse»).
`ollama` è installato su questa macchina ma spento.

---

## ③ Una guardia che controlla il nome della classe

```python
  trust_report.py:251   if llm is not None and type(llm).__name__ == "MockLLM":
                            sufficiency_status = "no_provider"
```

Il commento sopra dichiara lo scopo: dire `unreadable` *«farebbe sembrare un guasto ciò
che è una DIPENDENZA MANCANTE»*. Ma `mcp_server.py:8075` passa `a.wake.llm`, e
`agent.py:81` lo costruisce come **`LazyLLM`** — un involucro. **La guardia confronta un
nome e la porta le passa un altro oggetto**: funziona sull'SDK, è inerte sulla porta MCP.

### Misurato, non più solo letto — A/B nella stessa esecuzione

Il primo referto diceva: *«`unreadable` alla porta è misurato; che la causa sia
`LazyLLM` è letto in tre file»*. Un limite dichiarato è un debito, non
un'assicurazione — e appena l'ho usato come base per la tabella delle guardie di
ws4 sono andata a saldarlo:

```
  A  get_llm()  (ciò che passa l'SDK)   type=MockLLM   sufficiency='no_provider'   ✅ scatta
  B  LazyLLM()  (ciò che passa l'MCP)   type=LazyLLM   sufficiency='unreadable'    🔴 non scatta
```

**Stesso processo, stesso store, stessa query: l'unica differenza è la classe
dell'involucro.** Essendo un A/B nella stessa esecuzione è immune alla regola dei due
SHA. Banco: `banchi-ws2/la_guardia_scatta_o_no.py`.

⇒ 🔑 **Questa guardia non è né «viva» né «ridondante»: è VIVA SU UNA PORTA E INERTE
SULL'ALTRA.** Un banco che ne prova una sola la classifica in una delle due categorie
consuete — e sbaglia in entrambe le direzioni. Il criterio che le separa è una domanda
in più: **«da quante porte si arriva a questa riga, e ci arriva lo stesso oggetto?»**

---

## Cosa REGGE — e per il rilascio conta più dei tre difetti

```
  ✅  il moat ferma un claim che la sua fonte smentisce, su ENTRAMBE le porte,
      quando il giudice è disponibile — 8 celle su 8, prima scrittura inclusa
  ✅  quando NON ce la fa lo DICHIARA: grounding_score null · campo `moat`
      («this is NOT a pass») · avviso `L4-skipped` — e la recall restituisce []
  ✅  16 comandi provati da utente, ZERO rotture funzionali
      (--help · save --asserted-at · trust --verified-by · facts retirement-log
       [--counts] · index · search-docs · gateway keys create · gateway backup
       · status · health · tiers · airgap · doctor · import · airgap --live
       · facts undo)
  ✅  `facts undo <op_id>` mantiene «the lost fact comes back» ALLA LETTERA:
      scritto A, scritto B che lo supersede (controllo: A risulta SUPERSEDUTO),
      `facts undo 5b1fb307f5f145b5` → «restored: fact_id=feda4c4e43fb», EXIT=0,
      e nel db **entrambi i fatti sono VIVO**. È il percorso di recupero, e per
      un rilascio conta più di una funzione nuova.
  ✅  `airgap --live` PROVA quello che dichiara, su installazione predefinita:
      «ZERO EGRESS ✓ · socket.connect observed: 2 · non-loopback egress: 0», EXIT=0.
      La predizione con cui ci sono andata — «senza le pin offline la libreria HF
      farà un controllo di rete» — è FALSIFICATA. È il tipo di promessa che regge
      davanti a un analista ostile, perché si verifica da sola con un comando.
  ✅  il contratto di `doctor` regge: 2 avvisi, zero ✗ → rc=1, come promette l'--help
  ✅  `import` è consent-first ALLA LETTERA: su un export vero (1 conversazione,
      2 messaggi) risponde «1 conversations found (format: chatgpt) — nothing
      imported yet», elenca come importare, e il corpus resta a **0 fatti**
```

> 📌 **`import` era un buco dichiarato nella prima stesura**: l'avevo provato solo con
> un file inesistente e contato fra i miei errori, non fra le prove. Chiuso alle 16:45
> con `banchi-ws2/prova_import.py`. **Un comando "escluso" e un comando "provato e
> passato" non sono la stessa riga di un referto.**

⇒ **Un analista ostile non può dire «afferma di verificare e non verifica».**
Può dire: *«dice due secondi e ne mette diciassette»*, e *«la descrizione del tool
promette astensione, il parametro la restringe agli attributi assenti, e nel mezzo c'è
una classe dove risponde con l'evidenza sbagliata»*. **Avrebbe ragione su tutte e tre.**

---

## Il costo di questo documento: dieci righelli miei rotti

```
  1  isolamento a memoria        2 variabili su 3 → il PRODOTTO me l'ha detto (RuntimeWarning)
  2  `-k` invece di `--k`        rc=2 su 4 celle: sembrava un difetto grave
  3  parola distintiva da split  pescava «di» → NON TROVATO ovunque
  4  contatore PASS/WARN/FAIL    doctor usa ✓ e ! → «contratto rotto» FALSO
  5  backtick in un heredoc      ha mangiato una riga di un messaggio
  6  il daemon nella HOME        ha fatto dichiarare SANO un buco vero        ← il peggiore
  7  due stati per tre           «ammesso» ≠ «ammesso come verificato»
  8  il comando `trust`          non è il tool `hippo_trust_report`
  9  il NOME del campo           `"abstained"` matchava in OGNI risposta
 10  stderr non drenato          il server si bloccava a ~64 KB → sembrava un difetto suo
```

🔑 **Cinque facevano vedere difetti inesistenti; uno ha fatto dichiarare sano un buco
vero.** A smascherarli è stata ogni volta **la popolazione di controllo** — accendere di
proposito ciò che dovrebbe cambiare il numero. Se non cambia, non ho misurato il prodotto.

🔑 **E un righello che perde verso il VERDE non somiglia a un errore: somiglia a una buona
notizia, e nessuno la contesta.**

---

## Come si rifà

I banchi stanno **accanto a questo file**, in `docs/stato-reale/banchi-ws2/`. Ci stanno
perché la prima versione di questa sezione puntava allo scratchpad della sessione, che
domani non esiste più: **un documento che rimanda a file che spariscono non è
riproducibile, è un aneddoto con delle note.**

`<venv>` è la radice di un ambiente con `verimem` installato **da wheel** — non il repo:
il punto di ogni banco è misurare ciò che riceve chi installa.

```bash
python docs/stato-reale/banchi-ws2/dove_vanno_i_17_secondi.py <venv>          # ① le tre celle C/B/A
python docs/stato-reale/banchi-ws2/la_variabile_che_non_ha.py <venv>          # ① A/B su DELEGATE_ONLY
python docs/stato-reale/banchi-ws2/i_14_secondi_sono_il_caricamento.py <venv> # ① 4 scritture, 1 processo
python docs/stato-reale/banchi-ws2/quanto_e_largo_il_buco.py <venv>           # ② porta MCP — il righello buono
python docs/stato-reale/banchi-ws2/banco_astensione_entita.py                 # ② via API: serve il pavimento
python docs/stato-reale/banchi-ws2/lo_dice_o_tace.py <venv>                   # il degrado è dichiarato?
python docs/stato-reale/banchi-ws2/prova_generale.py <venv>                   # le 11 promesse del README
```

⚠️ **Nessuno può diventare un test della suite**: `tests/conftest.py:122` sostituisce
l'embedder con uno stub SHA-256 su **ogni** test, e queste misure passano tutte da un
coseno. **Sotto pytest misurerebbero lo stub.** Vanno eseguiti FUORI da pytest.

⚠️ **`quanto_e_largo_il_buco.py` drena `stderr` con un thread apposta.** Non è una
finezza: senza, il server si blocca dopo ~64 KB di log e il banco restituisce 3 risposte
su 14 — e sembra un difetto del prodotto. È il righello n° 10 della lista qui sopra.
