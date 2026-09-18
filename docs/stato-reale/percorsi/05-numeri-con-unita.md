# Numeri con unità — runbook

**Chi è.** Un agente che raccoglie misure: metri quadri, euro, giorni, pezzi. Per
lui una cifra senza unità non è un dato, e **due unità diverse sulla stessa cifra
sono due fatti diversi**, non un aggiornamento.

Eseguito dal wheel `verimem 0.7.6` da PyPI, ambiente pulito, il 18/09.

## Il preambolo
Come in `04`: venv, `pip install verimem`, `verimem doctor`.

## I passi

### 1 · Scrivi una misura con la sua fonte
```bash
verimem save "Il capannone 12 misura 450 metri quadri." \
  --topic <un/tuo/argomento> \
  --source "Perizia del 2026-09-01: il capannone 12 misura 450 mq."
```
✅ `admitted`, `grounding_score=99.64`, `judged=True`.

### 2 · 🔴 Scrivi la STESSA CIFRA con un'UNITÀ DIVERSA, e la stessa fonte
```bash
verimem save "Il capannone 12 misura 450 metri cubi." \
  --topic <lo stesso argomento> \
  --source "Perizia del 2026-09-01: il capannone 12 misura 450 mq."
```

**Ricevuta attesa**: fermato, oppure ammesso **ma segnalato**, e la ricevuta
nomina la grandezza in conflitto.

🔴 **MISURATO IL 18/09 — non succede né l'uno né l'altro:**
```
admitted id=32e2cbc406a6 topic='prova/percorso1'
  L3-supersession — a newer same-source value supersedes a stored fact
     this write updates an earlier value from the same source; the older value
     is superseded.
  grounded 97.3 — scored as supported by the source
  superseded 63bb19bf7697 — no longer served by default recall
```

⇒ **Un cambio di UNITÀ a parità di cifra viene letto come un'evoluzione della
stessa fonte.** Il fatto giusto (`450 metri quadri`) viene **superato** da uno che
la fonte non sostiene, e il giudice gli dà **97.3**. Un metro cubo non è un metro
quadro: non è un aggiornamento, è un'altra grandezza.

### 3 · Guarda che cosa serve adesso il richiamo
```bash
verimem recall "<le parole della misura>"
```
🔴 **Misurato**: `- Il capannone 12 misura 450 metri cubi. [0.87] moat 97.3`
La memoria serve come **corrente** il valore con l'unità sbagliata.

### 4 · Chiedi il verdetto di fiducia sulla stessa affermazione
```bash
verimem trust "<l'affermazione>" --source "<la stessa fonte>"
```
🔴 **Misurato**:
```
Anti-confab trust check   TRUSTED ✓
  checked:     L1 lexical screens, L4 moat
  the moat judged the source at 97.3
```

🔑 **La riga `checked:` è il meccanismo, ed è il motivo per cui questo percorso
esiste**: hanno girato **lo screen lessicale e il moat**. Il controllo che
confronta le **quantità** non compare fra quelli eseguiti — e senza di lui
«450 mq» e «450 m³» sono lo stesso numero con parole intorno.

## Tre modi di cadere
1. **Il comando non esiste** → la pagina è sbagliata.
2. **La ricevuta è diversa dall'attesa** → difetto del prodotto. **È il caso dei
   passi 2, 3 e 4, ed è aperto su tre comandi.**
3. **È un rosso già noto** → si annota e si prosegue.

## Sei arrivato quando
1. la scrittura del passo 2 è **fermata o segnalata**;
2. la ricevuta **nomina la grandezza** in conflitto, non solo «contraddizione»;
3. il richiamo serve **il valore con l'unità giusta**;
4. le tre porte si comportano **uguale**.

Al 18/09: **(1), (2) e (3) sono rossi** sulla riga di comando, **(4) non è
misurato**. È il percorso messo peggio dei quattro, ed è quello su cui il
prodotto ha più prove interne: una ragione in più per provarlo **alla porta**.
