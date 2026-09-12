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

❓ **Da riempire alla prima esecuzione**: quante variabili ha tolto il ciclo.
Se sono più di zero, **scrivilo nel post**: è la misura di quanto l'ambiente
della squadra sporca le misure della squadra.

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
