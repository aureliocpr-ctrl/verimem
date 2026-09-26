# I runbook dei tre percorsi — come si leggono, e cosa NON sono

`2026-09-12`. Questi file dicono **come** si percorre un percorso d'uso:
comandi esatti, ricevuta attesa riga per riga, tempo atteso.

**Non ridefiniscono i percorsi.** Cosa sia un percorso, quale sia il suo criterio
di arrivo e se sia stato eseguito o supportato sta in
`docs/stato-reale/PERCORSI-UTENTE.md`, e quella resta l'unica pagina che lo dice.
Qui si esegue; lì si decide se si è arrivati.

---

## ⚠️ LA REGOLA DI QUESTI FILE: ogni riga dichiara DA DOVE VIENE

Un runbook che non distingue ciò che è stato **visto** da ciò che è stato
**dedotto leggendo il codice** è peggio di nessun runbook: chi esegue trova una
differenza e non sa se ha davanti un difetto del prodotto o l'invenzione di chi
ha scritto la pagina. Quindi ogni comando e ogni ricevuta porta un marchio:

| | significato |
|---|---|
| ✅ | **misurato**: c'è un output reale dietro, e la pagina dice dove |
| 📖 | **letto dal codice**: derivato dal sorgente, **mai eseguito** |
| ❓ | **da riempire**: lo compila chi esegue, la prima volta |

**Chi esegue converte le 📖 in ✅ o apre un ticket.** Una 📖 che sopravvive a tre
esecuzioni senza diventare ✅ è una riga che nessuno ha guardato.

> Chi ha scritto questi file **non ha eseguito niente**: erano ordini, e la
> macchina era sotto la soglia di memoria. È la ragione per cui il marchio
> esiste.

---

## ⚠️ IL PASSO 0 VALE PER TUTTI E TRE, e non è il venv

**Un venv pulito NON basta.** L'ambiente della shell da cui si lancia porta
variabili che cambiano il comportamento del prodotto: chi non le toglie misura
l'ambiente di chi lo ha preceduto e lo attribuisce al prodotto.

✅ **Misurato**, e non è un timore teorico: nella misura del 06/09 del percorso
«da zero in dieci minuti» le variabili sporche **erano nove**, fra cui due che
puntavano allo store di un'altra sessione e una che spegne il giudizio locale.
Un altro caso l'08/09: quattro test rossi attribuiti al prodotto erano una sola
variabile ereditata.

🔑 **La trappola nota si evita; la trappola nuova si evita solo togliendo la
classe.** Quindi il passo 0 non elenca le variabili da togliere una per una: le
toglie **tutte** quelle del prodotto, e poi **verifica** che siano andate.

```bash
# togli l'intera classe, non i nomi che ti ricordi
for v in $(env | grep -oE '^(VERIMEM|ENGRAM|HIPPO)_[A-Z0-9_]*'); do unset "$v"; done

# il controllo che deve stampare ZERO righe — se ne stampa una, fermati
env | grep -E '^(VERIMEM|ENGRAM|HIPPO)_' || echo "ambiente pulito"
```

✅ **RIEMPITO ALL'ESECUZIONE — e il numero è di nuovo NOVE.** Nel giro del 13/09,
su una shell diversa e a sei giorni di distanza, il ciclo ha tolto **nove**
variabili: le stesse tre famiglie, fra cui due che puntano a uno store altrui e
una che spegne il giudizio locale. **Due misure indipendenti, stesso numero**:
non è un caso di quel giorno, è quanto l'ambiente della squadra sporca di
default.

---

## ⚠️ LA TERZA VARIABILE: pulire l'ambiente NON basta se poi lo imposti tardi

C'è una trappola che il passo 0 **non** chiude, e va detta qui perché non ha
niente a che vedere con lo sporco ereditato:

```
RuntimeWarning: il log eventi scrive in <casa>/.verimem/events.jsonl mentre la
data dir in uso è <altrove>: i fatti e la loro telemetria stanno in due posti
diversi. Succede quando HIPPO_DATA_DIR è impostata DOPO l'import di verimem
(EVENT_LOG_PATH si fissa all'import).
```

⇒ **Il percorso del log eventi si congela al momento dell'import.** Se scegli la
cartella dei dati dopo — dentro uno script, in un test, in un notebook — i fatti
finiscono in un posto e la loro telemetria in un altro, **e il prodotto te lo
dice**: quel `RuntimeWarning` esiste apposta.

🔑 **Due modi giusti, nessun terzo**: imposta la cartella dei dati **prima**
dell'import, oppure dichiara esplicitamente `ENGRAM_EVENT_LOG` se la vuoi
davvero altrove. ⚠️ E **isolare la cartella dei dati non isola il log**: è la
stessa trappola vista dall'altro lato, ed è stata misurata due volte.

---

## Come si riporta un'esecuzione

Chi esegue posta, per ogni passo: **il comando com'è stato battuto**, l'output
**incollato** (non riassunto), il **tempo** e l'**exit code**. Un passo senza
exit code non è eseguito: è raccontato.

⚠️ Se un comando non esiste, o esce diverso da quanto scritto qui, **non
aggiustare la pagina in silenzio**: è esattamente il difetto che una guida può
avere, ed è già capitato (una guida insegnava un comando che il prodotto non ha
mai avuto). Aprire un ticket vale più che correggere la riga.

---

## I tre file

| file | percorso | in `PERCORSI-UTENTE.md` |
|---|---|---|
| `01-da-zero-a-un-fatto-verificato.md` | da zero, dieci minuti | U-C |
| `02-un-agente-che-lavora-un-ora.md` | l'agente che lavora | U-A |
| `03-due-istanze-sullo-stesso-store.md` | due istanze, uno store | U-B |
| `04-una-risposta-che-cita-la-fonte.md` | rispondere mostrando su cosa ci si regge | — |
| `05-numeri-con-unita.md` | misure: la cifra senza unità non è un dato | — |

I due in fondo sono nati il 18/09 e **non** hanno una lettera: la pagina dei
percorsi ne descrive tre, questi sono i due campi d'uso che nessuno dei tre
copriva. Chi riconcilia le due liste tolga questa nota.
