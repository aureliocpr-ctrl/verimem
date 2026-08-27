# ⑦ Come verimem gestisce la memoria — il percorso di SCRITTURA

> ⏱️ **NOTA DATATA — 2026-08-27, ws7. Misura `main` a `544d27bd`, cioè 771 commit fa.**
> Non è datato perché sbagli: **è fra i meglio fatti della cartella** — dichiara SHA, istante e i comandi per rifare le misure, che è esattamente la forma che serve. È datato perché il **bersaglio è mobile**: `git rev-list --count 544d27bd..origin/main` dà **771**.
> ⚠️ **Non ho rimisurato il contenuto e non affermo che sia caduto**: dico dove sta. I comandi per rifarlo sono in fondo al documento, ed è il modo giusto di chiuderlo.
> 🪞 E una nota sul mio censimento: fino a stasera avevo classificato questo file come «senza SHA», perché il mio righello cercava lo SHA **in backtick** e qui sta in un **blocco intestato** (`SHA:` `DATA:` `COMANDI:`). Falso negativo mio — il documento faceva la cosa giusta e il mio criterio non la vedeva.

    SHA:      ws3/gate-precision @ 544d27bd
    ISTANTE:  2026-08-08 12:45–12:55  (i conteggi cambiano nel tempo: vedi nota in fondo)
    COMANDI:  in fondo, copiabili — ogni riga di questo documento è stata ESEGUITA
    VERDETTO: **FUNZIONA**, con tre limiti reali e due domande aperte (in fondo)

Scritto per Aurelio. Niente sigle senza spiegazione.

---

## 1. Che cosa succede, in concreto, quando scrivi un fatto

Un fatto non viene «salvato». Passa da tre stadi, e in ognuno può essere fermato.

**Stadio 1 — il controllo delle parole.** Costa zero, non chiama nessun modello, e
guarda solo *come è scritta* la frase. Ferma gli auto-elogi: «ho implementato X e
funziona», «è pronto per la produzione», «è sicuro». Sono 20 rilevatori
(`L1.0`…`L1.19`) e questo è il motivo per cui esistono: un agente che scrive nella
propria memoria «ho finito e funziona» sta scrivendo un desiderio, non un fatto.

**Stadio 2 — il giudice (nel codice si chiama *moat*).** Confronta il fatto con la
fonte che gli hai dato e produce un voto da 0 a 100. **Gira solo se passi una
fonte.** Senza fonte non c'è niente da confrontare: il fatto entra come
*dichiarazione non verificata*, ed è una scelta dichiarata, non un difetto.

**Stadio 3 — i controlli sul contenuto.** Guardano i dettagli: i numeri del fatto
sono davvero nella fonte? c'è una negazione che ribalta il senso? esiste già un
fatto che dice il contrario? Qui vive `L4.1`, il controllo che ha il ruolo più
delicato di tutto il prodotto (vedi §3).

Alla fine il fatto è **ammesso**, oppure **messo in quarantena** — cioè conservato
ma tenuto fuori dalle risposte.

---

## 2. Il banco: sei fatti scritti, cosa è successo davvero

Store isolato, niente tocca il corpus di casa. Il codice è in fondo.

| cosa ho scritto | fermato da | esito | voto del giudice |
|---|---|---|---|
| «Ho implementato il modulo di export e **funziona perfettamente in produzione**» — senza fonte | `L1.10` | 🔴 quarantena | mai chiamato |
| lo stesso, con una fonte che parla d'altro | `L1.10` + grounding | 🔴 quarantena | **0,2** |
| «L'ordine 77 conteneva **40 pezzi**» (i 40 non sono nella fonte) | `L4.1` | 🔴 quarantena | **95,8** |
| «Il magazzino di Verona contiene 480 pallet» + inventario che lo dice | — | ✅ ammesso | 98,2 |
| «Il magazzino di Trento contiene 90 pallet» — senza fonte | — | ✅ ammesso | **nessuno** |
| «Il magazzino di Verona contiene **300** pallet» + inventario di aprile | — | ✅ ammesso, e **ritira il fatto di marzo** | 97,8 |

**Scritti 6 → serviti 2.** E le quattro perdite sono tutte corrette: tre erano
affermazioni non sostenute, la quarta è il dato di marzo sostituito da quello di
aprile. È il prodotto che fa il suo mestiere.

---

## 3. 🔑 La riga più importante di tutto il documento

> «L'ordine 77 conteneva 40 pezzi» — **il giudice l'ha approvata a 95,8** e il
> controllo sui numeri l'ha fermata lo stesso.

Il numero 40 non compare nella fonte: è inventato. Il giudice, che valuta se il
senso generale della frase è coerente col documento, non se ne accorge — perché
*il senso* è coerente: si parla davvero dell'ordine 77.

⇒ **Il giudice da solo non basta, ed è la ragione per cui questo prodotto è diverso
da un motore di ricerca semantico.** Un sistema che si fidasse solo del punteggio
avrebbe accettato quel fatto a 95,8 e te l'avrebbe restituito come verificato.

⚠️ Ed è anche il motivo per cui `L4.1` **non si può alzare né abbassare a piacere**:
è l'unico che vede quel caso, e ieri l'abbiamo curato due volte perché sbagliava in
entrambe le direzioni (§6).

---

## 4. I numeri veri del corpus di casa

    8.999   fatti scritti da quando esiste lo store
    6.425   DAVVERO SERVITI — cioè che tornano indietro quando interroghi   (71,4%)
    1.828   ritirati perché sostituiti da un aggiornamento
      746   in quarantena e mai ritirati: NON tornano indietro, e nessuno lo vede
    ─────
    2.574   non arrivano all'utente                                        (28,6%)

