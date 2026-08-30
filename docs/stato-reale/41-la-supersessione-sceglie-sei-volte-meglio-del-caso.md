# La supersessione sceglie sei volte meglio del caso, e il danno è sceso di due terzi

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus.*

Questo pezzo è una buona notizia, ed è la prima della serata. Le altre quattro
hanno trovato cose che non andavano; questa misura una cura che abbiamo adottato
e verifica che abbia funzionato — con il controllo che serve a non prendere per
effetto quello che è solo un cambio di abitudini.

## La lezione esisteva già, e ho usato il suo righello

Prima di misurare ho cercato in memoria, ed è saltato fuori il fatto
`cb4043575870`, «la memoria si mangia i fatti veri». Non ho riletto solo la
conclusione: ho letto la sua **source**, perché è lì che sta il metodo.

    PERIMETRO DICHIARATO: coppie (ritirato non quarantinato, sostituto) = 579
    coppie SCRITTE DA NOI: 321
    0.00-0.15 parlano d'ALTRO   55 (17.1%)  stesso topic  98.2%
    0.15-0.50 intermedi         55 (17.1%)  stesso topic  96.4%
    0.50-0.80 simili            13 ( 4.0%)  stesso topic 100.0%
    0.80-1.01 duplicati        198 (61.7%)  stesso topic  65.2%
    mediana jaccard 1.000

Il righello è questo: per ogni coppia **(fatto ritirato, fatto che l'ha
sostituito)** si calcola la **similarità di Jaccard** fra le due proposizioni.
Sotto **0,15** i due testi parlano d'altro — è il ritiro sbagliato, un fratello
cancellato da un fatto che non lo aggiorna affatto. Sopra **0,80** sono
duplicati, cioè un aggiornamento legittimo.

## Il perimetro, prima dei numeri

La prima misura che ho fatto era su **918 coppie**, tutte. Dava «non duplicati
62,7%» contro il 34,2% di allora, e sembrava un peggioramento netto. **Non lo
era: stavo confrontando popolazioni diverse.** Il fatto originale dichiarava
«coppie SCRITTE DA NOI: 321 su 579», io avevo preso anche quelle scritte dagli
automatismi.

«Scritte da noi» si traduce esattamente in `writer_role='user'` (che nel corpus
coincide con `writer_principal='cli:local'`, 576 coppie ritirate). È il terzo
inciampo della stessa famiglia in una sera — dopo il 40,3% che mescolava due ere
e i 54 che ne contenevano 11 di un'altra popolazione. **La differenza è che
stavolta me ne sono accorto prima di scriverlo.**

## Il risultato, sul perimetro giusto

Coppie scritte da noi, misurate alle **21:44:55 del 30/08**:

| | coppie | «parlano d'ALTRO» | mediana jaccard |
|---|---|---|---|
| prima del 25/08 | 202 | **66 = 32,7%** | 0,224 |
| dal 25/08 | 246 | **25 = 10,2%** | 0,375 |

**I ritiri che cancellano un fatto che dice altro sono passati dal 32,7% al
10,2%: un terzo del valore precedente.** E la mediana sale da 0,224 a 0,375:
quando ritiriamo, il fatto ritirato assomiglia di più a quello che lo sostituisce.

Una precisazione che mi corregge una lettura intermedia: «stesso topic» è
**100,0% in entrambi i periodi** sulle nostre scritture. Il ribaltamento
cross-topic che avevo visto nella prima misura veniva interamente dai fatti
**non** nostri (`agent_inference` 1312, `system_hook` 380). Sulle nostre, la
supersessione è sempre stata confinata al topic.

## Il controllo, senza il quale il numero non vale

C'è un'obiezione ovvia: se dal 25/08 scriviamo fatti più simili fra loro — più
banchi, temi più stretti — allora il Jaccard sale da solo, e il miglioramento è
un'illusione contabile.

Si controlla misurando la **somiglianza di fondo**: coppie di fatti nostri, vivi,
dello stesso topic, **mai coinvolti in una supersessione** (campionate al
massimo 40 per topic, seed fisso).

| | fatti | coppie campionate | mediana jaccard | sotto 0,15 |
|---|---|---|---|---|
| prima del 25/08 | 7.066 | 990 | 0,091 | **62,6%** |
| dal 25/08 | 2.099 | 1.092 | 0,077 | **63,4%** |

**Il fondo non è cambiato** — anzi scende leggermente. Quindi il miglioramento
nelle supersessioni non viene da come scriviamo: viene da quali fatti vengono
ritirati.

## Il numero che dice quanto bene sceglie

Il fondo serve anche a un'altra cosa, ed è la misura più interessante del pezzo.

Se una supersessione scegliesse **a caso** un fratello dentro lo stesso topic,
colpirebbe un fatto che «parla d'altro» nel **63%** dei casi — perché è quella
la somiglianza tipica fra due fatti dello stesso topic.

Le supersessioni reali, dal 25/08, ne colpiscono il **10,2%**.

> **Sceglie sei volte meglio del caso.** Prima del 25/08 ne sceglieva **due**
> (32,7% contro 62,6%).

Detto altrimenti: il meccanismo non è «cieco con un tasso di errore», è un
meccanismo che **discrimina**, e la cura del 25/08 ne ha triplicato la
selettività.

## Quello che resta, e che non va nascosto

- **Venticinque coppie**, dal 25/08, sono ancora ritiri in cui il fatto
  cancellato diceva altro. Il tasso è basso, il numero non è zero.
- **La cura non è stata applicata integralmente.** «Un topic per misura», nella
  sua forma piena, produce **zero** supersessioni — era il rubinetto chiuso
  misurato allora (90 fatti in 36 ore, nessuna supersessione). Dal 25/08 di
  supersessioni nostre ce ne sono **246**: la disciplina è migliorata, non è
  diventata la regola.
- Il fondo è **campionato**, non esaustivo: 40 coppie per topic al massimo.
- **Zero** supersessioni coinvolgono un fatto-MASTER del consolidamento, da
  nessuno dei due lati. Non è un filtro che ho dimenticato: è che i MASTER non
  ritirano e non vengono ritirati.

## Per chi riprende

- Il righello è `docs/stato-reale/banchi/ws6-la-supersessione-oggi.py` (sola
  lettura). **Va eseguito su `writer_role='user'`**: sul corpus intero mescola
  le nostre scritture con quelle degli automatismi e il confronto storico salta.
- **Quello che non ho misurato**: *perché* il 25/08 sia stato lo spartiacque.
  Ho confrontato due finestre attorno a quella data perché è la data della cura
  registrata in memoria, non perché l'abbia individuata dai dati. Una
  regressione sul giorno esatto direbbe se il cambiamento è stato netto o
  graduale.

---

**Verifica**: store `~/.engram/semantic/semantic.db` in `mode=ro`, sole `SELECT`.
Istante dichiarato in linea (21:44:55 del 30/08). Righello ripreso dalla source
del fatto `cb4043575870`, non riscritto.
