# Da zero a un fatto verificato — runbook

Percorso **U-C** di `docs/stato-reale/PERCORSI-UTENTE.md` (definizione, criterio
di arrivo e stato stanno lì). Qui: i comandi, la ricevuta attesa, il tempo.

**Regime**: pacchetto installato da PyPI in un venv nuovo. Non dal repo.
**Legenda dei marchi**: `00-COME-SI-LEGGE.md`. ✅ misurato · 📖 letto dal codice ·
❓ da riempire.

**Criterio di arrivo** (dalla pagina dei percorsi): un fatto scritto **con la sua
fonte**, giudicato, e ritrovato — in meno di dieci minuti da un ambiente vuoto.

> ⚠️ **Prima di tutto esegui il passo 0 di `00-COME-SI-LEGGE.md`** (togliere le
> variabili del prodotto). Senza, questo percorso misura l'ambiente di chi ti ha
> preceduto.

---

## I sei passi, con i tempi già misurati

✅ **Misurati il 06/09 su un ambiente ripulito**, totale **357 s = 5,9 minuti**,
dentro i dieci. I tempi qui sotto sono quelli; il tuo scarto è il dato nuovo.

| # | passo | tempo atteso ✅ | il tuo ❓ |
|---|---|---|---|
| 0 | creare il venv | 7,5 s | |
| 1 | `pip install verimem` | 280,8 s | |
| 2 | `verimem warmup` | 28,3 s | |
| 3 | `verimem doctor` | 7,8 s · **exit=1** | |
| 4 | il quickstart | 16,3 s | |
| 5 | una scrittura tua + richiamo | 16,2 s | |

🔑 **L'ottanta per cento del tempo è `pip install`.** Se il totale sfora i dieci
minuti, guarda prima la rete: non è il prodotto.

---

## 0 · Il venv

```bash
python -m venv .venv-verimem
. .venv-verimem/bin/activate        # Windows: .venv-verimem\Scripts\activate
```

## 1 · L'installazione

```bash
pip install verimem
```

📖 **Atteso**: l'ultima riga nomina il pacchetto e la versione installata.
❓ **Scrivi quale versione ti è arrivata**: il resto della pagina è stato scritto
guardando una `0.7.x`, e una versione diversa può cambiare le ricevute.

## 2 · Il riscaldamento

```bash
verimem warmup
```

📖 Scarica e apre il modello del giudice locale. È il passo che rende giudicata
**la prima** scrittura invece di ammetterla al buio: saltarlo non rompe niente,
ma sposta il costo sul primo `remember` con fonte.

## 3 · La diagnosi

```bash
verimem doctor
```

⚠️ ✅ **Esce `1` anche quando il riscaldamento è riuscito** (misurato sul
pacchetto 0.7.6, 06/09). **Non è un tuo errore e non è un fallimento del
percorso**: è un difetto noto dell'exit code, che non discrimina fra «manca
qualcosa di grave» e «manca qualcosa di opzionale».

❓ **Incolla le righe che il doctor stampa sul giudice e sulle soglie.** Servono:
la pagina che dichiara le soglie ne nomina **due costanti** (40 e 80), mentre un
modello calibrato ne porta **una terza** — il 12/09 in CI valeva `99.64`. Sapere
quale delle tre ti dichiara il doctor è il dato che manca a tutti.

## 4 · Il quickstart

Il quickstart della documentazione, senza modifiche.

📖 Il pezzo che conta è la coppia di scritture sulla stessa fonte: una sostenuta
dal testo e una no. La seconda **non deve** tornare come verità.

✅ **La ricevuta attesa sulla seconda**, misurata il 06/09:

```
status=quarantined · quarantined_by=moat · grounding=0.69
```

⚠️ **Guarda lo `status`, non l'assenza del testo.** Una ricerca che rende zero
risultati soddisfa qualunque controllo che cerchi «la falsità non c'è» — anche
se a mancare è l'intero store. Un `0 risultati` non è una prova: lo `status` sì.

## 5 · La scrittura tua

```bash
verimem save "<una frase su un fatto tuo>" \
  --topic <un/tuo/argomento> --lineage-to auto \
  --source "<il testo che sostiene quella frase>"
verimem recall "<qualche parola di quella frase>"
```

✅ **La ricevuta quando la fonte sostiene la frase** (forma vista più volte):

```
admitted id=<12 hex> topic='<il tuo argomento>' narrative
  grounded 99.8 — scored as supported by the source
  chained -> <12 hex>
```

✅ **E quando non la sostiene** — provalo di proposito, è il percorso che conta:
metti nella frase un numero o un codice che la fonte **non** contiene.

```
stored QUARANTINED — L4.1: un numero che la fonte non dice non e' un numero
verificato: correggi il valore, oppure passa la fonte che lo contiene
```

🔑 **La cura è arricchire la fonte, non impoverire la frase.** Se togli il numero
per far passare la scrittura, hai salvato un fatto più povero e il gate ha vinto
contro di te invece che per te.

⚠️ 📖 **`--source` costa**: fa girare il giudice. Su una macchina fredda la prima
scrittura con fonte può prendere minuti, non secondi — ✅ misurato **303 s contro
3,7 s** senza fonte, dal pacchetto sotto la porta degli agenti il 04/09. Se hai
fatto il passo 2, il grosso è già pagato.

---

## Sei arrivato quando

1. un fatto **tuo** è `admitted` con un `grounded` che il comando stampa;
2. un fatto che la fonte **non** sostiene è `quarantined`, e lo `status` lo dice;
3. `verimem recall` con parole tue rende il primo e **non** il secondo;
4. il cronometro dice meno di dieci minuti.

❓ **Se una delle quattro non è vera, il percorso non è arrivato** — e vale più
un post che lo dice di una pagina aggiustata perché torni.