⚠️ **Attenzione a come si legge il 28,6%.** Non è «il prodotto perde un quarto della
memoria»: la maggior parte di quei ritiri è corretta, come nel banco sopra. Il
**quanto** sia corretta non lo sappiamo con precisione, ed è la prima domanda
aperta (§7).

E fra i 6.425 che l'utente riceve davvero:

    2.146   hanno un voto del giudice
    4.279   NON ce l'hanno — sono stati scritti senza fonte   (67%)

⇒ **Due terzi della memoria di casa non è mai stata verificata da nessuno.** Non è
un guasto: è la conseguenza di come l'abbiamo usata noi, scrivendo spesso senza
passare una fonte. Ma un utente che guarda «7.000 fatti» crede di avere 7.000 cose
verificate, e ne ha 2.146.

---

## 5. Cosa funziona, verificato

| capacità | esito |
|---|---|
| fermare gli auto-elogi senza chiamare un modello | ✅ `L1.10` scatta, costo zero |
| bocciare un fatto che la fonte non sostiene | ✅ voto 0,2 |
| **prendere un numero inventato che il giudice approva** | ✅ `L4.1`, il caso di §3 |
| far sostituire il dato vecchio dal nuovo | ✅ verificato: il fatto di marzo risulta ritirato dal fatto di aprile |
| ricostruire la storia di un dato | ✅ `history()` restituisce la catena completa, **e la stessa da qualunque anello** — sia partendo dal fatto attuale sia da quello vecchio |
| conservare il fatto quarantinato invece di cancellarlo | ✅ resta nel database, recuperabile |

---

## 6. I tre limiti reali

**① La fonte non viene conservata.** Passi un documento, il prodotto lo usa per
giudicare, e poi ne tiene solo un'impronta (`source_signature: sha256:7146fe19…`).

    ⇒ puoi sapere che due fatti vengono dalla STESSA fonte
    ⇒ NON puoi più sapere COSA diceva quella fonte
    ⇒ domani, davanti a un fatto con voto 98, non puoi rivedere su cosa è stato dato

Per un prodotto che si chiama «memoria verificata» questo è il limite che pesa di
più: la verifica c'è, la **prova** della verifica no.

**② Il fatto in quarantena è muto, e nessuno te lo dice.** I 746 fatti quarantinati
non tornano nelle risposte, e chi interroga non riceve nessun segnale del tipo
«c'era qualcosa ma l'ho trattenuto». Chi ha scritto quel fatto crede di averlo
salvato.

**③ Senza fonte il giudice non gira — ed è giusto, ma non è evidente.** Il fatto
entra e sembra salvato come tutti gli altri. Solo guardando il campo del voto
(vuoto) si capisce che nessuno l'ha controllato.

---

## 7. Le due domande aperte, che non ho risolto

**① Dei 2.574 fatti che non arrivano all'utente, quanti sono persi giustamente?**
Nel banco erano 4 su 4 corretti, ma sono casi che ho scritto io per farli fallire.
Sul corpus vero non è misurato. È la differenza fra «il prodotto è severo» e «il
prodotto mangia i dati», e finché non è misurata **non possiamo dire quale delle
due sia**.

**② `L4.1` sbaglia in entrambe le direzioni, e le due cure di ieri lo dimostrano.**
Ieri ho curato due difetti opposti dello stesso controllo: bocciava fatti veri
(perché non vedeva i numeri scritti come `grad.3`) e lasciava passare invenzioni
(perché non vedeva i numeri di quattro cifre). Sono corretti entrambi, ma il fatto
che il *medesimo* controllo sbagliasse nei due sensi dice che il criterio è ancora
fragile.

---

## 8. Come rifare tutto questo

```bash
# i numeri del corpus (il conto ufficiale del repo)
python scripts/quanti_fatti_sono_davvero_serviti.py "C:/Users/aurel/.engram"

# il banco dei sei fatti, su store isolato
python - <<'PY'
import os, tempfile, sqlite3
d = tempfile.mkdtemp(); os.environ["HIPPO_DATA_DIR"] = os.environ["ENGRAM_DATA_DIR"] = d
from verimem.client import Client
c = Client()
c.add("Ho implementato il modulo di export e funziona perfettamente in produzione.", topic="b")
c.add("L'ordine 77 conteneva 40 pezzi.", topic="b",
      source="Verbale: e' stato consegnato l'ordine 77. Ha partecipato Bianchi.")
c.add("Il magazzino di Verona contiene 480 pallet.", topic="b",
      source="Inventario 2026-03-01: magazzino Verona, 480 pallet a scaffale.")
c.add("Il magazzino di Verona contiene 300 pallet.", topic="b",
      source="Inventario 2026-04-01: magazzino Verona, 300 pallet a scaffale.")
cx = sqlite3.connect(str(c.semantic.db_path))
for r in cx.execute("SELECT id,status,round(coalesce(grounding_score,-1),1),"
                    "coalesce(superseded_by,'-'),substr(proposition,1,44) FROM facts"):
    print(r)
PY
```

⏱️ **Sull'istante della misura**: i conteggi del §4 sono delle 12:45 dell'8 agosto.
Il corpus cresce mentre lavoriamo — ieri quattro istanze hanno misurato lo stesso
numero ottenendo quattro valori diversi, tutti corretti, solo presi in momenti
diversi. Chi rifà i conti troverà numeri leggermente più alti: quello che deve
coincidere sono le **proporzioni**, non le cifre assolute.
