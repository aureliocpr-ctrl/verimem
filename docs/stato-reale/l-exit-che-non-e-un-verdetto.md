# L'`EXIT` che non è un verdetto: `suite_a_fette.py` propaga il codice di terminazione del SO

*ws3 «Galileo», 30/08 12:25. Nasce dallo spegnimento del PC di ieri sera, che ha
prodotto la prova migliore che potessi chiedere.*

## Il fatto

Ieri sera alle 22:16 ho lanciato `scripts/suite_a_fette.py --fette 3`. Alle
~22:28 il PC si è spento. Stamattina il log diceva:

```
=== 3 fette in 11.9 min ===
  fetta 0  EXIT=1073807364  (nessun riepilogo)
  fetta 1  EXIT=1073807364  (nessun riepilogo)
  fetta 2  EXIT=1073807364  (nessun riepilogo)

EXIT=1073807364
```

`1073807364` = **`0x40010004`** = **`DBG_TERMINATE_PROCESS`**: il codice con cui
Windows chiude un processo terminato dall'esterno. **Non è un fallimento dei
test: è la firma dello spegnimento.**

⚠️ Alle 22:26 — due minuti prima della morte — le tre fette erano al **9%, 15%,
10%**. La riga «*3 fette in **11.9 min***» **dichiara un completamento che non
c'è stato**.

## Il difetto NON è che l'informazione manchi

`scripts/suite_a_fette.py:88-104`:

```python
coda = [r for r in log.read_text(...).splitlines()
        if "passed" in r or "failed" in r or "error" in r]
esiti.append((i, rc, coda[-1] if coda else "(nessun riepilogo)"))
...
peggio = max(peggio, rc)
print(f"\nEXIT={peggio}")
return peggio
```

**Lo script SA**: quando pytest non ha lasciato una riga di riepilogo, scrive
`(nessun riepilogo)`. L'informazione è **presente e corretta**.

🔑 **Il difetto è DOVE sta.** L'ultima riga — `EXIT={peggio}` — è quella che si
legge, ed è quella che lo script **`return`a come proprio exit code**. Quella
riga **non porta la qualificazione**. E `max(peggio, rc)` **propaga il codice di
terminazione del sistema operativo come se fosse un verdetto di test**.

⇒ Chi legge l'ultima riga vede `EXIT=1073807364` e conclude **«il codice è
rotto»**. Chi legge tre righe più su vede «nessun riepilogo» e capisce. **La
riga più autorevole è la meno informata.**

## Perché conta ora

Ieri il gruppo ha adottato la **REGOLA-VERDE**: *nessuno scrive «funziona» senza
un `EXIT=` letto dal file*. Applicata **alla lettera** a questo log, produce il
verdetto opposto al vero: c'è un `EXIT=`, quindi «ho un verdetto», quindi «il
codice fallisce». **Una regola nata per impedire un falso «funziona» avrebbe
prodotto un falso «non funziona».**

📌 **Ho proposto e @lead-audit ha adottato la v3**: serve un **`EXIT=`
accompagnato da una riga di riepilogo pytest**. *Senza riepilogo, l'`EXIT` non è
un verdetto: è la firma di **come è morto** il processo.*

## La proposta (non applicata — lo script non è mio)

Una condizione sola, nel punto in cui lo script già ha il dato:

> se **una qualsiasi** fetta ha `(nessun riepilogo)`, l'ultima riga non deve
> essere `EXIT=<numero>` ma qualcosa come
> `NESSUN VERDETTO — <n> fette senza riepilogo (processo terminato?)`,
> e lo script dovrebbe restituire un codice **convenzionale** (es. 2) invece di
> propagare `rc` del SO.

⛔ **Non l'ho applicata**: `scripts/` non è nel mio perimetro e la scelta del
codice di ritorno tocca chi usa lo script in automazione. **Diagnosi e riga
pronte; la decisione è di chi lo mantiene.**

## Un secondo caso, più piccolo, dalla stessa riga

Il filtro `if "passed" in r or "failed" in r or "error" in r` **non riconosce**
la riga di pytest `no tests ran in 0.40s` — che è una **conclusione legittima**.
Una fetta che non raccoglie test verrebbe marcata `(nessun riepilogo)`, cioè
**letta come uccisa mentre è finita regolarmente**. ⚠️ **Non l'ho misurato**: è
lettura di codice, non un banco. Lo segnalo come tale.

## La classe, perché è la terza volta in due giorni

- Il campo `moat` **dice il vero** e la guida agli agenti promette di più.
- `quarantined_by` **era assente** e sembrava un difetto: era **eredità** (79,2%
  → 29,1% → **0,0%** spezzando per giorno).
- Qui l'`EXIT` **è corretto come numero** e falso come **verdetto**.

🔑 **In tutti e tre i casi il dato è giusto e la lettura è sbagliata, perché
manca accanto ciò che lo qualifica: la popolazione, la finestra, o il
riepilogo.** ⇒ *Prima di prendere un numero da un file, chiedersi cosa lo rende
un **verdetto** e non solo un **valore**.*

**Agent: Galileo**
